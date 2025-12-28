/**
 * 确认弹窗 composable
 */

window.useConfirm = function() {
    const { reactive } = Vue;
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
};

