import sys
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, create_engine, event
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))


@compiles(BigInteger, "sqlite")
def compile_bigint_as_integer_for_sqlite_test_tables(type_, compiler, **kwargs):
    return "INTEGER"

# Isolate application tests from local developer credentials and .env values.
TEST_JWT_SECRET_KEY = "unit-test-only-signing-key-with-at-least-32-bytes"
os.environ["JWT_SECRET_KEY"] = TEST_JWT_SECRET_KEY

import main
from auth import JWT_ALGORITHM, JWT_SECRET_KEY, create_access_token, hash_password, utcnow_naive, validate_jwt_secret
from database.models import Base, Region, Role, Tender, TenderDocument, TenderSource, User
from database.models.auth_session import AuthSession
from database.models.coordinator import Coordinator
from tender_scraper.storage.db_mapper import map_punjab_tender
from tender_scraper.storage.mysql_storage import persist_tender


class MutableClock:
    def __init__(self):
        self.now = utcnow_naive()

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)


class AuthSessionTests(unittest.TestCase):
    password = "Correct-Password-42"

    def test_jwt_secret_configuration_validation(self):
        invalid_secrets = (
            None,
            "",
            "   ",
            "CHANGE_THIS_SECRET",
            "change-this-development-secret",
            "REPLACE_WITH_LOCALLY_GENERATED_RANDOM_VALUE",
            "x" * 31,
        )
        for secret in invalid_secrets:
            with self.subTest(secret_type="missing" if secret is None else "unsafe"):
                with self.assertRaises(RuntimeError):
                    validate_jwt_secret(secret)

        self.assertEqual(validate_jwt_secret(TEST_JWT_SECRET_KEY), TEST_JWT_SECRET_KEY)
        self.assertEqual(JWT_SECRET_KEY, TEST_JWT_SECRET_KEY)

    def setUp(self):
        self.db_tempdir = tempfile.TemporaryDirectory()
        db_path = Path(self.db_tempdir.name) / "test.sqlite"
        self.engine = create_engine(
            f"sqlite+pysqlite:///{db_path.as_posix()}",
            connect_args={"check_same_thread": False, "timeout": 10},
        )
        Base.metadata.create_all(self.engine)
        self.TestSession = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        def populate_database_timestamps(session, flush_context, instances):
            now = utcnow_naive()
            for instance in session.new:
                if hasattr(instance, "created_at") and instance.created_at is None:
                    instance.created_at = now
                if hasattr(instance, "updated_at") and instance.updated_at is None:
                    instance.updated_at = now

        self.timestamp_listener = populate_database_timestamps
        event.listen(self.TestSession, "before_flush", self.timestamp_listener)
        self.clock = MutableClock()
        db = self.TestSession()
        role = Role(id=1, name="ADMIN", created_at=self.clock.now, updated_at=self.clock.now)
        db.add(role)
        db.add(User(
            id=1,
            username="session_test_user",
            password_hash=hash_password(self.password),
            name="Session Test User",
            email=None,
            role_id=1,
            is_active=True,
            created_at=self.clock.now,
            updated_at=self.clock.now,
        ))
        db.commit()
        db.close()

        def override_get_db():
            session = self.TestSession()
            try:
                yield session
            finally:
                session.close()

        self.override_get_db = override_get_db
        self.original_overrides = dict(main.app.dependency_overrides)
        main.app.dependency_overrides[main.get_db] = override_get_db
        self.clock_patch = patch.object(main, "utcnow_naive", side_effect=lambda: self.clock.now)
        self.clock_patch.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(self.original_overrides)
        self.clock_patch.stop()
        event.remove(self.TestSession, "before_flush", self.timestamp_listener)
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()
        self.db_tempdir.cleanup()

    def login(self):
        response = self.client.post("/api/auth/login", json={"username": "session_test_user", "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        return data, {"Authorization": f"Bearer {data['access_token']}"}

    def session_row(self, session_id):
        db = self.TestSession()
        try:
            return db.query(AuthSession).filter_by(session_id=session_id).one()
        finally:
            db.close()

    def test_login_creates_session_and_issues_sid_without_changing_jwt_lifetime(self):
        data, _ = self.login()
        payload = main.decode_access_token(data["access_token"])
        self.assertTrue(payload.get("sid"))
        self.assertEqual(payload["exp"] - payload["iat"], 3600)
        row = self.session_row(payload["sid"])
        self.assertEqual(row.user_id, 1)
        self.assertEqual(row.created_at, self.clock.now)
        self.assertEqual(row.last_activity_at, self.clock.now)

    def test_protected_request_expires_at_five_minutes_without_activity(self):
        _, headers = self.login()
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        self.clock.advance(299)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        self.clock.advance(1)
        response = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "session_idle_expired")

    def test_protected_requests_do_not_extend_activity(self):
        data, headers = self.login()
        session_id = main.decode_access_token(data["access_token"])["sid"]
        original_activity = self.session_row(session_id).last_activity_at
        self.clock.advance(240)
        for _ in range(3):
            self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        self.assertEqual(self.session_row(session_id).last_activity_at, original_activity)
        self.clock.advance(60)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)

    def test_valid_activity_uses_server_clock_and_resets_idle_window(self):
        data, headers = self.login()
        session_id = main.decode_access_token(data["access_token"])["sid"]
        self.clock.advance(240)
        rejected_timestamp = self.client.post(
            "/api/auth/activity", headers=headers, json={"timestamp": "2000-01-01T00:00:00Z"}
        )
        self.assertEqual(rejected_timestamp.status_code, 422)
        response = self.client.post("/api/auth/activity", headers=headers, json={})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.session_row(session_id).last_activity_at, self.clock.now)
        self.clock.advance(299)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        self.clock.advance(1)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)

    def test_activity_after_expiry_cannot_revive_session(self):
        data, headers = self.login()
        session_id = main.decode_access_token(data["access_token"])["sid"]
        self.clock.advance(300)
        response = self.client.post("/api/auth/activity", headers=headers, json={})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "session_idle_expired")
        self.assertEqual(self.session_row(session_id).last_activity_at, self.clock.now - timedelta(seconds=300))

    def test_reauthentication_replaces_session_and_invalidates_old_token(self):
        old_data, old_headers = self.login()
        old_sid = main.decode_access_token(old_data["access_token"])["sid"]
        self.clock.advance(300)
        response = self.client.post("/api/auth/reauthenticate", headers=old_headers, json={"password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        replacement = response.json()
        new_sid = main.decode_access_token(replacement["access_token"])["sid"]
        self.assertNotEqual(old_sid, new_sid)
        self.assertEqual(replacement["user"]["username"], "session_test_user")
        self.assertEqual(self.session_row(old_sid).revocation_reason, "reauthenticated")
        self.assertEqual(self.client.get("/api/auth/me", headers=old_headers).json()["detail"]["code"], "session_revoked")
        self.assertEqual(self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {replacement['access_token']}"}).status_code, 200)

    def test_incorrect_password_does_not_reset_idle_timeout(self):
        data, headers = self.login()
        session_id = main.decode_access_token(data["access_token"])["sid"]
        self.clock.advance(300)
        response = self.client.post("/api/auth/reauthenticate", headers=headers, json={"password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "invalid_credentials")
        self.assertEqual(self.session_row(session_id).last_activity_at, self.clock.now - timedelta(seconds=300))
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)

    def test_expired_jwt_revoked_session_missing_sid_and_inactive_user_are_rejected(self):
        data, headers = self.login()
        payload = main.decode_access_token(data["access_token"])
        expired = dict(payload, exp=int((datetime.now(timezone.utc) - timedelta(seconds=5)).timestamp()))
        import jwt
        expired_token = jwt.encode(expired, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        expired_response = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        self.assertEqual(expired_response.status_code, 401)
        self.assertEqual(expired_response.json()["detail"]["code"], "token_expired")

        legacy = create_access_token(1, "session_test_user", "ADMIN", "legacy-unused")
        legacy_payload = main.decode_access_token(legacy)
        legacy_payload.pop("sid")
        legacy_token = jwt.encode(legacy_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        missing = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy_token}"})
        self.assertEqual(missing.status_code, 401)
        self.assertEqual(missing.json()["detail"]["code"], "session_required")

        sid = payload["sid"]
        db = self.TestSession()
        db.query(AuthSession).filter_by(session_id=sid).update({"revoked_at": self.clock.now, "revocation_reason": "test"})
        db.commit()
        revoked = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(revoked.status_code, 401)
        self.assertEqual(revoked.json()["detail"]["code"], "session_revoked")
        db.query(User).filter_by(id=1).update({"is_active": False})
        db.commit()
        db.close()
        inactive = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(inactive.status_code, 403)
        self.assertEqual(inactive.json()["detail"]["code"], "user_inactive")

    def test_roles_and_coordinator_region_dependency_remain_enforced(self):
        _, admin_headers = self.login()
        self.assertEqual(self.client.get("/api/admin/users", headers=admin_headers).status_code, 200)

        db = self.TestSession()
        coordinator_role = Role(id=2, name="COORDINATOR", created_at=self.clock.now, updated_at=self.clock.now)
        viewer_role = Role(id=3, name="VIEWER", created_at=self.clock.now, updated_at=self.clock.now)
        region = Region(id=1, name="Test Region", created_at=self.clock.now, updated_at=self.clock.now)
        coordinator_user = User(
            id=2, username="coord", password_hash=hash_password(self.password), name="Coordinator",
            email=None, role_id=2, is_active=True, created_at=self.clock.now, updated_at=self.clock.now,
        )
        viewer = User(
            id=3, username="viewer", password_hash=hash_password(self.password), name="Viewer",
            email=None, role_id=3, is_active=True, created_at=self.clock.now, updated_at=self.clock.now,
        )
        db.add_all([coordinator_role, viewer_role, region, coordinator_user, viewer])
        db.flush()
        db.add(Coordinator(id=1, user_id=2, region_id=1, created_at=self.clock.now, updated_at=self.clock.now))
        db.commit()
        coord_token = main._issue_session(db, coordinator_user)
        viewer_token = main._issue_session(db, viewer)
        db.commit()
        db.close()
        coord_headers = {"Authorization": f"Bearer {coord_token}"}
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        self.assertEqual(self.client.get("/api/admin/users", headers=coord_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/admin/users", headers=viewer_headers).status_code, 403)
        region_db = self.TestSession()
        try:
            self.assertEqual(main.get_coordinator_region(SimpleNamespace(id=2), region_db), 1)
        finally:
            region_db.close()

    def test_concurrent_reauthentication_only_replaces_session_once(self):
        data, headers = self.login()
        self.clock.advance(300)

        def try_reauth():
            with TestClient(main.app) as client:
                return client.post("/api/auth/reauthenticate", headers=headers, json={"password": self.password})

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: try_reauth(), range(2)))
        self.assertEqual(sorted(response.status_code for response in responses), [200, 401])
        old_use = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(old_use.status_code, 401)

    def test_concurrent_activity_cannot_keep_session_alive_after_reauthentication(self):
        _, headers = self.login()
        self.clock.advance(299)

        def activity():
            with TestClient(main.app) as client:
                return client.post("/api/auth/activity", headers=headers, json={})

        def reauth():
            with TestClient(main.app) as client:
                return client.post("/api/auth/reauthenticate", headers=headers, json={"password": self.password})

        with ThreadPoolExecutor(max_workers=2) as pool:
            activity_future = pool.submit(activity)
            reauth_future = pool.submit(reauth)
            activity_response = activity_future.result()
            reauth_response = reauth_future.result()
        self.assertIn(activity_response.status_code, (200, 401))
        self.assertEqual(reauth_response.status_code, 200, reauth_response.text)
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).json()["detail"]["code"], "session_revoked")

    def test_scraper_checkpoint_requires_admin_and_preserves_response_and_file_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / "checkpoint.json"
            expected = {
                "Federal PPRA": {"last_date": "2026-10-28", "last_run_at": "2026-10-28T12:34:56+05:00"},
                "Punjab PPRA": {"last_date": "2026-10-27", "last_run_at": "2026-10-27T12:34:56+05:00"},
            }
            checkpoint.write_text(json.dumps(expected), encoding="utf-8")
            _, admin_headers = self.login()

            no_auth = self.client.get("/api/admin/scraper/checkpoint")
            self.assertEqual(no_auth.status_code, 401)

            db = self.TestSession()
            viewer_role = Role(id=3, name="VIEWER", created_at=self.clock.now, updated_at=self.clock.now)
            viewer = User(
                id=3,
                username="checkpoint_viewer",
                password_hash=hash_password(self.password),
                name="Checkpoint Viewer",
                email=None,
                role_id=3,
                is_active=True,
                created_at=self.clock.now,
                updated_at=self.clock.now,
            )
            db.add_all([viewer_role, viewer])
            db.flush()
            viewer_token = main._issue_session(db, viewer)
            db.commit()
            db.close()
            viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

            with patch.object(main, "CHECKPOINT_FILE", checkpoint):
                forbidden = self.client.get("/api/admin/scraper/checkpoint", headers=viewer_headers)
                self.assertEqual(forbidden.status_code, 403)

                success = self.client.get("/api/admin/scraper/checkpoint", headers=admin_headers)
                self.assertEqual(success.status_code, 200)
                self.assertEqual(success.json(), expected)

                admin_sid = main.decode_access_token(admin_headers["Authorization"].split()[1])["sid"]
                db = self.TestSession()
                db.query(AuthSession).filter_by(session_id=admin_sid).update({
                    "revoked_at": self.clock.now,
                    "revocation_reason": "test",
                })
                db.commit()
                db.close()
                invalid_session = self.client.get("/api/admin/scraper/checkpoint", headers=admin_headers)
                self.assertEqual(invalid_session.status_code, 401)

                _, fresh_admin_headers = self.login()
                checkpoint.unlink()
                missing_unauthorized = self.client.get("/api/admin/scraper/checkpoint", headers=viewer_headers)
                self.assertEqual(missing_unauthorized.status_code, 403)
                missing_admin = self.client.get("/api/admin/scraper/checkpoint", headers=fresh_admin_headers)
                self.assertEqual(missing_admin.status_code, 404)

                checkpoint.write_text("not-json", encoding="utf-8")
                malformed = self.client.get("/api/admin/scraper/checkpoint", headers=fresh_admin_headers)
                self.assertEqual(malformed.status_code, 500)

    def test_scraper_import_requires_admin_and_preserves_portal_dispatch(self):
        db = self.TestSession()
        viewer_role = Role(id=2, name="VIEWER", created_at=self.clock.now, updated_at=self.clock.now)
        viewer = User(
            id=2,
            username="import_viewer",
            password_hash=hash_password(self.password),
            name="Import Viewer",
            email=None,
            role_id=2,
            is_active=True,
            created_at=self.clock.now,
            updated_at=self.clock.now,
        )
        db.add_all([viewer_role, viewer])
        db.flush()
        viewer_token = main._issue_session(db, viewer)
        db.commit()
        db.close()
        viewer_headers = {"Authorization": f"Bearer {viewer_token}"}
        _, admin_headers = self.login()

        with patch.object(main, "process_local_punjab_tenders") as punjab_processor, patch.object(
            main, "process_local_balochistan_tenders"
        ) as balochistan_processor:
            payload = {"portal": "Punjab PPRA", "tenders": [{}]}
            no_auth = self.client.post("/api/scraper/import", json=payload)
            self.assertEqual(no_auth.status_code, 401)

            invalid_token = self.client.post(
                "/api/scraper/import", json=payload, headers={"Authorization": "Bearer invalid-token"}
            )
            self.assertEqual(invalid_token.status_code, 401)

            forbidden = self.client.post("/api/scraper/import", json=payload, headers=viewer_headers)
            self.assertEqual(forbidden.status_code, 403)
            punjab_processor.assert_not_called()
            balochistan_processor.assert_not_called()

            punjab_result = {"success": True, "portal": "Punjab PPRA", "created": 1}
            punjab_processor.return_value = punjab_result
            imported_punjab = self.client.post("/api/scraper/import", json=payload, headers=admin_headers)
            self.assertEqual(imported_punjab.status_code, 200)
            self.assertEqual(imported_punjab.json(), punjab_result)
            punjab_processor.assert_called_once_with(tenders=[{}])
            balochistan_processor.assert_not_called()

            punjab_processor.reset_mock()
            balochistan_result = {"success": True, "portal": "Balochistan PPRA", "created": 2}
            balochistan_processor.return_value = balochistan_result
            imported_balochistan = self.client.post(
                "/api/scraper/import",
                json={"portal": "Balochistan PPRA", "tenders": [{}, {}]},
                headers=admin_headers,
            )
            self.assertEqual(imported_balochistan.status_code, 200)
            self.assertEqual(imported_balochistan.json(), balochistan_result)
            balochistan_processor.assert_called_once_with(tenders=[{}, {}])
            punjab_processor.assert_not_called()

            punjab_processor.reset_mock()
            balochistan_processor.reset_mock()
            unsupported = self.client.post(
                "/api/scraper/import", json={"portal": "Unknown PPRA", "tenders": []}, headers=admin_headers
            )
            self.assertEqual(unsupported.status_code, 400)
            punjab_processor.assert_not_called()
            balochistan_processor.assert_not_called()

    def test_retired_document_routes_are_not_registered(self):
        retired_routes = {
            ("/api/tenders/{jazzid}/document/download", "POST"),
            ("/api/tenders/{jazzid}/document", "GET"),
        }
        registered_routes = {
            (route.path, method)
            for route in main.app.routes
            for method in getattr(route, "methods", set())
        }
        self.assertTrue(retired_routes.isdisjoint(registered_routes))

    def test_manual_tender_listing_and_detail_keep_external_document_url_and_metadata(self):
        document_url = "https://procurement.example.test/tender-document.pdf"
        db = self.TestSession()
        db.add_all([
            Region(id=1, name="Central", created_at=self.clock.now, updated_at=self.clock.now),
            TenderSource(id=1, name="Punjab PPRA", created_at=self.clock.now, updated_at=self.clock.now),
        ])
        db.commit()
        db.close()
        _, headers = self.login()

        created = self.client.post("/api/tenders", headers=headers, json={
            "source_id": 1,
            "region_id": 1,
            "tender_name": "Manual document URL test",
            "organization": "Test Organization",
            "city": "Lahore",
            "closed_date": "2026-11-10T00:00:00",
            "source_detail_url": "https://procurement.example.test/tender/123",
            "primary_document_url": document_url,
        })
        self.assertEqual(created.status_code, 201, created.text)
        jazzid = created.json()["jazzid"]

        listed = self.client.get("/api/tenders", headers=headers)
        self.assertEqual(listed.status_code, 200, listed.text)
        listed_tender = next(item for item in listed.json()["items"] if item["jazzid"] == jazzid)
        self.assertEqual(listed_tender["primary_document_url"], document_url)

        detail = self.client.get(f"/api/tenders/{jazzid}", headers=headers)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["primary_document_url"], document_url)
        self.assertEqual(detail.json()["document"], {"available": False, "status": "PENDING"})

        db = self.TestSession()
        try:
            tender = db.query(Tender).filter_by(jazzid=jazzid).one()
            document = db.query(TenderDocument).filter_by(tender_jazzid=jazzid).one()
            self.assertEqual(tender.primary_document_url, document_url)
            self.assertEqual(document.source_url, document_url)
            self.assertEqual(document.document_name, "tender_document.pdf")
            self.assertEqual(document.download_status, "PENDING")
            self.assertIsNone(document.local_path)
        finally:
            db.close()

    def test_scraper_mapping_and_persistence_keep_external_document_url_and_metadata(self):
        document_url = "https://procurement.example.test/punjab/bidding.pdf"
        db = self.TestSession()
        db.add(TenderSource(id=1, name="Punjab PPRA", created_at=self.clock.now, updated_at=self.clock.now))
        db.add(Region(id=1, name="Central", created_at=self.clock.now, updated_at=self.clock.now))
        db.commit()

        raw_tender = {
            "tender_details": "Scraped document URL test",
            "organization_details": "Test Organization",
            "bidding_document_url": document_url,
        }
        relevance = {"keyword_score": 0, "matched_keywords": [], "matched_capabilities": []}
        mapped = map_punjab_tender(raw_tender, {"relevance": relevance})
        result = persist_tender(db, mapped_tender=mapped, relevance=relevance)
        tender_id = result["tender"].jazzid
        db.expire_all()

        tender = db.query(Tender).filter_by(jazzid=tender_id).one()
        document = db.query(TenderDocument).filter_by(tender_jazzid=tender_id).one()
        self.assertEqual(tender.primary_document_url, document_url)
        self.assertEqual(document.source_url, document_url)
        self.assertEqual(document.document_name, "Bidding Document")
        self.assertEqual(document.download_status, "PENDING")
        self.assertIsNone(document.local_path)
        db.close()

    def test_tender_deletion_keeps_safe_local_file_cleanup(self):
        db = self.TestSession()
        db.add_all([
            Region(id=1, name="Central", created_at=self.clock.now, updated_at=self.clock.now),
            TenderSource(id=1, name="Punjab PPRA", created_at=self.clock.now, updated_at=self.clock.now),
        ])
        db.commit()
        db.close()
        _, headers = self.login()
        created = self.client.post("/api/tenders", headers=headers, json={
            "source_id": 1,
            "region_id": 1,
            "tender_name": "Delete cleanup test",
            "organization": "Test Organization",
            "city": "Lahore",
            "closed_date": "2026-11-10T00:00:00",
            "primary_document_url": "https://procurement.example.test/tender-document.pdf",
        })
        self.assertEqual(created.status_code, 201, created.text)
        jazzid = created.json()["jazzid"]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "data"
            documents_root = root / "documents"
            allowed_file = documents_root / "Punjab PPRA" / "tender.pdf"
            outside_file = Path(directory) / "outside.pdf"
            allowed_file.parent.mkdir(parents=True)
            allowed_file.write_bytes(b"in-root")
            outside_file.write_bytes(b"outside")

            db = self.TestSession()
            db.add_all([
                TenderDocument(
                    tender_jazzid=jazzid, document_type="PRIMARY", document_name="tender.pdf",
                    source_url="https://procurement.example.test/tender-document.pdf",
                    local_path="documents/Punjab PPRA/tender.pdf", download_status="DOWNLOADED",
                ),
                TenderDocument(
                    tender_jazzid=jazzid, document_type="ATTACHMENT", document_name="outside.pdf",
                    local_path="../outside.pdf", download_status="DOWNLOADED",
                ),
            ])
            db.commit()
            db.close()

            with patch.object(main, "DATA_DIR", root), patch.object(main, "DOCUMENTS_DIR", documents_root):
                response = self.client.delete(f"/api/tenders/{jazzid}", headers=headers)

            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse(allowed_file.exists())
            self.assertTrue(outside_file.exists())
            self.assertIn("documents/Punjab PPRA/tender.pdf", response.json()["documents_deleted"])
            self.assertIn("../outside.pdf", response.json()["documents_failed"])


if __name__ == "__main__":
    unittest.main()
