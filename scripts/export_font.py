#!/usr/bin/env python3
"""
TrueType font exporter for shorthand systems.

Converts a shorthand system into a .ttf font by:
  1. Processing the top N most common English words through the shorthand pipeline
  2. Rendering each word's merged spline path as a single filled glyph (via stroke expansion)
  3. Adding a GSUB liga lookup that substitutes word letter-sequences with their shorthand glyph

Usage:
    python export_font.py static/data/systems/orthic output.ttf
    python export_font.py static/data/systems/orthic output.ttf --max-words 500
    python export_font.py static/data/systems/orthic output.ttf --pen-width 0.015
"""

import argparse
import calendar
import json
import sys
import time
from io import StringIO
from pathlib import Path

import numpy as np
from scipy.interpolate import CubicSpline

from scripts.generate_pdf import load_system, process_text, tokenize_with_phrases, merge_word_splines

_DEFAULT_WORD_LIST = Path(__file__).parent / 'data' / 'en_wordlist.txt'


# ---------------------------------------------------------------------------
# Word list
# ---------------------------------------------------------------------------

def load_word_list(path: Path | None, max_words: int) -> list[str]:
    src = path if path else _DEFAULT_WORD_LIST
    words = []
    with open(src, encoding='utf-8') as f:
        for line in f:
            word = line.strip().lower()
            if word and word.isalpha():
                words.append(word)
                if len(words) >= max_words:
                    break
    return words


# ---------------------------------------------------------------------------
# Shorthand pipeline
# ---------------------------------------------------------------------------

def word_to_merged_splines(
    word: str,
    system: dict,
    active_modes: list[str] | None = None,
    active_rules: list[str] | None = None,
) -> list:
    """
    Run a single word through the shorthand pipeline.
    Returns the merged splines for that word (list of splines, each a list of [x,y]),
    or [] if the word cannot be rendered.
    """
    processed, multi_word_matches = process_text(word, system, active_rules)
    tokens, _ = tokenize_with_phrases(processed, system, active_modes, multi_word_matches)
    merged = merge_word_splines(tokens)
    if not merged or not merged[0]:
        return []
    return merged[0]


# ---------------------------------------------------------------------------
# Stroke expansion: open spline path → closed polygon outline
# ---------------------------------------------------------------------------

def spline_to_outline(control_points: list, pen_width: float, n_samples: int = 80) -> list[tuple]:
    """
    Expand a single open spline (given as natural-cubic-spline control points)
    into a closed polygon by offsetting ±pen_width/2 along the stroke normal.

    Returns a list of (x, y) float tuples forming a closed polygon,
    or [] if the spline has fewer than 2 points (not renderable).
    """
    if len(control_points) < 2:
        return []

    pts = np.array(control_points, dtype=float)
    t = np.linspace(0.0, 1.0, len(pts))
    t_dense = np.linspace(0.0, 1.0, n_samples)

    cs_x = CubicSpline(t, pts[:, 0], bc_type='natural')
    cs_y = CubicSpline(t, pts[:, 1], bc_type='natural')

    px = cs_x(t_dense)
    py = cs_y(t_dense)

    # First derivatives for tangent computation
    dx = cs_x(t_dense, 1)
    dy = cs_y(t_dense, 1)

    # Normalise tangents (guard against zero-length segments)
    mag = np.hypot(dx, dy)
    mag = np.where(mag < 1e-12, 1.0, mag)
    dx /= mag
    dy /= mag

    # Left-hand normal: rotate tangent 90° CCW
    nx, ny = -dy, dx
    r = pen_width / 2.0

    left_x = px + r * nx
    left_y = py + r * ny
    right_x = px - r * nx
    right_y = py - r * ny

    # Semicircular end cap (12 points, centred at stroke end, facing outward)
    angles_end = np.linspace(-np.pi / 2, np.pi / 2, 12)
    cap_end_x = px[-1] + r * (np.cos(angles_end) * dx[-1] - np.sin(angles_end) * dy[-1])
    cap_end_y = py[-1] + r * (np.cos(angles_end) * dy[-1] + np.sin(angles_end) * dx[-1])

    # Semicircular start cap (facing backward)
    angles_start = np.linspace(np.pi / 2, 3 * np.pi / 2, 12)
    cap_start_x = px[0] + r * (np.cos(angles_start) * dx[0] - np.sin(angles_start) * dy[0])
    cap_start_y = py[0] + r * (np.cos(angles_start) * dy[0] + np.sin(angles_start) * dx[0])

    # Full closed contour: left rail → end cap → right rail (reversed) → start cap
    cx = np.concatenate([left_x, cap_end_x, right_x[::-1], cap_start_x])
    cy = np.concatenate([left_y, cap_end_y, right_y[::-1], cap_start_y])

    return list(zip(cx.tolist(), cy.tolist()))


# ---------------------------------------------------------------------------
# Scale calibration
# ---------------------------------------------------------------------------

def compute_scale(system: dict, pen_width: float, upm: int) -> tuple[float, float]:
    """
    Auto-detect a scale factor and baseline offset so that glyphs fill the em
    square sensibly: the raw y range of all glyphs maps to ~1000 font units
    (ascender ≈ 700, descender ≈ -300).

    Returns (scale_factor, y_baseline_raw) where raw coordinates are transformed
    to font units as:  font_y = round((raw_y - y_baseline_raw) * scale_factor)
    """
    all_y = [
        pt[1]
        for glyph_points in system['glyphs'].values()
        for spline in glyph_points
        for pt in spline
    ]

    if not all_y:
        return 3000.0, 0.0

    y_min, y_max = min(all_y), max(all_y)
    y_range = y_max - y_min

    if y_range < 1e-10:
        return 3000.0, 0.0

    # Leave a margin of one pen_width on each side
    scale = upm / (y_range + 2 * pen_width)

    # Shift so the midpoint of the glyph band sits at +200 UPM (above baseline)
    y_mid = (y_min + y_max) / 2
    y_baseline_raw = y_mid - 200.0 / scale

    return scale, y_baseline_raw


# ---------------------------------------------------------------------------
# Font assembly
# ---------------------------------------------------------------------------

def build_font(system: dict, words: list[str], args) -> object:
    """
    Build and return a fontTools TTFont (OpenType/CFF) for the given system and words.
    Raises SystemExit on fatal errors.
    """
    try:
        from fontTools.fontBuilder import FontBuilder
        from fontTools.feaLib.builder import addOpenTypeFeatures
        from fontTools.pens.ttGlyphPen import TTGlyphPen
    except ImportError:
        print("Error: fonttools is required. Install with: uv sync --extra font", file=sys.stderr)
        sys.exit(1)

    upm: int = args.upm
    pen_width: float = args.pen_width
    max_len: int = args.max_word_length
    active_modes: list | None = args.modes.split(',') if args.modes else None
    active_rules: list | None = args.rules.split(',') if args.rules else None

    scale, y_baseline_raw = compute_scale(system, pen_width, upm)

    def to_font(x_raw: float, y_raw: float) -> tuple[int, int]:
        return (round(x_raw * scale), round((y_raw - y_baseline_raw) * scale))

    # ------------------------------------------------------------------
    # 1. Process every word through the pipeline
    # ------------------------------------------------------------------
    word_splines: dict[str, list] = {}
    n_skipped = 0
    for word in words:
        if len(word) > max_len:
            continue
        splines = word_to_merged_splines(word, system, active_modes, active_rules)
        if splines:
            word_splines[word] = splines
        else:
            n_skipped += 1

    if not word_splines:
        print("Error: no words could be rendered by this system.", file=sys.stderr)
        sys.exit(1)

    print(f"  Rendered {len(word_splines)} words, {n_skipped} skipped (no glyphs).", file=sys.stderr)

    # ------------------------------------------------------------------
    # 2. Build per-word glyph data (contours + metrics)
    # ------------------------------------------------------------------
    letter_names = [chr(c) for c in range(ord('a'), ord('z') + 1)]

    def glyph_name(word: str) -> str:
        return f"word_{word}"

    word_glyph_names = [glyph_name(w) for w in word_splines]
    glyph_order = ['.notdef', 'space'] + letter_names + word_glyph_names

    metrics: dict[str, tuple[int, int]] = {}

    # Static glyphs (no outlines — they exist only as GSUB input sequences)
    letter_advance = max(1, round(upm * 0.05))
    metrics['.notdef'] = (round(upm * 0.5), 0)
    metrics['space'] = (round(upm * 0.25), 0)
    for name in letter_names:
        metrics[name] = (letter_advance, 0)

    # Per-word glyph contours, keyed by glyph name
    glyph_contours: dict[str, list[list[tuple[int, int]]]] = {}

    for word, splines in word_splines.items():
        name = glyph_name(word)
        contours_font: list[list[tuple[int, int]]] = []
        all_x: list[int] = []

        for spline in splines:
            outline = spline_to_outline(spline, pen_width)
            if not outline:
                continue
            contour = [to_font(x, y) for x, y in outline]
            contours_font.append(contour)
            all_x.extend(pt[0] for pt in contour)

        if not contours_font or not all_x:
            metrics[name] = (round(upm * 0.5), 0)
            glyph_contours[name] = []
            continue

        side_bearing = max(0, round(upm * 0.03))
        x_min = min(all_x)
        x_max = max(all_x)
        advance = x_max - x_min + 2 * side_bearing
        shift = side_bearing - x_min

        metrics[name] = (advance, side_bearing)
        glyph_contours[name] = [[(x + shift, y) for x, y in c] for c in contours_font]

    # ------------------------------------------------------------------
    # 3. Assemble font tables with FontBuilder
    # ------------------------------------------------------------------
    fb = FontBuilder(upm, isTTF=True)
    fb.setupGlyphOrder(glyph_order)

    cmap = {ord(c): c for c in letter_names}
    cmap[0x0020] = 'space'
    fb.setupCharacterMap(cmap)

    fb.setupHorizontalMetrics(metrics)

    ascent = round(upm * 0.7)
    descent = round(upm * -0.3)
    fb.setupHorizontalHeader(ascent=ascent, descent=descent)

    system_name = Path(args.system_folder).name.capitalize()
    fb.setupOS2(
        sTypoAscender=ascent,
        sTypoDescender=descent,
        sTypoLineGap=0,
        usWinAscent=ascent,
        usWinDescent=-descent,
        fsType=0,
        sxHeight=round(upm * 0.5),
        sCapHeight=ascent,
        achVendID='ABRV',
        fsSelection=0x40,
    )

    fb.setupPost()
    fb.setupHead(unitsPerEm=upm)

    ps_name = f"AbbrvShorthand-{Path(args.system_folder).name.capitalize()}"
    family_name = f"Abbrv {system_name}"

    fb.setupNameTable({
        'familyName': family_name,
        'styleName': 'Regular',
        'uniqueFontIdentifier': f"{ps_name}:1.0",
        'fullName': f"{family_name} Regular",
        'version': 'Version 1.0',
        'psName': ps_name,
    })

    fb.setupDummyDSIG()

    mac_now = int(time.time()) - calendar.timegm((1904, 1, 1, 0, 0, 0))
    fb.font['head'].created = mac_now
    fb.font['head'].modified = mac_now
    fb.font['head'].flags = 0x000B

    # Build TrueType glyf table using TTGlyphPen
    glyphs_dict = {}

    for name in glyph_order:
        pen = TTGlyphPen(None)
        contours = glyph_contours.get(name, [])
        for contour in contours:
            if len(contour) < 2:
                continue
            pen.moveTo(contour[0])
            for pt in contour[1:]:
                pen.lineTo(pt)
            pen.closePath()
        glyphs_dict[name] = pen.glyph()

    fb.setupGlyf(glyphs_dict)

    # ------------------------------------------------------------------
    # 4. GSUB ligature table via feaLib
    # ------------------------------------------------------------------
    # Sort longest-first so longer ligatures take precedence over shorter prefixes
    sorted_words = sorted(word_splines.keys(), key=len, reverse=True)

    # Classify word glyphs as Ligature (class 2) in GDEF so IgnoreMarks works
    # correctly if added later; also required for correct rendering in some shapers.
    word_glyph_list = ' '.join(glyph_name(w) for w in sorted_words
                               if all(c in letter_names for c in w))

    fea_lines = [
        'languagesystem DFLT dflt;',
        'languagesystem latn dflt;',
        '',
        f'@ligature_glyphs = [{word_glyph_list}];',
        '',
        'table GDEF {',
        '    GlyphClassDef , @ligature_glyphs, , ;',
        '} GDEF;',
        '',
        'lookup liga_words {',
    ]
    for word in sorted_words:
        # Only include words whose every character is a mapped letter glyph
        if all(c in letter_names for c in word):
            letter_seq = ' '.join(word)
            fea_lines.append(f'    sub {letter_seq} by {glyph_name(word)};')
    fea_lines += [
        '} liga_words;',
        '',
        'feature rlig {',
        '    lookup liga_words;',
        '} rlig;',
        '',
        'feature liga {',
        '    lookup liga_words;',
        '} liga;',
        '',
        'feature calt {',
        '    lookup liga_words;',
        '} calt;',
    ]

    addOpenTypeFeatures(fb.font, StringIO('\n'.join(fea_lines)))

    return fb.font


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Export a shorthand system as an OpenType font (.otf)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python export_font.py static/data/systems/orthic output.otf
    python export_font.py static/data/systems/orthic output.otf --max-words 500
    python export_font.py static/data/systems/orthic output.otf --word-list my_words.txt
    python export_font.py static/data/systems/orthic output.otf --pen-width 0.015 --upm 2048
""",
    )
    parser.add_argument('system_folder', type=Path,
                        help='Path to system folder containing glyphs/modes/rules/phrases JSON')
    parser.add_argument('output_otf', type=Path,
                        help='Output .otf file path')
    parser.add_argument('--word-list', type=Path, default=None,
                        help='Word list file (one word per line); default: bundled en_wordlist.txt')
    parser.add_argument('--max-words', type=int, default=5000,
                        help='Max words to include (default: 5000)')
    parser.add_argument('--max-word-length', type=int, default=12,
                        help='Skip words longer than N chars (default: 12; some engines cap GSUB '
                             'ligature length)')
    parser.add_argument('--pen-width', type=float, default=0.02,
                        help='Stroke pen width in raw glyph coordinate units (default: 0.02)')
    parser.add_argument('--upm', type=int, default=1000,
                        help='Units per em (default: 1000)')
    parser.add_argument('--modes', type=str, default=None,
                        help='Comma-separated mode names to enable (default: all)')
    parser.add_argument('--rules', type=str, default=None,
                        help='Comma-separated rule names to apply (default: all)')

    args = parser.parse_args()

    if not args.system_folder.is_dir():
        print(f"Error: system folder not found: {args.system_folder}", file=sys.stderr)
        sys.exit(1)

    try:
        system = load_system(args.system_folder)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading system: {e}", file=sys.stderr)
        sys.exit(1)

    words = load_word_list(args.word_list, args.max_words)
    if not words:
        print("Error: word list is empty.", file=sys.stderr)
        sys.exit(1)

    print(f"Processing {len(words)} words against '{args.system_folder.name}'...", file=sys.stderr)

    font = build_font(system, words, args)
    font.save(str(args.output_otf))
    print(f"Saved: {args.output_otf}", file=sys.stderr)


if __name__ == '__main__':
    main()
