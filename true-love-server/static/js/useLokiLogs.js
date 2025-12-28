/**
 * Loki 日志页面 composable
 */

import * as api from './api.js';

const { ref, computed, nextTick } = Vue;

export function useLokiLogs(showToast) {
    // State
    const lokiServices = ref(['ai', 'base', 'server']);
    const lokiServiceFilter = ref(['ai', 'base', 'server']);
    const lokiLogs = ref([]);
    const lokiLoading = ref(false);
    const lokiLoadingOlder = ref(false);
    const lokiLoadingNewer = ref(false);
    const lokiLogsContainer = ref(null);
    const lokiAutoScroll = ref(true);
    const lokiPolling = ref(false);
    const lokiCanLoadOlder = ref(true);
    let lokiPollTimer = null;
    
    // 时间边界（毫秒）
    const lokiEarliestMs = ref(0);
    const lokiLatestMs = ref(0);
    
    // 过滤后的日志
    const filteredLokiLogs = computed(() => {
        if (lokiServiceFilter.value.length === lokiServices.value.length) {
            return lokiLogs.value;
        }
        return lokiLogs.value.filter(log => lokiServiceFilter.value.includes(log.service));
    });
    
    // 时间范围显示
    const lokiTimeRange = computed(() => {
        if (lokiLogs.value.length === 0) return '';
        const first = lokiLogs.value[0];
        const last = lokiLogs.value[lokiLogs.value.length - 1];
        if (first && last) {
            const startTime = first.time_str?.split(' ')[1] || '';
            const endTime = last.time_str?.split(' ')[1] || '';
            return `${startTime} ~ ${endTime}`;
        }
        return '';
    });
    
    // 查询 Loki 日志
    const fetchLokiLogs = async (startMs, endMs, direction = 'backward', prepend = false) => {
        try {
            const result = await api.fetchLokiLogs(startMs, endMs, 500, direction);
            
            if (result.data && result.data.logs) {
                const newLogs = result.data.logs;
                
                if (newLogs.length === 0) {
                    if (prepend) {
                        lokiCanLoadOlder.value = false;
                    }
                    return 0;
                }
                
                // 去重合并
                const existingKeys = new Set(lokiLogs.value.map(l => l.timestamp + '|' + l.raw));
                const uniqueNewLogs = newLogs.filter(l => !existingKeys.has(l.timestamp + '|' + l.raw));
                
                if (uniqueNewLogs.length === 0) {
                    return 0;
                }
                
                if (prepend) {
                    lokiLogs.value = [...uniqueNewLogs, ...lokiLogs.value];
                } else {
                    lokiLogs.value = [...lokiLogs.value, ...uniqueNewLogs];
                }
                
                // 按时间排序
                lokiLogs.value.sort((a, b) => a.timestamp - b.timestamp);
                
                // 更新时间边界
                if (lokiLogs.value.length > 0) {
                    lokiEarliestMs.value = lokiLogs.value[0].timestamp;
                    lokiLatestMs.value = lokiLogs.value[lokiLogs.value.length - 1].timestamp;
                }
                
                return uniqueNewLogs.length;
            }
            return 0;
        } catch (error) {
            console.error('Fetch Loki logs error:', error);
            showToast(error.message, 'error');
            return 0;
        }
    };
    
    // 初始化加载（最近 1 小时）
    const initLokiLogs = async () => {
        lokiLoading.value = true;
        lokiLogs.value = [];
        lokiCanLoadOlder.value = true;
        
        const now = Date.now();
        const oneHourAgo = now - 60 * 60 * 1000;  // 1 小时
        
        await fetchLokiLogs(oneHourAgo, now, 'forward', false);
        
        lokiLoading.value = false;
        
        nextTick(() => {
            scrollLokiToBottom();
        });
    };
    
    // 加载更早的日志（每次往前 1 小时）
    const loadOlderLogs = async () => {
        if (lokiLoadingOlder.value || !lokiCanLoadOlder.value || lokiLogs.value.length === 0) return;
        
        lokiLoadingOlder.value = true;
        
        const container = lokiLogsContainer.value;
        const prevScrollHeight = container ? container.scrollHeight : 0;
        
        const endMs = lokiEarliestMs.value - 1;
        const startMs = endMs - 60 * 60 * 1000;  // 往前 1 小时
        
        const count = await fetchLokiLogs(startMs, endMs, 'forward', true);
        
        if (count === 0) {
            lokiCanLoadOlder.value = false;
        }
        
        // 保持滚动位置
        nextTick(() => {
            if (container) {
                const newScrollHeight = container.scrollHeight;
                container.scrollTop = newScrollHeight - prevScrollHeight;
            }
        });
        
        lokiLoadingOlder.value = false;
    };
    
    // 加载最新日志
    const loadNewerLogs = async () => {
        if (lokiLoadingNewer.value) return;
        
        lokiLoadingNewer.value = true;
        
        const startMs = lokiLatestMs.value > 0 ? lokiLatestMs.value + 1 : Date.now() - 60 * 60 * 1000;
        const endMs = Date.now();
        
        const count = await fetchLokiLogs(startMs, endMs, 'forward', false);
        
        if (count > 0 && lokiAutoScroll.value) {
            nextTick(() => {
                scrollLokiToBottom();
            });
        }
        
        lokiLoadingNewer.value = false;
        return count;
    };
    
    // 刷新日志
    const refreshLokiLogs = async () => {
        await loadNewerLogs();
        showToast('日志已刷新', 'success');
    };
    
    // 清空日志
    const clearLokiLogs = () => {
        lokiLogs.value = [];
        lokiEarliestMs.value = 0;
        lokiLatestMs.value = 0;
        lokiCanLoadOlder.value = true;
    };
    
    // 切换服务过滤
    const toggleServiceFilter = (svc) => {
        const idx = lokiServiceFilter.value.indexOf(svc);
        if (idx > -1) {
            if (lokiServiceFilter.value.length > 1) {
                lokiServiceFilter.value.splice(idx, 1);
            }
        } else {
            lokiServiceFilter.value.push(svc);
        }
    };
    
    // 滚动控制
    const scrollLokiToBottom = () => {
        if (lokiLogsContainer.value) {
            lokiLogsContainer.value.scrollTop = lokiLogsContainer.value.scrollHeight;
        }
    };
    
    const scrollToTop = () => {
        if (lokiLogsContainer.value) {
            lokiLogsContainer.value.scrollTop = 0;
        }
    };
    
    // 滚动事件处理
    const handleLokiScroll = () => {
        if (!lokiLogsContainer.value) return;
        const { scrollTop, scrollHeight, clientHeight } = lokiLogsContainer.value;
        
        const atBottom = scrollHeight - scrollTop - clientHeight < 100;
        lokiAutoScroll.value = atBottom;
        
        if (atBottom && !lokiLoadingNewer.value) {
            loadNewerLogs();
        }
        
        if (scrollTop < 50 && !lokiLoadingOlder.value && lokiCanLoadOlder.value) {
            loadOlderLogs();
        }
    };
    
    const toggleLokiAutoScroll = () => {
        lokiAutoScroll.value = !lokiAutoScroll.value;
        if (lokiAutoScroll.value) {
            scrollLokiToBottom();
        }
    };
    
    // 轮询控制
    const startLokiPolling = () => {
        if (lokiPollTimer) return;
        lokiPolling.value = true;
        lokiPollTimer = setInterval(() => {
            loadNewerLogs();
        }, 5000);
    };
    
    const stopLokiPolling = () => {
        if (lokiPollTimer) {
            clearInterval(lokiPollTimer);
            lokiPollTimer = null;
        }
        lokiPolling.value = false;
    };
    
    return {
        lokiServices,
        lokiServiceFilter,
        lokiLogs,
        filteredLokiLogs,
        lokiLoading,
        lokiLoadingOlder,
        lokiLoadingNewer,
        lokiLogsContainer,
        lokiAutoScroll,
        lokiPolling,
        lokiCanLoadOlder,
        lokiTimeRange,
        initLokiLogs,
        loadNewerLogs,
        refreshLokiLogs,
        clearLokiLogs,
        toggleServiceFilter,
        handleLokiScroll,
        toggleLokiAutoScroll,
        scrollToTop,
        startLokiPolling,
        stopLokiPolling
    };
}

