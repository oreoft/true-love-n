/**
 * Toast 通知 composable
 */

const { ref } = Vue;

export function useToast() {
    const toasts = ref([]);
    
    const showToast = (message, type = 'info') => {
        const id = Date.now();
        toasts.value.push({ id, message, type });
        setTimeout(() => {
            toasts.value = toasts.value.filter(t => t.id !== id);
        }, 3000);
    };
    
    return {
        toasts,
        showToast
    };
}

