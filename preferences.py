import bpy
from bpy.types import Panel, AddonPreferences, Operator
from . import operators as ops
from .i18n import get_labels, _is_trackpad_enabled

_ADDON_PACKAGE = __package__  # 模块加载时记录包名


# -------------------- 重置参数 Operator --------------------
class UW_OT_reset_params(Operator):
    bl_idname = "uw.reset_params"
    bl_label = "Reset Parameters"
    bl_description = "Reset all Unity Walk parameters to default values"

    def execute(self, context):
        prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
        prefs.target_speed          = ops.TARGET_SPEED
        prefs.speed_step            = ops.SPEED_STEP
        prefs.speed_min             = ops.SPEED_MIN
        prefs.speed_max             = ops.SPEED_MAX
        prefs.mouse_sensitivity     = ops.MOUSE_SENSITIVITY
        prefs.trackpad_sensitivity  = 0.0015
        prefs.trackpad_speed_step   = 1.01
        prefs.damping               = ops.DAMPING
        prefs.sprint_multiplier     = ops.SPRINT_MULTIPLIER
        prefs.slow_multiplier       = ops.SLOW_MULTIPLIER
        prefs.cursor_style          = ops.CURSOR_STYLE
        prefs.warp_margin           = ops.WARP_MARGIN
        prefs.coast_stop_threshold  = ops.COAST_STOP_THRESHOLD
        prefs.coast_max_duration    = ops.COAST_MAX_DURATION
        return {"FINISHED"}


class UnityWalkPreferences(AddonPreferences):
    bl_idname = _ADDON_PACKAGE

    # 触控板
    trackpad_sensitivity: bpy.props.FloatProperty(
        name="Trackpad Sensitivity", default=0.0015,
        min=0.0001, max=0.02, step=0.1, precision=4,
        description="触控板双指滑动每移动1像素对应的视角旋转量（弧度）"
    )
    trackpad_speed_step: bpy.props.FloatProperty(
        name="Trackpad Speed Step", default=1.01,
        min=1.01, max=2.0, step=1, precision=2,
        description="修饰键+滑动调速时每次触发的速度缩放倍率，独立于滚轮步进"
    )

    # 速度
    target_speed: bpy.props.FloatProperty(
        name="Speed", default=ops.TARGET_SPEED,
        min=0.1, max=1000.0, step=10, precision=1,
        description="目标移动速度（单位/秒）。滚轮在导航中实时调整并自动保存"
    )
    speed_step: bpy.props.FloatProperty(
        name="Scroll Step", default=ops.SPEED_STEP,
        min=1.01, max=2.0, step=1, precision=2,
        description="每次滚轮调整速度的缩放倍率。上滚×此值，下滚÷此值"
    )
    speed_min: bpy.props.FloatProperty(
        name="Min Speed", default=ops.SPEED_MIN,
        min=0.01, max=10.0, step=1, precision=2,
        description="滚轮下调速度的下限（单位/秒）"
    )
    speed_max: bpy.props.FloatProperty(
        name="Max Speed", default=ops.SPEED_MAX,
        min=1.0, max=1000.0, step=100, precision=1,
        description="滚轮上调速度的上限（单位/秒）"
    )

    # 视角/移动
    mouse_sensitivity: bpy.props.FloatProperty(
        name="Mouse Sensitivity", default=ops.MOUSE_SENSITIVITY,
        min=0.0001, max=0.02, step=0.1, precision=4,
        description="鼠标每移动1像素对应的视角旋转量（弧度）"
    )
    damping: bpy.props.FloatProperty(
        name="Accel/Brake Feel", default=ops.DAMPING,
        min=1.0, max=30.0, step=10, precision=1,
        description="控制速度趋向目标值的平滑程度。越大越灵敏，越小越有漂移感"
    )
    sprint_multiplier: bpy.props.FloatProperty(
        name="Sprint Multiplier", default=ops.SPRINT_MULTIPLIER,
        min=1.0, max=10.0, step=10, precision=1,
        description="按住Shift时的临时速度倍率，松开后不影响目标速度"
    )
    slow_multiplier: bpy.props.FloatProperty(
        name="Slow Multiplier", default=ops.SLOW_MULTIPLIER,
        min=0.01, max=1.0, step=1, precision=2,
        description="按住Alt/Command时的临时速度倍率，松开后不影响目标速度"
    )

    # 光标
    cursor_style: bpy.props.EnumProperty(
        name="Cursor Style",
        items=[
            ("NONE",      "Hidden",    "导航时隐藏光标"),
            ("SCROLL_XY", "Scroll XY", "导航时显示四向箭头光标"),
            ("CROSSHAIR", "Crosshair", "导航时显示十字准星"),
            ("DOT",       "Dot",       "导航时显示圆点"),
        ],
        default="SCROLL_XY",
        description="导航时的光标样式"
    )

    # 边界teleport
    warp_margin: bpy.props.IntProperty(
        name="Edge Margin", default=ops.WARP_MARGIN,
        min=0, max=100,
        description="鼠标距视口边缘多少像素内触发传送到对侧，设为0则禁用"
    )

    # 惯性滑行
    coast_stop_threshold: bpy.props.FloatProperty(
        name="Stop Threshold", default=ops.COAST_STOP_THRESHOLD,
        min=0.001, max=1.0, step=1, precision=3,
        description="惯性滑行速度低于此值时视为已停止（单位/秒）"
    )
    coast_max_duration: bpy.props.FloatProperty(
        name="Max Duration", default=ops.COAST_MAX_DURATION,
        min=0.1, max=10.0, step=10, precision=1,
        description="惯性滑行的硬性时间上限（秒）"
    )

    # UI状态
    prefs_expanded: bpy.props.BoolProperty(
        name="Expand Preferences", default=False
    )

    def draw(self, context):
        layout = self.layout
        L, usage = get_labels(trackpad_mode=None)
        trackpad_on = _is_trackpad_enabled()

        if not trackpad_on:
            layout.label(text=L.get("trackpad_keymap_hint",
                      "To enable trackpad: Edit > Preferences > Keymap"),
                      icon="INFO", translate=False)
            layout.separator()

        layout.label(text=L["help_title"], translate=False)
        col = layout.column(align=True)
        for key, desc in usage:
            split = col.split(factor=0.38, align=True)
            split.label(text=key, translate=False)
            split.label(text=desc, translate=False)
        layout.separator()
        layout.operator("uw.reset_params", icon="LOOP_BACK")


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
        prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
        col = layout.column(align=True)

        # ---------- 第一层 ----------
        col.label(text=L["movement"], translate=False)
        col.prop(prefs, "target_speed",      text=L["base_speed"],  translate=False)
        col.prop(prefs, "speed_step",        text=L["speed_step"],  translate=False)
        col.prop(prefs, "mouse_sensitivity", text=L["sensitivity"],  translate=False)
        col.prop(prefs, "damping",           text=L["damping"],      translate=False)

        # 触控板参数：只在keymap里启用了触控板时显示
        trackpad_on = _is_trackpad_enabled()
        if trackpad_on:
            col.separator()
            col.label(text=L.get("trackpad", "Trackpad"), translate=False)
            sub = col.column(align=True)
            sub.prop(prefs, "trackpad_sensitivity",
                     text=L.get("trackpad_sensitivity", "Trackpad Sensitivity"), translate=False)
            sub.prop(prefs, "trackpad_speed_step",
                     text=L.get("trackpad_speed_step", "Trackpad Speed Step"), translate=False)

        # ---------- 折叠层 ----------
        box = layout.box()
        row = box.row()
        row.prop(prefs, "prefs_expanded",
                 icon="TRIA_DOWN" if prefs.prefs_expanded else "TRIA_RIGHT",
                 icon_only=True, emboss=False)
        row.label(text=L["preferences"], translate=False)

        if prefs.prefs_expanded:
            col2 = box.column(align=True)

            col2.label(text=L["speed_mod"], translate=False)
            col2.prop(prefs, "sprint_multiplier", text=L["sprint"],    translate=False)
            col2.prop(prefs, "slow_multiplier",   text=L["slow"],      translate=False)
            col2.prop(prefs, "speed_min",         text=L["speed_min"], translate=False)
            col2.prop(prefs, "speed_max",         text=L["speed_max"], translate=False)

            col2.separator()
            col2.label(text=L["cursor"], translate=False)
            col2.prop(prefs, "cursor_style", text=L["cursor_style"], translate=False)

            col2.separator()
            col2.label(text=L["warp"], translate=False)
            col2.prop(prefs, "warp_margin", text=L["warp_margin"], translate=False)

            col2.separator()
            col2.label(text=L["coasting"], translate=False)
            col2.prop(prefs, "coast_stop_threshold", text=L["coast_stop"],     translate=False)
            col2.prop(prefs, "coast_max_duration",   text=L["coast_duration"], translate=False)


# -------------------- Scene属性 --------------------
# 只保留target_speed在Scene里,因为滚轮调速需要写回并在下次进入导航时恢复
def register_properties():
    bpy.types.Scene.uw_target_speed = bpy.props.FloatProperty(
        name="Speed", default=ops.TARGET_SPEED,
        min=0.1, max=1000.0, step=10, precision=1,
        description="目标移动速度（单位/秒），滚轮在导航中实时调整并自动保存"
    )


def unregister_properties():
    if hasattr(bpy.types.Scene, "uw_target_speed"):
        delattr(bpy.types.Scene, "uw_target_speed")


classes = (
    UW_OT_reset_params,
    UnityWalkPreferences,
    VIEW3D_PT_unity_walk,
)
