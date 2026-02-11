#!/usr/bin/env python3
"""
Shorthand PDF Generator

Renders text as shorthand glyphs to PDF with full feature parity to the web drafter:
glyphs, modes, phrases, and rules.

Usage:
    python generate_pdf.py <system_folder> <input.txt> <output.pdf>

Example:
    python generate_pdf.py static/data/systems/orthic sample.txt output.pdf
    python generate_pdf.py static/data/systems/orthic sample.txt output.pdf --beginner
"""

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from scipy.interpolate import CubicSpline


def load_system(system_folder: Path) -> dict:
    """Load all 4 JSON files from a system folder."""
    system = {}

    required_files = ['glyphs.json', 'modes.json', 'rules.json', 'phrases.json']

    for filename in required_files:
        filepath = system_folder / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Required file not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            key = filename.replace('.json', '')
            system[key] = json.load(f)

    return system


def add_spaces_around_punctuation(text: str) -> str:
    """Add spaces around punctuation and digits."""
    pattern = r'([\d!"#$%&\'()*+,-./:;<=>?@\[\\\]^_`{|}~])'
    spaced_text = re.sub(pattern, r' \1 ', text)
    return spaced_text.strip()


def find_multi_word_tokens(text: str, phrases: dict) -> tuple[str, list]:
    """Find and extract multi-word tokens (phrases) from text."""
    matches = []

    if not phrases:
        return text, matches

    # Sort phrases by length (longest first) for greedy matching
    sorted_phrases = sorted(phrases.keys(), key=len, reverse=True)
    escaped_tokens = [re.escape(token) for token in sorted_phrases]

    if not escaped_tokens:
        return text, matches

    pattern = r'\b(' + '|'.join(escaped_tokens) + r')\b'

    def replacement(match):
        matches.append(match.group(0))
        return '§'

    new_text = re.sub(pattern, replacement, text)
    return new_text, matches


def process_text(text: str, system: dict, active_rules: list[str] | None = None) -> tuple[str, list]:
    """
    Process text through the transformation pipeline.

    Pipeline:
    1. Normalize whitespace (collapse newlines and multiple spaces)
    2. Lowercase
    3. Remove apostrophes
    4. Replace /, \\, - with spaces
    5. Add spaces around punctuation
    6. Find phrases and replace with § placeholder
    7. Apply rules (regex substitutions)
    """
    # Normalize whitespace - treat all whitespace as single spaces
    text = ' '.join(text.split())

    # Convert to lowercase
    text = text.lower()

    # Remove unsupported punctuation
    text = text.replace("'", '')

    # Replace certain punctuation with spaces
    for p in ['/', '\\', '-']:
        text = text.replace(p, ' ')

    # Add spaces around punctuation
    text = add_spaces_around_punctuation(text)

    # Find phrases and replace with placeholder
    text, multi_word_matches = find_multi_word_tokens(text, system['phrases'])

    # Apply rules
    if active_rules is None:
        active_rules = [rule['name'] for rule in system['rules']]

    for rule in system['rules']:
        if rule['name'] not in active_rules:
            continue

        try:
            regex = re.compile(rule['regex'])
            text = regex.sub(rule['replacement'], text)
        except re.error as e:
            print(f"Warning: Invalid regex in rule '{rule['name']}': {e}", file=sys.stderr)

    return text, multi_word_matches


def compare_tokenizations(a: dict, b: dict) -> bool:
    """
    Compare two tokenizations and return True if a is better than b.

    Priority:
    1. Higher mode count is better
    2. Lower token count is better
    3. Longer single token is better
    """
    if a['mode_count'] != b['mode_count']:
        return a['mode_count'] > b['mode_count']
    if a['count'] != b['count']:
        return a['count'] < b['count']
    if a['longest_token'] != b['longest_token']:
        return a['longest_token'] > b['longest_token']
    return False


def tokenize_string(word: str, system: dict, active_modes: list[str] | None = None) -> list:
    """
    Tokenize a word into glyph splines using a memoized greedy algorithm.

    Priority:
    1. Highest mode count (prefer mode matches)
    2. Lowest token count (prefer longer matches)
    3. Longest single token (tiebreaker)
    """
    if not word:
        return []

    glyphs = system['glyphs']
    modes = system['modes']

    if active_modes is None:
        active_modes = list(modes.keys())

    # Build regex list: modes first (higher priority), then glyphs
    regex_list = []

    # Add modes with their patterns
    for mode_name, mode_data in modes.items():
        if mode_name not in active_modes:
            continue
        try:
            pattern = re.compile(mode_data['pattern'])
            regex_list.append({
                'pattern': pattern,
                'value': mode_data['points'],
                'is_mode': True
            })
        except re.error:
            continue

    # Add glyphs (escape special regex characters in glyph names)
    for glyph_name, glyph_points in glyphs.items():
        escaped_pattern = re.escape(glyph_name)
        pattern = re.compile(escaped_pattern)
        regex_list.append({
            'pattern': pattern,
            'value': glyph_points,
            'is_mode': False
        })

    memo = {}

    def find_best_tokenization(start: int) -> dict | None:
        if start == len(word):
            return {'tokens': [], 'count': 0, 'longest_token': 0, 'mode_count': 0}

        if start in memo:
            return memo[start]

        best_tokenization = None

        for item in regex_list:
            pattern = item['pattern']
            value = item['value']
            is_mode = item['is_mode']

            # Try to match at the current position
            match = pattern.match(word, start)
            if match and match.start() == start:
                match_length = len(match.group(0))
                remaining = find_best_tokenization(start + match_length)

                if remaining is None:
                    continue

                current = {
                    'tokens': [value] + remaining['tokens'],
                    'count': 1 + remaining['count'],
                    'longest_token': max(match_length, remaining['longest_token']),
                    'mode_count': (1 if is_mode else 0) + remaining['mode_count']
                }

                if best_tokenization is None or compare_tokenizations(current, best_tokenization):
                    best_tokenization = current

        memo[start] = best_tokenization
        return best_tokenization

    result = find_best_tokenization(0)
    return result['tokens'] if result else []


def tokenize_with_phrases(text: str, system: dict, active_modes: list[str] | None,
                          multi_word_matches: list) -> tuple[list, list]:
    """Tokenize text, handling phrase placeholders. Returns (tokens, original_words)."""
    words = text.split()
    all_tokens = []
    original_words = []
    match_idx = 0

    for word in words:
        if word == '§':
            # Replace placeholder with phrase spline data
            if match_idx < len(multi_word_matches):
                phrase = multi_word_matches[match_idx]
                phrase_points = system['phrases'].get(phrase, [])
                all_tokens.append([phrase_points])
                original_words.append(phrase)
                match_idx += 1
            else:
                all_tokens.append([])
                original_words.append('')
        else:
            tokens = tokenize_string(word, system, active_modes)
            all_tokens.append(tokens)
            original_words.append(word)

    return all_tokens, original_words


def merge_word_splines(text_splines: list) -> list:
    """
    Merge word splines by concatenating points for each word and adjusting shifts.

    Each glyph is shifted so its first point connects to the last point of the
    previous glyph.
    """
    words = []

    for word_splines in text_splines:
        current_word = []
        current_shift = [0.0, 0.0]

        for gi, glyph_splines in enumerate(word_splines):
            if not glyph_splines:
                continue

            # Get the first point of the first spline of this glyph for normalization
            first_point = glyph_splines[0][0] if glyph_splines[0] else [0, 0]

            for points in glyph_splines:
                if not points:
                    continue

                # Clone points
                shifted_points = [[p[0], p[1]] for p in points]

                # Normalize: shift so glyph's origin is at (0,0) relative to its first point
                # Only for glyphs after the first one
                if gi != 0:
                    for i in range(len(shifted_points)):
                        shifted_points[i][0] -= first_point[0]
                        shifted_points[i][1] -= first_point[1]

                # Apply accumulated shift (position at end of previous glyph)
                for point in shifted_points:
                    point[0] += current_shift[0]
                    point[1] += current_shift[1]

                current_word.append(shifted_points)

            # Update shift to last point of last spline of this glyph
            if current_word and current_word[-1]:
                current_shift = list(current_word[-1][-1])

        words.append(current_word)

    return words


def interpolate_spline(points: list, num_points: int = 100) -> tuple[np.ndarray, np.ndarray]:
    """
    Interpolate points using natural cubic spline.

    Args:
        points: List of [x, y] control points
        num_points: Number of output points

    Returns:
        Tuple of (x_coords, y_coords) arrays
    """
    if len(points) < 2:
        x = np.array([p[0] for p in points])
        y = np.array([p[1] for p in points])
        return x, y

    x = np.array([p[0] for p in points])
    y = np.array([p[1] for p in points])
    t = np.linspace(0, 1, len(points))
    t_new = np.linspace(0, 1, num_points)

    # Natural cubic spline (bc_type='natural' sets second derivative to 0 at endpoints)
    cs_x = CubicSpline(t, x, bc_type='natural')
    cs_y = CubicSpline(t, y, bc_type='natural')

    return cs_x(t_new), cs_y(t_new)


def calculate_word_dimensions(word_splines: list, scaling_factor: float, glyph_scale: float) -> dict:
    """Calculate the dimensions of a word's splines."""
    if not word_splines:
        return {'width': 0, 'ascent': 0, 'descent': 0, 'x_min': 0}

    all_x = []
    all_y = []

    for spline_points in word_splines:
        if not spline_points:
            continue
        for p in spline_points:
            all_x.append(p[0] * scaling_factor * glyph_scale)
            all_y.append(p[1] * scaling_factor * glyph_scale)

    if not all_x:
        return {'width': 0, 'ascent': 0, 'descent': 0, 'x_min': 0}

    x_min = min(all_x)
    x_max = max(all_x)
    y_max = max(all_y)
    y_min = min(all_y)

    return {
        'width': x_max - x_min,
        'ascent': y_max,
        'descent': y_min,
        'x_min': x_min
    }


def render_to_pdf(word_splines: list, original_words: list,
                  output_path: Path, page_size: str = 'letter',
                  show_baselines: bool = False, beginner_mode: bool = False,
                  scale: float = 0.33) -> None:
    """
    Render tokenized words to PDF with automatic line wrapping.

    Args:
        word_splines: List of word splines (each word is a list of spline point lists)
        original_words: List of original words (for beginner mode labels)
        output_path: Path to output PDF file
        page_size: 'letter' or 'a4'
        show_baselines: Whether to show baseline guides
        beginner_mode: Whether to show original text under each word
        scale: Size multiplier for glyphs (default 0.33, use 1.0 for original size)
    """
    # Page dimensions in inches
    page_sizes = {
        'letter': (8.5, 11),
        'a4': (8.27, 11.69)
    }
    page_width, page_height = page_sizes.get(page_size, page_sizes['letter'])

    # Margins in inches
    margin = 0.75

    # Scaling factors
    scaling_factor = 6.0
    glyph_scale = 0.5 * scale  # Scale glyphs to reasonable size in inches
    space_between_words = 0.2 * scaling_factor * glyph_scale
    line_spacing = 0.4 * scaling_factor * glyph_scale
    if beginner_mode:
        line_spacing = 0.7 * scaling_factor * glyph_scale  # Extra space for text labels

    # Pre-calculate all word dimensions
    word_dims = [calculate_word_dimensions(w, scaling_factor, glyph_scale) for w in word_splines]

    # In beginner mode, calculate text widths and adjust spacing
    text_widths = []
    if beginner_mode:
        # Create a temporary figure to measure text
        temp_fig, temp_ax = plt.subplots(figsize=(page_width, page_height))
        temp_ax.set_xlim(0, page_width)
        temp_ax.set_ylim(0, page_height)
        renderer = temp_fig.canvas.get_renderer()

        for word_idx, orig_word in enumerate(original_words):
            if orig_word:
                # Create text and measure its width
                txt = temp_ax.text(0, 0, orig_word, fontsize=8)
                bbox = txt.get_window_extent(renderer=renderer)
                # Convert from display coordinates to data coordinates
                bbox_data = bbox.transformed(temp_ax.transData.inverted())
                text_width = bbox_data.width
                txt.remove()
            else:
                text_width = 0
            text_widths.append(text_width)

        plt.close(temp_fig)

    with PdfPages(output_path) as pdf:
        fig, ax = plt.subplots(figsize=(page_width, page_height))
        ax.set_xlim(0, page_width)
        ax.set_ylim(0, page_height)
        ax.set_aspect('equal')
        ax.axis('off')

        current_x = margin
        current_y = page_height - margin
        line_words = []  # Words on current line
        line_word_indices = []  # Indices of words on current line

        def render_line(fig, ax, current_y, line_words, line_word_indices):
            """Render all words on the current line. Returns (fig, ax, new_y)."""
            if not line_words:
                return fig, ax, current_y

            # Calculate line height from words on this line
            line_ascent = max(word_dims[i]['ascent'] for i in line_word_indices) if line_word_indices else 0.3
            line_descent = min(word_dims[i]['descent'] for i in line_word_indices) if line_word_indices else -0.1

            # Position baseline
            current_y -= line_ascent
            baseline_y = current_y

            # Check if we need a new page
            needed_height = abs(line_descent) + line_spacing
            if beginner_mode:
                needed_height += 0.2

            if current_y - needed_height < margin:
                # Save current page and start new one
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
                fig, ax = plt.subplots(figsize=(page_width, page_height))
                ax.set_xlim(0, page_width)
                ax.set_ylim(0, page_height)
                ax.set_aspect('equal')
                ax.axis('off')
                current_y = page_height - margin - line_ascent
                baseline_y = current_y

            # Draw baseline if requested
            if show_baselines:
                ax.axhline(y=baseline_y, xmin=margin/page_width,
                          xmax=(page_width-margin)/page_width,
                          color='gray', linestyle='--', linewidth=0.5, alpha=0.5)

            # Render each word
            render_x = margin
            for word_idx, word in zip(line_word_indices, line_words):
                if not word:
                    render_x += space_between_words
                    continue

                dims = word_dims[word_idx]
                word_start_x = render_x
                word_end_x = render_x
                num_splines = len(word)
                stroke_endpoints = set()  # Track endpoints of multi-point splines

                for spline_idx, spline_points in enumerate(word):
                    if not spline_points:
                        continue

                    scaled_points = [[p[0] * scaling_factor * glyph_scale,
                                     p[1] * scaling_factor * glyph_scale] for p in spline_points]

                    # Apply word-level x offset
                    for p in scaled_points:
                        p[0] = p[0] - dims['x_min'] + render_x

                    spline_x_max = max(p[0] for p in scaled_points)
                    word_end_x = max(word_end_x, spline_x_max)

                    if len(scaled_points) == 1:
                        # Skip single-point splines at the start of a word (elevation markers)
                        if spline_idx == 0:
                            continue
                        # Skip single-point splines that duplicate a stroke endpoint
                        # (these are connection markers, not real dots)
                        pt = (round(scaled_points[0][0], 4), round(scaled_points[0][1], 4))
                        if pt in stroke_endpoints:
                            continue
                        ax.plot(scaled_points[0][0], baseline_y + scaled_points[0][1],
                               'ko', markersize=2 * scale)
                    else:
                        x_interp, y_interp = interpolate_spline(scaled_points)
                        ax.plot(x_interp, baseline_y + y_interp, 'k-', linewidth=1.5 * scale)
                        # Track the endpoint of this stroke
                        endpoint = (round(scaled_points[-1][0], 4), round(scaled_points[-1][1], 4))
                        stroke_endpoints.add(endpoint)

                # Draw original word below shorthand in beginner mode
                if beginner_mode and word_idx < len(original_words):
                    word_center_x = (word_start_x + word_end_x) / 2
                    label_y = baseline_y + line_descent - 0.1
                    ax.text(word_center_x, label_y, original_words[word_idx],
                           ha='center', va='top', fontsize=8, color='gray')

                # Use the wider of shorthand or text label for spacing
                shorthand_width = word_end_x - word_start_x
                if beginner_mode and word_idx < len(text_widths):
                    # Center the text under the shorthand, so account for text extending beyond
                    text_half_width = text_widths[word_idx] / 2
                    shorthand_half_width = shorthand_width / 2
                    extra_text_space = max(0, text_half_width - shorthand_half_width)
                    render_x = word_end_x + extra_text_space + space_between_words
                else:
                    render_x = word_end_x + space_between_words

            # Move to next line
            current_y -= abs(line_descent) + line_spacing

            return fig, ax, current_y

        # Process all words with line wrapping
        for word_idx, (word, dims) in enumerate(zip(word_splines, word_dims)):
            word_width = dims['width']

            # In beginner mode, account for text label width
            if beginner_mode and word_idx < len(text_widths):
                effective_width = max(word_width, text_widths[word_idx])
            else:
                effective_width = word_width

            # Check if word fits on current line
            if current_x + effective_width > page_width - margin and line_words:
                # Render current line and start new one
                fig, ax, current_y = render_line(fig, ax, current_y, line_words, line_word_indices)
                line_words = []
                line_word_indices = []
                current_x = margin

            # Add word to current line
            line_words.append(word)
            line_word_indices.append(word_idx)
            current_x += effective_width + space_between_words

        # Render final line
        if line_words:
            fig, ax, current_y = render_line(fig, ax, current_y, line_words, line_word_indices)

        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description='Generate PDF from text using a shorthand system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python generate_pdf.py static/data/systems/orthic sample.txt output.pdf
    python generate_pdf.py static/data/systems/orthic sample.txt output.pdf --beginner
    python generate_pdf.py static/data/systems/orthic sample.txt output.pdf --page-size a4
    python generate_pdf.py static/data/systems/orthic sample.txt output.pdf --rules "Remove consecutive duplicates"
        '''
    )

    parser.add_argument('system_folder', type=Path,
                       help='Path to system folder containing JSON files')
    parser.add_argument('input_file', type=Path,
                       help='Path to input text file')
    parser.add_argument('output_pdf', type=Path,
                       help='Path to output PDF file')
    parser.add_argument('--page-size', choices=['letter', 'a4'], default='letter',
                       help='Page size (default: letter)')
    parser.add_argument('--rules', type=str, default=None,
                       help='Comma-separated list of rule names to apply (default: all)')
    parser.add_argument('--modes', type=str, default=None,
                       help='Comma-separated list of mode names to enable (default: all)')
    parser.add_argument('--show-baselines', action='store_true',
                       help='Show baseline guides')
    parser.add_argument('--beginner', action='store_true',
                       help='Show original text word under each shorthand word')
    parser.add_argument('--scale', type=float, default=0.33,
                       help='Size multiplier for glyphs (default: 0.33, use 1.0 for original large size)')

    args = parser.parse_args()

    # Validate inputs
    if not args.system_folder.is_dir():
        print(f"Error: System folder not found: {args.system_folder}", file=sys.stderr)
        sys.exit(1)

    if not args.input_file.is_file():
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Load system
    try:
        system = load_system(args.system_folder)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in system files: {e}", file=sys.stderr)
        sys.exit(1)

    # Read input text
    with open(args.input_file, 'r', encoding='utf-8') as f:
        input_text = f.read()

    # Parse rule and mode filters
    active_rules = None
    if args.rules:
        active_rules = [r.strip() for r in args.rules.split(',')]

    active_modes = None
    if args.modes:
        active_modes = [m.strip() for m in args.modes.split(',')]

    # Process text (now treats all input as continuous text)
    processed_text, multi_word_matches = process_text(input_text, system, active_rules)

    # Tokenize all words
    tokens, original_words = tokenize_with_phrases(
        processed_text, system, active_modes, multi_word_matches
    )

    # Merge word splines
    merged_words = merge_word_splines(tokens)

    # Render to PDF with automatic line wrapping
    render_to_pdf(merged_words, original_words, args.output_pdf,
                  page_size=args.page_size,
                  show_baselines=args.show_baselines,
                  beginner_mode=args.beginner,
                  scale=args.scale)

    print(f"PDF generated: {args.output_pdf}")


if __name__ == '__main__':
    main()
