/**
 * 定时提醒管理页面 composable
 */

window.useReminderPage = function(showToast, showConfirm) {
    const { ref, reactive } = Vue;

    const reminders = ref([]);
    const loading = ref(false);
    const deletingItems = ref({});

    // 添加弹窗状态
    const addModal = reactive({
        show: false,
        loading: false,
        receiver: '',
        content: '',
        targetTime: '',   // datetime-local 格式 YYYY-MM-DDTHH:MM
        atUser: '',
        platform: 'wechat',
    });

    // 修改弹窗状态
    const editModal = reactive({
        show: false,
        loading: false,
        jobId: '',
        newContent: '',
        newTime: '',      // datetime-local 格式
        originalContent: '',
        originalTime: '',
    });

    /**
     * 将 UTC ISO 字符串格式化为本地时间 + UTC 偏移显示
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
            return { full: `${mm}-${dd} ${hh}:${mi}:${ss}`, offset: offsetLabel };
        } catch (e) {
            return { full: isoStr, offset: '' };
        }
    };

    /**
     * datetime-local 值（YYYY-MM-DDTHH:MM）→ 带浏览器时区的 ISO-8601 字符串
     */
    const localInputToIso = (localStr) => {
        if (!localStr) return '';
        const offsetMin = -new Date().getTimezoneOffset();
        const sign = offsetMin >= 0 ? '+' : '-';
        const h = String(Math.floor(Math.abs(offsetMin) / 60)).padStart(2, '0');
        const m = String(Math.abs(offsetMin) % 60).padStart(2, '0');
        return `${localStr}:00${sign}${h}:${m}`;
    };

    /**
     * ISO 字符串 → datetime-local 输入框的初始值（YYYY-MM-DDTHH:MM，本地时区）
     */
    const isoToLocalInput = (isoStr) => {
        try {
            const d = new Date(isoStr);
            const y = d.getFullYear();
            const mo = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            const hh = String(d.getHours()).padStart(2, '0');
            const mi = String(d.getMinutes()).padStart(2, '0');
            return `${y}-${mo}-${dd}T${hh}:${mi}`;
        } catch (e) {
            return '';
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

    // ==================== 添加 ====================

    const openAddModal = () => {
        addModal.show = true;
        addModal.receiver = '';
        addModal.content = '';
        addModal.targetTime = '';
        addModal.atUser = '';
        addModal.platform = 'wechat';
    };

    const submitAdd = async () => {
        if (!addModal.receiver.trim() || !addModal.content.trim() || !addModal.targetTime) {
            showToast('接收者、内容、触发时间不能为空', 'error');
            return;
        }
        addModal.loading = true;
        try {
            const isoStr = localInputToIso(addModal.targetTime);
            await api.addReminder(
                addModal.receiver.trim(),
                addModal.content.trim(),
                isoStr,
                addModal.atUser.trim(),
                addModal.platform,
            );
            showToast('提醒添加成功', 'success');
            addModal.show = false;
            await fetchReminders();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            addModal.loading = false;
        }
    };

    // ==================== 修改 ====================

    const openEditModal = (job) => {
        editModal.show = true;
        editModal.jobId = job.job_id;
        editModal.newContent = job.content;
        editModal.newTime = isoToLocalInput(job.next_run_time);
        editModal.originalContent = job.content;
        editModal.originalTime = job._time.full + ' ' + job._time.offset;
    };

    const submitEdit = async () => {
        if (!editModal.newContent.trim() && !editModal.newTime) {
            showToast('时间和内容至少修改一项', 'error');
            return;
        }
        editModal.loading = true;
        try {
            const newTimeIso = editModal.newTime ? localInputToIso(editModal.newTime) : '';
            await api.updateReminder(
                editModal.jobId,
                newTimeIso,
                editModal.newContent.trim(),
            );
            showToast('提醒修改成功', 'success');
            editModal.show = false;
            await fetchReminders();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            editModal.loading = false;
        }
    };

    // ==================== 删除 ====================

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
        deleteReminder,
        // 添加
        addModal,
        openAddModal,
        submitAdd,
        // 修改
        editModal,
        openEditModal,
        submitEdit,
    };
};
