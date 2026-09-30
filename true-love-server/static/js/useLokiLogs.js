/**
 * Loki 日志页面 composable
 *
 * 列表从新到旧：最上面是最新的日志，往下滚自动加载更早的一页。
 * 服务过滤和关键词搜索都交给后端做，切换条件后从最新一页重新加载。
 */

window.useLokiLogs = function(showToast) {
    const { ref, computed } = Vue;

    const PAGE_SIZE = 50;
    // 距离页面底部多少像素时加载下一页
    const LOAD_OLDER_THRESHOLD = 300;

    // State
    const lokiServices = [
        { value: 'tl-ai', label: 'ai' },
        { value: 'tl-base', label: 'base' },
        { value: 'tl-server', label: 'server' }
    ];
    const lokiServiceFilter = ref(lokiServices.map(s => s.value));
    const lokiKeyword = ref('');
    const lokiLogs = ref([]);
    const lokiLoading = ref(false);
    const lokiLoadingOlder = ref(false);
    const lokiCanLoadOlder = ref(true);
    let lokiNextBeforeNs = '';
    // 每次重新加载加一，丢弃条件变化前发出的请求结果
    let lokiRequestSeq = 0;

    // 时间范围显示：最新 ~ 最早
    const lokiTimeRange = computed(() => {
        if (lokiLogs.value.length === 0) return '';
        const newest = lokiLogs.value[0];
        const oldest = lokiLogs.value[lokiLogs.value.length - 1];
        return `${newest.time_str} ~ ${oldest.time_str}`;
    });

    const logKey = (log) => log.ts_ns + '|' + log.raw;

    const fetchPage = async (beforeNs) => {
        const services = lokiServiceFilter.value.length === lokiServices.length
            ? ''
            : lokiServiceFilter.value.join(',');
        const result = await api.fetchLokiLogs({
            beforeNs,
            services,
            keyword: lokiKeyword.value.trim(),
            limit: PAGE_SIZE
        });
        return result.data || { logs: [], next_before_ns: '', has_more: false };
    };

    // 从最新一页重新加载
    const reloadLokiLogs = async () => {
        const seq = ++lokiRequestSeq;
        lokiLoading.value = true;
        lokiLoadingOlder.value = false;
        try {
            const page = await fetchPage('');
            if (seq !== lokiRequestSeq) return;
            lokiLogs.value = page.logs;
            lokiNextBeforeNs = page.next_before_ns;
            lokiCanLoadOlder.value = page.has_more;
        } catch (error) {
            if (seq !== lokiRequestSeq) return;
            console.error('Fetch Loki logs error:', error);
            showToast(error.message, 'error');
        } finally {
            if (seq === lokiRequestSeq) lokiLoading.value = false;
        }
    };

    // 加载更早的一页，接在列表末尾
    const loadOlderLogs = async () => {
        if (lokiLoading.value || lokiLoadingOlder.value || !lokiCanLoadOlder.value || !lokiNextBeforeNs) return;
        const seq = lokiRequestSeq;
        lokiLoadingOlder.value = true;
        try {
            const page = await fetchPage(lokiNextBeforeNs);
            if (seq !== lokiRequestSeq) return;
            const existing = new Set(lokiLogs.value.map(logKey));
            const olderLogs = page.logs.filter(l => !existing.has(logKey(l)));
            lokiLogs.value = [...lokiLogs.value, ...olderLogs];
            lokiNextBeforeNs = page.next_before_ns;
            lokiCanLoadOlder.value = page.has_more;
        } catch (error) {
            if (seq !== lokiRequestSeq) return;
            console.error('Fetch older Loki logs error:', error);
            showToast(error.message, 'error');
        } finally {
            if (seq === lokiRequestSeq) lokiLoadingOlder.value = false;
        }
    };

    const initLokiLogs = () => reloadLokiLogs();

    // 刷新：回到顶部并拉最新
    const refreshLokiLogs = () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return reloadLokiLogs();
    };

    // 切换服务过滤，至少保留一个
    const toggleServiceFilter = (svc) => {
        const idx = lokiServiceFilter.value.indexOf(svc);
        if (idx > -1) {
            if (lokiServiceFilter.value.length === 1) return;
            lokiServiceFilter.value.splice(idx, 1);
        } else {
            lokiServiceFilter.value.push(svc);
        }
        refreshLokiLogs();
    };

    const searchLokiLogs = () => refreshLokiLogs();

    const clearLokiKeyword = () => {
        if (!lokiKeyword.value) return;
        lokiKeyword.value = '';
        refreshLokiLogs();
    };

    // 向上箭头：同刷新
    const scrollToTop = () => refreshLokiLogs();

    // 向下箭头：到底部并拉更早的一页
    const scrollToBottom = async () => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
        await loadOlderLogs();
    };

    // 滚到底部附近时自动加载更早的日志
    const handleLokiScroll = () => {
        const distance = document.body.scrollHeight - (window.scrollY + window.innerHeight);
        if (distance < LOAD_OLDER_THRESHOLD) {
            loadOlderLogs();
        }
    };

    const activateLokiLogs = () => {
        window.addEventListener('scroll', handleLokiScroll, { passive: true });
        if (lokiLogs.value.length === 0) {
            initLokiLogs();
        }
    };

    const deactivateLokiLogs = () => {
        window.removeEventListener('scroll', handleLokiScroll);
    };

    return {
        lokiServices,
        lokiServiceFilter,
        lokiKeyword,
        lokiLogs,
        lokiLoading,
        lokiLoadingOlder,
        lokiCanLoadOlder,
        lokiTimeRange,
        initLokiLogs,
        loadOlderLogs,
        refreshLokiLogs,
        toggleServiceFilter,
        searchLokiLogs,
        clearLokiKeyword,
        scrollToTop,
        scrollToBottom,
        activateLokiLogs,
        deactivateLokiLogs
    };
};
