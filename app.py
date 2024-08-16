from flask import Flask, render_template, request, jsonify
import numpy as np
import json
from scipy.interpolate import CubicSpline, BSpline

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io
import base64

app = Flask(__name__)

# File paths for single-character and multi-character splines
SINGLE_CHAR_FILE = 'data/single_char_splines.json'
MULTI_CHAR_FILE = 'data/multi_char_splines.json'

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
    x = points[:, 0] * 32 - 16
    y = points[:, 1] * 32 - 16
    print(x)
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
    points = data['points']

    adjusted_points = adjust_points(points, np.array([-0.5, -0.5]))

    # Determine file based on character length
    if len(character) == 1:
        file_path = SINGLE_CHAR_FILE
    else:
        file_path = MULTI_CHAR_FILE

    # Load existing data
    try:
        with open(file_path, 'r') as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        existing_data = {}

    # Update or add new entry
    existing_data[character] = adjusted_points

    # Save updated data
    with open(file_path, 'w') as f:
        json.dump(existing_data, f, indent=4)

    return jsonify({'status': 'success'})

@app.route('/load')
def load():
    all_data = {}

    # Load single-character splines
    try:
        with open(SINGLE_CHAR_FILE, 'r') as f:
            single_char_data = json.load(f)
            all_data.update({k: adjust_points(v, np.array([0.5, 0.5])) for k, v in single_char_data.items()})
    except FileNotFoundError:
        pass

    # Load multi-character splines
    try:
        with open(MULTI_CHAR_FILE, 'r') as f:
            multi_char_data = json.load(f)
            all_data.update({k: adjust_points(v, np.array([0.5, 0.5])) for k, v in multi_char_data.items()})
    except FileNotFoundError:
        pass

    return jsonify(all_data)

@app.route('/delete', methods=['POST'])
def delete():
    data = request.json
    character = data['character']

    if len(character) == 1:
        file_path = SINGLE_CHAR_FILE
    else:
        file_path = MULTI_CHAR_FILE

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
    # Make sure to re-load the data, in case the drafter changed anything
    global char_splines
    global join_remap
    char_splines, join_remap = get_data()

# Writer code
def load_json_file(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def get_data():
    joins = load_json_file('data/multi_char_splines.json')
    char_data = load_json_file('data/single_char_splines.json')

    join_keys = list(joins.keys())
    join_remap = {k: str(i) for i, k in enumerate(join_keys)}
    join_data = {i: joins[join_keys[int(i)]] for i in join_remap.values()}

    char_splines = {
        char: np.array(points, dtype=np.float32)
        for char, points in {**char_data, **join_data}.items()
    }

    return char_splines, join_remap

# Load the data when the Flask app starts
char_splines, join_remap = get_data()

# def create_bspline(t, x, y, k=3):
#     n = len(x)  # Number of control points
#     m = n + k + 1  # Number of knots

#     # Create a knot vector with m knots
#     t_knots = np.concatenate(([0] * k, np.linspace(0, 1, n - k + 1), [1] * k))

#     # Create B-splines for x and y coordinates
#     spl_x = BSpline(t_knots, x, k)
#     spl_y = BSpline(t_knots, y, k)

#     return spl_x, spl_y

def interpolate_points(points, num_points=100):
    if len(points) < 2:
        return np.array([]), np.array([])

    x = points[:, 0]
    y = points[:, 1]
    t = np.linspace(0, 1, len(points))

    # t_new = np.linspace(0, 1, num_points)
    # tck_x, tck_y = create_bspline(t, x, y, k=3)
    # x_spline = tck_x(t_new)
    # y_spline = tck_y(t_new)

    # num_knots = len(x)
    # print(f'{num_knots=}')
    # if num_knots <= 3:
    x_spline = CubicSpline(t, x, bc_type='natural')(np.linspace(0, 1, num_points))
    y_spline = CubicSpline(t, y, bc_type='natural')(np.linspace(0, 1, num_points))
    # else:
    #     x_spline = BSpline(t, x, k=num_points-1)(np.linspace(0, 1, num_points))
    #     y_spline = BSpline(t, y, k=num_points-1)(np.linspace(0, 1, num_points))

    return x_spline, y_spline

def text_to_splines(text):
    '''A version of `text_to_splines` that treates entire words as a single spline'''
    global char_splines, join_remap

    lines = text.split('\n')
    splines = []
    red_dot_points = []
    word_space = 0.29
    cursor_pos = np.array([0, 0], dtype=np.float32)
    rightmost_x = 0 # for adding spaces between words
    y_offset = 0  # for adding newlines
    line_height = 2
    # char_buffer_width = 0.05

    for line in lines:
        words = line.split(' ')
        for word in words:
            word_points = []
            if word:
                for ci, char in enumerate(word):
                    if char not in char_splines:
                        raise RuntimeError(f"Char '{char}' does not exist in spline dict.")

                    # Shift points to cursor position
                    char_points = char_splines[char].copy()

                    if ci > 0: # not first character
                        # shift first point to (0, 0)
                        char_points -= char_points[0]
                        char_points = char_points[1:] # since it will connect to prev char

                    char_points += cursor_pos  # move to cursor pos
                    # char_points[:, 0] += char_buffer_width

                    word_points.append(char_points)

                    # move cursor and word endpoint tracker
                    rightmost_x = char_points[:, 0].max()
                    cursor_pos = char_points[-1].copy()

                    red_dot_points.append(char_points)  # for optionally plotting red dots

                # draw spline points
                word_points = np.concatenate(word_points)
                x_spline, y_spline = interpolate_points(word_points)
                splines.append((x_spline, y_spline))

                # reset cursor
                cursor_pos[0] = rightmost_x + word_space
                cursor_pos[1] = 0  # return to baseline height

        y_offset -= line_height

    return splines, red_dot_points


def text_to_separate_splines(text):
    global char_splines, join_remap

    lines = text.split('\n')
    splines = []
    red_dot_points = []
    word_space = 0.29
    cursor_pos = np.array([0, 0], dtype=np.float32)
    rightmost_x = 0 # for adding spaces between words
    y_offset = 0  # for adding newlines
    line_height = 2

    for line in lines:
        words = line.split(' ')
        for word in words:
            if word:
                for ci, char in enumerate(word):
                    if char not in char_splines:
                        raise RuntimeError(f"Char '{char}' does not exist in spline dict.")

                    # Shift points to cursor position
                    char_points = char_splines[char].copy()

                    if ci > 0: # not first character
                        # shift first point to (0, 0)
                        char_points -= char_points[0]

                    char_points += cursor_pos  # move to cursor pos

                    x_spline, y_spline = interpolate_points(char_points)
                    splines.append((x_spline, y_spline))
                    red_dot_points.append(char_points)  # for optionally plotting red dots

                    # move cursor and word endpoint tracker
                    rightmost_x = char_points[:, 0].max()
                    cursor_pos = char_points[-1].copy()

                # reset cursor
                cursor_pos[0] = rightmost_x + word_space
                cursor_pos[1] = 0  # return to baseline height

        y_offset -= line_height

    return splines, red_dot_points

def process_text(text):
    """Processes text in the following manner:

    - moving left to right
    - TODO: check for special starting characters ("th")
    - TODO: removes 'o' and 'a' before 'm' an 'n' if not at start of word
    - check for 2-character special joins
    """
    new_text = str(text)
    global join_remap
    n = len(text)
    for i in range(n):
        j = min(i + 2, n)
        k = text[i:j]
        if k in join_remap:
            new_text = new_text.replace(k, join_remap[k])
    return new_text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_splines', methods=['POST'])
def generate_splines():
    text = request.form['text']
    text = process_text(text)

    separate_splines = 'separate_splines' in request.form
    show_knot_points = 'show_knot_points' in request.form

    if separate_splines:
        splines, red_dot_points = text_to_separate_splines(text)
    else:
        splines, red_dot_points = text_to_splines(text)

    plt.figure(figsize=(9, 3))
    for x_spline, y_spline in splines:
        plt.plot(x_spline, y_spline, 'k')

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
