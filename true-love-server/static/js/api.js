/**
 * API 请求模块
 */

const SERVER_HOST = window.location.origin;

/**
 * 通用请求方法
 */
async function apiRequest(url, options = {}, host = SERVER_HOST) {
    try {
        const response = await fetch(host + url, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        const data = await response.json();
        if (data.code !== 0) {
            throw new Error(data.message || '请求失败');
        }
        return data;
    } catch (error) {
        if (error.message === 'Failed to fetch') {
            throw new Error('无法连接到服务器');
        }
        throw error;
    }
}

// 导出为全局对象
window.api = {
    request: apiRequest,
    
    // Listen API
    fetchListenStatus: () => apiRequest('/admin/listen/status'),
    
    addListen: (chatName) => apiRequest('/admin/listen/add', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    }),
    
    removeListen: (chatName) => apiRequest('/admin/listen/remove', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    }),
    
    resetListen: (chatName) => apiRequest('/admin/listen/reset', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    }),
    
    refreshListen: () => apiRequest('/admin/listen/refresh', { method: 'POST' }),
    
    resetAllListen: () => apiRequest('/admin/listen/reset-all', { method: 'POST' }),
    
    getAllMessage: (chatName) => apiRequest('/admin/listen/get-all-message', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    }),
    
    // Loki API
    fetchLokiLogs: (startMs, endMs, limit = 50, direction = 'backward') =>
        apiRequest(`/admin/loki/logs?start_ms=${startMs}&end_ms=${endMs}&limit=${limit}&direction=${direction}`),

    // Reminder API
    fetchReminderList: () => apiRequest('/admin/reminder/list'),

    addReminder: (receiver, content, targetTimeIso, atUser, platform) => apiRequest('/admin/reminder/add', {
        method: 'POST',
        body: JSON.stringify({ receiver, content, target_time_iso: targetTimeIso, at_user: atUser, platform })
    }),

    updateReminder: (jobId, newTimeIso, newContent) => apiRequest('/admin/reminder/update', {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId, new_time_iso: newTimeIso, new_content: newContent })
    }),

    deleteReminder: (jobId) => apiRequest('/admin/reminder/delete', {
        method: 'POST',
        body: JSON.stringify({ job_id: jobId })
    }),

    // Skill API
    fetchSkillList: () => apiRequest('/admin/skill/list'),

    saveSkill: (id, name, description, command, parameters) => apiRequest('/admin/skill/save', {
        method: 'POST',
        body: JSON.stringify({ id, name, description, command, parameters })
    }),

    deleteSkill: (id) => apiRequest('/admin/skill/delete', {
        method: 'POST',
        body: JSON.stringify({ id })
    }),
};

