bl_info = {
    "name": "Unity Style Walk Navigation",
    "author": "TokinoyuushaLink",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Right Mouse Hold | N Panel > Unity Walk",
    "description": "Unity-style right-click first-person navigation with inertia",
    "category": "3D View",
}

import bpy
from bpy.app.handlers import persistent

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

all_classes = operator_classes + panel_classes

addon_keymaps = []


@persistent
def on_load_post(filepath):
    try:
        prefs = bpy.context.preferences.addons[__package__].preferences
        enabled = prefs.allow_trackpad and prefs.use_trackpad
        for km, kmi in addon_keymaps:
            if kmi.idname == "view3d.unity_walk_trackpad":
                kmi.active = enabled
    except Exception:
        pass


def register():
    for cls in all_classes:
        bpy.utils.register_class(cls)

    register_properties()
    bpy.app.handlers.load_post.append(on_load_post)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

        kmi_mouse = km.keymap_items.new(
            VIEW3D_OT_unity_walk.bl_idname,
            type="RIGHTMOUSE",
            value="PRESS",
        )
        addon_keymaps.append((km, kmi_mouse))

        # 触控板版: 默认inactive,由allow_trackpad+use_trackpad双层开关控制
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

    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    unregister_properties()

    for cls in all_classes:
        bpy.utils.unregister_class(cls)
