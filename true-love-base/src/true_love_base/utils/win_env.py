# -*- coding: utf-8 -*-
"""
WinEnv - Windows 运行环境

wxautox4 靠 UI 自动化操作微信，对桌面环境有要求：
- 机器不能睡眠、熄屏，否则微信窗口操作不了
- 屏幕缩放必须是 100%，否则下载图片等依赖坐标的操作会失败
"""

import logging
import sys
from typing import Optional

LOG = logging.getLogger("WinEnv")

# SetThreadExecutionState 的标志位
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# 100% 缩放对应的 DPI
STANDARD_DPI = 96


def keep_awake() -> None:
    """
    阻止系统睡眠和熄屏

    状态绑定在调用线程上，线程结束后自动恢复，所以要在主线程里调用。
    """
    if sys.platform != 'win32':
        return

    try:
        import ctypes
        previous = ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
    except Exception as e:
        LOG.warning(f"Could not keep the system awake: {e}")
        return
    # 失败时返回 NULL
    if not previous:
        LOG.warning("Windows rejected the request to keep the system awake")
        return
    LOG.info("Keeping the system and display awake")


def display_scale_percent() -> Optional[int]:
    """
    获取当前用户的屏幕缩放比例

    读注册表而不是调 DPI 接口：进程没有声明 DPI 感知时接口返回的是虚拟值，
    而声明 DPI 感知会改变 wxautox4 的坐标系。

    Returns:
        缩放百分比（100 表示 100%），读不到时返回 None
    """
    if sys.platform != 'win32':
        return None

    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics") as key:
            dpi, _ = winreg.QueryValueEx(key, "AppliedDPI")
        return round(dpi * 100 / STANDARD_DPI)
    except Exception as e:
        LOG.debug(f"Could not read display scaling: {e}")
        return None
