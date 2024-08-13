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

def interpolate_points(points, method='linear', num_points=100):
    if len(points) < 2:
        return np.array([]), np.array([])

    x = points[:, 0]
    y = points[:, 1]
    t = np.linspace(0, 1, len(points))

    if method == 'linear':
        x_spline = np.interp(np.linspace(0, 1, num_points), t, x)
        y_spline = np.interp(np.linspace(0, 1, num_points), t, y)
    elif method == 'cubic':
        x_spline = CubicSpline(t, x, bc_type='natural')(np.linspace(0, 1, num_points))
        y_spline = CubicSpline(t, y, bc_type='natural')(np.linspace(0, 1, num_points))

    return x_spline, y_spline

def text_to_splines(text, interpolation_method='linear', separate_splines=False):
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

                    if separate_splines:
                        char_points = char_splines[char]
                        adjusted_points = char_points.copy()
                        adjusted_points[:, 0] += x_offset
                        adjusted_points[:, 1] += y_offset
                        x_spline, y_spline = interpolate_points(adjusted_points, method=interpolation_method)
                        splines.append((x_spline, y_spline))
                        knot_points.append(adjusted_points)

                        char_width = char_points[:, 0] + char_points[:, 0].min()
                        char_width = abs(char_width[0] - char_width[-1])
                        word_width += char_width
                        x_offset += char_points[-1, 0]
                        y_offset += char_points[-1, 1]
                    else:
                        if total_width == 0:
                            char_points = char_splines[char]
                            y_offset = char_points[-1, 1]
                            adjusted_points = char_points.copy()
                        else:
                            char_points = char_splines[char][1:]
                            adjusted_points = char_points.copy()
                            adjusted_points[:, 0] += total_width
                            adjusted_points[:, 1] += y_offset
                            y_offset = adjusted_points[-1, 1]

                        points.extend(adjusted_points)
                        total_width += char_points[-1, 0]

                # Calculate the width of the word and adjust x_offset for the next word
                if points:
                    word_width = np.max(np.array(points)[:, 0]) - np.min(np.array(points)[:, 0])

                x_word_offset += word_width + word_space
                x_offset = x_word_offset
                y_offset = 0

                if not separate_splines:
                    rescaled_points = np.array(points)
                    x_spline, y_spline = interpolate_points(rescaled_points, method=interpolation_method)
                    splines.append((x_spline, y_spline))
                    knot_points.append(rescaled_points)

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

    interpolation_method = request.form['interpolation_method']
    show_knot_points = 'show_knot_points' in request.form
    separate_splines = 'separate_splines' in request.form
    splines, knot_points = text_to_splines(text, interpolation_method, separate_splines)

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

if __name__ == '__main__':
    app.run(debug=True, port=5001)
