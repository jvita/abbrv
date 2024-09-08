from flask import Flask, render_template, request, jsonify
import numpy as np
import json
from scipy.interpolate import CubicSpline, BSpline
import os
import re

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io
import base64

app = Flask(__name__)

# File paths for single-character and multi-character splines
CHAR_FILE = 'static/data/characters.json'
JOINS_FILE = 'static/data/joins.json'
WORDS_FILE = 'static/data/words.json'
CHAR_DOTS_FILE = 'static/data/characters_dots.json'
JOINS_DOTS_FILE = 'static/data/joins_dots.json'
characters_dict = {}
joins_dict = {}
words_dict = {}
char_dots_dict = {}
joins_dots_dict = {}

def adjust_points(points, adjustment):
    """Adjust points by adding or subtracting a constant."""
    points = np.array(points)
    return (points + adjustment).tolist()

@app.route('/spline', methods=['POST'])
def spline():
    points = request.json['points']
    if not points:
        return jsonify({'spline': []})

    points = np.array(points)
    x = points[:, 0] * 76 - 38
    y = points[:, 1] * 76 - 38
    t = np.linspace(0, 1, len(points))

    num_plot_points = points.shape[0]*20

    x_dense = CubicSpline(t, x, bc_type='natural')(np.linspace(0, 1, num_plot_points))
    y_dense = CubicSpline(t, y, bc_type='natural')(np.linspace(0, 1, num_plot_points))

    if len(x_dense) < 2:
        return jsonify({'spline': []})

    try:
        spline_points = list(zip(x_dense.tolist(), y_dense.tolist()))
        return jsonify({'spline': spline_points})
    except Exception as e:
        print(f"Error in spline calculation: {e}")
        return jsonify({'spline': []})

@app.route('/save', methods=['POST'])
def save():
    data = request.json
    character = data['character']
    points = data['points']
    # dots = data['dots']
    dots = []

    # handle saving dots, if provided
    if len(dots) > 0:

        adjusted_points = adjust_points(dots, np.array([-0.5, -0.5]))

        # Load existing data
        try:
            with open(CHAR_DOTS_FILE, 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # Update or add new entry
        existing_data[character] = adjusted_points

        # Save updated data
        with open(CHAR_DOTS_FILE, 'w') as f:
            json.dump(existing_data, f, indent=4)

    adjusted_points = [adjust_points(p, np.array([-0.5, -0.5])) for p in points]

    # Load existing data
    try:
        with open(CHAR_FILE, 'r') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = {}

    # Update or add new entry
    existing_data[character] = adjusted_points

    # Save updated data
    with open(CHAR_FILE, 'w') as f:
        json.dump(existing_data, f, indent=4)

    return jsonify({'status': 'success'})

@app.route('/load_characters')
def load_characters():
    chars = {}

    # Load single-character splines
    try:
        with open(CHAR_FILE, 'r') as f:
            chars_data = json.load(f)
            chars.update({k: [adjust_points(p, np.array([0.5, 0.5])) for p in v] for k, v in chars_data.items()})
    except FileNotFoundError:
        pass

    return jsonify(chars)

@app.route('/load_dots')
def load_dots():
    dots = {'chars': {}, 'joins': {}}

    # Load single-character dots
    try:
        with open(CHAR_DOTS_FILE, 'r') as f:
            chars_data = json.load(f)
            dots['chars'].update({k: [adjust_points(p, np.array([0.5, 0.5])) for p in v] for k, v in chars_data.items()})
    except FileNotFoundError:
        pass

    return jsonify(dots)

@app.route('/delete', methods=['POST'])
def delete():
    data = request.json
    character = data['character']

    file_path = CHAR_FILE

    # Load existing data
    try:
        with open(file_path, 'r') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = {}

    # Remove the specified character
    if character in existing_data:
        del existing_data[character]

        # Save updated data
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=4)

        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Character not found'})

def execute_on_refresh():
    get_data()

# Writer code
def load_json_file(filename):
    if not os.path.isfile(filename):
        with open(filename, 'w') as f:
            f.write(json.dumps({}))

    with open(filename, 'r') as f:
        return json.load(f)

def get_data():
    global characters_dict
    _chars = load_json_file(CHAR_FILE)
    characters_dict = {
        char: [np.array(p, dtype=np.float32) for p in points]
        for char, points in _chars.items()
    }

    global char_dots_dict
    _dots = load_json_file(CHAR_DOTS_FILE)
    char_dots_dict = {
        char: np.array(points, dtype=np.float32)
        for char, points in _dots.items()
    }


def interpolate_points(points, num_points=100):
    if len(points) < 2:
        return (points[:, 0], points[:, 1])
        # return np.array([]), np.array([])

    x = points[:, 0]
    y = points[:, 1]
    t = np.linspace(0, 1, len(points))

    x_spline = CubicSpline(t, x, bc_type='natural')(np.linspace(0, 1, num_points))
    y_spline = CubicSpline(t, y, bc_type='natural')(np.linspace(0, 1, num_points))

    return x_spline, y_spline


def line_to_splines(
        line,
        elevate_th=False
    ):

    global characters_dict

    splines = []
    red_dot_points = []
    black_dot_points = []
    word_space = 0.1
    cursor_pos = np.array([0, 0], dtype=np.float32)
    char_height = 0.1

    words = line.strip().split(' ')
    for word in words:
        if (elevate_th) and (len(word) > 2) and (word[:2] == 'th'):
            cursor_pos[1] += char_height
            word = word[2:]

        leftmost_x = cursor_pos[0]
        glyph = ''
        i = 0
        first_glyph = True  # for disabling shift at start of word

        # search for the largest glyph
        while i < len(word):
            temp_glyph = ''
            longest_match = ''

            # Check all substrings starting at index i
            for j in range(i, len(word)):
                temp_glyph += word[j]
                if temp_glyph in characters_dict:
                    longest_match = temp_glyph

            if longest_match:
                glyph = longest_match

                # Shift the glyph points to the current cursor position
                glyph_points = characters_dict[glyph]
                if not first_glyph: # first char in word
                    glyph_points = [arr - glyph_points[0][0] for arr in glyph_points]
                glyph_points = [arr + cursor_pos for arr in glyph_points]

                # Build the spline
                leftmost_x = 0
                rightmost_x = 0
                for arr in glyph_points:
                    x_spline, y_spline = interpolate_points(arr)
                    splines.append((x_spline, y_spline))
                    red_dot_points.append(arr)

                # Update cursor pos
                cursor_pos = glyph_points[-1][-1].copy()

                i += len(glyph) - 1  # Move i to the end of the matched substring
                first_glyph = False

            i += 1  # Move to the next character

        cursor_pos[0] += (rightmost_x - leftmost_x) + word_space
        cursor_pos[1] = 0

    return splines, red_dot_points, black_dot_points


def remove_consecutive_duplicates(s):
    if not s:
        return ""

    result = [s[0]]  # Start with the first character
    e_count = 1 if s[0] == 'e' else 0  # Track consecutive 'e' characters

    for char in s[1:]:
        if char == 'e':
            e_count += 1
        else:
            e_count = 0  # Reset the count if the character is not 'e'

        if char != result[-1] or (char == 'e' and e_count <= 2):
            result.append(char)
        elif char != 'e' and char != result[-1]:
            result.append(char)

    return ''.join(result)


def remove_a_o_before_m_n(text):
    # Use a regular expression to find "a" or "o" before "m" or "n", not at the start of a word
    result = re.sub(r'(?<!\b)[ao](?=[mn])', '', text)
    return result

def process_text(
        text,
        remove_dups=False,
        oa_mn_rule=False
        ):

    if remove_dups:
        text = remove_consecutive_duplicates(text)
    if oa_mn_rule:
        text = remove_a_o_before_m_n(text)

    return text

# def points_to_svg(points, stroke_color='black', stroke_width=2, width=100, height=100):
#     # Start the SVG string
#     svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'

#     # Generate the path data
#     if points:
#         d = f'M {points[0][0]},{points[0][1]} '
#         d += ' '.join(f'L {x},{y}' for x, y in points[1:])

#         # Create the path element
#         svg += f'    <path d="{d}" stroke="{stroke_color}" stroke-width="{stroke_width}" fill="none" />\n'

#     # Close the SVG string
#     svg += '</svg>'

#     return svg


@app.route('/generate_splines', methods=['POST'])
def generate_splines():
    text = request.form['text']
    if text == '':
        text = 'a b c d e f g h i j k l m n o p q r s t u v w x y z'
    # text = process_text(text)

    if 'remove_duplicates' in request.form:
        text = remove_consecutive_duplicates(text)

    text = process_text(
        text,
        remove_dups='remove_duplicates' in request.form,
        oa_mn_rule='oa_mn_rule' in request.form
        )

    rules = {
        'elevate_th': 'elevate_th' in request.form,
    }

    y_offset = 0.
    line_positions = []
    lines = text.splitlines()
    nlines = len(lines)
    plt.figure(figsize=(15, 3*nlines))
    for i, line in enumerate(text.splitlines()):
        if len(line) == 0:
            continue  # empty line
        splines, red_dot_points, black_dot_points = line_to_splines(line, **rules)

        start_of_line = min(splines[0][0])  # leftmost x value; used for shifting

        if i > 0:  # not the first line
            # shift based on how tall you are
            y_offset += abs(max([max(sp_tup[1]) for sp_tup in splines]))

        for x_spline, y_spline in splines:
            if x_spline.shape[0] == 1 and 'show_dots' in request.form:
                plt.plot(
                    [_x-start_of_line for _x in x_spline],
                    [_y-y_offset for _y in y_spline],
                    'ko',
                    markersize=3
                    )
            else:
                plt.plot(
                    x_spline-start_of_line, y_spline-y_offset,
                    'k',
                    linewidth=3,
                    solid_capstyle='round'
                    )

        if 'show_dots' in request.form:
            # plot black dots
            for points in black_dot_points:
                if points is not None:
                    x, y = zip(*points)
                    plt.plot(
                        [_x-start_of_line for _x in x],
                        [_y-y_offset for _y in y],
                        'ko',
                        markersize=3
                        )

        if 'show_knot_points' in request.form:
            for points in red_dot_points:
                x, y = zip(*points)
                plt.plot([_x-start_of_line for _x in x], [_y-y_offset for _y in y], 'ro')

        # shift based on the y-position of the lowest point
        line_positions.append(y_offset)
        y_offset += 0.15 + abs(min([min(sp_tup[1]) for sp_tup in splines]))

    xlims = plt.gca().get_xlim()
    xlims = (xlims[0]-0.15, xlims[-1]+0.15) # make them extend just past a normal character length
    for y in line_positions:
        plt.plot(xlims, [-y, -y], '--', color='lightgrey', zorder=0)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.axis('off')

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode()

    return jsonify({'image': img_base64})

@app.route('/')
@app.route('/writer')
def writer():
    execute_on_refresh()
    return render_template('writer.html')

@app.route('/drafter')
def drafter():
    # execute_on_refresh()
    return render_template('drafter.html')

if __name__ == '__main__':
    app.run(debug=True)
