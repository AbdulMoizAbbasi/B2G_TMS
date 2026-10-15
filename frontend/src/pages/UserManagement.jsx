import { useCallback, useEffect, useState } from "react";
import { KeyRound, Pencil, Plus, RefreshCw, ShieldCheck, UserRound, UserRoundX } from "lucide-react";
import api from "../api";
import "./UserManagement.css";

const EMPTY_FORM = { username: "", name: "", email: "", role: "USER", region_id: "", password: "" };
const isActive = (user) => user.is_active ?? user.active ?? false;
const regionLabel = (user) => user.region_name ?? user.region?.name ?? user.region ?? "—";

function errorText(error, fallback) {
  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((item) => `${item.loc?.slice(-1)[0] ?? "Field"}: ${item.msg}`).join(" ");
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (!error.response) return "Unable to reach the server. Check your connection and try again.";
  return fallback;
}

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [resetUser, setResetUser] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const [actionId, setActionId] = useState(null);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/api/admin/users");
      setUsers(Array.isArray(response.data) ? response.data : response.data?.items ?? []);
    } catch (requestError) {
      setError(errorText(requestError, "Unable to load users."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(loadUsers);
    api.get("/api/regions").then((response) => { if (active) setRegions(Array.isArray(response.data) ? response.data : []); })
      .catch((requestError) => { if (active) setError(errorText(requestError, "Unable to load regions.")); });
    return () => { active = false; };
  }, [loadUsers]);

  const closeForm = () => { setFormOpen(false); setEditing(null); setForm(EMPTY_FORM); };
  const startCreate = () => { setEditing(null); setForm(EMPTY_FORM); setError(""); setNotice(""); setFormOpen(true); };
  const startEdit = (user) => {
    setEditing(user);
    setForm({ username: user.username ?? "", name: user.name ?? "", email: user.email ?? "", role: user.role ?? "USER", region_id: user.region_id == null ? "" : String(user.region_id), password: "" });
    setError(""); setNotice(""); setFormOpen(true);
  };

  const saveUser = async (event) => {
    event.preventDefault();
    setError(""); setNotice("");
    if (form.role === "COORDINATOR" && !form.region_id) {
      setError("Select a region for coordinator accounts.");
      return;
    }
    const payload = { username: form.username.trim(), name: form.name.trim(), email: form.email.trim(), role: form.role, region_id: form.role === "COORDINATOR" ? Number(form.region_id) : null };
    if (!editing) payload.password = form.password;
    setSaving(true);
    try {
      if (editing) await api.patch(`/api/admin/users/${editing.id}`, payload);
      else await api.post("/api/admin/users", payload);
      closeForm();
      setNotice(editing ? "User updated successfully." : "User created successfully.");
      await loadUsers();
    } catch (requestError) {
      setError(errorText(requestError, "Unable to save user."));
    } finally { setSaving(false); }
  };

  const toggleStatus = async (user) => {
    setActionId(user.id); setError(""); setNotice("");
    try {
      await api.patch(`/api/admin/users/${user.id}/status`, { is_active: !isActive(user) });
      setNotice(`${user.username} ${isActive(user) ? "deactivated" : "activated"}.`);
      await loadUsers();
    } catch (requestError) { setError(errorText(requestError, "Unable to update account status.")); }
    finally { setActionId(null); }
  };

  const resetPassword = async (event) => {
    event.preventDefault(); setError(""); setNotice(""); setActionId(resetUser.id);
    try {
      await api.post(`/api/admin/users/${resetUser.id}/reset-password`, { password: newPassword });
      setNotice(`Password reset for ${resetUser.username}.`);
      setResetUser(null); setNewPassword("");
    } catch (requestError) { setError(errorText(requestError, "Unable to reset password.")); }
    finally { setActionId(null); }
  };

  return <section className="user-management">
    <header className="user-management-header"><div><span className="user-management-eyebrow">ADMINISTRATION</span><h1>User Management</h1><p>Create accounts, manage assignments, and control access to Jazz Radar.</p></div><button className="um-primary-button" type="button" onClick={startCreate}><Plus size={17} />Add user</button></header>
    {error && <div className="um-alert um-alert-error" role="alert">{error}</div>}
    {notice && <div className="um-alert um-alert-success" role="status">{notice}</div>}
    <div className="um-table-card"><div className="um-table-heading"><div><h2>Portal users</h2><span>{users.length} accounts</span></div><button className="um-icon-button" type="button" onClick={loadUsers} disabled={loading} aria-label="Refresh users" title="Refresh users"><RefreshCw size={17} /></button></div>
      {loading ? <div className="um-empty-state">Loading users…</div> : users.length ? <div className="um-table-scroll"><table className="um-table"><thead><tr><th>User</th><th>Email</th><th>Role</th><th>Assigned region</th><th>Status</th><th><span className="um-sr-only">Actions</span></th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td><div className="um-user-cell"><span className="um-avatar"><UserRound size={17} /></span><span><strong>{user.username}</strong><small>{user.name || "—"}</small></span></div></td><td>{user.email || "—"}</td><td><span className="um-role"><ShieldCheck size={14} />{user.role}</span></td><td>{user.role === "COORDINATOR" ? regionLabel(user) : "—"}</td><td><span className={`um-status ${isActive(user) ? "is-active" : "is-inactive"}`}><i />{isActive(user) ? "Active" : "Inactive"}</span></td><td><div className="um-actions"><button type="button" className="um-action-button" onClick={() => startEdit(user)} title="Edit user" aria-label={`Edit ${user.username}`}><Pencil size={16} /></button><button type="button" className="um-action-button" onClick={() => { setResetUser(user); setNewPassword(""); setError(""); setNotice(""); }} title="Reset password" aria-label={`Reset password for ${user.username}`}><KeyRound size={16} /></button><button type="button" className="um-action-button" onClick={() => toggleStatus(user)} disabled={actionId === user.id} title={isActive(user) ? "Deactivate account" : "Activate account"} aria-label={`${isActive(user) ? "Deactivate" : "Activate"} ${user.username}`}>{isActive(user) ? <UserRoundX size={16} /> : <UserRound size={16} />}</button></div></td></tr>)}</tbody></table></div> : <div className="um-empty-state">No users found. Add a user to get started.</div>}
    </div>

    {formOpen && <div className="um-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) closeForm(); }}><section className="um-modal" role="dialog" aria-modal="true" aria-labelledby="um-form-title"><header><div><span className="user-management-eyebrow">ACCOUNT DETAILS</span><h2 id="um-form-title">{editing ? "Edit user" : "Create user"}</h2></div><button type="button" className="um-modal-close" onClick={closeForm} aria-label="Close">×</button></header><form onSubmit={saveUser}><div className="um-form-grid"><label>Username<input required autoComplete="off" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label><label>Full name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>Email<input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label><label>Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value, region_id: event.target.value === "COORDINATOR" ? form.region_id : "" })}><option value="USER">User</option><option value="COORDINATOR">Coordinator</option><option value="ADMIN">Admin</option></select></label>{form.role === "COORDINATOR" && <label className="um-full-width">Assigned region<select required value={form.region_id} onChange={(event) => setForm({ ...form, region_id: event.target.value })}><option value="">Select a region</option>{regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}</select></label>}{!editing && <label className="um-full-width">Temporary password<input required type="password" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>}</div><footer><button type="button" className="um-secondary-button" onClick={closeForm} disabled={saving}>Cancel</button><button type="submit" className="um-primary-button" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Create user"}</button></footer></form></section></div>}

    {resetUser && <div className="um-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !actionId) { setResetUser(null); setNewPassword(""); } }}><section className="um-modal um-reset-modal" role="dialog" aria-modal="true" aria-labelledby="um-reset-title"><header><div><span className="user-management-eyebrow">SECURITY</span><h2 id="um-reset-title">Reset password</h2></div><button type="button" className="um-modal-close" onClick={() => { setResetUser(null); setNewPassword(""); }} aria-label="Close">×</button></header><p>Set a new password for <strong>{resetUser.username}</strong>.</p><form onSubmit={resetPassword}><label>New password<input type="password" required minLength="8" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label><footer><button type="button" className="um-secondary-button" onClick={() => { setResetUser(null); setNewPassword(""); }}>Cancel</button><button className="um-primary-button" type="submit" disabled={actionId === resetUser.id}>{actionId === resetUser.id ? "Resetting…" : "Reset password"}</button></footer></form></section></div>}
  </section>;
}

export default UserManagement;
