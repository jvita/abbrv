from flask import Flask, render_template, request, jsonify
import numpy as np
import json
from scipy.interpolate import CubicSpline

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
    x = points[:, 0] * 30 - 15
    y = points[:, 1] * 30 - 15
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

def interpolate_points(points, num_points=100):
    if len(points) < 2:
        return np.array([]), np.array([])

    x = points[:, 0]
    y = points[:, 1]
    t = np.linspace(0, 1, len(points))

    x_spline = CubicSpline(t, x, bc_type='natural')(np.linspace(0, 1, num_points))
    y_spline = CubicSpline(t, y, bc_type='natural')(np.linspace(0, 1, num_points))

    return x_spline, y_spline

def text_to_splines(text):
    global char_splines, join_remap
    char_width = 0.17

    lines = text.split('\n')
    splines = []
    knot_points = []
    y_offset = 0
    max_width = 15
    line_height = 2
    word_space = 0.29
    y_offset = 0
    x_offset = 0
    total_width = 0
    x_word_offset = 0

    for line in lines:
        words = line.split(' ')
        for word in words:
            word_width = 0

            if word:
                points = []

                for char in word:
                    if char not in char_splines:
                        raise RuntimeError(f"Char '{char}' does not exist in spline dict.")

                    char_points = char_splines[char]
                    adjusted_points = char_points.copy()
                    adjusted_points[:, 0] += x_offset
                    adjusted_points[:, 1] += y_offset
                    x_spline, y_spline = interpolate_points(adjusted_points)
                    splines.append((x_spline, y_spline))
                    knot_points.append(adjusted_points)

                    char_width = char_points[:, 0].max() - char_points[:, 0].min()
                    word_width += char_width
                    x_offset += char_points[-1, 0]
                    y_offset += char_points[-1, 1]

                # Calculate the width of the word and adjust x_offset for the next word
                if points:
                    word_width = np.max(np.array(points)[:, 0]) - np.min(np.array(points)[:, 0])

                x_word_offset += word_width + word_space
                x_offset = x_word_offset
                y_offset = 0

        y_offset -= line_height
        x_word_offset = 0  # Reset word offset for the next line

    return splines, knot_points

def process_text(text):
    new_text = str(text)
    global join_remap
    for k, v in join_remap.items():
        new_text = new_text.replace(k, v)
    return new_text

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_splines', methods=['POST'])
def generate_splines():
    text = request.form['text']
    text = process_text(text)

    show_knot_points = 'show_knot_points' in request.form
    splines, knot_points = text_to_splines(text)

    plt.figure(figsize=(9, 3))
    for x_spline, y_spline in splines:
        plt.plot(x_spline, y_spline, 'k')

    if show_knot_points:
        for points in knot_points:
            x, y = zip(*points)
            plt.plot(x, y, 'ro')

    plt.gca().set_aspect('equal', adjustable='box')
    plt.axis('off')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode()

    return jsonify({'image': img_base64})

@app.route('/writer')
def writer():

    # Make sure to re-load the data, in case the drafter changed anything
    global char_splines
    global join_remap
    char_splines, join_remap = get_data()

    return render_template('writer.html')

@app.route('/drafter')
def drafter():
    return render_template('drafter.html')

if __name__ == '__main__':
    app.run(debug=True)
