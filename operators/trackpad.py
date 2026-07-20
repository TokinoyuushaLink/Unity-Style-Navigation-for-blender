"""
trackpad.py
触控板版 Unity Style Walk Navigation operator。
"""

import bpy
import math
import time
from mathutils import Vector
from bpy.types import Operator

from . import navigation_core as _nav_core  # 用于读取session变量
from . import _statusbar_state, ADDON_PACKAGE
from .navigation_core import (
    _KEY_MAP, _IS_MAC, _SPEED_ADJUST_KEY,
    PITCH_LIMIT,
    TRACKPAD_TIMEOUT, TRACKPAD_EXIT_THRESHOLD, TRACKPAD_SPEED_PIXELS,
    nav_init_state, nav_compute_dt, nav_update_move_state,
    nav_run_physics_substeps, nav_apply_to_view, nav_tag_statusbar_redraw,
    nav_restore_view_distance,
    nav_update_ortho_move_state, nav_update_ortho_movement,
    set_session_view_space,
)

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
            self._mouse_sensitivity = context.preferences.addons[ADDON_PACKAGE].preferences.trackpad_sensitivity

            # 正交模式：加载正交专属参数，覆盖session坐标
            if getattr(self, "_ortho_mode", False):
                prefs = context.preferences.addons[ADDON_PACKAGE].preferences
                self._ortho_keymap  = prefs.ortho_keymap
                self._zoom_scale    = prefs.ortho_zoom_scale
                self._zoom_velocity = 0.0
                self._zoom_target   = 0.0
                self._view_space    = (_nav_core._session_ortho_view_space if _nav_core._session_ortho_view_space is not None
                                       else (prefs.default_ortho_coord_system == "VIEW"))
            else:
                prefs = context.preferences.addons[ADDON_PACKAGE].preferences
                self._view_space = (_nav_core._session_persp_view_space if _nav_core._session_persp_view_space is not None
                                    else (prefs.default_coord_system == "VIEW"))
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
                context.preferences.addons[ADDON_PACKAGE].preferences.target_speed = self._target_speed
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
        if rv3d is None:
            nav_restore_view_distance(self, context)
            context.window_manager.event_timer_remove(self._timer)
            context.window.cursor_modal_restore()
            self.state = "IDLE"
            return {"RUNNING_MODAL"}
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
                context.preferences.addons[ADDON_PACKAGE].preferences.target_speed = self._target_speed
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
        all_keys = set(_KEY_MAP.keys()) | {"W", "S", "Q", "E", "A", "D"}
        if event.type in all_keys or event.type in slow_keys:
            if getattr(self, "_ortho_mode", False):
                self._update_ortho_move_state(event)
            else:
                nav_update_move_state(self, event)

        if event.type == "TAB" and event.value == "PRESS":
            self._view_space = not self._view_space
            if getattr(self, "_ortho_mode", False):
                set_session_view_space("ortho", self._view_space)
            else:
                set_session_view_space("persp", self._view_space)
            nav_tag_statusbar_redraw(self)

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

                    # 正交模式：滑行时zoom也衰减
                    if getattr(self, "_ortho_mode", False):
                        self._zoom_velocity += (0.0 - self._zoom_velocity) * smooth_factor
                        if abs(self._zoom_velocity) > 0.0001:
                            rv3d.view_distance = max(0.001, rv3d.view_distance + self._zoom_velocity * dt)

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
                            and (not getattr(self, "_ortho_mode", False)
                                 or abs(getattr(self, "_zoom_velocity", 0.0)) < 0.0001)
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
                    if getattr(self, "_ortho_mode", False):
                        self._update_ortho_movement(rv3d, dt)
                        # QE缩放惯性
                        smooth_factor = 1.0 - math.exp(-self._damping * dt)
                        self._zoom_velocity += (self._zoom_target - self._zoom_velocity) * smooth_factor
                        if abs(self._zoom_velocity) > 0.0001:
                            rv3d.view_distance = max(0.001, rv3d.view_distance + self._zoom_velocity * dt)
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

    # ---- 正交模式专用方法（委托给navigation_core）----

    def _update_ortho_move_state(self, event):
        nav_update_ortho_move_state(self, event, getattr(self, "_ortho_keymap", "WASD"))

    def _update_ortho_movement(self, rv3d, dt):
        nav_update_ortho_movement(self, rv3d, dt)
