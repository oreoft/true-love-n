/**
 * 设置页面 composable
 *
 * 每个机器人各不相同的设置（回调地址、推送的群）存在这台 server 的数据库里，保存后立即生效。
 */

window.useSettingsPage = function(showToast) {
    const { ref } = Vue;

    const settings = ref([]);
    const settingsLoading = ref(false);

    // 列表在输入框里一行一个
    const toText = (item) => item.type === 'list' ? (item.value || []).join('\n') : (item.value || '');

    const fromText = (item) => item.type === 'list'
        ? item.draft.split('\n').map(line => line.trim()).filter(Boolean)
        : item.draft.trim();

    const fetchSettings = async () => {
        settingsLoading.value = true;
        try {
            const data = await api.fetchSettings();
            settings.value = (data.data?.settings || []).map(item => ({
                ...item,
                draft: toText(item),
                saving: false,
            }));
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            settingsLoading.value = false;
        }
    };

    const isSettingChanged = (item) => item.draft !== toText(item);

    const isSettingEmpty = (item) => item.type === 'list' ? (item.value || []).length === 0 : !item.value;

    const saveSetting = async (item) => {
        item.saving = true;
        try {
            const data = await api.updateSetting(item.key, fromText(item));
            // 以服务端整理后的值为准（去空格、去重复）
            item.value = data.data.value;
            item.draft = toText(item);
            showToast(`${item.label}已保存`, 'success');
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            item.saving = false;
        }
    };

    const resetSetting = (item) => {
        item.draft = toText(item);
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
