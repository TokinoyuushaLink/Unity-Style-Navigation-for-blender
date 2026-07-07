bl_info = {
    "name": "Unity Style Walk Navigation",
    "author": "TokinoyuushaLink",
    "version": (1, 2, 0),
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

# 需要注册keymap的所有3D视口模式
# head=True确保我们的operator优先于原生右键菜单处理事件
_KNOWN_MODE_KEYMAPS = (
    ("3D View",         "VIEW_3D", "WINDOW"),
    ("3D View Generic", "VIEW_3D", "WINDOW"),
    ("Object Non-modal",                        "EMPTY", "WINDOW"),
    ("Object Mode",                             "EMPTY", "WINDOW"),
    ("Mesh",                                    "EMPTY", "WINDOW"),
    ("Curve",                                   "EMPTY", "WINDOW"),
    ("Curves",                                  "EMPTY", "WINDOW"),
    ("Armature",                                "EMPTY", "WINDOW"),
    ("Pose",                                    "EMPTY", "WINDOW"),
    ("Lattice",                                 "EMPTY", "WINDOW"),
    ("Font",                                    "EMPTY", "WINDOW"),
    ("Metaball",                                "EMPTY", "WINDOW"),
    ("Point Cloud",                             "EMPTY", "WINDOW"),
    ("Particle",                                "EMPTY", "WINDOW"),
    ("Sculpt",                                  "EMPTY", "WINDOW"),
    ("Vertex Paint",                            "EMPTY", "WINDOW"),
    ("Weight Paint",                            "EMPTY", "WINDOW"),
    ("Image Paint",                             "EMPTY", "WINDOW"),
    ("Sculpt Curves",                           "EMPTY", "WINDOW"),
    ("Grease Pencil",                           "EMPTY", "WINDOW"),
    ("Grease Pencil Edit Mode",                 "EMPTY", "WINDOW"),
    ("Grease Pencil Draw Mode",                 "EMPTY", "WINDOW"),
    ("Grease Pencil Sculpt Mode",               "EMPTY", "WINDOW"),
    ("Grease Pencil Weight Paint",              "EMPTY", "WINDOW"),
    ("Grease Pencil Vertex Paint",              "EMPTY", "WINDOW"),
)


def register():
    bpy.app.translations.register(__name__, translations_dict)

    for cls in all_classes:
        bpy.utils.register_class(cls)

    register_properties()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        for name, space_type, region_type in _KNOWN_MODE_KEYMAPS:
            km = kc.keymaps.new(
                name=name,
                space_type=space_type,
                region_type=region_type,
            )
            # head=True: 确保我们的operator在原生右键菜单之前处理事件
            kmi_mouse = km.keymap_items.new(
                VIEW3D_OT_unity_walk.bl_idname,
                type="RIGHTMOUSE",
                value="PRESS",
                head=True,
            )
            addon_keymaps.append((km, kmi_mouse))

        # 触控板版: 只注册在3D View, 默认关闭
        km_pad = kc.keymaps.new(name="3D View", space_type="VIEW_3D")
        kmi_pad = km_pad.keymap_items.new(
            VIEW3D_OT_unity_walk_trackpad.bl_idname,
            type="TRACKPADPAN",
            value="NOTHING",
        )
        kmi_pad.active = False
        addon_keymaps.append((km_pad, kmi_pad))

    bpy.types.STATUSBAR_HT_header.prepend(draw_statusbar)


def unregister():
    bpy.types.STATUSBAR_HT_header.remove(draw_statusbar)

    for km, kmi in addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except (ReferenceError, RuntimeError):
            pass
    addon_keymaps.clear()

    unregister_properties()

    for cls in all_classes:
        bpy.utils.unregister_class(cls)

    bpy.app.translations.unregister(__name__)
