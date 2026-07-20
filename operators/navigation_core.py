"""
navigation_core.py
透视/触控板版共享的导航常量、会话变量和nav_*函数。
"""

import bpy
from mathutils import Vector, Quaternion
import math
import time
import sys

_IS_MAC = sys.platform == "darwin"

# ADDON_PACKAGE：从__package__推算（navigation_core在operators/内，去掉两级）
ADDON_PACKAGE = __package__.split(".")[0]

# 状态栏数据总线（定义在此处，operators/__init__.py从这里re-export）
_statusbar_state = {
    "is_active":     False,
    "current_speed": 0.0,
    "target_speed":  0.0,
    "view_space":    False,
}

# 会话级坐标空间状态：None=未设置（用偏好默认值），True=View，False=World
_session_persp_view_space        = None  # 透视视图坐标空间
_session_ortho_view_space        = None  # 正交视图坐标空间
_session_camera_persp_view_space = None  # 透视相机坐标空间
_session_camera_ortho_view_space = None  # 正交相机坐标空间
_session_target_speed            = None  # 会话级移动速度（None时读prefs默认值）


def set_session_view_space(mode, value):
    """写入对应模式的session坐标空间"""
    global _session_persp_view_space, _session_ortho_view_space
    global _session_camera_persp_view_space, _session_camera_ortho_view_space
    if mode == "persp":
        _session_persp_view_space = value
    elif mode == "ortho":
        _session_ortho_view_space = value
    elif mode == "camera_persp":
        _session_camera_persp_view_space = value
    elif mode == "camera_ortho":
        _session_camera_ortho_view_space = value


def set_session_target_speed(value):
    """写入会话级移动速度"""
    global _session_target_speed
    _session_target_speed = value

# 平台键位预设
# Mac:  Option(alt)=调速  Command(oskey)=减速  Shift=加速
# Win:  Ctrl=调速         Alt=减速             Shift=加速
if _IS_MAC:
    _SPEED_ADJUST_KEY = "alt"    # event.alt  = Option
    _SLOW_KEY         = "oskey"  # event.oskey = Command
else:
    _SPEED_ADJUST_KEY = "ctrl"   # event.ctrl = Ctrl
    _SLOW_KEY         = "alt"    # event.alt  = Alt

# -------------------- 常量 --------------------
# 触发判定
CLICK_TIME_THRESHOLD = 0.18      # 秒, 短于这个时长视为点击意图
CLICK_MOVE_THRESHOLD = 4.0       # 像素, 鼠标移动超过这个距离视为导航意图

# 视角
MOUSE_SENSITIVITY = 0.0017
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



def nav_init_state(op, context):
    """初始化导航状态，从 AddonPreferences 读取参数"""
    rv3d = context.region_data
    region = context.region
    scene = context.scene
    prefs = context.preferences.addons[ADDON_PACKAGE].preferences

    op.state = "NAVIGATING"

    op._mouse_sensitivity       = prefs.mouse_sensitivity
    op._fov_compensation_strength = prefs.fov_compensation_strength
    op._damping              = prefs.damping
    op._sprint_multiplier    = prefs.sprint_multiplier
    op._slow_multiplier      = prefs.slow_multiplier
    op._cursor_style         = prefs.cursor_style
    op._warp_margin          = prefs.warp_margin
    op._coast_stop_threshold  = prefs.coast_stop_threshold
    op._coast_max_duration    = prefs.coast_max_duration
    op._enable_time_threshold = prefs.enable_time_threshold
    op._click_time_threshold  = prefs.click_time_threshold
    op._speed_accum          = 0.0  # 触控板调速累计像素
    op._trackpad_speed_step  = prefs.trackpad_speed_step
    op._zoom_scale = prefs.ortho_zoom_scale
    op._camera_zoom_velocity = 0.0
    op._camera_zoom_target   = 0.0

    op.original_view_distance    = rv3d.view_distance
    op.original_view_perspective = rv3d.view_perspective

    # 检测是否在camera视图
    op._camera_mode = (rv3d.view_perspective == "CAMERA")
    op._camera_obj  = None
    op._camera_ortho_mode = False
    op._camera_original_rotation_mode = None
    if op._camera_mode:
        cam = scene.camera
        if cam is not None:
            op._camera_obj = cam
            op._camera_ortho_mode = (cam.data.type == "ORTHO")
            op._camera_original_rotation_mode = cam.rotation_mode
            op.location = cam.matrix_world.translation.copy()
            fwd = cam.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
            op.yaw   = math.atan2(-fwd.x, fwd.y)
            op.pitch = math.asin(max(-1.0, min(1.0, fwd.z)))
        else:
            op._camera_mode = False

    if not op._camera_mode:
        if rv3d.view_perspective == "ORTHO":
            # 正交模式：不切换到透视，直接用view_location，location不减去depth偏移
            op._ortho_mode = True
            op.location = rv3d.view_location.copy()
        else:
            op._ortho_mode = False
            op.location = rv3d.view_location.copy()
            if rv3d.view_distance > 0:
                view_dir = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
                op.location = rv3d.view_location - view_dir * rv3d.view_distance

        rot = rv3d.view_rotation
        forward = rot @ Vector((0.0, 0.0, -1.0))
        op.yaw   = math.atan2(-forward.x, forward.y)
        op.pitch = math.asin(max(-1.0, min(1.0, forward.z)))

    # 根据当前模式读取对应的session坐标空间
    if op._camera_mode:
        if op._camera_ortho_mode:
            op._view_space = (_session_camera_ortho_view_space if _session_camera_ortho_view_space is not None
                              else (prefs.default_ortho_coord_system == "VIEW"))
        else:
            op._view_space = (_session_camera_persp_view_space if _session_camera_persp_view_space is not None
                              else (prefs.default_coord_system == "VIEW"))
    else:
        op._view_space = (_session_persp_view_space if _session_persp_view_space is not None
                          else (prefs.default_coord_system == "VIEW"))

    op.velocity      = Vector((0.0, 0.0, 0.0))
    op._target_speed = _session_target_speed if _session_target_speed is not None else prefs.target_speed
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
    # 正交相机：走正交平移+缩放逻辑
    if getattr(op, "_camera_mode", False) and getattr(op, "_camera_ortho_mode", False):
        if op._camera_obj is None:
            return
        try:
            mat = op._camera_obj.matrix_world.to_3x3()
        except ReferenceError:
            op._camera_mode = False
            return

        if getattr(op, "_view_space", False):
            # 视角空间：直接用相机自身的right/up轴
            right = mat @ Vector((1.0, 0.0, 0.0))
            up    = mat @ Vector((0.0, 1.0, 0.0))
        else:
            # 世界空间：用相机-Z轴（视线方向）排除最垂直的世界轴，剩余两个snap
            screen_right = mat @ Vector((1.0, 0.0, 0.0))
            screen_up    = mat @ Vector((0.0, 1.0, 0.0))
            screen_z     = mat @ Vector((0.0, 0.0, -1.0))
            world_axes   = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
            perp   = max(world_axes, key=lambda a: abs(a.dot(screen_z)))
            planar = [a for a in world_axes if a != perp]
            a0, a1 = planar
            right = a0 if abs(a0.dot(screen_right)) >= abs(a1.dot(screen_right)) else a1
            up    = a0 if abs(a0.dot(screen_up))    >= abs(a1.dot(screen_up))    else a1
            if right.dot(screen_right) < 0: right = -right
            if up.dot(screen_up)       < 0: up    = -up

        pan = Vector((0.0, 0.0, 0.0))
        if op.move_state["FORWARD"]:  pan += up
        if op.move_state["BACKWARD"]: pan -= up
        if op.move_state["RIGHT"]:    pan += right
        if op.move_state["LEFT"]:     pan -= right
        if pan.length > 0:
            pan.normalize()

        speed = op._target_speed
        if op.move_state["SLOW"]:     speed *= op._slow_multiplier
        elif op.move_state["SPRINT"]: speed *= op._sprint_multiplier

        smooth = 1.0 - math.exp(-op._damping * dt)
        op.velocity = op.velocity.lerp(pan * speed, smooth)
        op.location += op.velocity * dt

        # QE缩放ortho_scale（惯性平滑，和正交视口一样）
        zoom_speed = speed * getattr(op, "_zoom_scale", 3.0)
        if op.move_state["UP"]:
            op._camera_zoom_target = -zoom_speed
        elif op.move_state["DOWN"]:
            op._camera_zoom_target = zoom_speed
        else:
            op._camera_zoom_target = 0.0

        smooth = 1.0 - math.exp(-op._damping * dt)
        op._camera_zoom_velocity = op._camera_zoom_velocity + \
            (op._camera_zoom_target - op._camera_zoom_velocity) * smooth
        if abs(op._camera_zoom_velocity) > 0.0001:
            try:
                op._camera_obj.data.ortho_scale = max(
                    0.001, op._camera_obj.data.ortho_scale + op._camera_zoom_velocity * dt)
            except ReferenceError:
                op._camera_mode = False

        _statusbar_state["is_active"]    = True
        _statusbar_state["current_speed"] = op.velocity.length
        _statusbar_state["target_speed"]  = speed
        _statusbar_state["view_space"]    = getattr(op, "_view_space", False)
        return

    if getattr(op, "_view_space", False):
        yaw_quat   = Quaternion((0.0, 0.0, 1.0), op.yaw)
        pitch_quat = Quaternion((1.0, 0.0, 0.0), op.pitch + _PITCH_OFFSET)
        rot = yaw_quat @ pitch_quat
        forward = rot @ Vector((0.0, 0.0, -1.0))
        right   = rot @ Vector((1.0, 0.0,  0.0))
        up      = rot @ Vector((0.0, 1.0,  0.0))
    else:
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
    _statusbar_state["view_space"]    = getattr(op, "_view_space", False)


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
    rotation   = yaw_quat @ pitch_quat

    if getattr(op, "_camera_mode", False) and op._camera_obj is not None:
        try:
            op._camera_obj.location = op.location
            mode = getattr(op, "_camera_original_rotation_mode", "XYZ")
            if mode == 'QUATERNION':
                op._camera_obj.rotation_quaternion = rotation
            elif mode == 'AXIS_ANGLE':
                op._camera_obj.rotation_quaternion = rotation
            else:
                op._camera_obj.rotation_euler = rotation.to_euler(mode)
        except ReferenceError:
            op._camera_mode = False
    elif getattr(op, "_ortho_mode", False):
        # 正交模式：更新旋转和平移，不改view_distance
        rv3d.view_rotation = rotation
        rv3d.view_location = op.location
    else:
        rv3d.view_rotation = rotation
        rv3d.view_location = op.location
        rv3d.view_distance = 0.0


def nav_tag_statusbar_redraw(op):
    if op._statusbar_area is not None:
        try:
            op._statusbar_area.tag_redraw()
        except ReferenceError:
            op._statusbar_area = None


def nav_restore_view_distance(op, context):
    """退出时恢复view_distance和view_perspective"""
    if getattr(op, "_camera_mode", False):
        return  # camera模式下不恢复view_distance和view_perspective
    if getattr(op, "_ortho_mode", False):
        return  # 正交模式view_distance没有被改变，不恢复
    rv3d = context.region_data
    if rv3d is not None:
        if hasattr(op, "original_view_distance"):
            restored_distance = op.original_view_distance
            if restored_distance > 0:
                forward = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
                rv3d.view_location = op.location + forward * restored_distance
                rv3d.view_distance = restored_distance
        if hasattr(op, "original_view_perspective"):
            rv3d.view_perspective = op.original_view_perspective


# ---- 正交导航共享函数 ----

def nav_screen_space_axes(rv3d):
    """屏幕空间：right/up直接取view_rotation的X/Y轴"""
    right = rv3d.view_rotation @ Vector((1.0, 0.0, 0.0))
    up    = rv3d.view_rotation @ Vector((0.0, 1.0, 0.0))
    return right, up


def nav_world_space_axes(rv3d):
    """世界空间：用屏幕Z轴排除最垂直屏幕的世界轴，剩余两个snap到right/up"""
    screen_right = rv3d.view_rotation @ Vector((1.0, 0.0, 0.0))
    screen_up    = rv3d.view_rotation @ Vector((0.0, 1.0, 0.0))
    screen_z     = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
    world_axes   = [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    perp   = max(world_axes, key=lambda a: abs(a.dot(screen_z)))
    planar = [a for a in world_axes if a != perp]
    a0, a1 = planar
    right = a0 if abs(a0.dot(screen_right)) >= abs(a1.dot(screen_right)) else a1
    up    = a0 if abs(a0.dot(screen_up))    >= abs(a1.dot(screen_up))    else a1
    if right.dot(screen_right) < 0: right = -right
    if up.dot(screen_up)       < 0: up    = -up
    return right, up


def nav_update_ortho_move_state(op, event, keymap="WASD"):
    """正交模式按键解释，根据keymap方案（WASD/QEAD）映射到move_state"""
    if keymap == "QEAD":
        key_map = {
            "E": "FORWARD", "Q": "BACKWARD",
            "A": "LEFT",    "D": "RIGHT",
            "W": "UP",      "S": "DOWN",
        }
    else:  # WASD
        key_map = {
            "W": "FORWARD", "S": "BACKWARD",
            "A": "LEFT",    "D": "RIGHT",
            "Q": "UP",      "E": "DOWN",
        }
    if event.type in key_map:
        if event.value == "PRESS":
            op.move_state[key_map[event.type]] = True
        elif event.value == "RELEASE":
            op.move_state[key_map[event.type]] = False
    op.move_state["SPRINT"] = event.shift
    op.move_state["SLOW"]   = event.alt


def nav_update_ortho_movement(op, rv3d, dt):
    """正交模式移动：WASD屏幕/世界空间平移，QE/WS设置zoom目标速度"""
    if getattr(op, "_view_space", False):
        right, up = nav_screen_space_axes(rv3d)
    else:
        right, up = nav_world_space_axes(rv3d)

    pan = Vector((0.0, 0.0, 0.0))
    if op.move_state["FORWARD"]:  pan += up
    if op.move_state["BACKWARD"]: pan -= up
    if op.move_state["RIGHT"]:    pan += right
    if op.move_state["LEFT"]:     pan -= right
    if pan.length > 0:
        pan.normalize()

    speed = op._target_speed
    if op.move_state["SLOW"]:     speed *= op._slow_multiplier
    elif op.move_state["SPRINT"]: speed *= op._sprint_multiplier

    smooth = 1.0 - math.exp(-op._damping * dt)
    op.velocity  = op.velocity.lerp(pan * speed, smooth)
    op.location += op.velocity * dt

    zoom_speed = speed * getattr(op, "_zoom_scale", 3.0)
    if op.move_state["UP"]:
        op._zoom_target = -zoom_speed
    elif op.move_state["DOWN"]:
        op._zoom_target = zoom_speed
    else:
        op._zoom_target = 0.0

    _statusbar_state["is_active"]    = True
    _statusbar_state["current_speed"] = op.velocity.length
    _statusbar_state["target_speed"]  = speed
    _statusbar_state["view_space"]    = getattr(op, "_view_space", False)


def nav_warp_if_near_edge(op, context, event):
    """鼠标接近视口边缘时传送到对侧，防止光标移出视口"""
    if getattr(op, "_warp_margin", 0) == 0:
        return
    x, y   = event.mouse_x, event.mouse_y
    left   = op.region_x + op._warp_margin
    right  = op.region_x + op.region_width  - op._warp_margin
    bottom = op.region_y + op._warp_margin
    top    = op.region_y + op.region_height - op._warp_margin
    new_x, new_y = x, y
    if x <= left:    new_x = right
    elif x >= right: new_x = left
    if y <= bottom:  new_y = top
    elif y >= top:   new_y = bottom
    if new_x != x or new_y != y:
        context.window.cursor_warp(new_x, new_y)
        op._last_mouse_x = new_x
        op._last_mouse_y = new_y
        op._skip_next_mousemove = True


def nav_adjust_speed(op, context, direction):
    """滚轮调速：direction=1上滚加速，-1下滚减速"""
    if direction > 0:
        op._target_speed = min(op._speed_max, op._target_speed * op._speed_step)
    else:
        op._target_speed = max(op._speed_min, op._target_speed / op._speed_step)
    # 写入session变量和prefs（不写Scene，避免被Undo影响）
    set_session_target_speed(op._target_speed)
    context.preferences.addons[ADDON_PACKAGE].preferences.target_speed = op._target_speed


def nav_handle_view_rotate(op, event, fov_scale=1.0):
    """视角旋转输入处理：追踪鼠标位置，初始化/跳帧/更新yaw-pitch。
    fov_scale：FOV补偿系数，FOV越小值越小，旋转越慢（长焦下更精准）。
    适用于需要自己追踪_last_mouse_x/y的版本（鼠标版、正交版）。
    触控板版直接用mouse_prev增量，不使用此函数。"""
    if not op._mouse_initialized:
        op._mouse_initialized = True
        op._last_mouse_x = event.mouse_x
        op._last_mouse_y = event.mouse_y
        return True
    if op._skip_next_mousemove:
        op._skip_next_mousemove = False
        op._last_mouse_x = event.mouse_x
        op._last_mouse_y = event.mouse_y
        return True
    dx = event.mouse_x - op._last_mouse_x
    dy = event.mouse_y - op._last_mouse_y
    op.yaw   -= dx * op._mouse_sensitivity * fov_scale
    op.pitch += dy * op._mouse_sensitivity * fov_scale
    op.pitch  = max(-PITCH_LIMIT, min(PITCH_LIMIT, op.pitch))
    op._last_mouse_x = event.mouse_x
    op._last_mouse_y = event.mouse_y
    return True


def camera_fov_scale(lens, sensor_width=36.0, strength=1.0):
    """计算基于焦距的旋转补偿系数（含广角淡出lerp）。

    公式：
        fovT            = InverseLerp(minFOV, maxFOV, currentFOV)
        rawCompensation = tan(currentFOV/2) / tan(defaultFOV/2)
        result          = lerp(1.0, rawCompensation, (1 - fovT) * strength)

    strength=0: 不补偿（所有焦距灵敏度相同）
    strength=1: 长焦完全补偿，广角逐渐淡出补偿
    基准焦距50mm，传感器36mm（Blender默认）
    """
    MIN_FOV = 2.0
    MAX_FOV = 180.0

    # 当前半FOV（弧度）
    current_half_fov = math.atan(sensor_width / 2 / lens)
    # 基准半FOV：50mm / 36mm
    default_half_fov = math.atan(36 / 2 / 50)

    # tan比值（标准FOV补偿）
    raw = math.tan(current_half_fov) / math.tan(default_half_fov)

    # 当前FOV度数
    current_fov_deg = math.degrees(current_half_fov * 2)

    # 广角淡出：FOV越大，补偿越弱
    fov_t = max(0.0, min(1.0, (current_fov_deg - MIN_FOV) / (MAX_FOV - MIN_FOV)))
    lerp_t = (1.0 - fov_t) * strength

    return 1.0 + (raw - 1.0) * lerp_t  # lerp(1.0, raw, lerp_t)


def nav_finish_as_click(op, context, menu_by_mode):
    """短按右键后弹出context menu，用timer延迟确保modal先退出再弹出菜单"""
    import bpy as _bpy
    context.window_manager.event_timer_remove(op._timer)
    window = context.window
    area   = context.area
    region = context.region
    mode   = context.mode
    menu_name = menu_by_mode.get(mode, "VIEW3D_MT_object_context_menu")
    wm = context.window_manager
    blender_keyconfig = wm.keyconfigs.get("Blender")
    select_mouse = blender_keyconfig.preferences.select_mouse if blender_keyconfig else "LEFT"

    def show_menu():
        if select_mouse == "RIGHT":
            try:
                with _bpy.context.temp_override(window=window, area=area, region=region):
                    _bpy.ops.view3d.select("INVOKE_DEFAULT")
            except (RuntimeError, ReferenceError):
                pass
            return None
        try:
            with _bpy.context.temp_override(window=window, area=area, region=region):
                _bpy.ops.wm.call_menu("INVOKE_DEFAULT", name=menu_name)
        except (RuntimeError, KeyError, ReferenceError):
            try:
                with _bpy.context.temp_override(window=window, area=area, region=region):
                    _bpy.ops.wm.call_menu("INVOKE_DEFAULT", name="VIEW3D_MT_object_context_menu")
            except (RuntimeError, KeyError, ReferenceError):
                pass
        return None

    _bpy.app.timers.register(show_menu, first_interval=0.04)
    return {"FINISHED"}
