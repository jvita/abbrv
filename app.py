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

# def load_char_splines(filename='char_splines.json'):
#     with open(filename, 'r') as file:
#         data = json.load(file)

#     # Convert data to numpy arrays
#     char_splines = {char: np.array(points, dtype=np.float32) for char, points in data.items()}
#     return char_splines

# # Load spline knot points from JSON file
# char_splines = load_char_splines()

data = {
"a": [[0.00, 0.00], [0.29, 0.00]],
"b": [[0.00, 0.00], [0.21, 0.21], [0.14, 0.64], [0.07, 0.21], [0.29, 0.00]],
"c": [[0.21, 0.29], [0.07, 0.29], [0.00, 0.14], [0.07, 0.00], [0.29, 0.00]],
"d": [[0.00, 0.29], [0.50, 0.00], [1.00, 0.29]],
"e": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 2], [1, 2], [1, 1], [0, 1]],
"f": [[0, 0], [0, 2], [1, 2], [1, 1], [0, 1]],
"g": [[1, 2], [0, 1], [1, 0], [2, 1], [2, 2], [1, 1]],
"h": [[0, 0], [0, 2], [1, 2], [1, 1], [0, 1]],
"i": [[0, 0], [0, 2], [0, 1], [0, 1], [1, 1]],
"j": [[1, 2], [0, 0], [1, 0], [1, 1], [0, 1]],
"k": [[0, 0], [0, 2], [1, 2], [0, 1], [1, 1], [0, 0]],
"l": [[0, 0], [0, 2], [1, 2], [1, 0]],
"m": [[0, 0], [0, 2], [1, 1], [2, 2], [2, 0]],
"n": [[0, 0], [0, 2], [1, 2], [2, 0]],
"o": [[1, 2], [0, 1], [1, 0], [2, 1], [1, 2]],
"p": [[0, 0], [0, 2], [1, 2], [2, 1], [1, 0]],
"q": [[1, 2], [0, 1], [1, 0], [2, 1], [1, 3]],
"r": [[0, 0], [0, 2], [1, 2], [1, 1], [0, 1]],
"s": [[1, 2], [0, 1], [1, 0], [0, 1], [1, 2]],
"t": [[0, 2], [1, 2], [1, 0], [0, 0], [0, 2]],
"u": [[0, 0], [0, 2], [1, 2], [2, 2], [2, 0]],
"v": [[0, 2], [1, 0], [2, 2]],
"w": [[0, 2], [0, 0], [1, 2], [2, 0], [2, 2]],
"x": [[0, 0], [2, 2], [2, 0], [0, 2]],
"y": [[0, 2], [1, 1], [2, 2], [1, 0], [0, 0]],
"z": [[0, 2], [2, 2], [0, 0], [2, 0]]
}
# Convert data to numpy arrays
char_splines = {char: np.array(points, dtype=np.float32) for char, points in data.items()}


# Define spline knot points for each character
def interpolate_points(points, method='linear', num_points=100):
    if len(points) < 2:
        return np.array([]), np.array([])  # Return empty arrays if there are not enough points

    # x, y = zip(*points)
    print(f'{points=}')
    x = points[:, 0]
    y = points[:, 1]
    t = np.linspace(0, 1, len(points))

    # if (method == 'linear') or len(points) < 8:
    if method == 'linear':
        x_spline = np.interp(np.linspace(0, 1, num_points), t, x)
        y_spline = np.interp(np.linspace(0, 1, num_points), t, y)
    elif method == 'cubic':
        x_spline = CubicSpline(t, x, bc_type='natural')(np.linspace(0, 1, num_points))
        y_spline = CubicSpline(t, y, bc_type='natural')(np.linspace(0, 1, num_points))
        # x_spline = CubicSpline(t, x, bc_type=((1, 0), (1, 0)))(np.linspace(0, 1, num_points))
        # y_spline = CubicSpline(t, y, bc_type=((1, 0), (1, 0)))(np.linspace(0, 1, num_points))
    elif method == 'bspline':
        k = 4  # Cubic B-spline
        tck_x = BSpline(t, x, k, extrapolate=False)
        tck_y = BSpline(t, y, k, extrapolate=False)
        x_spline = tck_x(np.linspace(0, 1, num_points))
        y_spline = tck_y(np.linspace(0, 1, num_points))

    return x_spline, y_spline

def text_to_splines(text, interpolation_method='linear'):
    char_width = 0.29  # Default width
    char_height = 3  # Default height

    lines = text.split('\n')
    splines = []
    knot_points = []
    y_offset = 0
    max_width = 15
    line_height = 2
    word_space = 2  # Space between words

    for line_index, line in enumerate(lines):
        x_offset = 0

        words = line.split(' ')
        for word in words:
            if word:
                points = []
                total_width = 0  # To calculate the total width of the word

                # Collect points for the entire word
                for char in word:
                    if char in char_splines:
                        if total_width > 0:  # not the first char
                            # remove first knot of new char to avoid duplicates
                            char_points = char_splines[char][1:]
                        else:
                            char_points = char_splines[char]
                        # Adjust x-coordinates by shifting for the character's position within the word
                        adjusted_points = char_points.copy()
                        adjusted_points[:, 0] += total_width
                        # adjusted_points[:, 1] *= char_height
                        points.extend(adjusted_points)
                        total_width += char_width  # Move x_offset by character width for next character
                    else:
                        raise RuntimeError(f"Char '{char}' does not exist in spline dict.")

                # Rescale x-coordinates for the entire word
                scale = char_width * len(word) / (total_width or 1)  # Avoid division by zero
                # rescaled_points = [(x * scale, y) for x, y in points]
                rescaled_points = np.array(points)
                # rescaled_points[:, 1] *= char_height
                # rescaled_points[:, 0] *= scale

                # Interpolate for the entire word
                x_spline, y_spline = interpolate_points(rescaled_points, method=interpolation_method)
                splines.append((x_spline, y_spline))
                knot_points.append(rescaled_points)

                x_offset += total_width + word_space  # Adjust x_offset for each word

        y_offset -= line_height  # Fixed line height between lines of text

    return splines, knot_points

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_splines', methods=['POST'])
def generate_splines():
    text = request.form['text']
    interpolation_method = request.form['interpolation_method']
    show_knot_points = 'show_knot_points' in request.form
    splines, knot_points = text_to_splines(text, interpolation_method)

    # Plotting
    plt.figure(figsize=(15, 5))
    for x_spline, y_spline in splines:
        plt.plot(x_spline, y_spline, 'k')

    if show_knot_points:
        end = 0
        for points in knot_points:
            x, y = zip(*points)
            plt.plot(x, y, 'ro')  # Plot knot points as red dots

    plt.gca().set_aspect('equal', adjustable='box')
    plt.axis('off')

    # Save plot to a PNG image in memory
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    img_base64 = base64.b64encode(img.getvalue()).decode()

    return jsonify({'image': img_base64})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
