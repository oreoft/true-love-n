/**
 * API 请求模块
 */

const SERVER_HOST = window.location.origin;

/**
 * 通用请求方法
 */
export async function request(url, options = {}, host = SERVER_HOST) {
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

// ==================== Listen API ====================

export async function fetchListenStatus() {
    return request('/admin/listen/status');
}

export async function addListen(chatName) {
    return request('/admin/listen/add', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    });
}

export async function removeListen(chatName) {
    return request('/admin/listen/remove', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    });
}

export async function resetListen(chatName) {
    return request('/admin/listen/reset', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    });
}

export async function refreshListen() {
    return request('/admin/listen/refresh', { method: 'POST' });
}

export async function resetAllListen() {
    return request('/admin/listen/reset-all', { method: 'POST' });
}

export async function getAllMessage(chatName) {
    return request('/admin/listen/get-all-message', {
        method: 'POST',
        body: JSON.stringify({ chat_name: chatName })
    });
}

// ==================== Loki API ====================

export async function fetchLokiLogs(startMs, endMs, limit = 500, direction = 'backward') {
    return request(`/admin/loki/logs?start_ms=${startMs}&end_ms=${endMs}&limit=${limit}&direction=${direction}`);
}

