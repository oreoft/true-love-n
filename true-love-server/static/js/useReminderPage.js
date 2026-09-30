/**
 * 定时任务页面 composable
 *
 * 两种类型：普通提醒（一次性给一个接收者发一句话），定时任务（把写好的任务推给一批接收者，单次或每天）。
 */

window.useReminderPage = function(showToast, showConfirm) {
    const { ref, reactive, computed } = Vue;

    const reminders = ref([]);
    const tasks = ref([]);
    const jobOptions = ref([]);
    const timezones = ref([]);
    const loading = ref(false);
    const deletingItems = ref({});

    // 添加/修改弹窗状态（reminderId、taskId 不为空时是在修改）
    const addModal = reactive({
        show: false,
        loading: false,
        type: 'reminder',
        reminderId: '',
        receiver: '',
        content: '',
        targetTime: '',   // datetime-local 格式 YYYY-MM-DDTHH:MM
        atUser: '',
        platform: 'wechat',
        taskId: '',
        receivers: [],
        newReceiver: '',
        jobName: '',
        mode: 'daily',
        runAt: '',        // datetime-local 格式
        time: '09:00',
        timezone: 'Asia/Shanghai',
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

    const timezoneLabel = (value) => (timezones.value.find(tz => tz.value === value) || {}).label || value;

    const describeSchedule = (schedule) => schedule.mode === 'daily'
        ? `每天 ${schedule.time}（${timezoneLabel(schedule.timezone).replace('时间', '')}）`
        : '单次';

    // 两种类型合在一张表里，按下次执行时间排
    const scheduleItems = computed(() => [
        ...reminders.value.map(job => ({ ...job, kind: 'reminder', key: job.job_id, nextRun: job.next_run_time })),
        ...tasks.value.map(task => ({ ...task, kind: 'task', key: task.task_id, nextRun: task.next_run_time })),
    ].sort((a, b) => (a.nextRun || '9999').localeCompare(b.nextRun || '9999')));

    const fetchReminders = async () => {
        loading.value = true;
        try {
            const [reminderData, taskData] = await Promise.all([api.fetchReminderList(), api.fetchTaskList()]);
            reminders.value = (reminderData.data?.jobs || []).map(job => ({
                ...job,
                _time: formatTime(job.next_run_time)
            }));
            jobOptions.value = taskData.data?.jobs || [];
            timezones.value = taskData.data?.timezones || [];
            tasks.value = (taskData.data?.tasks || []).map(task => ({
                ...task,
                _time: task.next_run_time ? formatTime(task.next_run_time) : { full: '-', offset: '' },
                _schedule: describeSchedule(task.schedule),
            }));
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            loading.value = false;
        }
    };

    // ==================== 添加 ====================

    const openAddModal = () => {
        Object.assign(addModal, {
            show: true,
            type: 'reminder',
            reminderId: '',
            receiver: '',
            content: '',
            targetTime: '',
            atUser: '',
            platform: 'wechat',
            taskId: '',
            receivers: [],
            newReceiver: '',
            jobName: jobOptions.value[0] || '',
            mode: 'daily',
            runAt: '',
            time: '09:00',
            timezone: 'Asia/Shanghai',
        });
    };

    const openReminderEdit = (job) => {
        openAddModal();
        Object.assign(addModal, {
            reminderId: job.job_id,
            receiver: job.receiver,
            content: job.content,
            targetTime: isoToLocalInput(job.next_run_time),
            atUser: job.at_user || '',
            platform: job.platform || 'wechat',
        });
    };

    const openTaskEdit = (task) => {
        openAddModal();
        Object.assign(addModal, {
            type: 'task',
            taskId: task.task_id,
            receivers: [...task.receivers],
            jobName: task.job_name,
            mode: task.schedule.mode,
            runAt: task.schedule.mode === 'once' ? isoToLocalInput(task.schedule.run_at) : '',
            time: task.schedule.time || '09:00',
            timezone: task.schedule.timezone || 'Asia/Shanghai',
        });
    };

    const addTaskReceiver = () => {
        const name = addModal.newReceiver.trim();
        if (!name) return;
        if (addModal.receivers.some(existing => existing.trim() === name)) {
            showToast(`${name} 已经在列表里了`, 'error');
            return;
        }
        addModal.receivers.push(name);
        addModal.newReceiver = '';
    };

    const removeTaskReceiver = (index) => {
        addModal.receivers.splice(index, 1);
    };

    const submitTask = async () => {
        // 输入框里还没点"添加"的也算上
        const receivers = [...addModal.receivers, addModal.newReceiver].map(name => name.trim()).filter(Boolean);
        if (!addModal.jobName) {
            showToast('请选择任务方法', 'error');
            return;
        }
        if (addModal.mode === 'once' && !addModal.runAt) {
            showToast('请选择执行时间', 'error');
            return;
        }
        if (addModal.mode === 'daily' && !addModal.time) {
            showToast('请选择每天执行的时间', 'error');
            return;
        }
        const schedule = addModal.mode === 'once'
            ? { mode: 'once', run_at: localInputToIso(addModal.runAt) }
            : { mode: 'daily', time: addModal.time, timezone: addModal.timezone };
        addModal.loading = true;
        try {
            if (addModal.taskId) {
                await api.updateTask(addModal.taskId, addModal.jobName, receivers, schedule);
                showToast('定时任务已修改', 'success');
            } else {
                await api.addTask(addModal.jobName, receivers, schedule);
                showToast('定时任务已添加', 'success');
            }
            addModal.show = false;
            await fetchReminders();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            addModal.loading = false;
        }
    };

    const submitAdd = async () => {
        if (addModal.type === 'task') {
            return submitTask();
        }
        if (!addModal.receiver.trim() || !addModal.content.trim() || !addModal.targetTime) {
            showToast('接收者、内容、触发时间不能为空', 'error');
            return;
        }
        addModal.loading = true;
        try {
            const reminder = [
                addModal.receiver.trim(),
                addModal.content.trim(),
                localInputToIso(addModal.targetTime),
                addModal.atUser.trim(),
                addModal.platform,
            ];
            if (addModal.reminderId) {
                await api.updateReminder(addModal.reminderId, ...reminder);
                showToast('提醒已修改', 'success');
            } else {
                await api.addReminder(...reminder);
                showToast('提醒添加成功', 'success');
            }
            addModal.show = false;
            await fetchReminders();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            addModal.loading = false;
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

    const deleteTask = (task) => {
        showConfirm(
            '删除定时任务',
            `确定要删除「${task.job_name}」（${task._schedule}，${task.receivers.length} 个接收者）吗？`,
            async () => {
                deletingItems.value[task.task_id] = true;
                try {
                    await api.deleteTask(task.task_id);
                    showToast('定时任务已删除', 'success');
                    await fetchReminders();
                } catch (error) {
                    showToast(error.message, 'error');
                } finally {
                    delete deletingItems.value[task.task_id];
                }
            }
        );
    };

    const runTask = (task) => {
        showConfirm(
            '立即执行',
            `现在就把「${task.job_name}」推给 ${task.receivers.join('、')} 吗？不影响之后的定时。`,
            async () => {
                try {
                    await api.runTask(task.task_id);
                    showToast('已开始执行，推送需要一会儿', 'success');
                } catch (error) {
                    showToast(error.message, 'error');
                }
            }
        );
    };

    return {
        reminders,
        tasks,
        jobOptions,
        timezones,
        scheduleItems,
        reminderLoading: loading,
        deletingItems,
        fetchReminders,
        deleteReminder,
        // 添加
        addModal,
        openAddModal,
        submitAdd,
        openReminderEdit,
        // 定时任务
        openTaskEdit,
        addTaskReceiver,
        removeTaskReceiver,
        deleteTask,
        runTask,
    };
};
