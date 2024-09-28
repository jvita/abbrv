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

# from flask_debugtoolbar import DebugToolbarExtension
# app.config['SECRET_KEY'] = 'lorem ipsum'
# app.config['DEBUG_TB_PROFILER_ENABLED'] = True  # Enable the profiler
# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False  # Optional: avoid toolbar intercepting redirects

# app.debug = True  # Required for debug toolbar to work
# toolbar = DebugToolbarExtension(app)

# File paths for single-character and multi-character splines
CHAR_FILE = 'static/data/characters.json'
WORDS_FILE = 'static/data/words.json'
characters_dict = {}
words_dict = {}

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
    as_word = data['as_word']

    adjusted_points = [adjust_points(p, np.array([-0.5, -0.5])) for p in points]

    file_name = WORDS_FILE if as_word else CHAR_FILE

    # Load existing data
    try:
        with open(file_name, 'r') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = {}

    # Update or add new entry
    existing_data[character] = adjusted_points

    # Save updated data
    with open(file_name, 'w') as f:
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

@app.route('/load_words')
def load_words():
    words = {}

    # Load single-character splines
    try:
        with open(WORDS_FILE, 'r') as f:
            words_data = json.load(f)
            words.update({k: [adjust_points(p, np.array([0.5, 0.5])) for p in v] for k, v in words_data.items()})
    except FileNotFoundError:
        pass

    return jsonify(words)


@app.route('/delete', methods=['POST'])
def delete():
    data = request.json
    character = data['character']
    as_word = data['as_word']

    file_path = WORDS_FILE if as_word else CHAR_FILE

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

    global suffixes_dict
    suffixes_dict = {}
    to_del = []
    for k,v in characters_dict.items():
        if k[0] == '-' and len(k) > 1:
            # for things like -hood and -less
            _k = remove_consecutive_duplicates(k)
            suffixes_dict[_k] = v
            to_del.append(k)


    for k in to_del:
        del characters_dict[k]

    global words_dict
    _words = load_json_file(WORDS_FILE)
    words_dict = {
        word: [np.array(p, dtype=np.float32) for p in points]
        for word, points in _words.items()
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

def split_into_words(text):
    # Regular expression to split text by words, digits, and punctuation
    return re.findall(r'[A-Za-z]+|\d|[^\w\s]', text)

def line_to_splines(
        line,
        elevate_th=False,
        remap_words=False,
        abbreviate_suffixes=False,
    ):

    global characters_dict, suffixes_dict

    splines = []
    red_dot_points = []
    black_dot_points = []
    word_space = 0.1
    cursor_pos = np.array([0, 0], dtype=np.float32)
    char_height = 0.1

    words = [w.strip() for w in split_into_words(line.strip())]
    for word in words:
        # Apply rules that would modify the entire word
        if (elevate_th) and (len(word) > 2) and (word[:2] == 'th'):
            cursor_pos[1] += char_height
            word = word[2:]

        if (remap_words) and (len(word) >= 3) and (word[:3] == 'you'):
            cursor_pos[1] += char_height
            word = 'y' + word[3:]

        if remap_words and (word in words_dict):
            # Entire word exists, so just add it
            leftmost_x = 0
            rightmost_x = 0

            # Shift the glyph points to the current cursor position
            glyph_points = words_dict[word]
            minx = glyph_points[0][:, 0].min()
            for arr in glyph_points:
                arr[:, 0] -= minx
            glyph_points = [arr + cursor_pos for arr in glyph_points]

            for arr in glyph_points:
                leftmost_x = min(leftmost_x, arr[:, 0].min())
                rightmost_x = max(rightmost_x, arr[:, 0].max())

                x_spline, y_spline = interpolate_points(arr)
                splines.append((x_spline, y_spline))
                red_dot_points.append(arr)

            # Update cursor pos
            cursor_pos[0] = rightmost_x + word_space
            cursor_pos[1] = 0

            continue  # go to next word

        if abbreviate_suffixes:
            # Search for suffixes
            suffix_found = False
            suffix_points = []
            for suffix in suffixes_dict:
                if word.endswith(suffix[1:]):
                    suffix_points = [arr.copy() for arr in suffixes_dict[suffix]]
                    suffix_points = [arr - suffix_points[0][0] for arr in suffix_points]

                    word = word[:-len(suffix[1:])]
                    suffix_found = True
                    break  # Only handle one suffix per word

        glyph = ''
        i = 0
        first_glyph = True  # for disabling shift at start of word
        leftmost_x = 0
        rightmost_x = 0

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
                else:
                    minx = glyph_points[0][:, 0].min()
                    for arr in glyph_points:
                        arr[:, 0] -= minx
                glyph_points = [arr + cursor_pos for arr in glyph_points]

                # Build the spline
                for arr in glyph_points:
                    leftmost_x = min(leftmost_x, arr[:, 0].min())
                    rightmost_x = max(rightmost_x, arr[:, 0].max())

                    x_spline, y_spline = interpolate_points(arr)
                    splines.append((x_spline, y_spline))
                    red_dot_points.append(arr)

                # Update cursor pos
                cursor_pos = glyph_points[-1][-1].copy()

                i += len(glyph) - 1  # Move i to the end of the matched substring
                first_glyph = False

            i += 1  # Move to the next character

        if abbreviate_suffixes:
            # Append any suffix points
            if suffix_found:
                for arr in suffix_points:
                    arr += cursor_pos

                    leftmost_x = min(leftmost_x, arr[:, 0].min())
                    rightmost_x = max(rightmost_x, arr[:, 0].max())

                    x_spline, y_spline = interpolate_points(arr)
                    splines.append((x_spline, y_spline))
                    red_dot_points.append(arr)

                cursor_pos = arr[-1].copy()

        # Update cursor pos
        cursor_pos[0] = rightmost_x + word_space
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

        # Skip if char is the same as the last one (except for digits)
        if char != result[-1] or char.isdigit() or (char == 'e' and e_count <= 2):
            result.append(char)

    return ''.join(result)

def omit_a_o_before_m_n(input_string):
    # does not apply at the beginning of a word
    return re.sub(r'(?<!\b)([ao])(?=[mn])', '', input_string)

def omit_c_in_acq(input_string):
    return input_string.replace('acq', 'aq')

def omit_d_in_adj(input_string):
    return input_string.replace('adj', 'aj')

def omit_t_before_ch(input_string):
    return input_string.replace('tch', 'ch')

def omit_e_before_x(input_string):
    return input_string.replace('ex', 'x')

def split_text_with_linebreaks(text, max_width):
    # Split by lines first to preserve existing line breaks
    lines = text.splitlines()
    result = []

    for line in lines:
        words = line.split()
        current_line = []
        current_length = 0

        for word in words:
            # Check if adding the next word exceeds the max_width
            if current_length + len(word) + (len(current_line) > 0) > max_width:
                # Join the current line into a string and append it to the result
                result.append(' '.join(current_line))
                # Start a new line with the current word
                current_line = [word]
                current_length = len(word)
            else:
                # Add the word to the current line
                current_line.append(word)
                current_length += len(word) + (len(current_line) > 1)

        # Append the last processed line
        if current_line:
            result.append(' '.join(current_line))

    return result


def process_text(
        text,
        remove_dups=False,
        ao_mn_rule=False,
        acq_rule=False,
        adj_rule=False,
        tch_rule=False,
        ex_rule=False,
        ):

    text = text.lower()

    if remove_dups:
        text = remove_consecutive_duplicates(text)
    if ao_mn_rule:
        text = omit_a_o_before_m_n(text)
    if acq_rule:
        text = omit_c_in_acq(text)
    if adj_rule:
        text = omit_d_in_adj(text)
    if tch_rule:
        text = omit_t_before_ch(text)
    if ex_rule:
        text = omit_e_before_x(text)

    # remove unsupported punctuation
    for p in ["'"]:
        text = text.replace(p, '')
    for p in ['/', '\\', '-']:
        text = text.replace(p, ' ')

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

def text_to_splines(text, regex_dict):
    global characters_dict

    # Initialize an empty list to store the mapped integers
    glyphs = []
    
    i = 0
    while i < len(text):
        matched = False
        
        # Step 1: Try matching each regex pattern starting at the current index
        for regex, value in regex_dict.items():
            pattern = re.compile(regex)
            match = pattern.match(text, i)  # Check if the regex matches at the current position
            if match:
                # Add the corresponding integer value to the list
                glyphs.append(value)
                # Move the index forward by the length of the matched substring
                i += len(match.group(0))
                matched = True
                break

        # Step 2: If no regex pattern matched, check the longest match in char_dict
        if not matched:
            max_key_len = 0
            best_match = None
            best_value = None

            # Iterate over each key in char_dict to find the longest match at the current position
            for key, value in characters_dict.items():
                if text[i:i + len(key)] == key and len(key) > max_key_len:
                    max_key_len = len(key)
                    best_match = key
                    best_value = value

            if best_match:
                # Add the corresponding integer value to the list
                glyphs.append(best_value)
                # Move the index forward by the length of the matched key
                i += max_key_len
            else:
                # Handle unmapped characters (e.g., spaces or punctuation)
                glyphs.append(None)  # You can change None to any other default value if needed
                i += 1

    return glyphs

def merge_word_splines(char_splines):
    # Initialize a list to store the concatenated points for each word
    words = []
    current_word = []
    
    # Initialize the shift to [0, 0] for the first character
    current_shift = np.array([0, 0])
    first_char_in_word = True
    for char_arrays in char_splines:
        if char_arrays is None:
            # If None is encountered, it marks the end of a word
            if current_word:
                words.append(current_word)  # Add the current word to the words list
                current_word = []  # Reset for the next word
            current_shift = np.array([0, 0])  # Reset the shift for the next word
            first_char_in_word = True
        else:
            # Process each array in the list of arrays for the current character
            for pi, points_array in enumerate(char_arrays):
                shifted_points = points_array + current_shift
                if pi == 0 and not first_char_in_word:
                    # If not the first character in the word, shift the first array so that its first point is at [0, 0]
                    shifted_points -= points_array[0]

                current_word.append(shifted_points)
            
            # Update the shift to the last point of the last array in the current character
            current_shift = current_word[-1][-1]  # Last point of the last array
            first_char_in_word = False
    
    # After the loop, add the last word if it's not empty
    if current_word:
        words.append(current_word)
    
    return words

@app.route('/generate_splines', methods=['POST'])
def generate_splines():
    """
    Plots words as splines, handles line breaks by shifting each line downward.
    
    - text: Input text from user.
    - space_between_words: Horizontal space between words.
    - line_spacing: Vertical space between lines.
    """
    text = request.form['text']
    space_between_words, line_spacing = 0.2, 0.2

    plt.figure(figsize=(8, 8))  # Initialize figure

    # Variables to track positions for each line
    current_vertical_offset, right_most_point, left_most_point = 0, 0, 0
    line_positions = []  # Store y-positions of each line
    
    # Process each line of the text
    for line in text.splitlines():
        word_splines = merge_word_splines(text_to_splines(line, {}))
        current_shift = np.array([0, 0])
        line_x_pos, splines_to_plot = 0, []

        # Process each word in the line
        for word in word_splines:
            for points in word:
                shifted_points = points + current_shift
                splines_to_plot.append(shifted_points)

                # Update line and overall horizontal boundaries
                line_x_pos = max(shifted_points[:, 0].max(), line_x_pos)
                right_most_point = max(shifted_points[:, 0].max(), right_most_point)
                left_most_point = min(shifted_points[:, 0].min(), left_most_point)

            # Shift for the next word
            current_shift = np.array([line_x_pos + space_between_words, 0])

        # Calculate vertical bounds for current line
        highest_point_current_line = max(p[:, 1].max() for p in splines_to_plot)
        lowest_point_current_line = min(p[:, 1].min() for p in splines_to_plot)

        # Adjust vertical offset for the current line
        current_vertical_offset -= highest_point_current_line

        # Plot the splines for this line
        for points in splines_to_plot:
            shifted_points = points + np.array([0, current_vertical_offset])
            plot_spline(shifted_points)  # Reusable plot helper function

        # Adjust vertical offset for the next line
        line_positions.append(current_vertical_offset)
        current_vertical_offset += lowest_point_current_line - line_spacing

    # Plot baseline for each line
    plot_baselines(line_positions, left_most_point, right_most_point, space_between_words)

    # Save and return the SVG plot
    return jsonify({'image': save_plot_as_svg()})

# Helper functions
def plot_spline(points):
    """Plots individual splines."""
    if points.shape[0] == 1:
        plt.plot(points[:, 0], points[:, 1], 'ko', markersize=2.1)
    else:
        x, y = interpolate_points(points)
        plt.plot(x, y, 'k', linewidth=3, solid_capstyle='round')

def plot_baselines(line_positions, left_most, right_most, space_between_words):
    """Plots light-grey baselines for each line."""
    xlims = [left_most - space_between_words, right_most + space_between_words]
    for v in line_positions:
        plt.plot(xlims, [v, v], '--', color='lightgrey', zorder=0)
    plt.xlim(xlims)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.axis('off')

def save_plot_as_svg():
    """Saves the current plot as an SVG and returns its content."""
    img = io.BytesIO()
    plt.savefig(img, format='svg', bbox_inches='tight')
    img.seek(0)
    svg_content = img.getvalue().decode()
    plt.close()  # Close the figure after saving to free memory
    return svg_content


# @app.route('/generate_splines', methods=['POST'])
# def generate_splines():
#     text = request.form['text']
#     if text == '':
#         text = 'a b c d e f g h i j k l m n o p q r s t u v w x y z'

#     if 'remove_duplicates' in request.form:
#         text = remove_consecutive_duplicates(text)

#     text = process_text(
#         text,
#         remove_dups='remove_duplicates' in request.form,
#         ao_mn_rule='ao_mn_rule' in request.form,
#         acq_rule='acq_rule' in request.form,
#         adj_rule='adj_rule' in request.form,
#         tch_rule='tch_rule' in request.form,
#         ex_rule='ex_rule' in request.form,
#         )

#     glyph_splines = text_to_splines(text, {})
#     print(f'{glyph_splines=}')
#     word_splines = merge_word_splines(glyph_splines)
#     print(f'{word_splines=}')

#     rules = {
#         'remap_words': 'remap_words' in request.form,
#         'elevate_th': 'elevate_th' in request.form,
#         'abbreviate_suffixes': 'abbreviate_suffixes' in request.form,
#     }

#     y_offset = 0.
#     line_positions = []
#     lines = text.splitlines()
#     # lines = split_text_with_linebreaks(text, 26)
#     nlines = len(lines)
#     plt.figure(figsize=(15, 3*nlines))
#     for i, line in enumerate(lines):
#         if len(line) == 0:
#             continue  # empty line
#         splines, red_dot_points, black_dot_points = line_to_splines(line, **rules)

#         start_of_line = min(splines[0][0])  # leftmost x value; used for shifting

#         if i > 0:  # not the first line
#             # shift based on how tall you are
#             y_offset += abs(max([max(sp_tup[1]) for sp_tup in splines]))

#         for x_spline, y_spline in splines:
#             if x_spline.shape[0] == 1 and 'show_dots' in request.form:
#                 plt.plot(
#                     [_x-start_of_line for _x in x_spline],
#                     [_y-y_offset for _y in y_spline],
#                     'ko',
#                     markersize=3
#                     )
#             else:
#                 plt.plot(
#                     x_spline-start_of_line, y_spline-y_offset,
#                     'k',
#                     linewidth=3,
#                     solid_capstyle='round'
#                     )

#         if 'show_dots' in request.form:
#             # plot black dots
#             for points in black_dot_points:
#                 if points is not None:
#                     x, y = zip(*points)
#                     plt.plot(
#                         [_x-start_of_line for _x in x],
#                         [_y-y_offset for _y in y],
#                         'ko',
#                         markersize=3
#                         )

#         if 'show_knot_points' in request.form:
#             for points in red_dot_points:
#                 x, y = zip(*points)
#                 plt.plot([_x-start_of_line for _x in x], [_y-y_offset for _y in y], 'ro')

#         # shift based on the y-position of the lowest point
#         line_positions.append(y_offset)
#         y_offset += 0.15 + abs(min([min(sp_tup[1]) for sp_tup in splines]))

#     xlims = plt.gca().get_xlim()
#     xlims = (xlims[0]-0.15, xlims[-1]+0.15) # make them extend just past a normal character length
#     # xlims = (-.26, 2.4)
#     # xlims = (min(-0.26, xlims[0]), max(2.4, xlims[1]))
#     for y in line_positions:
#         plt.plot(xlims, [-y, -y], '--', color='lightgrey', zorder=0)
#     # ylims = plt.gca().get_ylim()
#     # ylims = (min(-0.3, ylims[0]), max(0.3, ylims[1]))
#     # plt.ylim(ylims)
#     plt.gca().set_aspect('equal', adjustable='box')
#     plt.axis('off')

#     img = io.BytesIO()
#     plt.savefig(img, format='svg', bbox_inches='tight')
#     img.seek(0)
#     svg_content = img.getvalue().decode()

#     return jsonify({'image': svg_content})

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
