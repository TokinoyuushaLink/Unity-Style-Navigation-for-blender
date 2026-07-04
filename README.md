https://github.com/user-attachments/assets/78f21800-bf00-4829-a0e3-60fb82aa49a7

Language: ![中文](https://github.com/TokinoyuushaLink/Unity-Style-Navigation-for-blender/blob/42e67b6bed68e842f83ec0ef76ff883d86ad8135/README_ZH.md)

# Unity Style Walk Navigation

**Version:** 1.1.2  
**License:** GNU General Public License v3.0 or later (GPL-3.0-or-later)  
**Author:** TokinoyuushaLink  
**Blender:** 4.2+

---

## Overview

A Unity Editor-style first-person walk navigation for the Blender 3D Viewport, replacing the built-in Walk mode.

- Enter navigation by holding right-click and moving the mouse; release to exit (with inertia coasting)
- Exponential smoothing for movement inertia — natural feel for acceleration, braking, and turning
- Scroll wheel adjusts movement speed in real-time; the value is saved automatically
- Trackpad support (Mac / Windows): two-finger swipe to control the view
- All parameters are stored in global addon preferences (not per `.blend` file)
- UI language follows Blender's interface language setting (Chinese / English)

---

## Installation

### Blender 4.2+ (Recommended)

Install as an Extension (the zip includes `blender_manifest.toml`):

`Edit > Preferences > Add-ons > Install from Disk`, select the zip file.

### Legacy Format

To use by placing directly in `scripts/addons`: remove `blender_manifest.toml` from the zip, extract the folder to your addons directory, restart Blender, and enable the addon from Add-ons preferences.

---

## Usage

### Mouse Users

| Input                 | Action                                          |
| --------------------- | ----------------------------------------------- |
| RMB + Move Mouse      | Enter first-person navigation                   |
| Release RMB           | Exit navigation (with inertia coasting)         |
| RMB during coasting   | Re-enter navigation                             |
| W / S / A / D / Q / E | Move Forward / Backward / Left /Right / Up Down |
| Shift                 | Sprint                                          |
| Alt                   | Slow / Precise movement                         |
| Scroll Up / Down      | Adjust movement speed                           |
| ESC                   | Force exit navigation                           |

### Trackpad Users

In `Edit > Preferences > Keymap`, search for `Unity Style Walk Navigation (Trackpad)` and enable it.


| Input                                     | Action                             |
| ----------------------------------------- | ---------------------------------- |
| Two-finger swipe                          | Enter navigation and control view  |
| Single-finger move                        | Trigger exit with coasting         |
| Stop swiping (timeout)                    | Trigger exit with coasting         |
| Two-finger swipe during coasting          | Resume navigation                  |
| WASD during coasting                      | Cancel coasting, resume navigation |
| Ctrl (Win) / Option (Mac) + swipe up/down | Adjust movement speed              |
| W / S / A / D / Q / E                     | Move                               |
| Shift                                     | Sprint                             |
| Alt (Win) / Command (Mac)                 | Slow                               |
| ESC                                       | Force exit immediately             |

---

## Parameters

> Note: Hover tips (tooltips) in Blender do not support translation via the addon translation API. All tooltips are displayed in Chinese regardless of interface language. This is a Blender platform limitation shared by all addons.

### N Panel (View tab)

| Parameter            | Description                                                  |
| -------------------- | ------------------------------------------------------------ |
| Speed                | Target movement speed (units/sec). The scroll wheel adjusts this in real-time and saves automatically. Shift/Alt/Command apply temporary multipliers without changing this value. |
| Scroll Step          | Speed scaling per scroll tick (default 1.15 = ±15%). Multiplicative: scroll up × value, scroll down ÷ value. |
| Mouse Sensitivity    | View rotation per pixel of mouse movement (radians). Higher = faster rotation. |
| Accel/Brake Feel     | Exponential decay smoothing: `factor = 1 - e^(-value × dt)`. Higher = snappier; lower = more drift. |
| Trackpad Sensitivity | View rotation per pixel of two-finger swipe. Independent from mouse sensitivity. |
| Trackpad Speed Step  | Speed scaling per trigger when using modifier+swipe. Same as Scroll Step but triggered every 20px of accumulated swipe distance. |

### AddonPreferences (Global Settings)

Expand the addon entry in Add-ons to access:

- **Allow Trackpad Mode**: Enable trackpad navigation globally
- Quick reference keymap table (platform-specific: Mac or Windows)
- **Reset Parameters**: Restore all parameters to defaults

The collapsible section in the N panel exposes additional parameters:

| Parameter         | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| Sprint Multiplier | Temporary speed multiplier while holding Shift. Applied on top of target speed. |
| Slow Multiplier   | Temporary speed multiplier while holding Alt (Win) or Command (Mac). Overrides Sprint. |
| Min / Max Speed   | Clamp range for scroll wheel speed adjustment.               |
| Cursor Style      | Cursor appearance during navigation: Hidden, Scroll XY, Crosshair, or Dot. |
| Edge Margin (px)  | Pixels from viewport edge to trigger cursor teleport to opposite side. Set 0 to disable. |
| Stop Threshold    | Coasting ends when speed drops below this value (units/sec). |
| Max Duration (s)  | Hard time limit for coasting to prevent infinite drift.      |

---

## Known Issues

### Trackpad triggers navigation in N panel

Swiping outside the 3D Viewport (Properties, Outliner, etc.) no longer triggers navigation. However, the N panel (sidebar) may still accidentally trigger navigation. This is due to a Blender API limitation: `TRACKPADPAN` events cannot distinguish between the main 3D viewport area and the N panel sidebar. No workaround is currently available.

### Windows trackpad: coasting cannot be interrupted by swiping

On Windows, two-finger swiping during inertia coasting does not resume navigation — you must wait for coasting to finish first. This does not occur on macOS. The cause is likely a difference in how `TRACKPADPAN` events are delivered between platforms.

### Windows trackpad: inertia interrupted by keyboard input

On Windows, the system-level trackpad momentum (`TRACKPADPAN` trailing events) is interrupted when a keyboard key is pressed, causing the view to stop abruptly. macOS trackpad experience is significantly better.

### Blender 4.5 + Vulkan stuttering (Windows)

Using Blender 4.5.x with the Vulkan rendering backend on Windows may cause noticeable stuttering during navigation. Switching to the OpenGL backend, or using Blender 4.2.x, is recommended.

---

## Platform Support

| Platform                       | Mouse Navigation | Trackpad Navigation                          |
| ------------------------------ | ---------------- | -------------------------------------------- |
| Windows + Blender 4.2 (OpenGL) | ✅ Works well     | ⚠️ Functional, coasting cannot be interrupted |
| Windows + Blender 4.5 (Vulkan) | ⚠️ Stuttering     | ⚠️ Stuttering, coasting cannot be interrupted |
| macOS + Blender 4.2+           | ✅ Works well     | ✅ Works well                                 |

---

## License

GNU General Public License v3.0 or later (GPL-3.0-or-later)

See https://www.gnu.org/licenses/gpl-3.0.html for the full license text.


