bl_info = {
    "name": "Unity Style Walk Navigation",
    "author": "TokinoyuushaLink",
    "version": (1, 1, 2),
    "blender": (4, 2, 0),
    "location": "3D View > Right Mouse Hold | N Panel > Unity Walk",
    "description": "Unity-style right-click first-person navigation with inertia",
    "category": "3D View",
}

import bpy

from .operators import (
    VIEW3D_OT_unity_walk,
    VIEW3D_OT_unity_walk_trackpad,
    draw_statusbar,
    classes as operator_classes,
)
from .preferences import (
    UnityWalkPreferences,
    UW_OT_reset_params,
    VIEW3D_PT_unity_walk,
    register_properties,
    unregister_properties,
    classes as panel_classes,
)
from .i18n import translations_dict

all_classes = operator_classes + panel_classes

addon_keymaps = []


def register():
    bpy.app.translations.register(__name__, translations_dict)

    for cls in all_classes:
        bpy.utils.register_class(cls)

    register_properties()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

        # 鼠标版: RIGHTMOUSE触发
        kmi_mouse = km.keymap_items.new(
            VIEW3D_OT_unity_walk.bl_idname,
            type="RIGHTMOUSE",
            value="PRESS",
        )
        addon_keymaps.append((km, kmi_mouse))

        # 触控板版: TRACKPADPAN触发,默认关闭
        # 用户可在 Edit > Preferences > Keymap 中手动启用
        kmi_pad = km.keymap_items.new(
            VIEW3D_OT_unity_walk_trackpad.bl_idname,
            type="TRACKPADPAN",
            value="NOTHING",
        )
        kmi_pad.active = False
        addon_keymaps.append((km, kmi_pad))

    bpy.types.STATUSBAR_HT_header.prepend(draw_statusbar)


def unregister():
    bpy.types.STATUSBAR_HT_header.remove(draw_statusbar)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    unregister_properties()

    for cls in all_classes:
        bpy.utils.unregister_class(cls)

    bpy.app.translations.unregister(__name__)
