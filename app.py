from flask import Flask, render_template, request, jsonify
import numpy as np
import json
from scipy.interpolate import CubicSpline, BSpline
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io
import base64

app = Flask(__name__)

# File paths for single-character and multi-character splines
CHAR_FILE = 'static/data/characters.json'
JOINS_FILE = 'static/data/joins.json'
characters = {}
joins = {}

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

    num_plot_points = 100

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
    joinchar = data['joinchar']
    points = data['points']

    if joinchar is None: # save as individual character
        adjusted_points = adjust_points(points, np.array([-0.5, -0.5]))

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
    else: # save in joins dictionary
        adjusted_points = adjust_points(points, np.array([-0.5, -0.5]))

        # Load existing data
        try:
            with open(JOINS_FILE, 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # Update or add new entry
        # data[character][join] is the array of points used when "character" is preceded by "join"
        if character not in existing_data:
            existing_data[character] = {joinchar: adjusted_points}
        else:
            # existing_data[character] = existing_data[character].update({joiningCharacter: adjusted_points})
            existing_data[character].update({joinchar: adjusted_points})

        # Save updated data
        with open(JOINS_FILE, 'w') as f:
            json.dump(existing_data, f, indent=4)

        return jsonify({'status': 'success'})


@app.route('/load_joins')
def load_joins():
    # Load single-character splines
    chars = {}
    try:
        with open(CHAR_FILE, 'r') as f:
            join_data = json.load(f)
            chars.update({k: adjust_points(v, np.array([0.5, 0.5])) for k, v in join_data.items()})
    except FileNotFoundError:
        pass

    # Load join splines
    joins = {}
    try:
        with open(JOINS_FILE, 'r') as f:
            join_data = json.load(f)
            joins.update({
                k: {
                    j: adjust_points(v, np.array([0.5, 0.5]))
                    for j, v in dct.items()
                    }
                for k, dct in join_data.items()
                })
    except FileNotFoundError:
        pass

    return jsonify({'chars': chars, 'joins': joins})


@app.route('/load_characters')
def load_characters():
    chars = {}

    # Load single-character splines
    try:
        with open(CHAR_FILE, 'r') as f:
            join_data = json.load(f)
            chars.update({k: adjust_points(v, np.array([0.5, 0.5])) for k, v in join_data.items()})
    except FileNotFoundError:
        pass

    return jsonify(chars)

@app.route('/delete', methods=['POST'])
def delete():
    data = request.json
    character = data['character']
    joinchar = data['joinchar']

    if joinchar is None: # delete the single character
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
    else:  # try to delete the join
        file_path = JOINS_FILE

        # Load existing data
        try:
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
        except FileNotFoundError:
            existing_data = {}

        # Remove the specified character
        if character in existing_data:
            if joinchar in existing_data[character]:
                del existing_data[character]

                # Save updated data
                with open(file_path, 'w') as f:
                    json.dump(existing_data, f, indent=4)

                return jsonify({'status': 'success'})
            else:
                return jsonify({'status': 'error', 'message': 'Join not found'})
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

def text_to_splines(text):
    raise NotImplementedError

def get_data():
    global characters
    _chars = load_json_file(CHAR_FILE)
    characters = {
        char: np.array(points, dtype=np.float32)
        for char, points in _chars.items()
    }

    global joins
    _joins = load_json_file(JOINS_FILE)
    joins = {
        char: {j: np.array(points, dtype=np.float32) for j, points in join_dict.items()}
        for char, join_dict in _joins.items()
    }

def interpolate_points(points, num_points=100):
    if len(points) < 2:
        return np.array([]), np.array([])

    x = points[:, 0]
    y = points[:, 1]
    t = np.linspace(0, 1, len(points))

    x_spline = CubicSpline(t, x, bc_type='natural')(np.linspace(0, 1, num_points))
    y_spline = CubicSpline(t, y, bc_type='natural')(np.linspace(0, 1, num_points))

    return x_spline, y_spline

def join_to_spline(char, cursor_pos, prev=None):
    global characters

    join_points = characters[char].copy()
    if prev is None: # first character in word
        # shift to properly respect spaces b/w words
        join_points[:, 0] += abs(join_points[:, 0].min())
    else:
        if (char in joins):
            if prev in joins[char]:
                # replace with modified version for the join
                join_points = joins[char][prev].copy()
            elif prev[-1] in joins[char]:  # try joining to last char instead
                join_points = joins[char][prev[-1]].copy()

        # shift to align with cursor position
        join_points -= join_points[0]

    join_points += cursor_pos  # move to cursor pos

    x_spline, y_spline = interpolate_points(join_points)
    splines = (x_spline, y_spline)
    red_dot_points = join_points  # for optionally plotting red dots

    # move cursor and word endpoint tracker
    rightmost_x = join_points[:, 0].max()
    cursor_pos = join_points[-1].copy()

    return splines, red_dot_points, rightmost_x, cursor_pos


def text_to_separate_splines(text):
    global characters

    lines = text.split('\n')
    splines = []
    red_dot_points = []
    word_space = 0.1
    cursor_pos = np.array([0, 0], dtype=np.float32)
    rightmost_x = 0 # for adding spaces between words
    y_offset = 0  # for adding newlines
    line_height = 2

    for line in lines:
        words = line.split(' ')
        for word in words:
            if word:
                join = ''
                prev = None
                for char in word:
                    test_join = join + char
                    if test_join in characters:
                        join = test_join
                    else:
                        if join:  # non-empty
                            # build spline
                            # ci-1 because char hasn't been added yet
                            returns = join_to_spline(join, cursor_pos, prev)
                            prev = join

                            splines.append(returns[0])
                            red_dot_points.append(returns[1])
                            rightmost_x = returns[2]
                            cursor_pos = returns[3]
                        join = char

                if join: # still something left
                    # build spline
                    returns = join_to_spline(join, cursor_pos, prev)

                    splines.append(returns[0])
                    red_dot_points.append(returns[1])
                    rightmost_x = returns[2]
                    cursor_pos = returns[3]

                cursor_pos[0] = rightmost_x + word_space
                cursor_pos[1] = 0

        y_offset -= line_height

    return splines, red_dot_points

# def process_text(text):
#     new_text = str(text)
#     global join_remap
#     n = len(text)
#     for i in range(n):
#         j = min(i + 2, n)
#         k = text[i:j]
#         if k in join_remap:
#             new_text = new_text.replace(k, join_remap[k])
#     return new_text

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

    separate_splines = 'separate_splines' in request.form
    show_knot_points = 'show_knot_points' in request.form

    if separate_splines:
        splines, red_dot_points = text_to_separate_splines(text)
    else:
        splines, red_dot_points = text_to_splines(text)

    plt.figure(figsize=(15, 3))
    for x_spline, y_spline in splines:
        plt.plot(
            x_spline, y_spline,
            'k',
            linewidth=3,
            solid_capstyle='round'
            )

    if show_knot_points:
        for points in red_dot_points:
            x, y = zip(*points)
            plt.plot(x, y, 'ro')

    xlims = plt.gca().get_xlim()
    plt.plot(xlims, [0, 0], '--', color='lightgrey', zorder=0)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.axis('off')

    img = io.BytesIO()
    plt.savefig(img, format='png')
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
