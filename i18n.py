import sys
import bpy

_IS_MAC = sys.platform == "darwin"

_LABELS = {
    "zh": {
        "panel_title":      "Unity Walk",
        "movement":         "移动",
        "base_speed":       "速度",
        "speed_step":       "滚轮步进",
        "sensitivity":      "鼠标灵敏度",
        "damping":          "加速/刹车手感",
        "preferences":      "偏好设置",
        "speed_mod":        "速度修饰",
        "sprint":           "冲刺倍率",
        "slow":             "慢速倍率",
        "speed_min":        "最小速度",
        "speed_max":        "最大速度",
        "cursor":           "光标",
        "cursor_style":     "样式",
        "warp":             "边界 Teleport",
        "warp_margin":      "边距(px)",
        "coasting":         "惯性滑行",
        "coast_stop":       "停止阈值",
        "coast_duration":   "最长时间(s)",
        "cur_none":         "隐藏",
        "cur_scroll":       "四向箭头",
        "cur_cross":        "十字准星",
        "cur_dot":          "圆点",
        "help_title":           "使用说明",
        "reset_btn":            "重置参数",
        "trackpad_sensitivity": "触控板灵敏度",
        "trackpad_speed_step":  "触控板调速步进",
        "trackpad":             "触控板",
        "trackpad_keymap_hint": "如需启用触控板，请到：编辑 > 偏好设置 > 键位映射 中勾选启用'Unity Style Walk Navigation (Trackpad)'",
    },
    "en": {
        "panel_title":      "Unity Walk",
        "movement":         "Movement",
        "base_speed":       "Speed",
        "speed_step":       "Scroll Step",
        "sensitivity":      "Mouse Sensitivity",
        "damping":          "Accel/Brake Feel",
        "preferences":      "Preferences",
        "speed_mod":        "Speed Modifiers",
        "sprint":           "Sprint Multiplier",
        "slow":             "Slow Multiplier",
        "speed_min":        "Min Speed",
        "speed_max":        "Max Speed",
        "cursor":           "Cursor",
        "cursor_style":     "Style",
        "warp":             "Edge Teleport",
        "warp_margin":      "Margin (px)",
        "coasting":         "Inertia Coasting",
        "coast_stop":       "Stop Threshold",
        "coast_duration":   "Max Duration (s)",
        "cur_none":         "Hidden",
        "cur_scroll":       "Scroll XY",
        "cur_cross":        "Crosshair",
        "cur_dot":          "Dot",
        "help_title":           "Usage Guide",
        "reset_btn":            "Reset Parameters",
        "trackpad_sensitivity": "Trackpad Sensitivity",
        "trackpad_speed_step":  "Trackpad Speed Step",
        "trackpad":             "Trackpad",
        "trackpad_keymap_hint": "To enable trackpad: Edit > Preferences > Keymap , enable 'Unity Style Walk Navigation (Trackpad)'",
    },
}

_USAGE_MOUSE = {
    "zh": [
        ("右键 + 移动鼠标", "进入第一人称导航"),
        ("W/S/A/D/Q/E",     "前进/后退/左移/右移/上升/下降"),
        ("Shift",           "加速"),
        ("Alt",             "减速"),
        ("滚轮",            "调整移动速度"),
        ("ESC",             "强制退出导航"),
    ],
    "en": [
        ("RMB + Move Mouse",  "Enter first-person navigation"),
        ("W/S/A/D/Q/E",       "Forward/Back/Left/Right/Up/Down"),
        ("Shift",             "Sprint"),
        ("Alt",               "Slow"),
        ("Scroll Up / Down",  "Adjust speed"),
        ("ESC",               "Force exit"),
    ],
}

_USAGE_TRACKPAD_MAC = {
    "zh": [
        ("双指滑动",         "进入导航并控制视角"),
        ("W/S/A/D/Q/E",      "前进/后退/左移/右移/上升/下降"),
        ("Shift",            "加速"),
        ("Command",          "减速"),
        ("Option + 上下滑动", "调整移动速度"),
        ("单指移动 / 超时",   "带滑行退出"),
        ("ESC",              "立刻退出"),
    ],
    "en": [
        ("Two-finger swipe",        "Enter navigation, control view"),
        ("W/S/A/D/Q/E",             "Forward/Back/Left/Right/Up/Down"),
        ("Shift",                   "Sprint"),
        ("Command",                 "Slow"),
        ("Option + swipe up/down",  "Adjust speed"),
        ("Single finger / timeout", "Exit with coasting"),
        ("ESC",                     "Force exit"),
    ],
}

_USAGE_TRACKPAD_WIN = {
    "zh": [
        ("双指滑动",          "进入导航并控制视角"),
        ("W/S/A/D/Q/E",       "前进/后退/左移/右移/上升/下降"),
        ("Shift",             "加速"),
        ("Alt",               "减速"),
        ("Ctrl + 上下滑动",   "调整移动速度"),
        ("单指移动 / 超时",    "带滑行退出"),
        ("ESC",               "立刻退出"),
    ],
    "en": [
        ("Two-finger swipe",      "Enter navigation, control view"),
        ("W/S/A/D/Q/E",           "Forward/Back/Left/Right/Up/Down"),
        ("Shift",                 "Sprint"),
        ("Alt",                   "Slow"),
        ("Ctrl + swipe up/down",  "Adjust speed"),
        ("Single finger / timeout", "Exit with coasting"),
        ("ESC",                   "Force exit"),
    ],
}


def _is_trackpad_enabled():
    """检查用户keymap里触控板operator是否已启用"""
    wm = bpy.context.window_manager
    for kc in (wm.keyconfigs.user, wm.keyconfigs.addon):
        if kc is None:
            continue
        for km in kc.keymaps:
            for kmi in km.keymap_items:
                if kmi.idname == "view3d.unity_walk_trackpad":
                    return kmi.active
    return False


def get_labels(trackpad_mode=False):
    locale = bpy.app.translations.locale
    lang = "zh" if locale.startswith("zh") else "en"
    if trackpad_mode is None:
        trackpad_mode = _is_trackpad_enabled()
    if trackpad_mode:
        usage = _USAGE_TRACKPAD_MAC[lang] if _IS_MAC else _USAGE_TRACKPAD_WIN[lang]
    else:
        usage = _USAGE_MOUSE[lang]
    return _LABELS[lang], usage


# Blender翻译字典: (context, msgid) -> translated_str
# context用"*"表示通用,不限于特定operator/panel
translations_dict = {
    "zh_CN": {
        ("*", "Trackpad Sensitivity"):      "触控板灵敏度",
        ("*", "Trackpad Speed Step"):       "触控板调速步进",
        ("*", "Speed"):                     "速度",
        ("*", "Scroll Step"):               "滚轮步进",
        ("*", "Min Speed"):                 "最小速度",
        ("*", "Max Speed"):                 "最大速度",
        ("*", "Mouse Sensitivity"):         "鼠标灵敏度",
        ("*", "Accel/Brake Feel"):          "加速/刹车手感",
        ("*", "Sprint Multiplier"):         "冲刺倍率",
        ("*", "Slow Multiplier"):           "慢速倍率",
        ("*", "Cursor Style"):              "光标样式",
        ("*", "Hidden"):                    "隐藏",
        ("*", "Scroll XY"):                 "四向箭头",
        ("*", "Crosshair"):                 "十字准星",
        ("*", "Dot"):                       "圆点",
        ("*", "Edge Margin"):               "边界边距",
        ("*", "Stop Threshold"):            "停止阈值",
        ("*", "Max Duration"):              "最长时间",
        ("*", "Expand Preferences"):        "展开偏好设置",
        ("*", "Reset Parameters"):          "重置参数",
        ("*", "Reset all Unity Walk parameters to default values"): "重置所有参数为默认值",
        ("*", "Usage Guide"):               "使用说明",
    },
}
