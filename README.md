https://github.com/user-attachments/assets/fb08b2f4-d3f4-4ae6-8d13-65b778fa8d3f



Language: ![中文](https://github.com/TokinoyuushaLink/Unity-Style-Navigation-for-blender/blob/42e67b6bed68e842f83ec0ef76ff883d86ad8135/README_ZH.md)

# Unity Style Walk Navigation <img width="32" height="32" alt="07c892c802f6455f674e9310a82cf8abd544adcc250fb0646306b35ee94cdb62" src="https://github.com/user-attachments/assets/de2ab594-4335-4e79-87de-c458ddaacc79" />


**Avaliable for Blender:** 4.2+

---

## Overview

A Unity Editor-style first-person walk navigation for the Blender 3D Viewport, replacing the built-in Walk mode.

- Enter navigation by holding right-click and moving the mouse , with inertia coasting .
- Exponential smoothing for movement inertia — natural feel for acceleration, braking, and turning
- Scroll wheel adjusts movement speed in real-time . 
- Trackpad support (Mac / Windows): two-finger swipe to control the view
- All parameters are stored in global addon preferences ，rather than per `.blend` file .
- Automatic Language switching by your blender language (Currently support Chinese and English only )

## Installation

### Blender 4.2+ (Recommended)

Install as an Extension (the zip includes `blender_manifest.toml`):

`Edit > Preferences > Add-ons > Install from Disk`, select the zip file.

### Legacy Format

To use by placing directly in `scripts/addons`: remove `blender_manifest.toml` from the zip, extract the folder to your addons directory, restart Blender, and enable the addon from Add-ons preferences.

## Usage

### Mouse Users

| Input                 | Action                                          |
| --------------------- | ----------------------------------------------- |
| RMB + Move Mouse      | Enter first-person navigation                   |
| W / S / A / D / Q / E | Move Forward / Backward / Left /Right / Up Down |
| Shift                 | Sprint                                          |
| Alt (Win) / Option (Mac) | Slow / Precise movement                         |
| Scroll Up / Down      | Adjust movement speed                           |
| ESC                   | Force exit navigation                           |

### Trackpad Users

In `Edit > Preferences > Keymap`, search for `Unity Style Walk Navigation (Trackpad)` and enable it.


| Input                                     | Action                             |
| ----------------------------------------- | ---------------------------------- |
| Two-finger swipe                          | Enter navigation and control view  |
| Single-finger move                        | Trigger exit with coasting         |
| W / S / A / D / Q / E                     | Move                               |
| Ctrl (Win) / Option (Mac) + swipe up/down | Adjust movement speed              |
| Shift                                     | Sprint                             |
| Alt (Win) / Command (Mac)                 | Slow                               |
| ESC                                       | Force exit immediately             |

---

## Parameters

> Note: Hover tooltips in Blender do not support translation via the addon translation API. All tooltips are displayed in Chinese regardless of interface language. This is a Blender platform limitation shared by all addons , detailed information have listed below .

### N Panel (View tab)

| Parameter            | Description                                                  |
| -------------------- | ------------------------------------------------------------ |
| Speed                | Target movement speed (units/sec).<br />Shift/Alt/Command apply temporary multipliers without changing this value. |
| Scroll Step          | Speed scaling per scroll tick (default 1.15 = ±15%). <br />Multiplicative: scroll up × value, scroll down ÷ value. |
| Mouse Sensitivity    | View rotation per pixel of mouse movement (radians). <br />Higher = faster rotation. |
| Accel/Brake Feel     | Exponential decay smoothing: `factor = 1 - e^(-value × dt)`. <br />Higher = snappier; lower = more drift. |
| Trackpad Sensitivity | View rotation per pixel of two-finger swipe. <br />Independent from mouse sensitivity. |
| Trackpad Speed Step  | Speed scaling per trigger when using modifier+swipe. <br />Same as Scroll Step but triggered every 20px of accumulated swipe distance. |


Preferences section in N panel exposes additional parameters:

| Parameter         | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| Sprint Multiplier | Speed multiplier while holding Shift. <br />Applied on top of target speed. |
| Slow Multiplier   | Speed multiplier while holding Alt (Win) or Command (Mac).|
| Min / Max Speed   | Clamp range for scroll wheel speed adjustment.               |
| Cursor Style      | Cursor appearance during navigation|
| Edge Margin (px)  | Pixels from viewport edge to trigger cursor teleport to opposite side.|
| Stop Threshold    | Coasting ends when speed drops below this value (units/sec). |
| Max Duration (s)  | Hard time limit for coasting to prevent infinite drift.      |

## Known Issues

### Trackpad triggers navigation in N panel

Swiping outside the 3D Viewport (Properties, Outliner, etc.) no longer triggers navigation. However, the N panel (sidebar) may still accidentally trigger navigation. This is due to a Blender API limitation: `TRACKPADPAN` events cannot distinguish between the main 3D viewport area and the N panel sidebar. No workaround is currently available.

### Windows trackpad: coasting cannot be interrupted by swiping

On Windows, two-finger swiping during inertia coasting does not resume navigation — you must wait for coasting to finish first. The cause is likely a difference in how `TRACKPADPAN` events are delivered between platforms.

### Mac trackpad: inertia interrupted by keyboard input

On Mac, the system-level trackpad momentum (`TRACKPADPAN` trailing events) is interrupted when a keyboard key is pressed, causing the view to stop abruptly.

### Blender 4.5 + Vulkan stuttering (Windows)

Using Blender 4.5.x with the Vulkan rendering backend on Windows may cause noticeable stuttering during navigation. Switching to the OpenGL backend, or using Blender 4.2.x, might solve the problem .

## Platform Support

| Platform                       | Mouse Navigation | Trackpad Navigation                          |
| ------------------------------ | ---------------- | -------------------------------------------- |
| Windows + Blender 4.2 (OpenGL) | ✅ Works well     | ⚠️ Coasting cannot be interrupted |
| macOS + Blender 4.2+           | ✅ Works well     | ⚠️ inertia interrupted by keyboard input    |

---

## License

GNU General Public License v3.0 or later (GPL-3.0-or-later)

See https://www.gnu.org/licenses/gpl-3.0.html for the full license text.


