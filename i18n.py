import sys
import bpy

_IS_MAC = sys.platform == "darwin"

_LABELS = {
    "zh": {
        "panel_title":      "Unity Style Walk Navigation",
        "movement":         "移动",
        "base_speed":       "速度",
        "speed_step":       "滚轮步进",
        "sensitivity":      "鼠标灵敏度",
        "fov_compensation": "FOV 旋转补偿",
        "damping":          "阻力",
        "preferences":      "偏好设置",
        "speed_mod":        "速度修饰",
        "sprint":           "冲刺倍率",
        "slow":             "慢速倍率",
        "speed_min":        "最小速度",
        "speed_max":        "最大速度",
        "cursor":           "光标",
        "cursor_style":     "样式",
        "warp":             "光标边界传送",
        "warp_margin":      "边距(px)",
        "time_threshold_group": "长按触发",
        "enable_time_threshold": "启用",
        "click_time_threshold":  "触发时间(s)",
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
        "trackpad_speed_step":  "触控板速度调整步进",
        "trackpad":             "触控板",
        "trackpad_keymap_hint": "如需启用触控板，请到：编辑 > 偏好设置 > 键位映射 中勾选启用'Unity Style Walk Navigation (Trackpad)'",
        "coord_system":         "透视坐标",
        "ortho_coord_system":   "正交坐标",
        "coord_group":          "坐标",
        "keymap_group":         "键位",
        "ortho_keymap":         "正交键位",
        "ortho":                "正交视图",
        "ortho_zoom_scale":     "缩放倍率",
    },
    "en": {
        "panel_title":      "Unity Style Walk Navigation",
        "movement":         "Movement",
        "base_speed":       "Speed",
        "speed_step":       "Scroll Step",
        "sensitivity":      "Mouse Sensitivity",
        "fov_compensation": "FOV Compensation",
        "damping":          "Resistance Force",
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
        "time_threshold_group": "Long Press",
        "enable_time_threshold": "Enable",
        "click_time_threshold":  "Duration (s)",
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
        "coord_system":         "Perspective",
        "ortho_coord_system":   "Ortho",
        "coord_group":          "Coordinate",
        "keymap_group":         "Keymap",
        "ortho_keymap":         "Ortho",
        "ortho":                "Ortho View",
        "ortho_zoom_scale":     "Zoom Scale",
    },
}

_USAGE_MOUSE = {
    "zh": [
        ("右键 + 移动鼠标", "进入第一人称导航"),
        ("W/S/A/D/Q/E",     "前进/后退/左移/右移/上升/下降"),
        ("Shift",           "加速"),
        ("Alt",             "减速"),
        ("滚轮",            "调整移动速度"),
        ("Tab",             "切换视角移动的空间坐标系"),
        ("ESC",             "强制退出导航"),
    ],
    "en": [
        ("RMB + Move Mouse",  "Enter first-person navigation"),
        ("W/S/A/D/Q/E",       "Forward/Back/Left/Right/Up/Down"),
        ("Shift",             "Sprint"),
        ("Alt",               "Slow"),
        ("Scroll Up / Down",  "Adjust speed"),
        ("Tab",               "Toggle camera's move space coordinate"),
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
        ("Tab",              "切换视角移动的空间坐标系"),
        ("单指移动 / 超时",   "带滑行退出"),
        ("ESC",              "立刻退出"),
    ],
    "en": [
        ("Two-finger swipe",        "Enter navigation, control view"),
        ("W/S/A/D/Q/E",             "Forward/Back/Left/Right/Up/Down"),
        ("Shift",                   "Sprint"),
        ("Command",                 "Slow"),
        ("Option + swipe up/down",  "Adjust speed"),
        ("Tab",                     "Toggle camera's move space coordinate"),
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
        ("Tab",               "切换视角移动的空间坐标系"),
        ("单指移动 / 超时",    "带滑行退出"),
        ("ESC",               "立刻退出"),
    ],
    "en": [
        ("Two-finger swipe",      "Enter navigation, control view"),
        ("W/S/A/D/Q/E",           "Forward/Back/Left/Right/Up/Down"),
        ("Shift",                 "Sprint"),
        ("Alt",                   "Slow"),
        ("Ctrl + swipe up/down",  "Adjust speed"),
        ("Tab",                   "Toggle camera's move space coordinate"),
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
        ("*", "FOV Compensation"):          "FOV 旋转补偿",
        ("*", "Drag"):                       "阻力",
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
        ("*", "Coordinate"):                 "坐标",
        ("*", "Ortho Coordinate"):           "正交坐标",
        ("*", "Ortho Keymap"):               "正交键位",
        ("*", "QEAD (Unity)"):               "QEAD（Unity风格）",
        ("*", "WASD (Default)"):             "WASD（默认）",
        ("*", "World Space"):                 "世界空间",
        ("*", "View Space"):                  "视角空间",
        ("*", "Reset Parameters"):          "重置参数",
        ("*", "Reset all Unity Walk parameters to default values"): "重置所有参数为默认值",
        ("*", "Usage Guide"):               "使用说明",
        ("*", "Ortho Zoom Scale"):          "缩放倍率",
    },
}
