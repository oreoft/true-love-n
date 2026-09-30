/**
 * 设置页面 composable
 *
 * 每个机器人各不相同的设置（回调地址、推送的群）存在这台 server 的数据库里，保存后立即生效。
 */

window.useSettingsPage = function(showToast) {
    const { ref } = Vue;

    const settings = ref([]);
    const settingsLoading = ref(false);

    // 列表类设置一行一个输入框，草稿是数组；newEntry 是底部"添加"输入框里还没加进去的内容
    const toDraft = (item) => item.type === 'list' ? [...(item.value || [])] : (item.value || '');

    const normalize = (item) => {
        if (item.type !== 'list') return item.draft.trim();
        const names = [...item.draft, item.newEntry].map(name => name.trim()).filter(Boolean);
        return [...new Set(names)];
    };

    const withDraft = (item) => ({ ...item, draft: toDraft(item), newEntry: '' });

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

    const isSettingChanged = (item) => item.type === 'list'
        ? JSON.stringify(normalize(item)) !== JSON.stringify(item.value || [])
        : item.draft.trim() !== (item.value || '');

    const isSettingEmpty = (item) => item.type === 'list' ? (item.value || []).length === 0 : !item.value;

    const saveSetting = async (item) => {
        item.saving = true;
        try {
            const data = await api.updateSetting(item.key, normalize(item));
            // 以服务端整理后的值为准（去空格、去重复）
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

    const addSettingEntry = (item) => {
        const name = item.newEntry.trim();
        if (!name) return;
        if (item.draft.some(existing => existing.trim() === name)) {
            showToast(`${name} 已经在列表里了`, 'error');
            return;
        }
        item.draft.push(name);
        item.newEntry = '';
    };

    const removeSettingEntry = (item, index) => {
        item.draft.splice(index, 1);
    };

    return {
        settings,
        settingsLoading,
        fetchSettings,
        saveSetting,
        resetSetting,
        isSettingChanged,
        isSettingEmpty,
        addSettingEntry,
        removeSettingEntry,
    };
};
