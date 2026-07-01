import bpy
from bpy.types import Panel, AddonPreferences, Operator
from . import operators as ops


# -------------------- 多语言文字 --------------------
_LABELS = {
    "zh": {
        "panel_title":      "Unity Walk",
        "movement":         "移动",
        "base_speed":       "基础速度",
        "sensitivity":      "鼠标灵敏度",
        "damping":          "加速/刹车平滑程度",
        "preferences":      "偏好设置",
        "speed_mod":        "速度修饰",
        "sprint":           "冲刺倍率",
        "slow":             "慢速倍率",
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
        # 使用说明
        "help_title":   "使用说明",
        "reset_btn":    "重置参数",
    },
    "en": {
        "panel_title":      "Unity Walk",
        "movement":         "Movement",
        "base_speed":       "Base Speed",
        "sensitivity":      "Mouse Sensitivity",
        "damping":          "Accel/Brake Smoothness",
        "preferences":      "Preferences",
        "speed_mod":        "Speed Modifiers",
        "sprint":           "Sprint Multiplier",
        "slow":             "Slow Multiplier",
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
        # usage guide
        "help_title":   "Usage Guide",
        "reset_btn":    "Reset Parameters",
    },
}


_USAGE = {
    "zh": [
        ("右键 + 移动鼠标", "进入第一人称导航"),
        ("W/S/A/D/Q/E",     "前进/后退/左移/右移/上升/下降"),
        ("Shift",           "加速移动"),
        ("Alt",             "减速移动"),
        ("滚轮",            "调整移动速度倍率"),
        ("ESC",             "强制退出导航"),
    ],
    "en": [
        ("RMB + Move Mouse",  "Enter first-person navigation"),
        ("W/S/A/D/Q/E",       "Forward/Backward/Left/Right/Up/Down"),
        ("Shift",             "Sprint"),
        ("Alt",               "Slow"),
        ("Scroll Up / Down",  "Adjust speed multiplier"),
        ("ESC",               "Force exit navigation"),
    ],
}


def get_labels():
    locale = bpy.app.translations.locale
    lang = "zh" if locale.startswith("zh") else "en"
    return _LABELS[lang], _USAGE[lang]


# -------------------- 重置参数 Operator --------------------
class UW_OT_reset_params(Operator):
    bl_idname = "uw.reset_params"
    bl_label = "Reset Parameters"
    bl_description = "Reset all Unity Walk parameters to default values"

    def execute(self, context):
        scene = context.scene
        scene.uw_base_max_speed     = ops.BASE_MAX_SPEED
        scene.uw_mouse_sensitivity  = ops.MOUSE_SENSITIVITY
        scene.uw_damping            = ops.DAMPING
        scene.uw_sprint_multiplier  = ops.SPRINT_MULTIPLIER
        scene.uw_slow_multiplier    = ops.SLOW_MULTIPLIER
        scene.uw_cursor_style       = ops.CURSOR_STYLE
        scene.uw_warp_margin        = ops.WARP_MARGIN
        scene.uw_coast_stop_threshold = ops.COAST_STOP_THRESHOLD
        scene.uw_coast_max_duration   = ops.COAST_MAX_DURATION
        return {"FINISHED"}


# -------------------- AddonPreferences --------------------
class UnityWalkPreferences(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout
        L, usage = get_labels()

        # 使用说明两列表格
        box = layout.box()
        box.label(text=L["help_title"], icon="INFO", translate=False)
        col = box.column(align=True)
        for key, desc in usage:
            if desc is None:
                # 分类标题行
                row = col.row()
                row.label(text=key, translate=False)
                col.separator(factor=0.3)
            else:
                split = col.split(factor=0.38, align=True)
                split.label(text=key, translate=False)
                split.label(text=desc, translate=False)
        layout.separator()
        layout.operator("uw.reset_params", icon="LOOP_BACK", text=L["reset_btn"], translate=False)


# -------------------- N面板 --------------------
class VIEW3D_PT_unity_walk(Panel):
    bl_label = "Unity Walk"
    bl_idname = "VIEW3D_PT_unity_walk"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "View"

    def draw(self, context):
        L, _ = get_labels()
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)

        # ---------- 第一层 ----------
        col.label(text=L["movement"], translate=False)
        col.prop(scene, "uw_base_max_speed",    text=L["base_speed"],   translate=False)
        col.prop(scene, "uw_mouse_sensitivity",  text=L["sensitivity"],  translate=False)
        col.prop(scene, "uw_damping",            text=L["damping"],      translate=False)

        # ---------- 折叠层 ----------
        box = layout.box()
        row = box.row()
        row.prop(scene, "uw_prefs_expanded",
                 icon="TRIA_DOWN" if scene.uw_prefs_expanded else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text=L["preferences"], translate=False)

        if scene.uw_prefs_expanded:
            col2 = box.column(align=True)

            col2.label(text=L["speed_mod"], translate=False)
            col2.prop(scene, "uw_sprint_multiplier", text=L["sprint"], translate=False)
            col2.prop(scene, "uw_slow_multiplier",   text=L["slow"],   translate=False)

            col2.separator()
            col2.label(text=L["cursor"], translate=False)
            col2.prop(scene, "uw_cursor_style", text=L["cursor_style"], translate=False)

            col2.separator()
            col2.label(text=L["warp"], translate=False)
            col2.prop(scene, "uw_warp_margin", text=L["warp_margin"], translate=False)

            col2.separator()
            col2.label(text=L["coasting"], translate=False)
            col2.prop(scene, "uw_coast_stop_threshold", text=L["coast_stop"],     translate=False)
            col2.prop(scene, "uw_coast_max_duration",   text=L["coast_duration"], translate=False)


# -------------------- Scene属性 --------------------
def register_properties():
    Scene = bpy.types.Scene

    Scene.uw_prefs_expanded = bpy.props.BoolProperty(
        name="展开偏好设置", default=False
    )
    Scene.uw_base_max_speed = bpy.props.FloatProperty(
        name="基础速度", default=ops.BASE_MAX_SPEED,
        min=0.1, max=100.0, step=10, precision=1,
        description="滚轮倍率为1.0时的最大移动速度（单位/秒）。滚轮可在导航中实时调整倍率"
    )
    Scene.uw_mouse_sensitivity = bpy.props.FloatProperty(
        name="鼠标灵敏度", default=ops.MOUSE_SENSITIVITY,
        min=0.0001, max=0.02, step=0.1, precision=4,
        description="鼠标每移动1像素对应的视角旋转角度（弧度）。数值越大转动越快"
    )
    Scene.uw_damping = bpy.props.FloatProperty(
        name="加速/刹车手感", default=ops.DAMPING,
        min=1.0, max=30.0, step=10, precision=1,
        description="控制起步加速和松键刹车的平滑程度。数值越大响应越灵敏，越小越有漂移感"
    )
    Scene.uw_sprint_multiplier = bpy.props.FloatProperty(
        name="冲刺倍率", default=ops.SPRINT_MULTIPLIER,
        min=1.0, max=10.0, step=10, precision=1,
        description="按住 Shift 时的速度倍率"
    )
    Scene.uw_slow_multiplier = bpy.props.FloatProperty(
        name="慢速倍率", default=ops.SLOW_MULTIPLIER,
        min=0.01, max=1.0, step=1, precision=2,
        description="按住 Alt 时的速度倍率"
    )
    Scene.uw_cursor_style = bpy.props.EnumProperty(
        name="光标样式",
        items=[
            ("NONE",      "隐藏","导航时隐藏鼠标光标"),
            ("SCROLL_XY", "四向箭头","导航时显示四向移动光标"),
            ("CROSSHAIR", "十字准星","导航时显示十字准星"),
            ("DOT",       "圆点","导航时显示圆点"),
        ],
        default="SCROLL_XY",
        description="进入导航模式后鼠标光标的显示样式"
    )
    Scene.uw_warp_margin = bpy.props.IntProperty(
        name="边界边距", default=ops.WARP_MARGIN,
        min=0, max=100,
        description="鼠标距视口边缘多少像素时触发传送到对侧，防止光标移出视口范围"
    )
    Scene.uw_coast_stop_threshold = bpy.props.FloatProperty(
        name="停止阈值", default=ops.COAST_STOP_THRESHOLD,
        min=0.001, max=1.0, step=1, precision=3,
        description="松开右键后惯性滑行速度低于此值时视为已停止（单位/秒）"
    )
    Scene.uw_coast_max_duration = bpy.props.FloatProperty(
        name="最长时间", default=ops.COAST_MAX_DURATION,
        min=0.1, max=10.0, step=10, precision=1,
        description="惯性滑行的最长持续时间上限（秒），防止极端情况下长时间停不下来"
    )


def unregister_properties():
    Scene = bpy.types.Scene
    props = [
        "uw_prefs_expanded",
        "uw_base_max_speed", "uw_mouse_sensitivity", "uw_damping",
        "uw_sprint_multiplier", "uw_slow_multiplier", "uw_cursor_style",
        "uw_warp_margin", "uw_coast_stop_threshold", "uw_coast_max_duration",
    ]
    for p in props:
        if hasattr(Scene, p):
            delattr(Scene, p)


classes = (
    UW_OT_reset_params,
    UnityWalkPreferences,
    VIEW3D_PT_unity_walk,
)
