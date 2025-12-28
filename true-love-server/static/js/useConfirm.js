/**
 * 确认弹窗 composable
 */

const { reactive } = Vue;

export function useConfirm() {
    const confirmModal = reactive({
        show: false,
        title: '',
        message: '',
        onConfirm: () => {}
    });
    
    const showConfirm = (title, message, onConfirm) => {
        confirmModal.title = title;
        confirmModal.message = message;
        confirmModal.onConfirm = () => {
            confirmModal.show = false;
            onConfirm();
        };
        confirmModal.show = true;
    };
    
    return {
        confirmModal,
        showConfirm
    };
}

