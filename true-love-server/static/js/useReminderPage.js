/**
 * 定时提醒管理页面 composable
 */

window.useReminderPage = function(showToast, showConfirm) {
    const { ref } = Vue;

    const reminders = ref([]);
    const loading = ref(false);
    const deletingItems = ref({});

    /**
     * 将 UTC ISO 字符串格式化为本地时间 + UTC 偏移显示
     * 例：2026-05-11T06:30:00+00:00 → { full: "05-11 14:30:00", offset: "UTC+8" }
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

            return {
                full: `${mm}-${dd} ${hh}:${mi}:${ss}`,
                offset: offsetLabel
            };
        } catch (e) {
            return { full: isoStr, offset: '' };
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
        deleteReminder
    };
};
