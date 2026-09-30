/**
 * 设置页面 composable
 *
 * 每个机器人各不相同的设置（如本机回调地址）存在这台 server 的数据库里，保存后立即生效。
 */

window.useSettingsPage = function(showToast) {
    const { ref } = Vue;

    const settings = ref([]);
    const settingsLoading = ref(false);

    const normalize = (item) => item.draft.trim();

    const withDraft = (item) => ({ ...item, draft: item.value || '' });

    const fetchSettings = async () => {
        settingsLoading.value = true;
        try {
            const data = await api.fetchSettings();
            settings.value = (data.data?.settings || []).map(item => ({
                ...withDraft(item),
                saving: false,
            }));
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            settingsLoading.value = false;
        }
    };

    const isSettingChanged = (item) => normalize(item) !== (item.value || '');

    const isSettingEmpty = (item) => !item.value;

    const saveSetting = async (item) => {
        item.saving = true;
        try {
            const data = await api.updateSetting(item.key, normalize(item));
            // 以服务端整理后的值为准（去空格、去末尾斜杠）
            item.value = data.data.value;
            Object.assign(item, withDraft(item));
            showToast(`${item.label}已保存`, 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            item.saving = false;
        }
    };

    const resetSetting = (item) => {
        Object.assign(item, withDraft(item));
    };

    return {
        settings,
        settingsLoading,
        fetchSettings,
        saveSetting,
        resetSetting,
        isSettingChanged,
        isSettingEmpty,
    };
};
