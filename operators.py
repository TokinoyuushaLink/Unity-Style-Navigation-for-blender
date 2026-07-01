import bpy
from mathutils import Vector, Quaternion
from bpy.types import Operator
import math
import time

# 模块级共享状态: 供状态栏绘制函数读取当前导航状态(速度倍率/实时速度)
# 只有在NAVIGATING/COASTING状态下才会被更新, is_active=False时状态栏不绘制任何内容
_statusbar_state = {
    "is_active": False,
    "speed_multiplier": 1.0,
    "current_speed": 0.0,
    "target_speed": 0.0,
}


# -------------------- 可调参数(后续迁移到 AddonPreferences) --------------------
# 触发判定
CLICK_TIME_THRESHOLD = 0.18      # 秒, 短于这个时长视为点击意图
CLICK_MOVE_THRESHOLD = 4.0       # 像素, 鼠标移动超过这个距离视为导航意图

# 视角
MOUSE_SENSITIVITY = 0.0022
PITCH_LIMIT = math.radians(89.0)

# 移动
BASE_MAX_SPEED = 12.0            # 滚轮倍率为1.0时的最大速度 (units/s)
SPRINT_MULTIPLIER = 2.5
SLOW_MULTIPLIER = 0.25           # Alt按下时的减速倍率
DAMPING = 8.0                    # 控制加速/刹车/转向的平滑手感, 越大越灵敏
PHYSICS_SUBSTEP = 1 / 60        # 子步进步长, 防止TIMER抖动导致位移突变

# 光标
HIDE_CURSOR = False              # 导航状态下是否隐藏鼠标光标
CURSOR_STYLE = "SCROLL_XY"      # 导航状态下的光标样式

# 惯性滑行
COAST_STOP_THRESHOLD = 0.05      # units/s, 速度低于此值视为已停止
COAST_MAX_DURATION = 2.0         # 秒, 滑行硬性超时保护

# 滚轮速度倍率
SPEED_MULTIPLIER_MIN = 0.1
SPEED_MULTIPLIER_MAX = 10.0
SPEED_MULTIPLIER_STEP = 1.15
DEFAULT_SPEED_MULTIPLIER = 1.0

# 边界teleport留边距(像素)
WARP_MARGIN = 20

_PITCH_OFFSET = math.pi / 2  # apply_to_view里的常量偏移,避免每帧重算

# 按键到移动方向的映射, 模块级避免每次update_move_state都重建字典
_KEY_MAP = {
    "W": "FORWARD",
    "S": "BACKWARD",
    "A": "LEFT",
    "D": "RIGHT",
    "E": "UP",
    "Q": "DOWN",
}


class VIEW3D_OT_unity_walk(Operator):
    """右键长按判断 + Unity风格第一人称漫游(惯性移动 + 鼠标视角)

    交互逻辑:
    - 右键 PRESS 时进入 WAITING 状态, 开始计时并记录初始鼠标位置
    - 如果在阈值时间内 RELEASE, 且鼠标几乎没移动 -> 判定为"点击", 转交原生右键菜单
    - 如果超过阈值时间, 或鼠标移动超过阈值距离 -> 判定为"导航意图", 切换到 NAVIGATING 状态
    - NAVIGATING 状态下松开右键 -> 直接退出(和Unity一样, 不需要再按ESC)
    """

    bl_idname = "view3d.unity_walk"
    bl_label = "Unity Style Walk Navigation"
    bl_options = {"REGISTER"}

    menu_by_mode = {
        "OBJECT": "VIEW3D_MT_object_context_menu",
        "EDIT_MESH": "VIEW3D_MT_edit_mesh_context_menu",
        "EDIT_SURFACE": "VIEW3D_MT_edit_surface",
        "EDIT_TEXT": "VIEW3D_MT_edit_font_context_menu",
        "EDIT_ARMATURE": "VIEW3D_MT_edit_armature",
        "EDIT_CURVE": "VIEW3D_MT_edit_curve_context_menu",
        "EDIT_METABALL": "VIEW3D_MT_edit_metaball_context_menu",
        "EDIT_LATTICE": "VIEW3D_MT_edit_lattice_context_menu",
        "POSE": "VIEW3D_MT_pose_context_menu",
        "PAINT_VERTEX": "VIEW3D_PT_paint_vertex_context_menu",
        "PAINT_WEIGHT": "VIEW3D_PT_paint_weight_context_menu",
        "PAINT_TEXTURE": "VIEW3D_PT_paint_texture_context_menu",
        "SCULPT": "VIEW3D_PT_sculpt_context_menu",
    }

    def invoke(self, context, event):
        if context.space_data is None or context.space_data.type != "VIEW_3D":
            return {"PASS_THROUGH"}

        self.state = "WAITING"
        self.press_time = 0.0
        self.start_mouse_x = event.mouse_x
        self.start_mouse_y = event.mouse_y

        self._timer = context.window_manager.event_timer_add(1 / 60, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {"RUNNING_MODAL"}

    # -------------------- 核心循环(状态机分发) --------------------
    def modal(self, context, event):
        if self.state == "WAITING":
            return self.modal_waiting(context, event)
        return self.modal_navigating(context, event)

    # ---------------- WAITING 状态: 判断点击 vs 导航 ----------------
    def modal_waiting(self, context, event):
        if event.type == "RIGHTMOUSE" and event.value == "RELEASE":
            return self.finish_as_click(context)

        moved = self.mouse_moved_distance(event)

        scene = context.scene
        click_time = getattr(scene, "uw_click_time_threshold", CLICK_TIME_THRESHOLD)
        click_move = getattr(scene, "uw_click_move_threshold", CLICK_MOVE_THRESHOLD)

        # 时间判定已禁用,保留接口供后续需要时恢复
        # if event.type == "TIMER":
        #     self.press_time += 1 / 60
        #     if self.press_time >= click_time:
        #         return self.start_navigating(context, event)

        if moved >= click_move:
            return self.start_navigating(context, event)

        return {"RUNNING_MODAL"}

    def mouse_moved_distance(self, event):
        dx = event.mouse_x - self.start_mouse_x
        dy = event.mouse_y - self.start_mouse_y
        return math.hypot(dx, dy)

    def finish_as_click(self, context):
        context.window_manager.event_timer_remove(self._timer)
        self.call_context_menu(context)
        return {"FINISHED"}

    def call_context_menu(self, context):
        wm = context.window_manager
        blender_keyconfig = wm.keyconfigs["Blender"]
        select_mouse = blender_keyconfig.preferences.select_mouse

        if select_mouse == "LEFT":
            try:
                bpy.ops.wm.call_menu(name=self.menu_by_mode[context.mode])
            except (RuntimeError, KeyError):
                try:
                    bpy.ops.wm.call_panel(name=self.menu_by_mode[context.mode])
                except (RuntimeError, KeyError):
                    pass
        else:
            bpy.ops.view3d.select("INVOKE_DEFAULT")

    # ---------------- 切换进入导航状态 ----------------
    def start_navigating(self, context, event):
        rv3d = context.region_data
        region = context.region

        self.state = "NAVIGATING"

        # 从Scene属性读取当前参数,存到实例变量,导航过程中保持一致
        scene = context.scene
        self._base_max_speed = getattr(scene, "uw_base_max_speed", BASE_MAX_SPEED)
        self._mouse_sensitivity = getattr(scene, "uw_mouse_sensitivity", MOUSE_SENSITIVITY)
        self._damping = getattr(scene, "uw_damping", DAMPING)
        self._sprint_multiplier = getattr(scene, "uw_sprint_multiplier", SPRINT_MULTIPLIER)
        self._slow_multiplier = getattr(scene, "uw_slow_multiplier", SLOW_MULTIPLIER)
        self._cursor_style = getattr(scene, "uw_cursor_style", CURSOR_STYLE)
        self._warp_margin = getattr(scene, "uw_warp_margin", WARP_MARGIN)
        self._click_time_threshold = getattr(scene, "uw_click_time_threshold", CLICK_TIME_THRESHOLD)
        self._click_move_threshold = getattr(scene, "uw_click_move_threshold", CLICK_MOVE_THRESHOLD)
        self._coast_stop_threshold = getattr(scene, "uw_coast_stop_threshold", COAST_STOP_THRESHOLD)
        self._coast_max_duration = getattr(scene, "uw_coast_max_duration", COAST_MAX_DURATION)

        # 记录原始 view_distance, 退出时恢复, 防止滚轮/中键失效
        self.original_view_distance = rv3d.view_distance

        self.location = rv3d.view_location.copy()
        if rv3d.view_distance > 0:
            view_dir = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
            self.location = rv3d.view_location - view_dir * rv3d.view_distance

        rot = rv3d.view_rotation
        forward = rot @ Vector((0.0, 0.0, -1.0))
        self.yaw = math.atan2(-forward.x, forward.y)
        self.pitch = math.asin(max(-1.0, min(1.0, forward.z)))

        self.velocity = Vector((0.0, 0.0, 0.0))
        self.speed_multiplier = DEFAULT_SPEED_MULTIPLIER

        self.move_state = {
            "FORWARD": False,
            "BACKWARD": False,
            "LEFT": False,
            "RIGHT": False,
            "UP": False,
            "DOWN": False,
            "SPRINT": False,
            "SLOW": False,
        }

        self.region_x = region.x
        self.region_y = region.y
        self.region_width = region.width
        self.region_height = region.height

        # 手动追踪鼠标位置, 不依赖event.mouse_prev_x/y
        # (teleport后Blender的mouse_prev不一定可靠, 自己追踪更精确)
        self._coasting = False
        self._coast_elapsed = 0.0
        self._last_mouse_x = 0
        self._last_mouse_y = 0
        self._mouse_initialized = False
        self._skip_next_mousemove = False
        self._last_tick_time = time.perf_counter()

        # 缓存statusbar区域引用, 避免每帧遍历screen.areas
        self._statusbar_area = next(
            (a for a in context.window.screen.areas if a.type == "STATUSBAR"), None
        )

        context.window.cursor_modal_set(self._cursor_style)

        # 立刻写入一次完整状态, 避免"进入瞬间抽动"(distance/location不一致的中间帧)
        self.apply_to_view(rv3d)

        return {"RUNNING_MODAL"}

    # ---------------- NAVIGATING 状态 ----------------
    def modal_navigating(self, context, event):
        rv3d = context.region_data

        if event.type == "RIGHTMOUSE":
            # 只响应发生在我们的3D视口区域内的右键事件,
            # 避免在其他区域(Properties/Outliner等)右键时被误触发
            in_region = (
                self.region_x <= event.mouse_x <= self.region_x + self.region_width
                and self.region_y <= event.mouse_y <= self.region_y + self.region_height
            )
            if in_region:
                if event.value == "RELEASE" and not self._coasting:
                    if self.velocity.length < self._coast_stop_threshold:
                        return self.exit_navigating(context)
                    self._coasting = True
                    self._coast_elapsed = 0.0
                    context.window.cursor_modal_restore()
                elif event.value == "PRESS" and self._coasting:
                    self._coasting = False
                    self._mouse_initialized = False
                    self._skip_next_mousemove = False
                    for key in self.move_state:
                        self.move_state[key] = False
                    # 重新从Scene读取参数,用户可能在滑行期间调整了N面板
                    scene = context.scene
                    self._base_max_speed = getattr(scene, "uw_base_max_speed", BASE_MAX_SPEED)
                    self._mouse_sensitivity = getattr(scene, "uw_mouse_sensitivity", MOUSE_SENSITIVITY)
                    self._damping = getattr(scene, "uw_damping", DAMPING)
                    self._sprint_multiplier = getattr(scene, "uw_sprint_multiplier", SPRINT_MULTIPLIER)
                    self._slow_multiplier = getattr(scene, "uw_slow_multiplier", SLOW_MULTIPLIER)
                    self._cursor_style = getattr(scene, "uw_cursor_style", CURSOR_STYLE)
                    self._warp_margin = getattr(scene, "uw_warp_margin", WARP_MARGIN)
                    self._coast_stop_threshold = getattr(scene, "uw_coast_stop_threshold", COAST_STOP_THRESHOLD)
                    self._coast_max_duration = getattr(scene, "uw_coast_max_duration", COAST_MAX_DURATION)
                    context.window.cursor_modal_set(self._cursor_style)

        if event.type == "ESC":
            return self.exit_navigating(context)

        # 只在非滑行状态下响应鼠标/键盘输入
        if not self._coasting:
            if event.type == "MOUSEMOVE":
                if not self._mouse_initialized:
                    self._mouse_initialized = True
                    self._last_mouse_x = event.mouse_x
                    self._last_mouse_y = event.mouse_y
                elif self._skip_next_mousemove:
                    self._skip_next_mousemove = False
                    self._last_mouse_x = event.mouse_x
                    self._last_mouse_y = event.mouse_y
                else:
                    dx = event.mouse_x - self._last_mouse_x
                    dy = event.mouse_y - self._last_mouse_y

                    self.yaw -= dx * self._mouse_sensitivity
                    self.pitch += dy * self._mouse_sensitivity
                    self.pitch = max(-PITCH_LIMIT, min(PITCH_LIMIT, self.pitch))

                    self._last_mouse_x = event.mouse_x
                    self._last_mouse_y = event.mouse_y

                self.warp_if_near_edge(context, event)

            if event.type == "WHEELUPMOUSE":
                self.speed_multiplier = min(
                    SPEED_MULTIPLIER_MAX, self.speed_multiplier * SPEED_MULTIPLIER_STEP
                )
            elif event.type == "WHEELDOWNMOUSE":
                self.speed_multiplier = max(
                    SPEED_MULTIPLIER_MIN, self.speed_multiplier / SPEED_MULTIPLIER_STEP
                )

            if event.type in _KEY_MAP or event.type in {
                "LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_ALT", "RIGHT_ALT", "TIMER"
            }:
                self.update_move_state(event)

        if event.type == "TIMER":
            try:
                dt = self.compute_dt()

                if self._coasting:
                    self._coast_elapsed += dt
                    # desired=零向量, velocity自然衰减
                    smooth_factor = 1.0 - math.exp(-self._damping * dt)
                    self.velocity = self.velocity.lerp(Vector((0.0, 0.0, 0.0)), smooth_factor)
                    self.location += self.velocity * dt

                    if (self.velocity.length < self._coast_stop_threshold
                            or self._coast_elapsed >= self._coast_max_duration):
                        return self.exit_navigating(context)
                else:
                    self.run_physics_substeps(dt)

                self.apply_to_view(rv3d)
                context.area.tag_redraw()
                self.tag_statusbar_redraw()
            except Exception as e:
                print(f"[unity_walk] 更新出错, 强制退出: {e}")
                return self.exit_navigating(context)

        # 滑行状态下, 除了TIMER和右键(右键已经在上面处理过了,
        # 透传出去会再次触发invoke产生双实例冲突)之外的事件透传,
        # 恢复中键/滚轮等原生行为
        if self._coasting and event.type not in {"TIMER", "RIGHTMOUSE"}:
            return {"PASS_THROUGH"}

        return {"RUNNING_MODAL"}

    def warp_if_near_edge(self, context, event):
        x = event.mouse_x
        y = event.mouse_y

        left = self.region_x + self._warp_margin
        right = self.region_x + self.region_width - self._warp_margin
        bottom = self.region_y + self._warp_margin
        top = self.region_y + self.region_height - self._warp_margin

        new_x, new_y = x, y

        if x <= left:
            new_x = right
        elif x >= right:
            new_x = left

        if y <= bottom:
            new_y = top
        elif y >= top:
            new_y = bottom

        if new_x != x or new_y != y:
            context.window.cursor_warp(new_x, new_y)
            self._last_mouse_x = new_x
            self._last_mouse_y = new_y
            # 标记跳过下一次MOUSEMOVE, 防止cursor_warp额外触发的事件
            # 产生虚假的大幅delta导致视角跳动
            self._skip_next_mousemove = True

    def compute_dt(self):
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now
        return min(dt, 0.5)

    def run_physics_substeps(self, dt):
        # 快速路径: 正常帧dt约等于PHYSICS_SUBSTEP, 直接单次调用不走循环
        if dt <= PHYSICS_SUBSTEP:
            self.update_movement(dt)
            return
        # 慢速路径: dt异常偏大时才拆成多个子步进
        remaining = dt
        steps = 0
        while remaining > 0 and steps < 8:
            step = min(PHYSICS_SUBSTEP, remaining)
            self.update_movement(step)
            remaining -= step
            steps += 1

    def update_move_state(self, event):
        if event.type in _KEY_MAP:
            if event.value == "PRESS":
                self.move_state[_KEY_MAP[event.type]] = True
            elif event.value == "RELEASE":
                self.move_state[_KEY_MAP[event.type]] = False

        self.move_state["SPRINT"] = event.shift
        self.move_state["SLOW"] = event.alt

    def update_movement(self, dt):
        forward = Vector((-math.sin(self.yaw), math.cos(self.yaw), 0.0))
        right = Vector((forward.y, -forward.x, 0.0))
        up = Vector((0.0, 0.0, 1.0))

        desired = Vector((0.0, 0.0, 0.0))
        if self.move_state["FORWARD"]:
            desired += forward
        if self.move_state["BACKWARD"]:
            desired -= forward
        if self.move_state["RIGHT"]:
            desired += right
        if self.move_state["LEFT"]:
            desired -= right
        if self.move_state["UP"]:
            desired += up
        if self.move_state["DOWN"]:
            desired -= up

        if desired.length > 0:
            desired.normalize()

        target_speed = self._base_max_speed * self.speed_multiplier
        if self.move_state["SLOW"]:
            target_speed *= self._slow_multiplier
        elif self.move_state["SPRINT"]:
            target_speed *= self._sprint_multiplier

        # 期望速度向量: 有方向有大小, 没有输入时为零向量(即"目标是静止")
        desired_velocity = desired * target_speed

        # 指数平滑: 每帧把当前速度往目标速度拉一次
        # smooth_factor用exp形式而不是简单的self._damping*dt, 是为了在帧率不稳定时
        # 保持一致的手感(数学上正确的离散化指数衰减, 不受dt大小影响)
        # 起步/刹车/转向都走同一套公式, 天然对称, 不需要clamp
        smooth_factor = 1.0 - math.exp(-self._damping * dt)
        self.velocity = self.velocity.lerp(desired_velocity, smooth_factor)

        self.location += self.velocity * dt

        _statusbar_state["is_active"] = True
        _statusbar_state["speed_multiplier"] = self.speed_multiplier
        _statusbar_state["current_speed"] = self.velocity.length
        _statusbar_state["target_speed"] = target_speed

    def apply_to_view(self, rv3d):
        yaw_quat = Quaternion((0.0, 0.0, 1.0), self.yaw)
        pitch_quat = Quaternion((1.0, 0.0, 0.0), self.pitch + _PITCH_OFFSET)
        rv3d.view_rotation = yaw_quat @ pitch_quat
        rv3d.view_location = self.location
        rv3d.view_distance = 0.0

    def tag_statusbar_redraw(self):
        if self._statusbar_area is not None:
            try:
                self._statusbar_area.tag_redraw()
            except ReferenceError:
                # area可能已经被Blender释放(比如切换了工作区),重新查找
                self._statusbar_area = None

    def exit_navigating(self, context):
        rv3d = context.region_data

        if rv3d is not None and hasattr(self, "original_view_distance"):
            restored_distance = self.original_view_distance
            if restored_distance > 0:
                forward = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
                rv3d.view_location = self.location + forward * restored_distance
                rv3d.view_distance = restored_distance

        context.window_manager.event_timer_remove(self._timer)
        context.window.cursor_modal_restore()
        context.area.tag_redraw()

        _statusbar_state["is_active"] = False
        self.tag_statusbar_redraw()

        return {"FINISHED"}


def draw_statusbar(self, context):
    if not _statusbar_state["is_active"]:
        return

    layout = self.layout
    layout.label(text=f"Speed: {_statusbar_state['target_speed']:.1f} u/s")


classes = (VIEW3D_OT_unity_walk,)