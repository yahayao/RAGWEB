ALTER TABLE chat_users
    ADD COLUMN IF NOT EXISTS auth_token_hash VARCHAR(64);

CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_users_auth_token_hash
    ON chat_users(auth_token_hash);
