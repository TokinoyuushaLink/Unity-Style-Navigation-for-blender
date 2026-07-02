import bpy
from bpy.types import Panel, AddonPreferences, Operator
from . import operators as ops
from .i18n import get_labels

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
        prefs.trackpad_sensitivity  = ops.MOUSE_SENSITIVITY
        prefs.damping               = ops.DAMPING
        prefs.sprint_multiplier     = ops.SPRINT_MULTIPLIER
        prefs.slow_multiplier       = ops.SLOW_MULTIPLIER
        prefs.cursor_style          = ops.CURSOR_STYLE
        prefs.warp_margin           = ops.WARP_MARGIN
        prefs.coast_stop_threshold  = ops.COAST_STOP_THRESHOLD
        prefs.coast_max_duration    = ops.COAST_MAX_DURATION
        return {"FINISHED"}


# -------------------- AddonPreferences --------------------
def _update_allow_trackpad(self, context):
    import sys
    addon_init = sys.modules.get(_ADDON_PACKAGE)
    if addon_init is None:
        return
    prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
    enabled = prefs.allow_trackpad and prefs.use_trackpad
    for km, kmi in addon_init.addon_keymaps:
        if kmi.idname == "view3d.unity_walk_trackpad":
            kmi.active = enabled
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _update_use_trackpad(self, context):
    import sys
    addon_init = sys.modules.get(_ADDON_PACKAGE)
    if addon_init is None:
        return
    prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
    enabled = prefs.allow_trackpad and prefs.use_trackpad
    for km, kmi in addon_init.addon_keymaps:
        if kmi.idname == "view3d.unity_walk_trackpad":
            kmi.active = enabled


class UnityWalkPreferences(AddonPreferences):
    bl_idname = _ADDON_PACKAGE

    # 触控板
    allow_trackpad: bpy.props.BoolProperty(
        name="允许触控板模式 / Allow Trackpad Mode",
        default=False,
        update=_update_allow_trackpad,
        description=(
            "允许触控板导航功能。开启后可在N面板启用。"
            "/ Allow trackpad navigation."
        )
    )
    use_trackpad: bpy.props.BoolProperty(
        name="启用触控板模式 / Enable Trackpad Mode",
        default=False,
        update=_update_use_trackpad,
        description="启用触控板导航 / Enable trackpad navigation"
    )
    trackpad_sensitivity: bpy.props.FloatProperty(
        name="触控板灵敏度", default=ops.MOUSE_SENSITIVITY,
        min=0.0001, max=0.02, step=0.1, precision=4,
        description="触控板双指滑动每移动1像素对应的视角旋转量（弧度）"
    )

    # 速度
    target_speed: bpy.props.FloatProperty(
        name="速度", default=ops.TARGET_SPEED,
        min=0.1, max=1000.0, step=10, precision=1,
        description="目标移动速度（单位/秒）。滚轮在导航中实时调整并自动保存"
    )
    speed_step: bpy.props.FloatProperty(
        name="滚轮步进", default=ops.SPEED_STEP,
        min=1.01, max=2.0, step=1, precision=2,
        description="每次滚轮调整速度的缩放倍率。上滚×此值，下滚÷此值"
    )
    speed_min: bpy.props.FloatProperty(
        name="最小速度", default=ops.SPEED_MIN,
        min=0.01, max=10.0, step=1, precision=2,
        description="滚轮下调速度的下限（单位/秒）"
    )
    speed_max: bpy.props.FloatProperty(
        name="最大速度", default=ops.SPEED_MAX,
        min=1.0, max=1000.0, step=100, precision=1,
        description="滚轮上调速度的上限（单位/秒）"
    )

    # 视角/移动
    mouse_sensitivity: bpy.props.FloatProperty(
        name="鼠标灵敏度", default=ops.MOUSE_SENSITIVITY,
        min=0.0001, max=0.02, step=0.1, precision=4,
        description="鼠标每移动1像素对应的视角旋转量（弧度）"
    )
    damping: bpy.props.FloatProperty(
        name="加速/刹车手感", default=ops.DAMPING,
        min=1.0, max=30.0, step=10, precision=1,
        description="控制速度趋向目标值的平滑程度。越大越灵敏，越小越有漂移感"
    )
    sprint_multiplier: bpy.props.FloatProperty(
        name="冲刺倍率", default=ops.SPRINT_MULTIPLIER,
        min=1.0, max=10.0, step=10, precision=1,
        description="按住Shift时的临时速度倍率，松开后不影响目标速度"
    )
    slow_multiplier: bpy.props.FloatProperty(
        name="慢速倍率", default=ops.SLOW_MULTIPLIER,
        min=0.01, max=1.0, step=1, precision=2,
        description="按住Alt时的临时速度倍率，松开后不影响目标速度"
    )

    # 光标
    cursor_style: bpy.props.EnumProperty(
        name="光标样式",
        items=[
            ("NONE",      "Hidden / 隐藏",       "导航时隐藏鼠标光标"),
            ("SCROLL_XY", "Scroll XY / 四向箭头", "导航时显示四向移动光标"),
            ("CROSSHAIR", "Crosshair / 十字准星", "导航时显示十字准星"),
            ("DOT",       "Dot / 圆点",           "导航时显示圆点"),
        ],
        default="SCROLL_XY",
        description="进入导航模式后鼠标光标的显示样式"
    )

    # 边界teleport
    warp_margin: bpy.props.IntProperty(
        name="边界边距", default=ops.WARP_MARGIN,
        min=0, max=100,
        description="鼠标距视口边缘多少像素内触发传送到对侧，设为0则禁用"
    )

    # 惯性滑行
    coast_stop_threshold: bpy.props.FloatProperty(
        name="停止阈值", default=ops.COAST_STOP_THRESHOLD,
        min=0.001, max=1.0, step=1, precision=3,
        description="惯性滑行速度低于此值时视为已停止（单位/秒）"
    )
    coast_max_duration: bpy.props.FloatProperty(
        name="最长时间", default=ops.COAST_MAX_DURATION,
        min=0.1, max=10.0, step=10, precision=1,
        description="惯性滑行的硬性时间上限（秒）"
    )

    # UI状态
    prefs_expanded: bpy.props.BoolProperty(
        name="展开偏好设置", default=False
    )

    def draw(self, context):
        layout = self.layout
        L, usage = get_labels()

        layout.prop(self, "allow_trackpad", translate=False)
        layout.separator()

        box = layout.box()
        box.label(text=L["help_title"], icon="INFO", translate=False)
        col = box.column(align=True)
        for key, desc in usage:
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
        prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
        col = layout.column(align=True)

        # ---------- 第一层 ----------
        col.label(text=L["movement"], translate=False)
        col.prop(prefs, "target_speed",      text=L["base_speed"],  translate=False)
        col.prop(prefs, "speed_step",        text=L["speed_step"],  translate=False)
        col.prop(prefs, "mouse_sensitivity", text=L["sensitivity"],  translate=False)
        col.prop(prefs, "damping",           text=L["damping"],      translate=False)
        col.separator()
        if prefs.allow_trackpad:
            col.prop(prefs, "use_trackpad",
                     text=L.get("use_trackpad", "Enable Trackpad Mode"), translate=False)
            row = col.row()
            row.enabled = prefs.use_trackpad
            row.prop(prefs, "trackpad_sensitivity",
                     text=L.get("trackpad_sensitivity", "Trackpad Sensitivity"), translate=False)

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
        name="速度", default=ops.TARGET_SPEED,
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
