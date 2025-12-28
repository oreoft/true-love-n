/**
 * 列表页面 composable
 */

import * as api from './api.js';

const { ref, reactive, watch, nextTick } = Vue;

export function useListPage(showToast, showConfirm) {
    // State
    const listeners = ref([]);
    const summary = ref({ healthy: 0, unhealthy: 0 });
    const loading = ref(false);
    const loadingItems = reactive({});
    
    // Add Modal
    const showAddModal = ref(false);
    const newChatName = ref('');
    const addLoading = ref(false);
    const addInput = ref(null);
    
    // Test Alive Modal
    const testAliveModal = reactive({
        show: false,
        chatName: '',
        loading: false,
        error: null,
        result: null
    });
    
    // 获取监听状态
    const fetchStatus = async () => {
        loading.value = true;
        try {
            const data = await api.fetchListenStatus();
            listeners.value = data.data?.listeners || [];
            summary.value = data.data?.summary || { healthy: 0, unhealthy: 0 };
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            loading.value = false;
        }
    };
    
    // 添加监听
    const addListener = async () => {
        if (!newChatName.value.trim()) return;
        
        addLoading.value = true;
        try {
            await api.addListen(newChatName.value.trim());
            showToast('添加成功', 'success');
            showAddModal.value = false;
            newChatName.value = '';
            await fetchStatus();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            addLoading.value = false;
        }
    };
    
    // 删除监听
    const removeOne = (chatName) => {
        showConfirm('删除确认', `确定要删除「${chatName}」的监听吗？`, async () => {
            loadingItems[chatName] = 'remove';
            try {
                await api.removeListen(chatName);
                showToast('删除成功', 'success');
                await fetchStatus();
            } catch (error) {
                showToast(error.message, 'error');
            } finally {
                delete loadingItems[chatName];
            }
        });
    };
    
    // 重置单个监听
    const resetOne = async (chatName) => {
        loadingItems[chatName] = 'reset';
        try {
            const data = await api.resetListen(chatName);
            showToast(data.data?.message || '重置成功', 'success');
            await fetchStatus();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            delete loadingItems[chatName];
        }
    };
    
    // 刷新全部
    const refreshAll = async () => {
        loading.value = true;
        try {
            const data = await api.refreshListen();
            const result = data.data;
            showToast(`刷新完成：成功 ${result?.success_count || 0}，失败 ${result?.fail_count || 0}`, 'success');
            await fetchStatus();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            loading.value = false;
        }
    };
    
    // 重置全部
    const resetAll = () => {
        showConfirm('重置确认', '确定要重置所有监听吗？这将重启所有监听连接。', async () => {
            loading.value = true;
            try {
                const data = await api.resetAllListen();
                const result = data.data;
                showToast(result?.message || '重置全部完成', 'success');
                await fetchStatus();
            } catch (error) {
                showToast(error.message, 'error');
            } finally {
                loading.value = false;
            }
        });
    };
    
    // 测活
    const testAlive = async (chatName) => {
        testAliveModal.show = true;
        testAliveModal.chatName = chatName;
        testAliveModal.loading = true;
        testAliveModal.error = null;
        testAliveModal.result = null;
        loadingItems[chatName] = 'test';
        
        try {
            const data = await api.getAllMessage(chatName);
            testAliveModal.result = data.data;
        } catch (error) {
            testAliveModal.error = error.message;
        } finally {
            testAliveModal.loading = false;
            delete loadingItems[chatName];
        }
    };
    
    // Watch modal to focus input
    watch(showAddModal, (val) => {
        if (val) {
            nextTick(() => {
                addInput.value?.focus();
            });
        }
    });
    
    return {
        listeners,
        summary,
        loading,
        loadingItems,
        showAddModal,
        newChatName,
        addLoading,
        addInput,
        testAliveModal,
        fetchStatus,
        addListener,
        removeOne,
        resetOne,
        refreshAll,
        resetAll,
        testAlive
    };
}

