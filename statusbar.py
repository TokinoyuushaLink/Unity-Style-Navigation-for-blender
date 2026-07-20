"""
statusbar.py
状态栏绘制函数，注册到 STATUSBAR_HT_header。
数据来源：operators.navigation_core._statusbar_state（由各operator在TIMER里写入）。
"""

from .operators.navigation_core import _statusbar_state


def draw_statusbar(self, context):
    if not _statusbar_state["is_active"]:
        return

    layout = self.layout
    coord  = "View" if _statusbar_state["view_space"] else "World"
    layout.label(text=f"Coord: {coord}")
    layout.label(text=f"Speed: {_statusbar_state['target_speed']:.1f} u/s")
