/**
 * 动态技能管理页面 composable
 */

window.useSkillPage = function(showToast, showConfirm) {
    const { ref, reactive } = Vue;

    const skills = ref([]);
    const loading = ref(false);
    const skillDeletingItems = ref({});

    // 添加弹窗状态
    const skillAddModal = reactive({
        show: false,
        loading: false,
        id: '',
        name: '',
        description: '',
        command: '',
        parameters: '',
    });

    // 修改弹窗状态（id 只读，是主键）
    const skillEditModal = reactive({
        show: false,
        loading: false,
        id: '',
        name: '',
        description: '',
        command: '',
        parameters: '',
    });

    /**
     * ISO 字符串简化为 MM-DD HH:mm，无值返回 '—'
     */
    const _fmtDt = (isoStr) => {
        if (!isoStr) return '—';
        try {
            const d = new Date(isoStr);
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            const hh = String(d.getHours()).padStart(2, '0');
            const mi = String(d.getMinutes()).padStart(2, '0');
            return `${mm}-${dd} ${hh}:${mi}`;
        } catch (e) { return isoStr; }
    };

    const fetchSkills = async () => {
        loading.value = true;
        try {
            const data = await api.fetchSkillList();
            skills.value = (data.data?.skills || []).map(s => ({
                ...s,
                _lastUsed: _fmtDt(s.last_used_at),
            }));
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            loading.value = false;
        }
    };

    // ==================== 添加 ====================

    const openSkillAddModal = () => {
        skillAddModal.show = true;
        skillAddModal.id = '';
        skillAddModal.name = '';
        skillAddModal.description = '';
        skillAddModal.command = '';
        skillAddModal.parameters = '';
    };

    const _validateParams = (paramsStr) => {
        if (!paramsStr.trim()) return true;
        try { JSON.parse(paramsStr); return true; } catch (e) { return false; }
    };

    const submitSkillAdd = async () => {
        if (!skillAddModal.id.trim() || !skillAddModal.name.trim() ||
            !skillAddModal.description.trim() || !skillAddModal.command.trim()) {
            showToast('ID、名称、描述、命令不能为空', 'error');
            return;
        }
        if (!_validateParams(skillAddModal.parameters)) {
            showToast('参数必须是合法的 JSON 格式', 'error');
            return;
        }
        skillAddModal.loading = true;
        try {
            await api.saveSkill(
                skillAddModal.id.trim(),
                skillAddModal.name.trim(),
                skillAddModal.description.trim(),
                skillAddModal.command.trim(),
                skillAddModal.parameters.trim() || null,
            );
            showToast('技能添加成功', 'success');
            skillAddModal.show = false;
            await fetchSkills();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            skillAddModal.loading = false;
        }
    };

    // ==================== 修改 ====================

    const openSkillEditModal = (skill) => {
        skillEditModal.show = true;
        skillEditModal.id = skill.id;
        skillEditModal.name = skill.name;
        skillEditModal.description = skill.description;
        skillEditModal.command = skill.command;
        skillEditModal.parameters = skill.parameters || '';
    };

    const submitSkillEdit = async () => {
        if (!skillEditModal.name.trim() || !skillEditModal.description.trim() ||
            !skillEditModal.command.trim()) {
            showToast('名称、描述、命令不能为空', 'error');
            return;
        }
        if (!_validateParams(skillEditModal.parameters)) {
            showToast('参数必须是合法的 JSON 格式', 'error');
            return;
        }
        skillEditModal.loading = true;
        try {
            await api.saveSkill(
                skillEditModal.id,
                skillEditModal.name.trim(),
                skillEditModal.description.trim(),
                skillEditModal.command.trim(),
                skillEditModal.parameters.trim() || null,
            );
            showToast('技能修改成功', 'success');
            skillEditModal.show = false;
            await fetchSkills();
        } catch (error) {
            showToast(error.message, 'error');
        } finally {
            skillEditModal.loading = false;
        }
    };

    // ==================== 删除 ====================

    const deleteSkill = (id, name) => {
        showConfirm(
            '删除技能',
            `确定要删除技能「${name || id}」吗？`,
            async () => {
                skillDeletingItems.value[id] = true;
                try {
                    await api.deleteSkill(id);
                    showToast('技能已删除', 'success');
                    await fetchSkills();
                } catch (error) {
                    showToast(error.message, 'error');
                } finally {
                    delete skillDeletingItems.value[id];
                }
            }
        );
    };

    return {
        skills,
        skillLoading: loading,
        skillDeletingItems,
        fetchSkills,
        deleteSkill,
        // 添加
        skillAddModal,
        openSkillAddModal,
        submitSkillAdd,
        // 修改
        skillEditModal,
        openSkillEditModal,
        submitSkillEdit,
    };
};
