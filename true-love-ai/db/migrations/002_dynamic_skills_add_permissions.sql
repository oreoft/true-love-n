-- dynamic_skills 表：新增 permissions 列
-- 存储权限白名单 JSON 数组，如 ["wechat:admin123"] 或 ["lark:*"]
-- 为 NULL 时表示不限制（所有人可用）

ALTER TABLE dynamic_skills ADD COLUMN permissions TEXT;
