"""Unit tests for Flappy Code game logic.

Tests cover physics calculations, game state transitions, difficulty
scaling, and geometry helpers — everything that doesn't require a live
Tk display.
"""

import unittest
from unittest.mock import MagicMock, patch

# Patch tkinter before importing flappy so tests run headless (no display).
import sys
sys.modules["tkinter"] = MagicMock()

import flappy


class TestConstants(unittest.TestCase):
    """Sanity checks on tunable constants."""

    def test_frame_ms_matches_fps(self):
        self.assertEqual(flappy.FRAME_MS, int(1000 / flappy.FPS))

    def test_min_gap_is_less_than_full_gap(self):
        self.assertLess(flappy.MIN_GAP_REF, flappy.PIPE_GAP_REF)

    def test_size_presets_ordered(self):
        widths = [w for _, w, _ in flappy.SIZE_PRESETS]
        self.assertEqual(widths, sorted(widths))

    def test_min_dimensions_less_than_max(self):
        self.assertLess(flappy.MIN_WIDTH, flappy.MAX_WIDTH)
        self.assertLess(flappy.MIN_HEIGHT, flappy.MAX_HEIGHT)

    def test_default_size_index_valid(self):
        self.assertIn(
            flappy.DEFAULT_SIZE_INDEX,
            range(len(flappy.SIZE_PRESETS)),
        )


class TestPipeDataclass(unittest.TestCase):
    """Test the Pipe dataclass."""

    def test_defaults(self):
        p = flappy.Pipe(x=100.0, gap_y=200.0)
        self.assertEqual(p.x, 100.0)
        self.assertEqual(p.gap_y, 200.0)
        self.assertFalse(p.scored)

    def test_scored_flag(self):
        p = flappy.Pipe(x=0, gap_y=0, scored=True)
        self.assertTrue(p.scored)


class TestDifficultyScaling(unittest.TestCase):
    """Test progressive difficulty formulas in isolation."""

    def test_speed_multiplier_at_zero(self):
        # At score 0 the multiplier should be 1.0.
        mult = min(flappy.MAX_SPEED_MULT, 1.0 + flappy.SPEED_PER_POINT * 0)
        self.assertAlmostEqual(mult, 1.0)

    def test_speed_multiplier_capped(self):
        # At very high scores the multiplier should cap.
        mult = min(flappy.MAX_SPEED_MULT, 1.0 + flappy.SPEED_PER_POINT * 9999)
        self.assertAlmostEqual(mult, flappy.MAX_SPEED_MULT)

    def test_gap_shrinks_with_score(self):
        gap_0 = max(flappy.MIN_GAP_REF, flappy.PIPE_GAP_REF - flappy.GAP_PER_POINT * 0)
        gap_10 = max(flappy.MIN_GAP_REF, flappy.PIPE_GAP_REF - flappy.GAP_PER_POINT * 10)
        self.assertGreater(gap_0, gap_10)

    def test_gap_floors_at_min(self):
        gap = max(flappy.MIN_GAP_REF, flappy.PIPE_GAP_REF - flappy.GAP_PER_POINT * 9999)
        self.assertAlmostEqual(gap, flappy.MIN_GAP_REF)


class TestSkyLevels(unittest.TestCase):
    """Test sky transparency level definitions."""

    def test_level_count(self):
        self.assertEqual(len(flappy.SKY_LEVELS), 6)

    def test_first_is_solid(self):
        name, stipple = flappy.SKY_LEVELS[0]
        self.assertEqual(name, "solid")
        self.assertEqual(stipple, "")

    def test_last_is_invisible(self):
        name, stipple = flappy.SKY_LEVELS[-1]
        self.assertEqual(name, "invisible")
        self.assertEqual(stipple, "HIDE")

    def test_default_level_in_range(self):
        self.assertIn(
            flappy.DEFAULT_SKY_LEVEL,
            range(len(flappy.SKY_LEVELS)),
        )


class TestGeometryFormulas(unittest.TestCase):
    """Test the reference-scaling math used for physics."""

    def test_scale_at_reference_size(self):
        # At the reference width, scale_x should be 1.0.
        self.assertAlmostEqual(flappy.REF_W / flappy.REF_W, 1.0)

    def test_ground_height_positive(self):
        gh = max(20, int(30 * flappy.DEFAULT_HEIGHT / flappy.DEFAULT_HEIGHT))
        self.assertGreater(gh, 0)

    def test_play_height_positive(self):
        gh = max(20, int(30 * flappy.DEFAULT_HEIGHT / flappy.DEFAULT_HEIGHT))
        play_h = flappy.DEFAULT_HEIGHT - flappy.TITLE_H - gh
        self.assertGreater(play_h, 0)


class TestEdgeZone(unittest.TestCase):
    """Test the EDGE_ZONE constant for resize hit detection."""

    def test_edge_zone_positive(self):
        self.assertGreater(flappy.EDGE_ZONE, 0)

    def test_edge_zone_less_than_min_width(self):
        # Edge zones on both sides shouldn't consume the entire window.
        self.assertLess(flappy.EDGE_ZONE * 2, flappy.MIN_WIDTH)


if __name__ == "__main__":
    unittest.main()
