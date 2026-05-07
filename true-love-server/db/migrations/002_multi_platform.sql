-- 多平台支持迁移
-- 手动执行，幂等（SQLite 不支持 IF NOT EXISTS on column，逐条执行忽略已存在错误即可）

ALTER TABLE group_messages ADD COLUMN platform VARCHAR(32) NOT NULL DEFAULT 'wechat';
ALTER TABLE group_messages ADD COLUMN sender_id VARCHAR(128) NOT NULL DEFAULT '';
ALTER TABLE group_messages ADD COLUMN sender_name VARCHAR(128) NOT NULL DEFAULT '';
ALTER TABLE group_messages ADD COLUMN chat_name VARCHAR(128) NOT NULL DEFAULT '';
-- 回填历史数据：sender_id / sender_name / chat_name 与现有字段保持一致
UPDATE group_messages SET sender_id = sender WHERE sender_id = '';
UPDATE group_messages SET sender_name = sender WHERE sender_name = '';
UPDATE group_messages SET chat_name = chat_id WHERE chat_name = '';

-- 新索引
CREATE INDEX IF NOT EXISTS idx_platform_chat ON group_messages (platform, chat_id);

-- 确认回填无空值后删除旧冗余列（执行前可先 SELECT COUNT(*) FROM group_messages WHERE sender_id = ''）
ALTER TABLE group_messages DROP COLUMN sender;