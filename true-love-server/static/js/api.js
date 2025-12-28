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
    fetchLokiLogs: (startMs, endMs, limit = 500, direction = 'backward') => 
        apiRequest(`/admin/loki/logs?start_ms=${startMs}&end_ms=${endMs}&limit=${limit}&direction=${direction}`)
};

