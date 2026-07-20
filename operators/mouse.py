"""
mouse.py
鼠标版 Unity Style Walk Navigation operator。
"""

import bpy
import math
import time
from mathutils import Vector
from bpy.types import Operator

from . import _statusbar_state, ADDON_PACKAGE
from . import navigation_core as _nav_core
from .navigation_core import (
    _KEY_MAP, _IS_MAC,
    CLICK_MOVE_THRESHOLD,
    nav_init_state, nav_compute_dt,
    nav_run_physics_substeps, nav_apply_to_view, nav_tag_statusbar_redraw,
    nav_warp_if_near_edge, nav_adjust_speed, nav_handle_view_rotate, camera_fov_scale,
    set_session_view_space, nav_finish_as_click,
)

class VIEW3D_OT_unity_walk(Operator):
    """透视视图 Unity 风格第一人称漫游（右键 + 鼠标视角 + 惯性移动）

    状态机：WAITING → NAVIGATING（含 _coasting 子状态）

    WAITING：
    - 右键 RELEASE 且鼠标几乎未移动 → 短按，弹出原生右键菜单
    - 鼠标移动超过阈值距离 → 进入 NAVIGATING

    NAVIGATING：
    - 鼠标控制视角，WASD/QE 移动，滚轮调速，Tab 切换坐标空间
    - Camera 视图下直接移动 camera 物体，退出后保持 Camera 视图
    - 松开右键 → 带惯性滑行退出；ESC → 立即退出
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
        self._press_time   = 0.0
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

        if self.mouse_moved_distance(event) >= CLICK_MOVE_THRESHOLD:
            return self.start_navigating(context, event)

        if event.type == "TIMER":
            prefs = context.preferences.addons[ADDON_PACKAGE].preferences
            if prefs.enable_time_threshold:
                self._press_time += 1 / 60
                if self._press_time >= prefs.click_time_threshold:
                    return self.start_navigating(context, event)

        return {"RUNNING_MODAL"}

    def mouse_moved_distance(self, event):
        dx = event.mouse_x - self.start_mouse_x
        dy = event.mouse_y - self.start_mouse_y
        return math.hypot(dx, dy)

    def finish_as_click(self, context):
        return nav_finish_as_click(self, context, self.menu_by_mode)

    # ---------------- 切换进入导航状态 ----------------
    def start_navigating(self, context, event):
        rv3d = context.region_data
        if rv3d is None:
            context.window_manager.event_timer_remove(self._timer)
            return {"CANCELLED"}
        nav_init_state(self, context)

        self._last_mouse_x = event.mouse_x
        self._last_mouse_y = event.mouse_y
        self._mouse_initialized = False
        self._skip_next_mousemove = False

        context.window.cursor_modal_set(self._cursor_style)
        nav_apply_to_view(self, rv3d)
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
                    prefs = context.preferences.addons[ADDON_PACKAGE].preferences
                    self._target_speed      = _nav_core._session_target_speed if _nav_core._session_target_speed is not None else prefs.target_speed
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
                fov_scale = 1.0
                strength  = getattr(self, "_fov_compensation_strength", 1.0)
                try:
                    if getattr(self, "_camera_mode", False) and self._camera_obj is not None:
                        cam = self._camera_obj.data
                        fov_scale = camera_fov_scale(cam.lens, cam.sensor_width, strength)
                    elif context.space_data is not None:
                        fov_scale = camera_fov_scale(context.space_data.lens, strength=strength)
                except Exception:
                    pass
                nav_handle_view_rotate(self, event, fov_scale)
                self.warp_if_near_edge(context, event)

            if event.type == "TAB" and event.value == "PRESS":
                self._view_space = not self._view_space
                if getattr(self, "_camera_mode", False):
                    if getattr(self, "_camera_ortho_mode", False):
                        set_session_view_space("camera_ortho", self._view_space)
                    else:
                        set_session_view_space("camera_persp", self._view_space)
                else:
                    set_session_view_space("persp", self._view_space)
                nav_tag_statusbar_redraw(self)

            if event.type == "WHEELUPMOUSE":
                nav_adjust_speed(self, context, 1)
            elif event.type == "WHEELDOWNMOUSE":
                nav_adjust_speed(self, context, -1)

            slow_keys = {"LEFT_SHIFT", "RIGHT_SHIFT", "LEFT_ALT", "RIGHT_ALT", "TIMER"}
            if _IS_MAC:
                slow_keys.add("OSKEY")
            if event.type in _KEY_MAP or event.type in slow_keys:
                self.update_move_state(event)

        if event.type == "TIMER":
            try:
                dt = nav_compute_dt(self)

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
                    nav_run_physics_substeps(self, dt)

                nav_apply_to_view(self, rv3d)
                context.area.tag_redraw()
                nav_tag_statusbar_redraw(self)
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
        nav_warp_if_near_edge(self, context, event)

    def update_move_state(self, event):
        if event.type in _KEY_MAP:
            if event.value == "PRESS":
                self.move_state[_KEY_MAP[event.type]] = True
            elif event.value == "RELEASE":
                self.move_state[_KEY_MAP[event.type]] = False

        self.move_state["SPRINT"] = event.shift
        self.move_state["SLOW"] = event.alt

    def exit_navigating(self, context):
        rv3d = context.region_data

        if self._camera_mode:
            pass  # camera模式退出时保持camera视图
        elif rv3d is not None:
            if hasattr(self, "original_view_distance"):
                restored_distance = self.original_view_distance
                if restored_distance > 0:
                    forward = rv3d.view_rotation @ Vector((0.0, 0.0, -1.0))
                    rv3d.view_location = self.location + forward * restored_distance
                    rv3d.view_distance = restored_distance
            # 恢复原始视图模式（正交/透视）
            if hasattr(self, "original_view_perspective"):
                rv3d.view_perspective = self.original_view_perspective

        context.window_manager.event_timer_remove(self._timer)
        context.window.cursor_modal_restore()
        context.area.tag_redraw()

        _statusbar_state["is_active"] = False
        nav_tag_statusbar_redraw(self)

        return {"FINISHED"}
