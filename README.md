# Flappy Code

A tiny Flappy Bird overlay for macOS. It sits on top of Cursor / VS Code /
whatever else you have open, so when your LLM is spinning you can flap
through a few pipes instead of staring at a spinner.

The whole thing is one file, no dependencies beyond what ships with
Python 3 on macOS.

## Why tkinter?

A quick round of research before building:

- **Electron / Tauri** — overkill; Electron in particular eats CPU, which
  defeats the point.
- **pygame** — transparent/always-on-top windows don't work reliably on
  macOS (SDL has no native support and the common `pywin32` workaround is
  Windows-only).
- **Swift / SwiftUI** — lowest CPU, but needs Xcode + a full build step.
- **tkinter** — already on your Mac (`/usr/bin/python3`), supports
  `-alpha` translucency and `-topmost` via Tk 8.6, uses native widgets so
  it barely touches the CPU when idle. Canvas is more than fast enough
  for a handful of rectangles and an oval.

tkinter wins on the "nothing to install, low CPU, good enough graphics"
axis, so that's what this is built with.

## Run

```
python3 flappy.py
```

or, from this folder:

```
./run.sh
```

## Controls

- **Space / Up / W / click** — flap
- **P** — pause / resume (or the `II` button)
- **R** — restart any time (or the `↻` button)
- **+** / **−** — grow / shrink the window
- **Drag the dark title strip** — move the window
- **Drag the bottom-right corner grip** — resize
- **×** button or **Esc** — quit

The window is frameless, semi-transparent (`alpha = 0.92`), and stays on
top of everything else. It starts in the top-right of your main display;
drag it wherever.

### macOS focus note

Frameless (`overrideredirect`) Tk windows don't become "key" by default on
macOS, so keypresses are ignored. Flappy Code works around this with
`::tk::unsupported::MacWindowStyle plain none`, a brief
`overrideredirect(False)/(True)` toggle after the window is mapped, and a
`focus_force()` every time you click the game. If keys still feel iffy
after launch, click inside the game once to grab focus.

## Tweaking

All the knobs are at the top of `flappy.py`:

- `WIDTH`, `HEIGHT` — window size
- `FPS` — lower this if you want even less CPU
- `WINDOW_ALPHA` — how see-through the whole window is (0 – 1)
- `GRAVITY`, `FLAP_V`, `PIPE_SPEED`, `PIPE_GAP` — difficulty

## Not included (on purpose)

- High scores / persistence
- Sound
- Sprites or art assets
- A bundler / `.app` wrapper

Keeping it a single-file script is the whole point — it launches in
under a second and uses a few MB of RAM.
