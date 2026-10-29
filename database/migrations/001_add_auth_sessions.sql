-- Apply to the JazzRadar database before deploying backend code that requires sid.
-- Existing access tokens intentionally have no auth_sessions row and will be rejected.
CREATE TABLE `auth_sessions` (
  `session_id` varchar(36) NOT NULL,
  `user_id` bigint(20) unsigned NOT NULL,
  `created_at` datetime NOT NULL,
  `last_activity_at` datetime NOT NULL,
  `revoked_at` datetime DEFAULT NULL,
  `revocation_reason` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`session_id`),
  KEY `ix_auth_sessions_user_revoked` (`user_id`, `revoked_at`),
  KEY `ix_auth_sessions_last_activity` (`last_activity_at`),
  CONSTRAINT `fk_auth_sessions_user`
    FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
