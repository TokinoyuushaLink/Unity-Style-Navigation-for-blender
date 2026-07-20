https://github.com/user-attachments/assets/84f4aff7-b95d-4b05-98f5-ad102d9bf3a4

Language: ![中文](https://github.com/TokinoyuushaLink/Unity-Style-Navigation-for-blender/blob/42e67b6bed68e842f83ec0ef76ff883d86ad8135/README_ZH.md)

# Unity Style Walk Navigation <img width="32" height="32" alt="07c892c802f6455f674e9310a82cf8abd544adcc250fb0646306b35ee94cdb62" src="https://github.com/user-attachments/assets/de2ab594-4335-4e79-87de-c458ddaacc79" />

## Overview

A Unity Editor-style first-person walk navigation for the Blender 3D Viewport, replacing the built-in Walk mode.

- Enter navigation by holding right-click and moving the mouse, with inertia coasting on release.
- Exponential smoothing for movement inertia — natural feel for acceleration, braking, and turning.
- Independent navigation logic for Perspective, Orthographic, and Camera views.
- Press Tab during navigation to toggle World/View Space coordinate; setting persists within the session.
- Trackpad support (Mac / Windows): two-finger swipe to control the view.
- All parameters stored in global addon preferences (not per `.blend` file).
- Automatic language switching (currently supports Chinese and English).

---

## Installation

### Blender 4.2+ (Recommended)

`Edit > Preferences > Add-ons > Install from Disk`, select the zip file.

### Legacy Format

Remove `blender_manifest.toml` from the zip, extract to `scripts/addons`, restart Blender and enable from Add-ons.

---

## Usage

### Mouse

| Input                    | Action                                    |
| ------------------------ | ----------------------------------------- |
| RMB + Move Mouse         | Enter first-person navigation             |
| W / S / A / D / Q / E    | Forward / Back / Left / Right / Up / Down |
| Shift                    | Sprint                                    |
| Alt (Win) / Option (Mac) | Slow                                      |
| Scroll Up / Down         | Adjust speed                              |
| Tab                      | Toggle move space coordinate              |
| ESC                      | Force exit                                |

### Trackpad

In `Edit > Preferences > Keymap`, search for `Unity Style Walk Navigation (Trackpad)` and enable it.

| Input                                     | Action                            |
| ----------------------------------------- | --------------------------------- |
| Two-finger swipe                          | Enter navigation and control view |
| W / S / A / D / Q / E                     | Move                              |
| Ctrl (Win) / Option (Mac) + swipe up/down | Adjust speed                      |
| Shift                                     | Sprint                            |
| Alt (Win) / Command (Mac)                 | Slow                              |
| Tab                                       | Toggle move space coordinate      |
| ESC                                       | Force exit                        |

### Orthographic View

Short right-click shows the context menu. Hold or drag to enter navigation.

**WASD Keymap (Default)**

| Input            | Action                               |
| ---------------- | ------------------------------------ |
| RMB + Move Mouse | Rotate view (orthographic preserved) |
| W / S / A / D    | Pan up / down / left / right         |
| Q / E            | Zoom in / out                        |
| Tab              | Toggle coordinate                    |

**QEAD Keymap (Unity-style)**

| Input         | Action                       |
| ------------- | ---------------------------- |
| E / Q / A / D | Pan up / down / left / right |
| W / S         | Zoom in / out                |
| Tab           | Toggle coordinate            |

---

## Parameters

> Note: Hover tooltips in Blender do not support the addon translation API. All tooltips display in Chinese regardless of interface language.

### N Panel (View tab)

| Parameter            | Description                                                  |
| -------------------- | ------------------------------------------------------------ |
| Speed                | Movement speed (units/sec). <br />Adjusted by scroll wheel during navigation and saved automatically. |
| Scroll Step          | Speed scaling per scroll tick (default 1.15). <br />Target speed = current × or ÷ this value. |
| Mouse Sensitivity    | View rotation per pixel of mouse movement (radians).         |
| FOV Compensation     | How much lens focal length affects rotation speed (0–1). Reference lens: 50mm. Formula:<br />`lerp(`<br />    `1,`<br />    ` tan(currentFOV ÷ 2) ÷ tan(defaultFOV ÷ 2),`<br />    ` (1-fovT) × strength`<br />`)`<br />where `fovT` is the normalized FOV position in the 2°–180° range.<br />0 = no compensation, 1 = full compensation. |
| Drag                 | Velocity resistance: `factor = 1 - e^(-value × dt)`. <br />Higher = snappier; lower = more drift. |
| Trackpad Sensitivity | View rotation per pixel of two-finger swipe. <br />Independent from mouse sensitivity. |
| Trackpad Speed Step  | Speed scaling per trigger when using modifier+swipe. <br />Triggered every 20px of accumulated swipe. |
| Zoom Scale           | Ortho zoom speed as a multiplier of movement speed.          |

#### Preferences

**Coordinate**

| Parameter   | Description                                                  |
| ----------- | ------------------------------------------------------------ |
| Perspective | Default coordinate space for perspective view: World Space or View Space. Toggle with Tab. |
| Ortho       | Default coordinate space for orthographic view: World Space or View Space. |

**Keymap**

| Parameter | Description                                               |
| --------- | --------------------------------------------------------- |
| Ortho     | WASD (default, Q/E zoom) or QEAD (Unity-style, W/S zoom). |

**Speed Modifiers**

| Parameter         | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| Sprint Multiplier | Temporary speed multiplier while holding Shift.              |
| Slow Multiplier   | Temporary speed multiplier while holding Alt (Win) or Command (Mac). |
| Min / Max Speed   | Clamp range for scroll wheel speed adjustment.               |

**Other**

| Parameter        | Description                                                  |
| ---------------- | ------------------------------------------------------------ |
| Cursor Style     | Cursor appearance during navigation.                         |
| Edge Margin (px) | Pixels from viewport edge to trigger cursor teleport. Set 0 to disable. |
| Stop Threshold   | Coasting ends when speed drops below this value (units/sec). |
| Max Duration (s) | Hard time limit for coasting to prevent infinite drift.      |

---

## Known Issues

### Trackpad triggers navigation in N panel

Swiping outside the 3D Viewport (Properties, Outliner, etc.) no longer triggers navigation. However, the N panel sidebar may still accidentally trigger navigation due to a Blender API limitation. No workaround currently available.

### Windows trackpad: coasting cannot be interrupted by swiping

On Windows, two-finger swiping during inertia coasting does not resume navigation. Likely due to differences in how `TRACKPADPAN` events are delivered between platforms.

### Mac trackpad: inertia interrupted by keyboard input

On Mac, pressing a keyboard key interrupts system-level trackpad momentum, causing the view to stop abruptly.

### Blender 4.5 + Vulkan stuttering (Windows)

Using Blender 4.5.x with the Vulkan backend on Windows may cause noticeable stuttering. Switching to OpenGL or using Blender 4.2.x is recommended.

---

## Platform Support

| Platform                       | Mouse Navigation | Trackpad Navigation                     |
| ------------------------------ | ---------------- | --------------------------------------- |
| Windows + Blender 4.2 (OpenGL) | ✅ Works well     | ⚠️ Coasting cannot be interrupted        |
| macOS + Blender 4.2+           | ✅ Works well     | ⚠️ Inertia interrupted by keyboard input |

---

## License

GNU General Public License v3.0 or later (GPL-3.0-or-later)

See https://www.gnu.org/licenses/gpl-3.0.html for the full license text.
