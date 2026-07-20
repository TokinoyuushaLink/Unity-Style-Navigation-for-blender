"""
ortho.py
正交视图 Unity Style Walk Navigation operator。
"""

import bpy
import math
import time
from mathutils import Vector, Quaternion
from bpy.types import Operator

from . import _statusbar_state, ADDON_PACKAGE
from .navigation_core import (
    _KEY_MAP, _PITCH_OFFSET,
    CLICK_MOVE_THRESHOLD,
    nav_screen_space_axes, nav_world_space_axes,
    nav_update_ortho_move_state, nav_update_ortho_movement,
    nav_warp_if_near_edge, nav_adjust_speed, nav_handle_view_rotate,
    set_session_view_space, nav_finish_as_click,
)
from . import navigation_core as _nav_core  # 用于读取session变量

class VIEW3D_OT_unity_walk_ortho(Operator):
    """正交视图导航（完全独立类）

    - 右键+移动鼠标 → 旋转视角（保持正交投影）
    - WASD → 屏幕空间平移
    - Q/E → 缩小/放大正交比例（view_distance）
    - Shift → 加速，Alt → 减速
    - ESC / 松开右键 → 退出
    """

    bl_idname = "view3d.unity_walk_ortho"
    bl_label = "Unity Style Walk Navigation"
    bl_options = {"REGISTER"}

    # 复用鼠标版的菜单映射
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

        rv3d = context.region_data
        if rv3d is None or rv3d.view_perspective != "ORTHO":
            return {"PASS_THROUGH"}

        # WAITING状态：等待判断短按（菜单）还是长按（导航）
        self.state = "WAITING"
        self.start_mouse_x = event.mouse_x
        self.start_mouse_y = event.mouse_y
        self._press_time   = 0.0

        self._timer = context.window_manager.event_timer_add(1 / 60, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        rv3d = context.region_data
        if rv3d is None:
            return self._exit(context)

        if self.state == "WAITING":
            return self._modal_waiting(context, event)
        return self._modal_navigating(context, event)

    def _modal_waiting(self, context, event):
        if event.type == "RIGHTMOUSE" and event.value == "RELEASE":
            return self._finish_as_click(context)

        dx = event.mouse_x - self.start_mouse_x
        dy = event.mouse_y - self.start_mouse_y
        if (dx * dx + dy * dy) >= CLICK_MOVE_THRESHOLD ** 2:
            return self._start_navigating(context)

        if event.type == "TIMER":
            prefs = context.preferences.addons[ADDON_PACKAGE].preferences
            if prefs.enable_time_threshold:
                self._press_time += 1 / 60
                if self._press_time >= prefs.click_time_threshold:
                    return self._start_navigating(context)

        return {"RUNNING_MODAL"}

    def _finish_as_click(self, context):
        return nav_finish_as_click(self, context, self.menu_by_mode)

    def _start_navigating(self, context):
        """从WAITING切换到NAVIGATING，读取所有参数"""
        rv3d = context.region_data
        if rv3d is None:
            context.window_manager.event_timer_remove(self._timer)
            return {"CANCELLED"}
        self.state = "NAVIGATING"

        prefs = context.preferences.addons[ADDON_PACKAGE].preferences
        self._mouse_sensitivity         = prefs.mouse_sensitivity
        self._fov_compensation_strength = prefs.fov_compensation_strength
        self._damping              = prefs.damping
        self._sprint_multiplier    = prefs.sprint_multiplier
        self._slow_multiplier      = prefs.slow_multiplier
        self._cursor_style         = prefs.cursor_style
        self._warp_margin          = prefs.warp_margin
        self._coast_stop_threshold = prefs.coast_stop_threshold
        self._coast_max_duration   = prefs.coast_max_duration
        scene = context.scene
        self._target_speed = _nav_core._session_target_speed if _nav_core._session_target_speed is not None else prefs.target_speed
        self._speed_step   = prefs.speed_step
        self._speed_min    = prefs.speed_min
        self._speed_max    = prefs.speed_max
        self._zoom_scale       = prefs.ortho_zoom_scale
        self._ortho_keymap     = prefs.ortho_keymap
        self._view_space       = (_nav_core._session_ortho_view_space if _nav_core._session_ortho_view_space is not None
                                  else (prefs.default_ortho_coord_system == "VIEW"))

        self.original_view_distance = rv3d.view_distance
        self.location = rv3d.view_location.copy()
        rot = rv3d.view_rotation
        forward = rot @ Vector((0.0, 0.0, -1.0))
        self.yaw   = math.atan2(-forward.x, forward.y)
        self.pitch = math.asin(max(-1.0, min(1.0, forward.z)))
        self.velocity = Vector((0.0, 0.0, 0.0))

        self.move_state = {
            "FORWARD": False, "BACKWARD": False,
            "LEFT": False,    "RIGHT": False,
            "UP": False,      "DOWN": False,
            "SPRINT": False,  "SLOW": False,
        }

        region = context.region
        self.region_x      = region.x
        self.region_y      = region.y
        self.region_width  = region.width
        self.region_height = region.height

        self._coasting          = False
        self._coast_elapsed     = 0.0
        self._last_mouse_x      = 0
        self._last_mouse_y      = 0
        self._mouse_initialized = False
        self._skip_next_mousemove = False
        self._last_tick_time    = time.perf_counter()
        self._zoom_velocity     = 0.0
        self._zoom_target       = 0.0

        self._statusbar_area = next(
            (a for a in context.window.screen.areas if a.type == "STATUSBAR"), None
        )

        context.window.cursor_modal_set(self._cursor_style)
        _statusbar_state["is_active"]    = True
        _statusbar_state["target_speed"]  = self._target_speed
        _statusbar_state["view_space"]    = self._view_space

        return {"RUNNING_MODAL"}

    def _modal_navigating(self, context, event):
        rv3d = context.region_data
        if rv3d is None:
            return self._exit(context)

        if event.type == "ESC":
            return self._exit(context)

        if event.type == "RIGHTMOUSE":
            in_region = (
                self.region_x <= event.mouse_x <= self.region_x + self.region_width
                and self.region_y <= event.mouse_y <= self.region_y + self.region_height
            )
            if in_region and event.value == "RELEASE" and not self._coasting:
                if (self.velocity.length < self._coast_stop_threshold
                        and abs(self._zoom_velocity) < 0.0001):
                    return self._exit(context)
                self._coasting = True
                self._coast_elapsed = 0.0
                context.window.cursor_modal_restore()
            elif in_region and event.value == "PRESS" and self._coasting:
                self._coasting = False
                self._mouse_initialized = False
                context.window.cursor_modal_set(self._cursor_style)

        # 鼠标移动 → 旋转视角
        if not self._coasting and event.type == "MOUSEMOVE":
            nav_handle_view_rotate(self, event)
            self._warp_if_near_edge(context, event)

        # 滚轮调速
        if not self._coasting:
            if event.type == "WHEELUPMOUSE":
                nav_adjust_speed(self, context, 1)
            elif event.type == "WHEELDOWNMOUSE":
                nav_adjust_speed(self, context, -1)

        # 按键状态（两种keymap方案的所有按键都监听）
        all_keys = set(_KEY_MAP.keys()) | {"W", "S", "Q", "E", "A", "D"}
        if event.type in all_keys or event.type in {
            "LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_ALT", "RIGHT_ALT", "TIMER"
        }:
            self._update_move_state(event)

        if event.type == "TAB" and event.value == "PRESS":
            self._view_space = not self._view_space
            set_session_view_space("ortho", self._view_space)
            _statusbar_state["view_space"] = self._view_space
            if self._statusbar_area:
                try:
                    self._statusbar_area.tag_redraw()
                except ReferenceError:
                    pass

        if event.type == "TIMER":
            try:
                now = time.perf_counter()
                dt = min(now - self._last_tick_time, 0.5)
                self._last_tick_time = now

                if self._coasting:
                    self._coast_elapsed += dt
                    smooth = 1.0 - math.exp(-self._damping * dt)
                    self.velocity = self.velocity.lerp(Vector((0.0, 0.0, 0.0)), smooth)
                    self.location += self.velocity * dt
                    # 滑行时zoom也继续衰减
                    self._zoom_velocity += (0.0 - self._zoom_velocity) * smooth
                    if abs(self._zoom_velocity) > 0.0001:
                        rv3d.view_distance = max(0.001, rv3d.view_distance + self._zoom_velocity * dt)
                    if (self.velocity.length < self._coast_stop_threshold
                            and abs(self._zoom_velocity) < 0.0001
                            or self._coast_elapsed >= self._coast_max_duration):
                        return self._exit(context)
                else:
                    self._update_movement(rv3d, dt)
                    # QE缩放惯性：_zoom_velocity平滑趋向_zoom_target
                    smooth = 1.0 - math.exp(-self._damping * dt)
                    self._zoom_velocity += (self._zoom_target - self._zoom_velocity) * smooth
                    if abs(self._zoom_velocity) > 0.0001:
                        rv3d.view_distance = max(0.001, rv3d.view_distance + self._zoom_velocity * dt)

                # apply: 旋转+平移，不改view_distance
                yaw_quat   = Quaternion((0.0, 0.0, 1.0), self.yaw)
                pitch_quat = Quaternion((1.0, 0.0, 0.0), self.pitch + _PITCH_OFFSET)
                rv3d.view_rotation = yaw_quat @ pitch_quat
                rv3d.view_location = self.location

                _statusbar_state["target_speed"] = self._target_speed
                context.area.tag_redraw()
                if self._statusbar_area:
                    try:
                        self._statusbar_area.tag_redraw()
                    except ReferenceError:
                        self._statusbar_area = None
            except Exception as e:
                print(f"[unity_walk_ortho] 更新出错: {e}")
                return self._exit(context)

        return {"RUNNING_MODAL"}

    def _update_move_state(self, event):
        nav_update_ortho_move_state(self, event, getattr(self, "_ortho_keymap", "WASD"))

    def _screen_space_axes(self, rv3d):
        return nav_screen_space_axes(rv3d)

    def _world_space_axes(self, rv3d):
        return nav_world_space_axes(rv3d)

    def _update_movement(self, rv3d, dt):
        nav_update_ortho_movement(self, rv3d, dt)

    def _warp_if_near_edge(self, context, event):
        nav_warp_if_near_edge(self, context, event)

    def _exit(self, context):
        context.window_manager.event_timer_remove(self._timer)
        context.window.cursor_modal_restore()
        context.area.tag_redraw()
        _statusbar_state["is_active"] = False
        if self._statusbar_area:
            try:
                self._statusbar_area.tag_redraw()
            except ReferenceError:
                pass
        return {"FINISHED"}
