# Admin 后台定时提醒管理功能设计

**日期：** 2026-05-11  
**项目：** true-love-server  
**状态：** 已批准

---

## 背景

当前 admin 后台（`/admin`）有两个 Tab：监听列表管理（`📋 列表`）和 Loki 日志（`📝 日志`）。

用户通过 AI 对话可以设置定时提醒（`set_reminder` skill），提醒被存储在 APScheduler + SQLite 中，但管理员目前无法在后台可视化查看和管理所有待执行的提醒任务。

---

## 目标

在 admin 后台新增 `⏰ 提醒` Tab，实现：
- 查看所有待执行的定时提醒（不分 receiver，全量展示）
- 展示：接收者、提醒内容、触发时间（含时区转换）、平台
- 支持管理员手动删除任意提醒

---

## 架构

### 时区处理

- APScheduler 以 `timezone='UTC'` 初始化，`next_run_time` 存储并返回 UTC 时间
- 后端返回 ISO-8601 字符串（如 `2026-05-11T06:30:00+00:00`）
- 前端用 JavaScript `toLocaleString()` 按浏览器本地时区渲染，避免后端硬编码时区
- 同时展示本地时间和 UTC 偏移（如 `14:30:00` / `UTC+8`）

### 数据来源

每条 APScheduler job 的 `job.kwargs` 包含完整信息：
- `receiver`: 接收者 ID
- `content`: 提醒内容
- `at_user`: @的用户（可选）
- `platform`: 平台（wechat/lark）

过滤条件：`job.id.startswith("reminder_")` 且 `job.next_run_time` 不为 None。

---

## 后端变更（true-love-server）

### 新增接口：`routes.py`

**1. `GET /admin/reminder/list`**
- 无需 token（与现有 admin 接口一致）
- 返回所有待执行 reminder jobs
- 返回字段：`job_id`, `receiver`, `content`, `at_user`, `platform`, `next_run_time`（ISO UTC）

**2. `POST /admin/reminder/delete`**
- Body: `{ job_id: string }`
- 删除指定提醒，job 不存在时返回 404 错误

---

## 前端变更（true-love-server/static/）

### `api.js`
新增两个方法：
- `fetchReminderList()` → `GET /admin/reminder/list`
- `deleteReminder(jobId)` → `POST /admin/reminder/delete`

### 新增 `useReminderPage.js`
Composable，封装：
- `reminders`：提醒列表状态
- `loading`：加载状态
- `fetchReminders()`：拉取列表
- `deleteReminder(jobId)`：删除并刷新
- 时间格式化工具函数（UTC ISO → 本地时间字符串 + UTC偏移显示）

### `index.html`
1. Header 新增 `⏰ 提醒` Tab 按钮
2. 新增 reminder tab 视图：
   - 表头：接收者 / 内容 / 触发时间 / 平台 / 操作
   - 每行展示一条提醒，含删除按钮（带确认弹窗）
   - 空状态提示
   - 手动刷新按钮

### `app.js`
- 引入 `useReminderPage` composable
- Tab 切换逻辑：切换到 `reminders` Tab 时自动 fetch 列表
- spread reminder page 属性到模板

---

## UI 草图

```
[ 📋 列表 ] [ 📝 日志 ] [ ⏰ 提醒 ]

┌──────────────────────────────────────────────────────────┐
│  定时提醒 (3)                                  [刷新]    │
├──────────────────────────────────────────────────────────┤
│  接收者          内容           触发时间       平台  操作 │
├──────────────────────────────────────────────────────────┤
│  wx_abc123       关火           14:30 UTC+8   wechat [删] │
│  某某群          下午去开会     16:00 UTC+8   wechat [删] │
│  lark_user1      喝药           09:00 UTC+8   lark   [删] │
└──────────────────────────────────────────────────────────┘
```

---

## 文件变更清单

| 文件 | 变更类型 |
|------|----------|
| `src/true_love_server/api/routes.py` | 新增 2 个接口 |
| `static/js/api.js` | 新增 2 个 API 方法 |
| `static/js/useReminderPage.js` | 新增文件 |
| `static/index.html` | 新增 Tab 按钮 + 提醒视图 |
| `static/js/app.js` | 集成 reminder composable |

---

## 不在范围内

- 新建提醒（提醒通过 AI 对话创建，不在 admin 前台创建）
- 编辑提醒内容
- 历史已执行提醒记录
