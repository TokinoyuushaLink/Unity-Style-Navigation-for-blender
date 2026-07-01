bl_info = {
    "name": "Unity Walk Navigation",
    "author": "TokinoyuushaLink",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Right Mouse Hold | N Panel > Unity Walk",
    "description": "Unity-style right-click first-person navigation with inertia",
    "category": "3D View",
}

import bpy
from bpy.app.handlers import persistent

from .operators import (
    VIEW3D_OT_unity_walk,
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

menumodes = [
    "Object Mode",
    "Mesh",
    "Curve",
    "Armature",
    "Metaball",
    "Lattice",
    "Font",
    "Pose",
]
panelmodes = [
    "Vertex Paint",
    "Weight Paint",
    "Image Paint",
    "Sculpt",
]

disabled_native_keymap_items = []


def disable_native_rmb_menus():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.user
    if kc is None:
        return

    for mode_name in menumodes:
        km = kc.keymaps.get(mode_name)
        if km is None:
            continue
        for kmi in km.keymap_items:
            if kmi.idname == "wm.call_menu" and kmi.type == "RIGHTMOUSE" and kmi.active:
                kmi.active = False
                disabled_native_keymap_items.append(kmi)

    for mode_name in panelmodes:
        km = kc.keymaps.get(mode_name)
        if km is None:
            continue
        for kmi in km.keymap_items:
            if kmi.idname == "wm.call_panel" and kmi.type == "RIGHTMOUSE" and kmi.active:
                kmi.active = False
                disabled_native_keymap_items.append(kmi)


def restore_native_rmb_menus():
    for kmi in disabled_native_keymap_items:
        try:
            kmi.active = True
        except ReferenceError:
            pass
    disabled_native_keymap_items.clear()


@persistent
def on_load_post(filepath):
    # 文件加载后重新禁用原生右键菜单(Blender重载会重置keymap状态)
    disable_native_rmb_menus()


def register():
    for cls in all_classes:
        bpy.utils.register_class(cls)

    register_properties()
    disable_native_rmb_menus()
    bpy.app.handlers.load_post.append(on_load_post)

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi = km.keymap_items.new(
            VIEW3D_OT_unity_walk.bl_idname,
            type="RIGHTMOUSE",
            value="PRESS",
        )
        addon_keymaps.append((km, kmi))

    bpy.types.STATUSBAR_HT_header.prepend(draw_statusbar)


def unregister():
    bpy.types.STATUSBAR_HT_header.remove(draw_statusbar)

    if on_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(on_load_post)

    restore_native_rmb_menus()

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    unregister_properties()

    for cls in all_classes:
        bpy.utils.unregister_class(cls)
