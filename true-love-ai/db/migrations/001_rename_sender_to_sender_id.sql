-- user_memory 表：将 sender 列重命名为 sender_id
-- SQLite 支持 RENAME COLUMN（3.25.0+），MySQL/PostgreSQL 同样支持

ALTER TABLE user_memory RENAME COLUMN sender TO sender_id;
