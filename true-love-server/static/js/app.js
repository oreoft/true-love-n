/**
 * 主应用入口
 */

import { useToast } from './useToast.js';
import { useConfirm } from './useConfirm.js';
import { useListPage } from './useListPage.js';
import { useLokiLogs } from './useLokiLogs.js';

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
            
            // List page - spread all properties
            ...listPage,
            
            // Loki logs page - spread all properties
            ...lokiLogs
        };
    }
}).mount('#app');

