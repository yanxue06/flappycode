#!/usr/bin/env python3
"""
Flappy Code - a tiny, low-CPU Flappy Bird overlay you can play while your
LLM is thinking. Built with stdlib tkinter only, so there's nothing to
install: just `python3 flappy.py`.

Design goals
------------
* Transparent, always-on-top, draggable frameless window.
* Small (320x420 by default) so it sits in a corner of your screen.
* Sleeps between frames and only redraws what it needs, so CPU stays low.
* One file, no dependencies.

Controls
--------
* Space / Up / Click on the game      : flap
* P                                   : pause / resume
* R                                   : restart after game over
* Drag the top bar                    : move the window
* X button or Esc                     : quit

Tested on macOS with the system Tk 8.6 (Python 3.10+).
"""

from __future__ import annotations

import random
import sys
import tkinter as tk
from dataclasses import dataclass


# ----- Tunables ---------------------------------------------------------------
# Smaller numbers here = less CPU. The game is simple enough that 50 FPS is
# fine even on a laptop running Cursor + a bunch of other apps.
WIDTH = 320
HEIGHT = 420
TITLE_H = 24           # height of the draggable title strip
FPS = 50
FRAME_MS = int(1000 / FPS)

GRAVITY = 0.38
FLAP_V = -6.2
MAX_FALL = 9.0

PIPE_W = 46
PIPE_GAP = 130          # vertical gap between upper and lower pipe
PIPE_SPACING = 170      # horizontal distance between pipe pairs
PIPE_SPEED = 2.2

BIRD_R = 11
BIRD_X = 80

# Colors - kept cheap (solid fills only, no images, no gradients).
BG = "#112028"         # dark teal so the translucent window still looks nice
SKY_TOP = "#78c6e8"
SKY_BOT = "#b8e8f5"
PIPE_FILL = "#6fbf3a"
PIPE_EDGE = "#3b7a1e"
BIRD_FILL = "#ffd23f"
BIRD_EDGE = "#8a5a00"
GROUND = "#d6b36a"
TITLE_BG = "#1d2d36"
TITLE_FG = "#cfe6ef"
TEXT_FG = "#ffffff"

# Overall window translucency. 1.0 = opaque, 0.0 = invisible.
# Tk's -alpha applies to the whole window (content included) which is the
# only transparency mode that's reliable on macOS.
WINDOW_ALPHA = 0.92


@dataclass
class Pipe:
    x: float
    gap_y: float         # center Y of the gap
    scored: bool = False


class FlappyGame:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self._configure_window()
        self._build_ui()
        self._bind_keys()
        self._reset()
        # Kick off the main loop.
        self.root.after(FRAME_MS, self._tick)

    # -- window setup ------------------------------------------------------
    def _configure_window(self) -> None:
        self.root.title("Flappy Code")
        # Frameless so we can draw our own mini title bar.
        self.root.overrideredirect(True)
        # Always on top of other apps (works on macOS/Win/Linux w/ compositor).
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-alpha", WINDOW_ALPHA)
        except tk.TclError:
            pass  # very old Tk; just stay opaque
        # Start in the top-right-ish corner.
        sw = self.root.winfo_screenwidth()
        x = max(20, sw - WIDTH - 40)
        y = 60
        self.root.geometry(f"{WIDTH}x{HEIGHT}+{x}+{y}")
        self.root.minsize(WIDTH, HEIGHT)
        self.root.configure(bg=BG)

    def _build_ui(self) -> None:
        # Title strip (drag handle + close button).
        self.title_bar = tk.Frame(self.root, bg=TITLE_BG, height=TITLE_H)
        self.title_bar.pack(fill="x", side="top")
        self.title_bar.pack_propagate(False)

        self.title_lbl = tk.Label(
            self.title_bar,
            text="  Flappy Code   (Space to flap  ·  P pause  ·  drag me)",
            bg=TITLE_BG,
            fg=TITLE_FG,
            font=("Menlo", 10),
            anchor="w",
        )
        self.title_lbl.pack(side="left", fill="y")

        self.close_btn = tk.Label(
            self.title_bar,
            text=" × ",
            bg=TITLE_BG,
            fg="#ff7b7b",
            font=("Menlo", 14, "bold"),
            cursor="hand2",
        )
        self.close_btn.pack(side="right")
        self.close_btn.bind("<Button-1>", lambda _e: self.root.destroy())

        # Main canvas where the game is drawn. `highlightthickness=0` removes
        # the default focus border so there are no extra pixels to repaint.
        self.canvas = tk.Canvas(
            self.root,
            width=WIDTH,
            height=HEIGHT - TITLE_H,
            bg=SKY_BOT,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Make the title bar draggable.
        for w in (self.title_bar, self.title_lbl):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        # Flap on click anywhere in the game area.
        self.canvas.bind("<Button-1>", lambda _e: self._flap())

        # Pre-create the persistent shapes we can just move / reconfigure
        # each frame instead of clearing and redrawing the whole canvas.
        h = HEIGHT - TITLE_H
        self.sky_id = self.canvas.create_rectangle(
            0, 0, WIDTH, h - 30, fill=SKY_BOT, outline=""
        )
        self.ground_id = self.canvas.create_rectangle(
            0, h - 30, WIDTH, h, fill=GROUND, outline=""
        )
        self.bird_id = self.canvas.create_oval(
            BIRD_X - BIRD_R, 0, BIRD_X + BIRD_R, 2 * BIRD_R,
            fill=BIRD_FILL, outline=BIRD_EDGE, width=2,
        )
        # Little eye so the bird doesn't look like a lemon.
        self.eye_id = self.canvas.create_oval(
            0, 0, 0, 0, fill="black", outline=""
        )

        self.score_id = self.canvas.create_text(
            WIDTH // 2, 26,
            text="0",
            fill=TEXT_FG,
            font=("Menlo", 22, "bold"),
        )
        # Shadow behind the score for legibility against the sky.
        self.score_shadow_id = self.canvas.create_text(
            WIDTH // 2 + 2, 28,
            text="0",
            fill="#003040",
            font=("Menlo", 22, "bold"),
        )
        self.canvas.tag_lower(self.score_shadow_id, self.score_id)

        self.msg_id = self.canvas.create_text(
            WIDTH // 2, (h // 2),
            text="", fill=TEXT_FG, font=("Menlo", 14, "bold"),
            justify="center",
        )

    def _bind_keys(self) -> None:
        self.root.bind("<space>", lambda _e: self._flap())
        self.root.bind("<Up>", lambda _e: self._flap())
        self.root.bind("<KeyPress-w>", lambda _e: self._flap())
        self.root.bind("<KeyPress-p>", lambda _e: self._toggle_pause())
        self.root.bind("<KeyPress-r>", lambda _e: self._maybe_restart())
        self.root.bind("<Escape>", lambda _e: self.root.destroy())

    # -- drag-to-move ------------------------------------------------------
    def _drag_start(self, event: tk.Event) -> None:
        self._drag_dx = event.x_root - self.root.winfo_x()
        self._drag_dy = event.y_root - self.root.winfo_y()

    def _drag_move(self, event: tk.Event) -> None:
        x = event.x_root - self._drag_dx
        y = event.y_root - self._drag_dy
        self.root.geometry(f"+{x}+{y}")

    # -- game state --------------------------------------------------------
    def _reset(self) -> None:
        self.bird_y = (HEIGHT - TITLE_H) / 2
        self.bird_v = 0.0
        self.pipes: list[Pipe] = []
        self.score = 0
        self.state = "ready"   # ready | playing | paused | dead
        self.pipe_ids: dict[int, tuple[int, int]] = {}  # pipe id -> (top_id, bot_id)
        # Seed a pipe far enough away that the player has time to react.
        self._spawn_pipe(WIDTH + 40)
        self._spawn_pipe(WIDTH + 40 + PIPE_SPACING)
        self._render_msg("Press SPACE to start")
        self._update_score_text()

    def _spawn_pipe(self, x: float) -> None:
        play_h = HEIGHT - TITLE_H - 30  # minus ground
        margin = 50
        gap_y = random.uniform(margin + PIPE_GAP / 2,
                               play_h - margin - PIPE_GAP / 2)
        pipe = Pipe(x=x, gap_y=gap_y)
        # Top pipe rectangle, bottom pipe rectangle.
        top_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=PIPE_FILL, outline=PIPE_EDGE, width=2,
        )
        bot_id = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=PIPE_FILL, outline=PIPE_EDGE, width=2,
        )
        # Keep ground + score on top.
        self.canvas.tag_raise(self.ground_id)
        self.canvas.tag_raise(self.bird_id)
        self.canvas.tag_raise(self.eye_id)
        self.canvas.tag_raise(self.score_shadow_id)
        self.canvas.tag_raise(self.score_id)
        self.canvas.tag_raise(self.msg_id)
        self.pipes.append(pipe)
        self.pipe_ids[id(pipe)] = (top_id, bot_id)

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
            self.bird_v = FLAP_V

    def _toggle_pause(self) -> None:
        if self.state == "playing":
            self.state = "paused"
            self._render_msg("Paused\n(press P to resume)")
        elif self.state == "paused":
            self.state = "playing"
            self._render_msg("")

    def _maybe_restart(self) -> None:
        if self.state == "dead":
            # Nuke existing pipe canvas items.
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
        play_h = HEIGHT - TITLE_H - 30
        # Bird physics.
        self.bird_v = min(self.bird_v + GRAVITY, MAX_FALL)
        self.bird_y += self.bird_v

        # Ground / ceiling collisions.
        if self.bird_y - BIRD_R <= 0:
            self.bird_y = BIRD_R
            self.bird_v = 0
        if self.bird_y + BIRD_R >= play_h:
            self._die()
            return

        # Move + score pipes.
        for pipe in self.pipes:
            pipe.x -= PIPE_SPEED
            if not pipe.scored and pipe.x + PIPE_W < BIRD_X - BIRD_R:
                pipe.scored = True
                self.score += 1
                self._update_score_text()

        # Remove off-screen pipes, spawn new ones.
        if self.pipes and self.pipes[0].x + PIPE_W < -4:
            self._remove_pipe(self.pipes[0])
        last_x = max((p.x for p in self.pipes), default=WIDTH)
        if last_x < WIDTH - PIPE_SPACING + 40:
            self._spawn_pipe(last_x + PIPE_SPACING)

        # Pipe collision.
        for pipe in self.pipes:
            if pipe.x + PIPE_W < BIRD_X - BIRD_R:
                continue
            if pipe.x > BIRD_X + BIRD_R:
                break
            gap_top = pipe.gap_y - PIPE_GAP / 2
            gap_bot = pipe.gap_y + PIPE_GAP / 2
            if self.bird_y - BIRD_R < gap_top or self.bird_y + BIRD_R > gap_bot:
                self._die()
                return

    def _die(self) -> None:
        self.state = "dead"
        self._render_msg(f"Game Over\nScore: {self.score}\n(press R to restart)")

    # -- rendering ---------------------------------------------------------
    def _render(self) -> None:
        # Bird.
        self.canvas.coords(
            self.bird_id,
            BIRD_X - BIRD_R, self.bird_y - BIRD_R,
            BIRD_X + BIRD_R, self.bird_y + BIRD_R,
        )
        # Eye position tracks the bird's vertical movement a little.
        ex = BIRD_X + 3
        ey = self.bird_y - 3
        self.canvas.coords(self.eye_id, ex - 2, ey - 2, ex + 2, ey + 2)

        # Pipes.
        play_h = HEIGHT - TITLE_H - 30
        for pipe in self.pipes:
            top_id, bot_id = self.pipe_ids[id(pipe)]
            gap_top = pipe.gap_y - PIPE_GAP / 2
            gap_bot = pipe.gap_y + PIPE_GAP / 2
            self.canvas.coords(top_id, pipe.x, 0, pipe.x + PIPE_W, gap_top)
            self.canvas.coords(bot_id, pipe.x, gap_bot, pipe.x + PIPE_W, play_h)

    def _update_score_text(self) -> None:
        self.canvas.itemconfigure(self.score_id, text=str(self.score))
        self.canvas.itemconfigure(self.score_shadow_id, text=str(self.score))

    def _render_msg(self, text: str) -> None:
        self.canvas.itemconfigure(self.msg_id, text=text)


def main() -> int:
    # Lower the Tk update rate slightly by avoiding automatic idle tasks
    # piling up. Tk handles this fine out of the box on macOS.
    root = tk.Tk()
    FlappyGame(root)
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
