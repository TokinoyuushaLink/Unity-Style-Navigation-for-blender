# Unity Style Walk Navigation

**Version:** 1.1.0  
**License:** GNU General Public License v3.0 or later (GPL-3.0-or-later)  
**Author:** TokinoyuushaLink  
**Blender:** 4.2+

---

## 功能简介

为 Blender 3D 视口提供 Unity Editor 风格的第一人称漫游导航，替代原生 Walk 模式。

- 右键长按 + 移动鼠标进入导航，松开退出（带惯性滑行）
- 指数平滑的移动惯性，起步/刹车/转向手感自然
- 滚轮实时调整移动速度，速度值自动保存
- 支持触控板（Mac/Windows），双指滑动控制视角
- 全参数可调，保存在插件全局设置中（不随 .blend 文件变化）
- 中英文界面自动跟随 Blender 语言设置

---

## 安装方法

### Blender 4.2+（推荐）

通过 Extension 方式安装（zip 包含 `blender_manifest.toml`）：

`Edit > Preferences > Add-ons > Install from Disk`，选择 zip 文件。

### 旧格式兼容

如需直接放到 `scripts/addons` 目录使用，删除 zip 中的 `blender_manifest.toml` 文件后解压到插件目录，重启 Blender 后在 Add-ons 中搜索启用。

---

## 使用方法

### 鼠标用户

| 操作 | 功能 |
|------|------|
| 右键 + 移动鼠标 | 进入第一人称导航 |
| 松开右键 | 退出导航（带惯性滑行） |
| 滑行中再次右键 | 重新进入导航 |
| W / S | 前进 / 后退 |
| A / D | 左移 / 右移 |
| Q / E | 下降 / 上升 |
| Shift | 加速冲刺 |
| Alt | 减速精细移动 |
| 滚轮上 / 下 | 调整移动速度 |
| ESC | 强制退出导航 |

### 触控板用户

需要先在 `Edit > Preferences > Add-ons > Unity Style Walk Navigation` 中开启 **Allow Trackpad Mode**，然后在 N 面板中启用 **Enable Trackpad Mode**。

| 操作 | 功能 |
|------|------|
| 双指滑动 | 进入导航并控制视角 |
| 单指移动 | 触发带滑行的退出 |
| 停止滑动（超时） | 触发带滑行的退出 |
| 滑行中再次双指滑动 | 重新进入导航 |
| 滑行中按 WASD | 取消滑行，重新进入导航 |
| 双指捏合 | 调整移动速度 |
| W / S / A / D / Q / E | 移动（同鼠标模式） |
| Shift | 加速 |
| Alt | 减速 |
| ESC | 立刻退出 |

---

## 参数说明

### N 面板（View 标签）

| 参数 | 说明 |
|------|------|
| 速度 | 目标移动速度（单位/秒），滚轮调整后自动保存 |
| 滚轮步进 | 每次滚轮调整的速度缩放比例（默认 1.15，即每次 ±15%）|
| 鼠标灵敏度 | 鼠标位移对应的视角旋转量（弧度） |
| 加速/刹车手感 | 速度平滑系数，越大越灵敏，越小越有漂移感 |
| 启用触控板模式 | 启用触控板导航（需先在 AddonPreferences 中允许）|
| 触控板灵敏度 | 触控板双指滑动对应的视角旋转量（独立于鼠标灵敏度）|

### AddonPreferences（全局设置）

展开 Add-ons 中的插件条目可访问：

- **Allow Trackpad Mode**：允许触控板导航功能
- 使用说明快捷键表
- **重置参数**：将所有参数恢复为默认值

折叠层（N 面板）中还可调整：速度倍率范围、光标样式、边界 Teleport 边距、惯性滑行参数等。

---

## 已知问题

### 触控板在 N 面板中误触发导航

在 N 面板中双指滑动时，导航有时会被意外触发。这是因为 Blender 的事件系统无法在 `TRACKPADPAN` 事件中区分 3D 视口主区域和侧边 N 面板，属于 Blender API 限制，暂无解决方案。

### Windows 触控板在滑行期间无法被打断

在 Windows 上，惯性滑行过程中双指滑动不会重新进入导航，必须等滑行结束后才能再次触发。Mac 上不存在此问题，双指滑动可以随时打断滑行。原因尚不明确，可能与 Windows 和 Mac 上 `TRACKPADPAN` 事件的传递机制差异有关。

### Windows 触控板体验较差

Windows 触控板的 `TRACKPADPAN` 事件惯性（系统级 momentum）在按下键盘按键时会被系统打断，导致视角惯性丢失。Mac 触控板体验更好。

### Blender 4.5 + Vulkan 卡顿（Windows）

在 Windows 上使用 Blender 4.5.x 并启用 Vulkan 渲染后端时，导航过程中可能出现明显卡顿。建议切换至 OpenGL 后端，或使用 Blender 4.2.x 版本。

---

## 平台支持

| 平台 | 鼠标导航 | 触控板导航 |
|------|----------|------------|
| Windows + Blender 4.2 (OpenGL) | ✅ 正常 | ⚠️ 可用，滑行期间无法打断 |
| Windows + Blender 4.5 (Vulkan) | ⚠️ 有卡顿 | ⚠️ 有卡顿，滑行期间无法打断 |
| macOS + Blender 4.2+ | ✅ 正常 | ✅ 体验良好 |

---

## 许可证

GNU General Public License v3.0 or later (GPL-3.0-or-later)

本插件以 GPL-3.0-or-later 许可证发布，详见 https://www.gnu.org/licenses/gpl-3.0.html
