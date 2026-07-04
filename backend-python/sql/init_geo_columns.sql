-- init_geo_columns.sql — 为 chat_users 表增加 MaxMind GeoLite2 地理位置字段
-- 可重复执行，不会重复添加已存在的列或索引
-- 在启动新代码前执行此 SQL

ALTER TABLE chat_users
    ADD COLUMN IF NOT EXISTS country_code varchar(2),
    ADD COLUMN IF NOT EXISTS country_name varchar(100),
    ADD COLUMN IF NOT EXISTS manual_geo boolean NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_chat_users_country_code
    ON chat_users (country_code);
