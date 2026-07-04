import bpy
from mathutils import Vector, Quaternion
from bpy.types import Operator
import math
import time
import sys

_ADDON_PACKAGE = __package__
_IS_MAC = sys.platform == "darwin"

# 平台键位预设
# Mac:  Option(alt)=调速  Command(oskey)=减速  Shift=加速
# Win:  Ctrl=调速         Alt=减速             Shift=加速
if _IS_MAC:
    _SPEED_ADJUST_KEY = "alt"    # event.alt  = Option
    _SLOW_KEY         = "oskey"  # event.oskey = Command
else:
    _SPEED_ADJUST_KEY = "ctrl"   # event.ctrl = Ctrl
    _SLOW_KEY         = "alt"    # event.alt  = Alt

# 模块级共享状态: 供状态栏绘制函数读取当前导航状态(速度倍率/实时速度)
# 只有在NAVIGATING/COASTING状态下才会被更新, is_active=False时状态栏不绘制任何内容
_statusbar_state = {
    "is_active": False,
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
TARGET_SPEED = 12.0              # 目标速度(units/s), 滚轮直接调整这个值
SPRINT_MULTIPLIER = 2.5          # Shift临时倍率
SLOW_MULTIPLIER = 0.25           # Alt临时倍率
DAMPING = 8.0                    # 控制加速/刹车/转向的平滑手感
PHYSICS_SUBSTEP = 1 / 60

# 滚轮调速
SPEED_STEP = 1.15                # 每次滚动的缩放比例
SPEED_MIN = 0.1                  # 速度下限
SPEED_MAX = 100.0                # 速度上限

# 光标
HIDE_CURSOR = False
CURSOR_STYLE = "SCROLL_XY"

# 惯性滑行
COAST_STOP_THRESHOLD = 0.05
COAST_MAX_DURATION = 2.0

# 触控板
TRACKPAD_TIMEOUT = 0.3           # 秒,最后一次TRACKPADPAN后超过此时间触发滑行退出
TRACKPAD_EXIT_THRESHOLD = 10.0   # 像素,单指累计移动超过此距离才触发退出
TRACKPAD_SPEED_PIXELS = 20.0     # 修饰键调速:每累计多少像素触发一次speed_step

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

        click_move = CLICK_MOVE_THRESHOLD

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

        # 从AddonPreferences读取参数
        prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
        self._mouse_sensitivity    = prefs.mouse_sensitivity
        self._damping              = prefs.damping
        self._sprint_multiplier    = prefs.sprint_multiplier
        self._slow_multiplier      = prefs.slow_multiplier
        self._cursor_style         = prefs.cursor_style
        self._warp_margin          = prefs.warp_margin
        self._click_time_threshold = CLICK_TIME_THRESHOLD
        self._click_move_threshold = CLICK_MOVE_THRESHOLD
        self._coast_stop_threshold = prefs.coast_stop_threshold
        self._coast_max_duration   = prefs.coast_max_duration

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

        self.velocity      = Vector((0.0, 0.0, 0.0))
        prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
        scene = context.scene
        self._target_speed = getattr(scene, "uw_target_speed", prefs.target_speed)
        self._speed_step   = prefs.speed_step
        self._speed_min    = prefs.speed_min
        self._speed_max    = prefs.speed_max

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
                    # 重新从AddonPreferences读取参数
                    prefs = context.preferences.addons[_ADDON_PACKAGE].preferences
                    scene = context.scene
                    self._target_speed      = getattr(scene, "uw_target_speed", prefs.target_speed)
                    self._speed_step        = prefs.speed_step
                    self._speed_min         = prefs.speed_min
                    self._speed_max         = prefs.speed_max
                    self._mouse_sensitivity = prefs.mouse_sensitivity
                    self._damping           = prefs.damping
                    self._sprint_multiplier = prefs.sprint_multiplier
                    self._slow_multiplier   = prefs.slow_multiplier
                    self._cursor_style      = prefs.cursor_style
                    self._warp_margin       = prefs.warp_margin
                    self._coast_stop_threshold = prefs.coast_stop_threshold
                    self._coast_max_duration   = prefs.coast_max_duration
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
                self._target_speed = min(self._speed_max, self._target_speed * self._speed_step)
                context.scene.uw_target_speed = self._target_speed
                context.preferences.addons[_ADDON_PACKAGE].preferences.target_speed = self._target_speed
            elif event.type == "WHEELDOWNMOUSE":
                self._target_speed = max(self._speed_min, self._target_speed / self._speed_step)
                context.scene.uw_target_speed = self._target_speed
                context.preferences.addons[_ADDON_PACKAGE].preferences.target_speed = self._target_speed

            slow_keys = {"LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_ALT", "RIGHT_ALT", "TIMER"}
            if _IS_MAC:
                slow_keys.add("OSKEY")
            if event.type in _KEY_MAP or event.type in slow_keys:
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
        if dt <= PHYSICS_SUBSTEP:
            self.update_movement(dt)
            return
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

        target_speed = self._target_speed
        if self.move_state["SLOW"]:
            target_speed *= self._slow_multiplier
        elif self.move_state["SPRINT"]:
            target_speed *= self._sprint_multiplier

        desired_velocity = desired * target_speed

        smooth_factor = 1.0 - math.exp(-self._damping * dt)
        self.velocity = self.velocity.lerp(desired_velocity, smooth_factor)

        self.location += self.velocity * dt

        _statusbar_state["is_active"] = True
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


# ==================== 模块级共享函数(鼠标版和触控板版都使用) ====================

def nav_init_state(op, context):
    """初始化导航状态,从Scene属性读取参数"""
    rv3d = context.region_data
    region = context.region
    scene = context.scene
    prefs = context.preferences.addons[_ADDON_PACKAGE].preferences

    op.state = "NAVIGATING"

    op._mouse_sensitivity    = prefs.mouse_sensitivity
    op._damping              = prefs.damping
    op._sprint_multiplier    = prefs.sprint_multiplier
    op._slow_multiplier      = prefs.slow_multiplier
    op._cursor_style         = prefs.cursor_style
    op._warp_margin          = prefs.warp_margin
    op._coast_stop_threshold = prefs.coast_stop_threshold
    op._coast_max_duration   = prefs.coast_max_duration
    op._speed_accum          = 0.0  # 触控板调速累计像素
    op._trackpad_speed_step  = prefs.trackpad_speed_step

    op.original_view_distance = rv3d.view_distance

    op.location = rv3d.view_location.copy()
    if rv3d.view_distance > 0:
        view_dir = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
        op.location = rv3d.view_location - view_dir * rv3d.view_distance

    rot = rv3d.view_rotation
    forward = rot @ Vector((0.0, 0.0, -1.0))
    op.yaw   = math.atan2(-forward.x, forward.y)
    op.pitch = math.asin(max(-1.0, min(1.0, forward.z)))

    op.velocity      = Vector((0.0, 0.0, 0.0))
    op._target_speed = getattr(scene, "uw_target_speed", prefs.target_speed)
    op._speed_step   = prefs.speed_step
    op._speed_min    = prefs.speed_min
    op._speed_max    = prefs.speed_max

    op.move_state = {
        "FORWARD": False, "BACKWARD": False,
        "LEFT": False,    "RIGHT": False,
        "UP": False,      "DOWN": False,
        "SPRINT": False,  "SLOW": False,
    }

    op.region_x      = region.x
    op.region_y      = region.y
    op.region_width  = region.width
    op.region_height = region.height

    op._coasting          = False
    op._coast_elapsed     = 0.0
    op._last_tick_time    = time.perf_counter()
    op._mousemove_accum   = 0.0  # 触控板模式单指累计移动像素

    op._statusbar_area = next(
        (a for a in context.window.screen.areas if a.type == "STATUSBAR"), None
    )

    nav_apply_to_view(op, rv3d)


def nav_compute_dt(op):
    now = time.perf_counter()
    dt = now - op._last_tick_time
    op._last_tick_time = now
    return min(dt, 0.5)


def nav_update_move_state(op, event):
    if event.type in _KEY_MAP:
        if event.value == "PRESS":
            op.move_state[_KEY_MAP[event.type]] = True
        elif event.value == "RELEASE":
            op.move_state[_KEY_MAP[event.type]] = False
    op.move_state["SPRINT"] = event.shift
    op.move_state["SLOW"] = getattr(event, _SLOW_KEY)


def nav_update_movement(op, dt):
    forward = Vector((-math.sin(op.yaw), math.cos(op.yaw), 0.0))
    right   = Vector((forward.y, -forward.x, 0.0))
    up      = Vector((0.0, 0.0, 1.0))

    desired = Vector((0.0, 0.0, 0.0))
    if op.move_state["FORWARD"]:  desired += forward
    if op.move_state["BACKWARD"]: desired -= forward
    if op.move_state["RIGHT"]:    desired += right
    if op.move_state["LEFT"]:     desired -= right
    if op.move_state["UP"]:       desired += up
    if op.move_state["DOWN"]:     desired -= up

    if desired.length > 0:
        desired.normalize()

    target_speed = op._target_speed
    if op.move_state["SLOW"]:
        target_speed *= op._slow_multiplier
    elif op.move_state["SPRINT"]:
        target_speed *= op._sprint_multiplier

    smooth_factor = 1.0 - math.exp(-op._damping * dt)
    op.velocity = op.velocity.lerp(desired * target_speed, smooth_factor)
    op.location += op.velocity * dt

    _statusbar_state["is_active"]    = True
    _statusbar_state["current_speed"] = op.velocity.length
    _statusbar_state["target_speed"]  = target_speed


def nav_run_physics_substeps(op, dt):
    if dt <= PHYSICS_SUBSTEP:
        nav_update_movement(op, dt)
        return
    remaining = dt
    steps = 0
    while remaining > 0 and steps < 8:
        step = min(PHYSICS_SUBSTEP, remaining)
        nav_update_movement(op, step)
        remaining -= step
        steps += 1


def nav_apply_to_view(op, rv3d):
    yaw_quat   = Quaternion((0.0, 0.0, 1.0), op.yaw)
    pitch_quat = Quaternion((1.0, 0.0, 0.0), op.pitch + _PITCH_OFFSET)
    rv3d.view_rotation = yaw_quat @ pitch_quat
    rv3d.view_location = op.location
    rv3d.view_distance = 0.0


def nav_tag_statusbar_redraw(op):
    if op._statusbar_area is not None:
        try:
            op._statusbar_area.tag_redraw()
        except ReferenceError:
            op._statusbar_area = None


def nav_restore_view_distance(op, context):
    """退出时恢复view_distance,防止滚轮/中键失效"""
    rv3d = context.region_data
    if rv3d is not None and hasattr(op, "original_view_distance"):
        restored_distance = op.original_view_distance
        if restored_distance > 0:
            forward = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
            rv3d.view_location = op.location + forward * restored_distance
            rv3d.view_distance = restored_distance


class VIEW3D_OT_unity_walk_trackpad(Operator):
    """触控板版Unity Walk导航(完全独立,不继承鼠标版)

    状态机: IDLE → NAVIGATING(含_coasting子状态) → IDLE
    - TRACKPADPAN(双指滑动) → 进入导航,控制视角
    - MOUSEMOVE(单指移动)   → 触发带滑行的退出,回到IDLE
    - 超时无TRACKPADPAN     → 同样触发带滑行的退出
    - WASD → 移动, Shift → 加速, Alt → 减速, ESC → 完全退出
    """

    bl_idname = "view3d.unity_walk_trackpad"
    bl_label = "Unity Style Walk Navigation (Trackpad)"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        if context.space_data is None or context.space_data.type != "VIEW_3D":
            return {"PASS_THROUGH"}

        self._timer = context.window_manager.event_timer_add(1 / 60, window=context.window)
        context.window_manager.modal_handler_add(self)

        self.state = "IDLE"
        self._trackpad_last_time = 0.0
        self._trackpad_timeout = TRACKPAD_TIMEOUT

        return {"RUNNING_MODAL"}

    def cancel(self, context):
        """Blender内部取消时调用,只做资源清理"""
        if hasattr(self, "_timer"):
            context.window_manager.event_timer_remove(self._timer)

    def modal(self, context, event):
        if self.state == "IDLE":
            return self._modal_idle(context, event)
        return self._modal_navigating(context, event)

    def _modal_idle(self, context, event):
        if event.type == "ESC":
            context.window_manager.event_timer_remove(self._timer)
            return {"CANCELLED"}

        if event.type == "TRACKPADPAN":
            # 检查鼠标是否在3D视口的WINDOW子区域内
            # (N面板/Header/Toolbar等子区域不应触发导航)
            if context.area is None or context.area.type != "VIEW_3D":
                return {"PASS_THROUGH"}
            viewport_region = next(
                (r for r in context.area.regions if r.type == "WINDOW"), None
            )
            if viewport_region is None:
                return {"PASS_THROUGH"}
            if not (viewport_region.x <= event.mouse_x <= viewport_region.x + viewport_region.width
                    and viewport_region.y <= event.mouse_y <= viewport_region.y + viewport_region.height):
                return {"PASS_THROUGH"}

            nav_init_state(self, context)
            self._mouse_sensitivity = context.preferences.addons[_ADDON_PACKAGE].preferences.trackpad_sensitivity
            region = context.region
            context.window.cursor_modal_set("NONE")
            context.window.cursor_warp(
                region.x + region.width // 2,
                region.y + region.height // 2,
            )
            self._skip_next_mousemove = True
            self._trackpad_last_time = time.perf_counter()
            # 立刻消费第一帧(修饰键按下时调速,否则旋转视角)
            speed_modifier = getattr(event, _SPEED_ADJUST_KEY)
            if speed_modifier:
                dy = event.mouse_y - event.mouse_prev_y
                self._speed_accum += dy
                while abs(self._speed_accum) >= TRACKPAD_SPEED_PIXELS:
                    if self._speed_accum > 0:
                        self._target_speed = min(self._speed_max, self._target_speed * self._trackpad_speed_step)
                        self._speed_accum -= TRACKPAD_SPEED_PIXELS
                    else:
                        self._target_speed = max(self._speed_min, self._target_speed / self._trackpad_speed_step)
                        self._speed_accum += TRACKPAD_SPEED_PIXELS
                context.scene.uw_target_speed = self._target_speed
                context.preferences.addons[_ADDON_PACKAGE].preferences.target_speed = self._target_speed
            else:
                dx = event.mouse_x - event.mouse_prev_x
                dy = event.mouse_y - event.mouse_prev_y
                self.yaw   -= dx * self._mouse_sensitivity
                self.pitch += dy * self._mouse_sensitivity
                self.pitch  = max(-PITCH_LIMIT, min(PITCH_LIMIT, self.pitch))
            return {"RUNNING_MODAL"}

        return {"PASS_THROUGH"}

    def _modal_navigating(self, context, event):
        rv3d = context.region_data

        if event.type == "ESC":
            nav_restore_view_distance(self, context)
            context.window_manager.event_timer_remove(self._timer)
            context.window.cursor_modal_restore()
            context.area.tag_redraw()
            _statusbar_state["is_active"] = False
            nav_tag_statusbar_redraw(self)
            return {"FINISHED"}

        # TRACKPADPAN → 视角旋转或调速(按住修饰键时)
        # Mac: Option(alt=True) + 滑动 → 调速
        # Windows: Ctrl(ctrl=True) + 滑动 → 调速
        if event.type == "TRACKPADPAN":
            self._trackpad_last_time = time.perf_counter()
            self._mousemove_accum = 0.0
            if self._coasting:
                self._coasting = False
                self._coast_elapsed = 0.0
                context.window.cursor_modal_set("NONE")
                context.window.cursor_warp(
                    self.region_x + self.region_width // 2,
                    self.region_y + self.region_height // 2,
                )
                self._skip_next_mousemove = True

            speed_modifier = getattr(event, _SPEED_ADJUST_KEY)
            if speed_modifier:
                # 修饰键+滑动 → 调速(累计dy达到阈值才触发一次)
                dy = event.mouse_y - event.mouse_prev_y
                self._speed_accum += dy
                while abs(self._speed_accum) >= TRACKPAD_SPEED_PIXELS:
                    if self._speed_accum > 0:
                        self._target_speed = min(self._speed_max, self._target_speed * self._trackpad_speed_step)
                        self._speed_accum -= TRACKPAD_SPEED_PIXELS
                    else:
                        self._target_speed = max(self._speed_min, self._target_speed / self._trackpad_speed_step)
                        self._speed_accum += TRACKPAD_SPEED_PIXELS
                context.scene.uw_target_speed = self._target_speed
                context.preferences.addons[_ADDON_PACKAGE].preferences.target_speed = self._target_speed
            else:
                # 无修饰键 → 视角旋转,同时重置调速累计
                self._speed_accum = 0.0
                dx = event.mouse_x - event.mouse_prev_x
                dy = event.mouse_y - event.mouse_prev_y
                self.yaw   -= dx * self._mouse_sensitivity
                self.pitch += dy * self._mouse_sensitivity
                self.pitch  = max(-PITCH_LIMIT, min(PITCH_LIMIT, self.pitch))

        # MOUSEMOVE(单指移动):
        # 导航中: 累计超过阈值触发滑行退出
        # 滑行中: 直接显示光标(打断滑行的隐藏状态)
        if event.type == "MOUSEMOVE":
            if self._skip_next_mousemove:
                self._skip_next_mousemove = False
            elif self._coasting:
                # 滑行期间单指移动 → 立刻显示光标
                context.window.cursor_modal_restore()
            else:
                dx = event.mouse_x - event.mouse_prev_x
                dy = event.mouse_y - event.mouse_prev_y
                self._mousemove_accum += math.hypot(dx, dy)
                has_input = any(
                    self.move_state[k]
                    for k in ("FORWARD", "BACKWARD", "LEFT", "RIGHT", "UP", "DOWN")
                )
                if self._mousemove_accum > TRACKPAD_EXIT_THRESHOLD and not has_input:
                    self._coasting = True
                    self._coast_elapsed = 0.0
                    self._mousemove_accum = 0.0
                    context.window.cursor_modal_restore()

        slow_keys = {"LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_ALT", "RIGHT_ALT", "TIMER"}
        if _IS_MAC:
            slow_keys.add("OSKEY")
        if event.type in _KEY_MAP or event.type in slow_keys:
            nav_update_move_state(self, event)

        if event.type == "TIMER":
            try:
                dt = nav_compute_dt(self)

                # 超时检测: 有WASD输入时不触发
                has_input = any(
                    self.move_state[k]
                    for k in ("FORWARD", "BACKWARD", "LEFT", "RIGHT", "UP", "DOWN")
                )
                if has_input:
                    self._mousemove_accum = 0.0  # 按键期间重置累计,避免松键瞬间误触发
                if (not self._coasting
                        and not has_input
                        and time.perf_counter() - self._trackpad_last_time
                        > self._trackpad_timeout):
                    self._coasting = True
                    self._coast_elapsed = 0.0
                    # 注意: 不在这里restore光标,等滑行完全结束后才显示
                    # MOUSEMOVE打断时则立刻显示(见MOUSEMOVE处理)

                if self._coasting:
                    self._coast_elapsed += dt
                    smooth_factor = 1.0 - math.exp(-self._damping * dt)
                    self.velocity = self.velocity.lerp(Vector((0.0, 0.0, 0.0)), smooth_factor)
                    self.location += self.velocity * dt

                    # 滑行期间有WASD输入 → 取消滑行,重新进入导航
                    has_input = any(
                        self.move_state[k]
                        for k in ("FORWARD", "BACKWARD", "LEFT", "RIGHT", "UP", "DOWN")
                    )
                    if has_input:
                        self._coasting = False
                        self._coast_elapsed = 0.0
                        self._mousemove_accum = 0.0
                        # 重新隐藏光标钳制到中央
                        context.window.cursor_modal_set("NONE")
                        context.window.cursor_warp(
                            self.region_x + self.region_width // 2,
                            self.region_y + self.region_height // 2,
                        )
                        self._skip_next_mousemove = True
                    elif (self.velocity.length < self._coast_stop_threshold
                            or self._coast_elapsed >= self._coast_max_duration):
                        # 滑行结束:恢复view_distance,显示光标,回到IDLE
                        nav_restore_view_distance(self, context)
                        context.window.cursor_modal_restore()
                        self.state = "IDLE"
                        self._coasting = False
                        self._coast_elapsed = 0.0
                        _statusbar_state["is_active"] = False
                        nav_tag_statusbar_redraw(self)
                        context.area.tag_redraw()
                        return {"RUNNING_MODAL"}
                else:
                    nav_run_physics_substeps(self, dt)

                nav_apply_to_view(self, rv3d)
                context.area.tag_redraw()
                nav_tag_statusbar_redraw(self)
            except Exception as e:
                print(f"[unity_walk_trackpad] 更新出错: {e}")
                context.window_manager.event_timer_remove(self._timer)
                context.window.cursor_modal_restore()
                return {"CANCELLED"}

        return {"RUNNING_MODAL"}


def draw_statusbar(self, context):
    if not _statusbar_state["is_active"]:
        return

    layout = self.layout
    layout.label(text=f"Speed: {_statusbar_state['target_speed']:.1f} u/s")


classes = (VIEW3D_OT_unity_walk, VIEW3D_OT_unity_walk_trackpad)