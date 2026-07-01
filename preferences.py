import bpy
from bpy.types import Panel, AddonPreferences, Operator
from . import operators as ops
from .i18n import get_labels


# -------------------- 重置参数 Operator --------------------
class UW_OT_reset_params(Operator):
    bl_idname = "uw.reset_params"
    bl_label = "Reset Parameters"
    bl_description = "Reset all Unity Walk parameters to default values"

    def execute(self, context):
        scene = context.scene
        scene.uw_target_speed         = ops.TARGET_SPEED
        scene.uw_speed_step           = ops.SPEED_STEP
        scene.uw_speed_min            = ops.SPEED_MIN
        scene.uw_speed_max            = ops.SPEED_MAX
        scene.uw_mouse_sensitivity    = ops.MOUSE_SENSITIVITY
        scene.uw_damping              = ops.DAMPING
        scene.uw_sprint_multiplier    = ops.SPRINT_MULTIPLIER
        scene.uw_slow_multiplier      = ops.SLOW_MULTIPLIER
        scene.uw_cursor_style         = ops.CURSOR_STYLE
        scene.uw_warp_margin          = ops.WARP_MARGIN
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
        col.prop(scene, "uw_target_speed",       text=L["base_speed"],  translate=False)
        col.prop(scene, "uw_speed_step",         text=L["speed_step"],  translate=False)
        col.prop(scene, "uw_mouse_sensitivity",  text=L["sensitivity"], translate=False)
        col.prop(scene, "uw_damping",            text=L["damping"],     translate=False)

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
            col2.prop(scene, "uw_sprint_multiplier", text=L["sprint"],    translate=False)
            col2.prop(scene, "uw_slow_multiplier",   text=L["slow"],      translate=False)
            col2.prop(scene, "uw_speed_min",         text=L["speed_min"], translate=False)
            col2.prop(scene, "uw_speed_max",         text=L["speed_max"], translate=False)

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
    Scene.uw_target_speed = bpy.props.FloatProperty(
        name="速度", default=ops.TARGET_SPEED,
        min=0.1, max=1000.0, step=10, precision=1,
        description=(
            "当前导航的目标移动速度（单位/秒）。"
            "这是实际使用的速度值，滚轮在导航中直接修改并自动保存到此处。"
            "Shift/Alt 的加减速是在此值基础上的临时倍率，不会修改这个值"
        )
    )
    Scene.uw_speed_step = bpy.props.FloatProperty(
        name="滚轮步进", default=ops.SPEED_STEP,
        min=1.01, max=2.0, step=1, precision=2,
        description=(
            "每次滚动滚轮时速度的缩放倍率。"
            "上滚：速度 × 此值；下滚：速度 ÷ 此值。"
            "例如默认值 1.15 表示每次调整约 ±15%，"
            "数值越大每次变化幅度越大"
        )
    )
    Scene.uw_speed_min = bpy.props.FloatProperty(
        name="最小速度", default=ops.SPEED_MIN,
        min=0.01, max=10.0, step=1, precision=2,
        description="滚轮下调速度的下限（单位/秒），速度不会低于此值"
    )
    Scene.uw_speed_max = bpy.props.FloatProperty(
        name="最大速度", default=ops.SPEED_MAX,
        min=1.0, max=1000.0, step=100, precision=1,
        description="滚轮上调速度的上限（单位/秒），速度不会高于此值"
    )
    Scene.uw_mouse_sensitivity = bpy.props.FloatProperty(
        name="鼠标灵敏度", default=ops.MOUSE_SENSITIVITY,
        min=0.0001, max=0.02, step=0.1, precision=4,
        description=(
            "鼠标每移动 1 像素对应的视角旋转量（弧度）。"
            "视角旋转 = 鼠标位移（像素）× 此值。"
            "数值越大转动越快，越小越精细"
        )
    )
    Scene.uw_damping = bpy.props.FloatProperty(
        name="加速/刹车手感", default=ops.DAMPING,
        min=1.0, max=30.0, step=10, precision=1,
        description=(
            "控制速度趋向目标值的平滑程度，使用指数衰减公式："
            "每帧插值系数 = 1 - e^(-此值 × dt)。"
            "数值越大起步和刹车越灵敏，越小越有漂移/惯性感"
        )
    )
    Scene.uw_sprint_multiplier = bpy.props.FloatProperty(
        name="冲刺倍率", default=ops.SPRINT_MULTIPLIER,
        min=1.0, max=10.0, step=10, precision=1,
        description=(
            "按住 Shift 时的临时速度倍率。"
            "实际速度上限 = 目标速度 × 此值。"
            "松开 Shift 立刻恢复，不修改目标速度"
        )
    )
    Scene.uw_slow_multiplier = bpy.props.FloatProperty(
        name="慢速倍率", default=ops.SLOW_MULTIPLIER,
        min=0.01, max=1.0, step=1, precision=2,
        description=(
            "按住 Alt 时的临时速度倍率，优先级高于 Shift。"
            "实际速度上限 = 目标速度 × 此值。"
            "松开 Alt 立刻恢复，不修改目标速度"
        )
    )
    Scene.uw_cursor_style = bpy.props.EnumProperty(
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
    Scene.uw_warp_margin = bpy.props.IntProperty(
        name="边界边距", default=ops.WARP_MARGIN,
        min=0, max=100,
        description=(
            "鼠标距视口边缘多少像素内触发传送到对侧边缘，防止光标移出视口。"
            "设为 0 则禁用边界传送"
        )
    )
    Scene.uw_coast_stop_threshold = bpy.props.FloatProperty(
        name="停止阈值", default=ops.COAST_STOP_THRESHOLD,
        min=0.001, max=1.0, step=1, precision=3,
        description=(
            "松开右键后惯性滑行时，速度低于此值（单位/秒）则视为已停止并退出导航。"
            "数值越大停止越早，越小滑行越充分"
        )
    )
    Scene.uw_coast_max_duration = bpy.props.FloatProperty(
        name="最长时间", default=ops.COAST_MAX_DURATION,
        min=0.1, max=10.0, step=10, precision=1,
        description=(
            "惯性滑行的硬性时间上限（秒）。"
            "超过此时间无论速度多少都会强制退出导航，防止极端情况下长时间停不下来"
        )
    )


def unregister_properties():
    Scene = bpy.types.Scene
    props = [
        "uw_prefs_expanded",
        "uw_target_speed", "uw_speed_step", "uw_speed_min", "uw_speed_max",
        "uw_mouse_sensitivity", "uw_damping",
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
