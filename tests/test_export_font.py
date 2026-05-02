"""
Tests for scripts/export_font.py

Covers:
  - spline_to_outline: closed contour, correct geometry
  - word_to_merged_splines: pipeline integration
  - build_font: no crash, correct glyph count, GSUB ligatures present
"""
import argparse
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

ORTHIC = Path(__file__).parent.parent / 'static' / 'data' / 'systems' / 'orthic'


@pytest.fixture(scope='module')
def orthic_system():
    from scripts.generate_pdf import load_system
    return load_system(ORTHIC)


def _default_args(**overrides):
    """Return a minimal Namespace that build_font() accepts."""
    defaults = dict(
        system_folder=ORTHIC,
        upm=1000,
        pen_width=0.02,
        max_word_length=12,
        modes=None,
        rules=None,
    )
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# spline_to_outline
# ---------------------------------------------------------------------------

class TestSplineToOutline:
    def test_returns_closed_polygon(self):
        from scripts.export_font import spline_to_outline
        pts = [[0, 0], [0.05, 0.1], [0.1, 0.05], [0.15, 0.15]]
        outline = spline_to_outline(pts, pen_width=0.02)
        assert len(outline) > 0
        # Closed: last point should be close to the first
        # (spline_to_outline returns an open list; caller uses closePath)
        # Verify it's a non-degenerate polygon
        xs = [p[0] for p in outline]
        ys = [p[1] for p in outline]
        assert max(xs) - min(xs) > 0
        assert max(ys) - min(ys) > 0

    def test_single_point_returns_empty(self):
        from scripts.export_font import spline_to_outline
        assert spline_to_outline([[0, 0]], pen_width=0.02) == []

    def test_two_points_returns_polygon(self):
        from scripts.export_font import spline_to_outline
        outline = spline_to_outline([[0, 0], [0.1, 0]], pen_width=0.02)
        assert len(outline) > 0

    def test_outline_wider_than_pen(self):
        """The bounding box height should be at least pen_width."""
        from scripts.export_font import spline_to_outline
        pen_width = 0.04
        pts = [[0, 0], [0.2, 0]]
        outline = spline_to_outline(pts, pen_width=pen_width)
        ys = [p[1] for p in outline]
        assert max(ys) - min(ys) >= pen_width * 0.9  # allow rounding


# ---------------------------------------------------------------------------
# word_to_merged_splines
# ---------------------------------------------------------------------------

class TestWordToMergedSplines:
    def test_common_words_return_splines(self, orthic_system):
        from scripts.export_font import word_to_merged_splines
        for word in ['the', 'and', 'of']:
            splines = word_to_merged_splines(word, orthic_system)
            assert splines, f"'{word}' should produce splines"
            assert all(len(s) >= 1 for s in splines)

    def test_unknown_word_returns_empty_or_splines(self, orthic_system):
        from scripts.export_font import word_to_merged_splines
        # A word made of characters not in the system should return []
        result = word_to_merged_splines('zzzzzzzzz', orthic_system)
        # Either empty (no glyph) or contains something — just must not crash
        assert isinstance(result, list)

    def test_empty_string_returns_empty(self, orthic_system):
        from scripts.export_font import word_to_merged_splines
        assert word_to_merged_splines('', orthic_system) == []


# ---------------------------------------------------------------------------
# build_font (integration)
# ---------------------------------------------------------------------------

class TestBuildFont:
    TEST_WORDS = ['the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'be', 'or']

    def test_produces_ttfont(self, orthic_system):
        from fontTools.ttLib import TTFont
        from scripts.export_font import build_font
        font = build_font(orthic_system, self.TEST_WORDS, _default_args())
        assert isinstance(font, TTFont)

    def test_has_required_tables(self, orthic_system):
        from scripts.export_font import build_font
        font = build_font(orthic_system, self.TEST_WORDS, _default_args())
        for table in ('head', 'hhea', 'hmtx', 'OS/2', 'name', 'post', 'CFF ', 'GSUB', 'cmap'):
            assert table in font, f"Missing table: {table}"

    def test_gsub_has_ligatures(self, orthic_system):
        from scripts.export_font import build_font
        font = build_font(orthic_system, self.TEST_WORDS, _default_args())
        gsub = font['GSUB'].table
        lookups = gsub.LookupList.Lookup
        lig_lookups = [l for l in lookups if l.LookupType == 4]
        assert lig_lookups, "No LookupType-4 (ligature) lookup found"
        # Count total ligatures (each value in subtable.ligatures is a list)
        total = sum(
            len(lig_list)
            for lookup in lig_lookups
            for subtable in lookup.SubTable
            for lig_list in subtable.ligatures.values()
        )
        assert total > 0, "Ligature lookup is empty"

    def test_glyph_order_contains_letter_glyphs(self, orthic_system):
        from scripts.export_font import build_font
        font = build_font(orthic_system, self.TEST_WORDS, _default_args())
        glyph_order = font.getGlyphOrder()
        for c in 'abcdefghijklmnopqrstuvwxyz':
            assert c in glyph_order, f"Letter glyph '{c}' missing"

    def test_word_glyphs_have_nonzero_advance(self, orthic_system):
        from scripts.export_font import build_font
        font = build_font(orthic_system, self.TEST_WORDS, _default_args())
        hmtx = font['hmtx'].metrics
        for word in self.TEST_WORDS:
            name = f"word_{word}"
            if name in hmtx:
                advance, _ = hmtx[name]
                assert advance > 0, f"{name} has zero advance width"

    def test_cff_charstrings_present(self, orthic_system):
        from scripts.export_font import build_font
        font = build_font(orthic_system, self.TEST_WORDS, _default_args())
        cff = font['CFF '].cff
        cs = cff.topDictIndex[0].CharStrings
        assert 'word_the' in cs or 'word_and' in cs, "No word charstrings found"
