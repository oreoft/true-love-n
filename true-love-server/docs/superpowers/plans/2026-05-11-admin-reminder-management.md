# Admin 定时提醒管理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 admin 后台新增"⏰ 提醒"Tab，展示所有待执行的定时提醒并支持管理员删除。

**Architecture:** 后端在 `routes.py` 新增两个 `/admin/reminder/*` 接口，读取 APScheduler 的 job 列表；前端按现有 composable 模式新增 `useReminderPage.js`，在 `index.html` 中增加第三个 Tab。时区处理：后端返回 UTC ISO 字符串，前端用 `toLocaleString()` 按浏览器本地时区渲染。

**Tech Stack:** Python 3.12, FastAPI, APScheduler, Vue 3 (CDN, 无构建), vanilla JS

---

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `src/true_love_server/api/routes.py` | 修改：新增 2 个 admin reminder 接口 |
| `static/js/api.js` | 修改：新增 2 个 API 方法 |
| `static/js/useReminderPage.js` | 创建：提醒 Tab composable |
| `static/index.html` | 修改：新增 Tab 按钮 + 提醒视图 + 引入新 JS |
| `static/js/app.js` | 修改：集成 reminder composable，扩展 switchTab |

---

## Task 1: 后端 — 新增 `GET /admin/reminder/list` 接口

**Files:**
- Modify: `src/true_love_server/api/routes.py`

- [ ] **Step 1: 在 `routes.py` 末尾新增 reminder list 接口**

在 `routes.py` 文件末尾（第 459 行之后）追加以下代码：

```python
# ==================== Admin 定时提醒管理接口 ====================

@router.get("/admin/reminder/list")
async def list_reminders():
    """
    列出所有待执行的定时提醒任务（Admin 用，不按 receiver 过滤）

    Returns:
        - jobs: 提醒任务列表，每项包含 job_id, receiver, content, at_user, platform, next_run_time
    """
    from ..services.scheduler_service import scheduler

    jobs = scheduler.get_jobs()
    result = []
    for job in jobs:
        if not job.id.startswith("reminder_"):
            continue
        if not job.next_run_time:
            continue
        kwargs = job.kwargs or {}
        result.append({
            "job_id": job.id,
            "receiver": kwargs.get("receiver", ""),
            "content": kwargs.get("content", ""),
            "at_user": kwargs.get("at_user", ""),
            "platform": kwargs.get("platform", "wechat"),
            "next_run_time": job.next_run_time.isoformat(),
        })

    result.sort(key=lambda x: x["next_run_time"])
    LOG.info("admin/reminder/list: count=%d", len(result))
    return ApiResponse(data={"jobs": result, "total": len(result)})
```

- [ ] **Step 2: 验证接口可用**

启动服务后执行：
```bash
curl http://localhost:8000/admin/reminder/list
```
期望返回：
```json
{"code": 0, "data": {"jobs": [], "total": 0}, "message": ""}
```

---

## Task 2: 后端 — 新增 `POST /admin/reminder/delete` 接口

**Files:**
- Modify: `src/true_love_server/api/routes.py`

- [ ] **Step 1: 在 Task 1 新增代码之后继续追加 delete 接口**

```python
@router.post("/admin/reminder/delete")
async def admin_delete_reminder(request: dict):
    """
    Admin 删除指定提醒任务

    Body:
        - job_id: 要删除的任务 ID
    """
    from ..services.scheduler_service import scheduler

    job_id = request.get("job_id", "").strip()
    if not job_id:
        raise ValidationException("job_id 不能为空")

    job = scheduler.get_job(job_id)
    if not job:
        raise ValidationException(f"未找到提醒任务: {job_id}")

    scheduler.remove_job(job_id)
    LOG.info("admin/reminder/delete: job_id=%s", job_id)
    return ApiResponse(data={"job_id": job_id})
```

- [ ] **Step 2: 验证删除接口（用一个不存在的 job_id 测试错误路径）**

```bash
curl -X POST http://localhost:8000/admin/reminder/delete \
  -H "Content-Type: application/json" \
  -d '{"job_id": "reminder_fake_123"}'
```
期望返回 code 非 0，message 含"未找到提醒任务"。

- [ ] **Step 3: 提交后端变更**

```bash
cd /Users/oreoft/IdeaProjects/my/true-love-n/true-love-server
git add src/true_love_server/api/routes.py
git commit -m "feat: add admin reminder list and delete endpoints"
```

---

## Task 3: 前端 — 扩展 `api.js`

**Files:**
- Modify: `static/js/api.js`

- [ ] **Step 1: 在 `api.js` 的 `window.api` 对象末尾（`fetchLokiLogs` 之后）追加 reminder API 方法**

将文件末尾：
```js
    // Loki API
    fetchLokiLogs: (startMs, endMs, limit = 50, direction = 'backward') =>
        apiRequest(`/admin/loki/logs?start_ms=${startMs}&end_ms=${endMs}&limit=${limit}&direction=${direction}`)
};
```

改为：
```js
    // Loki API
    fetchLokiLogs: (startMs, endMs, limit = 50, direction = 'backward') =>
        apiRequest(`/admin/loki/logs?start_ms=${startMs}&end_ms=${endMs}&limit=${limit}&direction=${direction}`),

    // Reminder API
    fetchReminderList: () => apiRequest('/admin/reminder/list'),

    deleteReminder: (jobId) => apiRequest('/admin/reminder/delete', {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId })
    })
};
```

- [ ] **Step 2: 提交**

```bash
git add static/js/api.js
git commit -m "feat: add reminder API methods to api.js"
```

---

## Task 4: 前端 — 创建 `useReminderPage.js`

**Files:**
- Create: `static/js/useReminderPage.js`

- [ ] **Step 1: 创建文件**

```js
/**
 * 定时提醒管理页面 composable
 */

window.useReminderPage = function(showToast, showConfirm) {
    const { ref } = Vue;

    const reminders = ref([]);
    const loading = ref(false);
    const deletingItems = ref({});

    /**
     * 将 UTC ISO 字符串格式化为本地时间 + UTC 偏移显示
     * 例：2026-05-11T06:30:00+00:00 → { local: "14:30:00", offset: "UTC+8", full: "05-11 14:30:00" }
     */
    const formatTime = (isoStr) => {
        try {
            const d = new Date(isoStr);
            const offsetMin = -d.getTimezoneOffset();
            const sign = offsetMin >= 0 ? '+' : '-';
            const absH = Math.floor(Math.abs(offsetMin) / 60);
            const offsetLabel = `UTC${sign}${absH}`;

            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            const hh = String(d.getHours()).padStart(2, '0');
            const mi = String(d.getMinutes()).padStart(2, '0');
            const ss = String(d.getSeconds()).padStart(2, '0');

            return {
                full: `${mm}-${dd} ${hh}:${mi}:${ss}`,
                offset: offsetLabel
            };
        } catch (e) {
            return { full: isoStr, offset: '' };
        }
    };

    const fetchReminders = async () => {
        loading.value = true;
        try {
            const data = await api.fetchReminderList();
            reminders.value = (data.data?.jobs || []).map(job => ({
                ...job,
                _time: formatTime(job.next_run_time)
            }));
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            loading.value = false;
        }
    };

    const deleteReminder = (jobId, content) => {
        showConfirm(
            '删除提醒',
            `确定要删除提醒「${content || jobId}」吗？`,
            async () => {
                deletingItems.value[jobId] = true;
                try {
                    await api.deleteReminder(jobId);
                    showToast('提醒已删除', 'success');
                    await fetchReminders();
                } catch (error) {
                    showToast(error.message, 'error');
                } finally {
                    delete deletingItems.value[jobId];
                }
            }
        );
    };

    return {
        reminders,
        reminderLoading: loading,
        deletingItems,
        fetchReminders,
        deleteReminder
    };
};
```

- [ ] **Step 2: 提交**

```bash
git add static/js/useReminderPage.js
git commit -m "feat: add useReminderPage composable"
```

---

## Task 5: 前端 — 更新 `index.html`

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: 在 header 中追加第三个 Tab 按钮**

找到文件中以下代码段：
```html
                    <button 
                        :class="['btn', 'btn-sm', activeTab === 'logs' ? 'btn-primary' : 'btn-outline-light']"
                        @click="switchTab('logs')"
                    >
                        📝 日志
                    </button>
```

在其后追加：
```html
                    <button 
                        :class="['btn', 'btn-sm', activeTab === 'reminders' ? 'btn-primary' : 'btn-outline-light']"
                        @click="switchTab('reminders')"
                    >
                        ⏰ 提醒
                    </button>
```

- [ ] **Step 2: 在 Logs Page template 之后、Add Modal 之前插入提醒视图**

找到文件中：
```html
        <!-- Add Modal -->
```

在其前插入：
```html
        <!-- Reminders Page -->
        <template v-else-if="activeTab === 'reminders'">
            <div class="list-container">
                <div class="list-header">
                    <span class="list-title">定时提醒 ({{ reminders.length }})</span>
                    <button class="btn btn-outline btn-sm" @click="fetchReminders" :disabled="reminderLoading">
                        {{ reminderLoading ? '加载中...' : '刷新' }}
                    </button>
                </div>

                <div v-if="reminderLoading && reminders.length === 0" class="loading">
                    <div class="spinner"></div>
                    <p>加载中...</p>
                </div>

                <div v-else-if="reminders.length === 0 && !reminderLoading" class="empty-state">
                    <div class="empty-icon">⏰</div>
                    <p class="empty-text">暂无待执行的提醒任务</p>
                </div>

                <div v-else class="reminder-table-wrapper">
                    <table class="reminder-table">
                        <thead>
                            <tr>
                                <th>接收者</th>
                                <th>提醒内容</th>
                                <th>触发时间</th>
                                <th>平台</th>
                                <th>操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="job in reminders" :key="job.job_id">
                                <td class="reminder-receiver">{{ job.receiver }}</td>
                                <td class="reminder-content">{{ job.content }}</td>
                                <td class="reminder-time">
                                    <span class="time-local">{{ job._time.full }}</span>
                                    <span class="time-offset">{{ job._time.offset }}</span>
                                </td>
                                <td>
                                    <span :class="['platform-badge', job.platform]">{{ job.platform }}</span>
                                </td>
                                <td>
                                    <button
                                        class="btn btn-danger btn-sm"
                                        @click="deleteReminder(job.job_id, job.content)"
                                        :disabled="deletingItems[job.job_id]"
                                    >
                                        {{ deletingItems[job.job_id] ? '删除中...' : '删除' }}
                                    </button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </template>

```

- [ ] **Step 3: 在 `</body>` 前的 script 引入列表中追加新 composable**

找到：
```html
    <script src="/static/js/useLokiLogs.js"></script>
    <script src="/static/js/app.js"></script>
```

改为：
```html
    <script src="/static/js/useLokiLogs.js"></script>
    <script src="/static/js/useReminderPage.js"></script>
    <script src="/static/js/app.js"></script>
```

- [ ] **Step 4: 在 `styles.css` 末尾追加提醒表格样式**

注意：`.list-header` 在 CSS 中已存在（line 242），只需追加表格相关样式。

在 `/Users/oreoft/IdeaProjects/my/true-love-n/true-love-server/static/styles.css` 末尾（`}` 最后一行之后）追加：

```css
/* ==================== Reminder Table ==================== */

.reminder-table-wrapper {
    overflow-x: auto;
    padding: 0 16px 16px;
    background: white;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.reminder-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.reminder-table th {
    text-align: left;
    padding: 10px 12px;
    background: #f9fafb;
    border-bottom: 2px solid #e5e7eb;
    color: #6b7280;
    font-weight: 600;
    white-space: nowrap;
}

.reminder-table td {
    padding: 12px;
    border-bottom: 1px solid #f3f4f6;
    vertical-align: middle;
}

.reminder-table tr:last-child td {
    border-bottom: none;
}

.reminder-table tr:hover td {
    background: #f9fafb;
}

.reminder-receiver {
    font-family: monospace;
    font-size: 12px;
    color: #6b7280;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.reminder-content {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-weight: 500;
}

.reminder-time {
    white-space: nowrap;
}

.time-local {
    display: block;
    font-weight: 500;
    font-size: 13px;
}

.time-offset {
    display: block;
    font-size: 11px;
    color: #9ca3af;
    margin-top: 2px;
}

.platform-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 500;
}

.platform-badge.wechat {
    background: #dcfce7;
    color: #16a34a;
}

.platform-badge.lark {
    background: #dbeafe;
    color: #2563eb;
}
```

- [ ] **Step 5: 提交 HTML + CSS 变更**

```bash
git add static/index.html static/styles.css
git commit -m "feat: add reminder tab UI to admin page"
```

---

## Task 6: 前端 — 更新 `app.js`

**Files:**
- Modify: `static/js/app.js`

- [ ] **Step 1: 整体替换 `app.js` 内容，集成 reminder composable**

将 `static/js/app.js` 完整替换为：

```js
/**
 * 主应用入口
 */

(function() {
    const { createApp, ref, onMounted, onUnmounted } = Vue;

    createApp({
        setup() {
            // Tab state
            const activeTab = ref('list');
            
            // Toast & Confirm
            const { toasts, showToast } = useToast();
            const { confirmModal, showConfirm } = useConfirm();
            
            // List page
            const listPage = useListPage(showToast, showConfirm);
            
            // Loki logs page
            const lokiLogs = useLokiLogs(showToast);

            // Reminder page
            const reminderPage = useReminderPage(showToast, showConfirm);
            
            // Tab 切换
            const switchTab = (tab) => {
                activeTab.value = tab;
                
                if (tab === 'logs') {
                    if (lokiLogs.lokiLogs.value.length === 0) {
                        lokiLogs.initLokiLogs();
                    }
                    lokiLogs.startLokiPolling();
                } else {
                    lokiLogs.stopLokiPolling();
                }

                if (tab === 'reminders') {
                    reminderPage.fetchReminders();
                }
            };
            
            // 初始化
            onMounted(() => {
                listPage.fetchStatus();
            });
            
            // 清理
            onUnmounted(() => {
                lokiLogs.stopLokiPolling();
            });
            
            return {
                // Tab
                activeTab,
                switchTab,
                
                // Toast & Confirm
                toasts,
                confirmModal,
                
                // List page
                ...listPage,
                
                // Loki logs page
                ...lokiLogs,

                // Reminder page
                ...reminderPage
            };
        }
    }).mount('#app');
})();
```

- [ ] **Step 2: 提交**

```bash
git add static/js/app.js
git commit -m "feat: integrate reminder composable into app.js"
```

---

## Task 7: 验证整体功能

- [ ] **Step 1: 启动服务**

```bash
cd /Users/oreoft/IdeaProjects/my/true-love-n/true-love-server
uv run python -m true_love_server
```

- [ ] **Step 2: 在浏览器访问 `http://localhost:8000/admin`**

验证：
- Header 显示三个 Tab：📋 列表、📝 日志、⏰ 提醒
- 点击"⏰ 提醒"Tab，页面显示"暂无待执行的提醒任务"（空状态）
- 点击"刷新"按钮，不报错

- [ ] **Step 3: 通过 curl 手动添加一条测试提醒，再验证 admin 显示**

```bash
# 添加测试提醒（5分钟后触发）
curl -X POST http://localhost:8000/action/reminder/add \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_token_here",
    "job_id": "reminder_test_999",
    "target_time_iso": "2026-05-11T18:00:00+08:00",
    "receiver": "test_receiver",
    "content": "测试提醒内容",
    "platform": "wechat"
  }'
```

刷新 admin 提醒 Tab，验证该条记录出现且：
- 接收者显示正确
- 触发时间显示本地时区时间（如 `18:00:00` + `UTC+8`）
- 平台徽章显示绿色 `wechat`

- [ ] **Step 4: 点击删除按钮**

确认弹窗显示，确认后该条记录从列表消失，显示"提醒已删除" toast。
