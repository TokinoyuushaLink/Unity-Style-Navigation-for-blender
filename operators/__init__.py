"""
operators/__init__.py
export classes、draw_statusbar，以及跨模块共享的数据。
"""

# _statusbar_state和ADDON_PACKAGE定义在navigation_core，从那里导入
from .navigation_core import (
    ADDON_PACKAGE,
    _statusbar_state,
    TARGET_SPEED, SPEED_STEP, SPEED_MIN, SPEED_MAX,
    MOUSE_SENSITIVITY, DAMPING, SPRINT_MULTIPLIER, SLOW_MULTIPLIER,
    CURSOR_STYLE, WARP_MARGIN, COAST_STOP_THRESHOLD, COAST_MAX_DURATION,
    CLICK_TIME_THRESHOLD, CLICK_MOVE_THRESHOLD,
    PITCH_LIMIT, PHYSICS_SUBSTEP,
    TRACKPAD_TIMEOUT, TRACKPAD_EXIT_THRESHOLD, TRACKPAD_SPEED_PIXELS,
    nav_init_state, nav_compute_dt, nav_update_move_state,
    nav_run_physics_substeps, nav_apply_to_view, nav_tag_statusbar_redraw,
    nav_restore_view_distance,
    nav_screen_space_axes, nav_world_space_axes,
    nav_update_ortho_move_state, nav_update_ortho_movement,
    nav_warp_if_near_edge,
    nav_adjust_speed, nav_handle_view_rotate, camera_fov_scale,
    set_session_view_space, set_session_target_speed, nav_finish_as_click,
)

from .mouse       import VIEW3D_OT_unity_walk
from .trackpad    import VIEW3D_OT_unity_walk_trackpad
from .ortho       import VIEW3D_OT_unity_walk_ortho
from ..statusbar  import draw_statusbar

classes = (
    VIEW3D_OT_unity_walk,
    VIEW3D_OT_unity_walk_trackpad,
    VIEW3D_OT_unity_walk_ortho,
)
