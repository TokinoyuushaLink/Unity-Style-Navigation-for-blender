import bpy

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
        "help_title":       "使用说明",
        "reset_btn":        "重置参数",
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
        "help_title":       "Usage Guide",
        "reset_btn":        "Reset Parameters",
    },
}

_USAGE = {
    "zh": [
        ("右键 + 移动鼠标", "进入第一人称导航"),
        ("W/S/A/D/Q/E",     "前进/后退/左移/右移/上升/下降"),
        ("Shift",           "加速移动"),
        ("Alt",             "减速移动"),
        ("滚轮",            "调整移动速度"),
        ("ESC",             "强制退出导航"),
    ],
    "en": [
        ("RMB + Move Mouse",  "Enter first-person navigation"),
        ("W/S/A/D/Q/E",       "Forward/Backward/Left/Right/Up/Down"),
        ("Shift",             "Sprint"),
        ("Alt",               "Slow"),
        ("Scroll Up / Down",  "Adjust speed"),
        ("ESC",               "Force exit navigation"),
    ],
}


def get_labels():
    locale = bpy.app.translations.locale
    lang = "zh" if locale.startswith("zh") else "en"
    return _LABELS[lang], _USAGE[lang]
