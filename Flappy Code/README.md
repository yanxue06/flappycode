# Flappy Code

A tiny, zero-dependency Flappy Bird overlay for macOS. Pop it open on top of
Cursor, VS Code, or your terminal while your LLM is thinking — flap through
pipes instead of staring at a spinner.

**One file. No install. Just `python3 flappy.py`.**

## Features

- Translucent, always-on-top, frameless window
- Resize from any edge or corner (not just bottom-right)
- Six-level sky transparency so you can see your code through the game
- Progressive difficulty: pipes speed up and gaps shrink as you score
- Low CPU usage: skips rendering when paused, idle, or on game-over screen
- Preset sizes (S / M / L / XL) or free-resize to any dimension

## Requirements

- macOS with Python 3.10+ (uses the built-in `tkinter` / Tk 8.6)
- No `pip install` needed — stdlib only

## Quick Start

```bash
# Option 1: run directly
python3 flappy.py

# Option 2: use the launcher script
./run.sh
```

## Controls

| Key / Action | Effect |
|---|---|
| **Space** / **Up** / **W** / **Click** | Flap |
| **P** (or `II` button) | Pause / resume |
| **R** (or `↻` button) | Restart |
| **+** / **-** | Grow / shrink window |
| **S** (or size button) | Cycle S / M / L / XL presets |
| **[** / **]** / **T** (or `◐` button) | Adjust sky transparency |
| **Drag title bar** | Move window |
| **Drag any edge or corner** | Resize window |
| **Esc** or **x** button | Quit |

## Transparency

The sky is the only translucent layer — bird, pipes, ground, and score stay
crisp. Six levels cycle through:

| Level | Fill |
|---|---|
| solid | 100% opaque |
| mostly solid | ~75% |
| medium (default) | ~50% |
| mostly clear | ~25% |
| very clear | ~12% |
| invisible | sky hidden entirely |

Implemented with Tk stipple patterns + the macOS `-transparent` window
attribute. No per-pixel alpha blending needed.

## Tweaking

All tunables live at the top of `flappy.py`:

| Variable | What it does |
|---|---|
| `SIZE_PRESETS` | S/M/L/XL dimensions |
| `FPS` | Target frame rate (lower = less CPU) |
| `GRAVITY_REF`, `FLAP_V_REF`, `MAX_FALL_REF` | Bird physics feel |
| `SPEED_PER_POINT`, `MAX_SPEED_MULT` | How fast pipes accelerate |
| `GAP_PER_POINT`, `MIN_GAP_REF` | How the gap narrows (set `SPEED_PER_POINT = 0` to disable) |
| `SKY_LEVELS` | Stipple patterns for each transparency step |

## Testing

```bash
python3 -m pytest test_flappy.py -v
```

20 unit tests cover constants, physics scaling, difficulty curves, and
geometry helpers. Tests run headless (tkinter is mocked).

## Why tkinter?

| Option | Verdict |
|---|---|
| Electron / Tauri | Overkill, high CPU |
| pygame | No reliable transparent/always-on-top on macOS |
| Swift / SwiftUI | Needs Xcode + build step |
| **tkinter** | Already installed, low CPU, good enough graphics |

## Not Included (on purpose)

- High scores / persistence
- Sound
- Sprites or art assets
- A bundler / `.app` wrapper

Single-file simplicity is the point — launches in under a second, uses a
few MB of RAM.
