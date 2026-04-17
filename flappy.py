#!/usr/bin/env python3
"""
Flappy Code - a tiny, low-CPU Flappy Bird overlay you can play while your
LLM is thinking. Built with stdlib tkinter only, so there's nothing to
install: just `python3 flappy.py`.

Design goals
------------
* Translucent, always-on-top, draggable frameless window.
* Resizable (drag the corner grip, or use +/- keys).
* Sleeps between frames and only redraws what it needs, so CPU stays low.
* One file, no dependencies.

Controls
--------
* Space / Up / W / Click on the game  : flap
* P                                   : pause / resume
* R                                   : restart (works any time)
* + / =   and   - / _                 : grow / shrink the window
* Drag the top bar                    : move the window
* Drag the bottom-right corner        : resize
* X button or Esc                     : quit

Tested on macOS with the system Tk 8.6 (Python 3.10+).
"""

from __future__ import annotations

import platform
import random
import sys
import tkinter as tk
from dataclasses import dataclass


# ----- Tunables ---------------------------------------------------------------
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 420
MIN_WIDTH = 220
MIN_HEIGHT = 300
MAX_WIDTH = 900
MAX_HEIGHT = 1200
TITLE_H = 24
GRIP_SIZE = 14          # size of the bottom-right resize grip
FPS = 50
FRAME_MS = int(1000 / FPS)

# Physics are defined in a "reference" 320x420 window; we scale the bird and
# pipe dimensions with the window so the game stays playable at any size.
REF_W = 320
REF_H = 420 - TITLE_H

GRAVITY_REF = 0.38
FLAP_V_REF = -6.2
MAX_FALL_REF = 9.0
PIPE_SPEED_REF = 2.2
PIPE_W_REF = 46
PIPE_GAP_REF = 130
PIPE_SPACING_REF = 170
BIRD_R_REF = 11
BIRD_X_REF = 80

# Colors - kept cheap (solid fills only, no images, no gradients).
BG = "#112028"
SKY_BOT = "#b8e8f5"
PIPE_FILL = "#6fbf3a"
PIPE_EDGE = "#3b7a1e"
BIRD_FILL = "#ffd23f"
BIRD_EDGE = "#8a5a00"
GROUND = "#d6b36a"
TITLE_BG = "#1d2d36"
TITLE_FG = "#cfe6ef"
TEXT_FG = "#ffffff"
GRIP_FG = "#8aa7b0"

WINDOW_ALPHA = 0.92
IS_MAC = platform.system() == "Darwin"


@dataclass
class Pipe:
    x: float
    gap_y: float
    scored: bool = False


class FlappyGame:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.width = DEFAULT_WIDTH
        self.height = DEFAULT_HEIGHT
        self._configure_window()
        self._build_ui()
        self._bind_keys()
        self._reset()
        # On macOS, overrideredirect windows don't become "key" automatically
        # and so never receive keypresses. Force focus a few times after the
        # window is mapped - once is sometimes not enough.
        self.root.after(50, self._grab_focus)
        self.root.after(200, self._grab_focus)
        self.root.after(500, self._grab_focus)
        self.root.after(FRAME_MS, self._tick)

    # -- window setup ------------------------------------------------------
    def _configure_window(self) -> None:
        self.root.title("Flappy Code")
        # Frameless: on macOS the combination of overrideredirect+True with a
        # quick False/True toggle after mapping is the usual trick to make the
        # resulting window still accept keyboard input.
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", WINDOW_ALPHA)
        except tk.TclError:
            pass
        sw = self.root.winfo_screenwidth()
        x = max(20, sw - self.width - 40)
        y = 60
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.configure(bg=BG)

        # macOS-only: tell Tk to treat this as a plain, borderless window that
        # can still be activated (receives keystrokes). Safe no-op elsewhere.
        if IS_MAC:
            try:
                self.root.tk.call(
                    "::tk::unsupported::MacWindowStyle",
                    "style", self.root._w, "plain", "none",
                )
            except tk.TclError:
                pass
            # Toggle overrideredirect once the window is mapped - fixes the
            # "frameless window never gets keyboard focus" bug on macOS.
            def _toggle():
                try:
                    self.root.overrideredirect(False)
                    self.root.overrideredirect(True)
                    self.root.attributes("-topmost", True)
                    self._grab_focus()
                except tk.TclError:
                    pass
            self.root.after(100, _toggle)

    def _build_ui(self) -> None:
        # Title strip (drag handle + buttons).
        self.title_bar = tk.Frame(self.root, bg=TITLE_BG, height=TITLE_H)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.title_bar,
            text="  Flappy Code   space=flap  P=pause  R=restart",
            bg=TITLE_BG,
            fg=TITLE_FG,
            font=("Menlo", 10),
            anchor="w",
        )
        self.title_lbl.pack(side="left", fill="y")

        # Close button.
        self.close_btn = tk.Label(
            self.title_bar,
            text=" \u00d7 ",
            bg=TITLE_BG,
            fg="#ff7b7b",
            font=("Menlo", 14, "bold"),
            cursor="hand2",
        )
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Button-1>", lambda _e: self.root.destroy())

        # Restart button (visible text button, works even if keys don't).
        self.restart_btn = tk.Label(
            self.title_bar,
            text=" \u21bb ",
            bg=TITLE_BG,
            fg="#9bf0a3",
            font=("Menlo", 13, "bold"),
            cursor="hand2",
        )
        self.restart_btn.pack(side="right")
        self.restart_btn.bind("<Button-1>", lambda _e: self._restart())

        # Pause button.
        self.pause_btn = tk.Label(
            self.title_bar,
            text=" II ",
            bg=TITLE_BG,
            fg="#ffe082",
            font=("Menlo", 11, "bold"),
            cursor="hand2",
        )
        self.pause_btn.pack(side="right")
        self.pause_btn.bind("<Button-1>", lambda _e: self._toggle_pause())

        # Main canvas.
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height - TITLE_H,
            bg=SKY_BOT,
            highlightthickness=0,
            bd=0,
            takefocus=1,
        )
        self.canvas.pack(fill="both", expand=True)

        # Drag the title bar to move the window.
        for w in (self.title_bar, self.title_lbl):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        # Click anywhere on the game area to flap. Also steal focus back so
        # the keyboard keeps working (macOS overrideredirect focus quirk).
        self.canvas.bind("<Button-1>", self._canvas_click)
        # Any click on the root should also grab focus.
        self.root.bind("<Button-1>", lambda _e: self._grab_focus(), add="+")

        # Pre-create the persistent shapes. We reuse these every frame.
        self.ground_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=GROUND, outline="",
        )
        self.bird_id = self.canvas.create_oval(
            0, 0, 0, 0, fill=BIRD_FILL, outline=BIRD_EDGE, width=2,
        )
        self.eye_id = self.canvas.create_oval(
            0, 0, 0, 0, fill="black", outline="",
        )
        self.score_shadow_id = self.canvas.create_text(
            0, 0, text="0", fill="#003040",
            font=("Menlo", 22, "bold"),
        )
        self.score_id = self.canvas.create_text(
            0, 0, text="0", fill=TEXT_FG,
            font=("Menlo", 22, "bold"),
        )
        self.msg_id = self.canvas.create_text(
            0, 0, text="", fill=TEXT_FG,
            font=("Menlo", 14, "bold"),
            justify="center",
        )

        # Resize grip in the bottom-right corner of the canvas.
        self.grip_id = self.canvas.create_polygon(
            0, 0, 0, 0, 0, 0,
            fill=GRIP_FG, outline="",
        )
        self.canvas.tag_bind(self.grip_id, "<ButtonPress-1>", self._resize_start)
        self.canvas.tag_bind(self.grip_id, "<B1-Motion>", self._resize_move)
        # Make the canvas call _on_configure when the window is resized so we
        # can update the backing layout (pipes, ground, grip).
        self.canvas.bind("<Configure>", self._on_configure)

    def _bind_keys(self) -> None:
        # Bind to both root and canvas so whichever has focus still works.
        for target in (self.root, self.canvas):
            target.bind("<space>", lambda _e: self._flap())
            target.bind("<Up>", lambda _e: self._flap())
            target.bind("<KeyPress-w>", lambda _e: self._flap())
            target.bind("<KeyPress-W>", lambda _e: self._flap())
            target.bind("<KeyPress-p>", lambda _e: self._toggle_pause())
            target.bind("<KeyPress-P>", lambda _e: self._toggle_pause())
            target.bind("<KeyPress-r>", lambda _e: self._restart())
            target.bind("<KeyPress-R>", lambda _e: self._restart())
            target.bind("<Escape>", lambda _e: self.root.destroy())
            target.bind("<KeyPress-plus>", lambda _e: self._resize_step(+40))
            target.bind("<KeyPress-equal>", lambda _e: self._resize_step(+40))
            target.bind("<KeyPress-minus>", lambda _e: self._resize_step(-40))
            target.bind("<KeyPress-underscore>", lambda _e: self._resize_step(-40))

    # -- focus helpers -----------------------------------------------------
    def _grab_focus(self) -> None:
        try:
            self.root.lift()
            self.root.focus_force()
            self.canvas.focus_set()
        except tk.TclError:
            pass

    def _canvas_click(self, _event: tk.Event) -> None:
        self._grab_focus()
        self._flap()

    # -- drag-to-move ------------------------------------------------------
    def _drag_start(self, event: tk.Event) -> None:
        self._drag_dx = event.x_root - self.root.winfo_x()
        self._drag_dy = event.y_root - self.root.winfo_y()

    def _drag_move(self, event: tk.Event) -> None:
        x = event.x_root - self._drag_dx
        y = event.y_root - self._drag_dy
        self.root.geometry(f"+{x}+{y}")

    # -- resize ------------------------------------------------------------
    def _resize_start(self, event: tk.Event) -> None:
        self._resize_x0 = event.x_root
        self._resize_y0 = event.y_root
        self._resize_w0 = self.width
        self._resize_h0 = self.height

    def _resize_move(self, event: tk.Event) -> None:
        dx = event.x_root - self._resize_x0
        dy = event.y_root - self._resize_y0
        new_w = max(MIN_WIDTH, min(MAX_WIDTH, self._resize_w0 + dx))
        new_h = max(MIN_HEIGHT, min(MAX_HEIGHT, self._resize_h0 + dy))
        self._apply_size(new_w, new_h)

    def _resize_step(self, delta: int) -> None:
        # Keep the aspect ratio roughly at DEFAULT_W : DEFAULT_H.
        ratio = DEFAULT_HEIGHT / DEFAULT_WIDTH
        new_w = max(MIN_WIDTH, min(MAX_WIDTH, self.width + delta))
        new_h = max(MIN_HEIGHT, min(MAX_HEIGHT, int(new_w * ratio)))
        self._apply_size(new_w, new_h)

    def _apply_size(self, new_w: int, new_h: int) -> None:
        self.width = new_w
        self.height = new_h
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry(f"{new_w}x{new_h}+{x}+{y}")
        # Configure event will fire and call _on_configure, but do it now so
        # the player doesn't see a flicker.
        self._relayout()

    def _on_configure(self, event: tk.Event) -> None:
        # Canvas's own width/height reflect its current size.
        self._relayout()

    def _relayout(self) -> None:
        # Called whenever the window size changes. Redraw the ground + grip
        # and reposition the score text.
        play_h = self._play_h()
        ground_h = self._ground_h()
        self.canvas.coords(
            self.ground_id,
            0, play_h, self.width, play_h + ground_h,
        )
        # Score near the top-center.
        self.canvas.coords(self.score_id, self.width // 2, 26)
        self.canvas.coords(self.score_shadow_id, self.width // 2 + 2, 28)
        # Message centered.
        self.canvas.coords(self.msg_id, self.width // 2, play_h // 2)
        # Grip in bottom-right.
        ch = play_h + ground_h
        self.canvas.coords(
            self.grip_id,
            self.width, ch,
            self.width - GRIP_SIZE, ch,
            self.width, ch - GRIP_SIZE,
        )

    # -- geometry helpers --------------------------------------------------
    def _play_h(self) -> int:
        # Visible playable height (above the ground).
        return self.height - TITLE_H - self._ground_h()

    def _ground_h(self) -> int:
        return max(20, int(30 * self.height / DEFAULT_HEIGHT))

    def _scale_x(self) -> float:
        return self.width / REF_W

    def _scale_y(self) -> float:
        return self._play_h() / REF_H

    def _pipe_w(self) -> float:
        return PIPE_W_REF * self._scale_x()

    def _pipe_gap(self) -> float:
        return PIPE_GAP_REF * self._scale_y()

    def _pipe_spacing(self) -> float:
        return PIPE_SPACING_REF * self._scale_x()

    def _pipe_speed(self) -> float:
        return PIPE_SPEED_REF * self._scale_x()

    def _bird_r(self) -> float:
        return BIRD_R_REF * min(self._scale_x(), self._scale_y())

    def _bird_x(self) -> float:
        return BIRD_X_REF * self._scale_x()

    def _gravity(self) -> float:
        return GRAVITY_REF * self._scale_y()

    def _flap_v(self) -> float:
        return FLAP_V_REF * self._scale_y()

    def _max_fall(self) -> float:
        return MAX_FALL_REF * self._scale_y()

    # -- game state --------------------------------------------------------
    def _reset(self) -> None:
        play_h = self._play_h()
        self.bird_y = play_h / 2
        self.bird_v = 0.0
        self.pipes: list[Pipe] = []
        self.pipe_ids: dict[int, tuple[int, int]] = {}
        self.score = 0
        self.state = "ready"
        self._spawn_pipe(self.width + 40)
        self._spawn_pipe(self.width + 40 + self._pipe_spacing())
        self._relayout()
        self._render_msg("Press SPACE\nor click to start")
        self._update_score_text()

    def _spawn_pipe(self, x: float) -> None:
        play_h = self._play_h()
        margin = max(40, play_h * 0.12)
        gap = self._pipe_gap()
        gap_y = random.uniform(margin + gap / 2, play_h - margin - gap / 2)
        pipe = Pipe(x=x, gap_y=gap_y)
        top_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=PIPE_FILL, outline=PIPE_EDGE, width=2,
        )
        bot_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=PIPE_FILL, outline=PIPE_EDGE, width=2,
        )
        self.pipes.append(pipe)
        self.pipe_ids[id(pipe)] = (top_id, bot_id)
        # Stacking: pipes below bird/score/grip.
        self.canvas.tag_raise(self.ground_id)
        self.canvas.tag_raise(self.bird_id)
        self.canvas.tag_raise(self.eye_id)
        self.canvas.tag_raise(self.score_shadow_id)
        self.canvas.tag_raise(self.score_id)
        self.canvas.tag_raise(self.msg_id)
        self.canvas.tag_raise(self.grip_id)

    def _remove_pipe(self, pipe: Pipe) -> None:
        top_id, bot_id = self.pipe_ids.pop(id(pipe))
        self.canvas.delete(top_id)
        self.canvas.delete(bot_id)
        self.pipes.remove(pipe)

    # -- input -------------------------------------------------------------
    def _flap(self) -> None:
        if self.state == "ready":
            self.state = "playing"
            self._render_msg("")
        if self.state == "playing":
            self.bird_v = self._flap_v()

    def _toggle_pause(self) -> None:
        if self.state == "playing":
            self.state = "paused"
            self._render_msg("Paused\n(P to resume)")
        elif self.state == "paused":
            self.state = "playing"
            self._render_msg("")

    def _restart(self) -> None:
        # Always valid - not just when dead.
        for pipe in list(self.pipes):
            self._remove_pipe(pipe)
        self._reset()

    # -- simulation --------------------------------------------------------
    def _tick(self) -> None:
        if self.state == "playing":
            self._step()
        self._render()
        self.root.after(FRAME_MS, self._tick)

    def _step(self) -> None:
        play_h = self._play_h()
        bird_r = self._bird_r()
        bird_x = self._bird_x()

        self.bird_v = min(self.bird_v + self._gravity(), self._max_fall())
        self.bird_y += self.bird_v

        if self.bird_y - bird_r <= 0:
            self.bird_y = bird_r
            self.bird_v = 0
        if self.bird_y + bird_r >= play_h:
            self._die()
            return

        speed = self._pipe_speed()
        pipe_w = self._pipe_w()
        for pipe in self.pipes:
            pipe.x -= speed
            if not pipe.scored and pipe.x + pipe_w < bird_x - bird_r:
                pipe.scored = True
                self.score += 1
                self._update_score_text()

        if self.pipes and self.pipes[0].x + pipe_w < -4:
            self._remove_pipe(self.pipes[0])
        spacing = self._pipe_spacing()
        last_x = max((p.x for p in self.pipes), default=self.width)
        if last_x < self.width - spacing + 40:
            self._spawn_pipe(last_x + spacing)

        gap = self._pipe_gap()
        for pipe in self.pipes:
            if pipe.x + pipe_w < bird_x - bird_r:
                continue
            if pipe.x > bird_x + bird_r:
                break
            gap_top = pipe.gap_y - gap / 2
            gap_bot = pipe.gap_y + gap / 2
            if self.bird_y - bird_r < gap_top or self.bird_y + bird_r > gap_bot:
                self._die()
                return

    def _die(self) -> None:
        self.state = "dead"
        self._render_msg(
            f"Game Over\nScore: {self.score}\n(R or \u21bb to restart)"
        )

    # -- rendering ---------------------------------------------------------
    def _render(self) -> None:
        bird_x = self._bird_x()
        bird_r = self._bird_r()
        self.canvas.coords(
            self.bird_id,
            bird_x - bird_r, self.bird_y - bird_r,
            bird_x + bird_r, self.bird_y + bird_r,
        )
        ex = bird_x + bird_r * 0.3
        ey = self.bird_y - bird_r * 0.3
        es = max(2, bird_r * 0.25)
        self.canvas.coords(self.eye_id, ex - es, ey - es, ex + es, ey + es)

        play_h = self._play_h()
        gap = self._pipe_gap()
        pipe_w = self._pipe_w()
        for pipe in self.pipes:
            top_id, bot_id = self.pipe_ids[id(pipe)]
            gap_top = pipe.gap_y - gap / 2
            gap_bot = pipe.gap_y + gap / 2
            self.canvas.coords(top_id, pipe.x, 0, pipe.x + pipe_w, gap_top)
            self.canvas.coords(bot_id, pipe.x, gap_bot, pipe.x + pipe_w, play_h)

    def _update_score_text(self) -> None:
        txt = str(self.score)
        self.canvas.itemconfigure(self.score_id, text=txt)
        self.canvas.itemconfigure(self.score_shadow_id, text=txt)

    def _render_msg(self, text: str) -> None:
        self.canvas.itemconfigure(self.msg_id, text=text)


def main() -> int:
    root = tk.Tk()
    FlappyGame(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
