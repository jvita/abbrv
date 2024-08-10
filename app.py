from flask import Flask, render_template, request, jsonify
import numpy as np
from scipy.interpolate import CubicSpline, BSpline

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io
import base64

app = Flask(__name__)

# Define spline knot points for each character
char_splines = {
    'a': [(0, 0), (1, 0)],
    'b': [(0.00, 0.00), (0.33, 0.08), (0.67, 0.31), (0.83, 0.69), (0.50, 1.00), (0.17, 0.69), (0.33, 0.31), (0.67, 0.08), (1.00, 0.00)],
    'c': [(1, 2), (0, 1), (1, 0), (2, 1)],
    'd': [(0, 0), (0, 2), (1, 3), (2, 2), (2, 0)],
    'e': [(0, 0), (1, 0), (1, 1), (0, 1), (0, 2), (1, 2), (1, 1), (0, 1)],
    'f': [(0, 0), (0, 2), (1, 2), (1, 1), (0, 1)],
    'g': [(1, 2), (0, 1), (1, 0), (2, 1), (2, 2), (1, 1)],
    'h': [(0, 0), (0, 2), (1, 2), (1, 1), (0, 1)],
    'i': [(0, 0), (0, 2), (0, 1), (0, 1), (1, 1)],
    'j': [(1, 2), (0, 0), (1, 0), (1, 1), (0, 1)],
    'k': [(0, 0), (0, 2), (1, 2), (0, 1), (1, 1), (0, 0)],
    'l': [(0, 0), (0, 2), (1, 2), (1, 0)],
    'm': [(0, 0), (0, 2), (1, 1), (2, 2), (2, 0)],
    'n': [(0, 0), (0, 2), (1, 2), (2, 0)],
    'o': [(1, 2), (0, 1), (1, 0), (2, 1), (1, 2)],
    'p': [(0, 0), (0, 2), (1, 2), (2, 1), (1, 0)],
    'q': [(1, 2), (0, 1), (1, 0), (2, 1), (1, 3)],
    'r': [(0, 0), (0, 2), (1, 2), (1, 1), (0, 1)],
    's': [(1, 2), (0, 1), (1, 0), (0, 1), (1, 2)],
    't': [(0, 2), (1, 2), (1, 0), (0, 0), (0, 2)],
    'u': [(0, 0), (0, 2), (1, 2), (2, 2), (2, 0)],
    'v': [(0, 2), (1, 0), (2, 2)],
    'w': [(0, 2), (0, 0), (1, 2), (2, 0), (2, 2)],
    'x': [(0, 0), (2, 2), (2, 0), (0, 2)],
    'y': [(0, 2), (1, 1), (2, 2), (1, 0), (0, 0)],
    'z': [(0, 2), (2, 2), (0, 0), (2, 0)]
}

def word_to_spline(word):
    points = []
    x_offset = 0
    for char in word.lower():
        if char in char_splines:
            char_points = char_splines[char]
            # Adjust x-coordinates
            adjusted_points = [(x + x_offset, y) for x, y in char_points]

            # If not the first character, remove the first point to connect to the previous character
            if points:
                adjusted_points = adjusted_points[1:]

            points.extend(adjusted_points)
            x_offset += max(x for x, _ in char_points) + 1  # Fixed space between characters

    return points

def interpolate_points(points, method='linear', num_points=1000):
    if len(points) < 2:
        return np.array([]), np.array([])  # Return empty arrays if there are not enough points

    x, y = zip(*points)
    t = np.linspace(0, 1, len(points))

    if method == 'linear':
        x_spline = np.interp(np.linspace(0, 1, num_points), t, x)
        y_spline = np.interp(np.linspace(0, 1, num_points), t, y)
    elif method == 'cubic':
        x_spline = CubicSpline(t, x)(np.linspace(0, 1, num_points))
        y_spline = CubicSpline(t, y)(np.linspace(0, 1, num_points))
    elif method == 'bspline':
        k = 3  # Cubic B-spline
        tck_x = BSpline(t, x, k, extrapolate=False)
        tck_y = BSpline(t, y, k, extrapolate=False)
        x_spline = tck_x(np.linspace(0, 1, num_points))
        y_spline = tck_y(np.linspace(0, 1, num_points))

    return x_spline, y_spline

def text_to_splines(text, interpolation_method='linear'):
    lines = text.split('\n')  # Split by newlines to handle multiple lines
    splines = []
    knot_points = []
    y_offset = 0
    max_width = 15  # Max width of the plot
    line_height = 4  # Fixed height for each line of text
    space_width = 2  # Fixed width for spaces

    for line_index, line in enumerate(lines):
        words = line.split(' ')  # Split each line into words
        x_offset_line = 0  # Reset x_offset for each new line

        for word in words:
            if word:  # Only process non-empty words
                points = word_to_spline(word)
                # Adjust y-coordinates for each line and x-coordinates for each word
                adjusted_points = [(x + x_offset_line, y + y_offset) for x, y in points]
                x_offset_line += max(x for x, _ in points) + space_width  # Adjust x_offset for each word

                x_spline, y_spline = interpolate_points(adjusted_points, method=interpolation_method)
                splines.append((x_spline, y_spline))
                knot_points.append(adjusted_points)

        y_offset -= line_height  # Fixed line height between lines of text

    return splines, knot_points

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate_splines', methods=['POST'])
def generate_splines():
    text = request.form['text']
    interpolation_method = request.form['interpolation_method']
    splines, knot_points = text_to_splines(text, interpolation_method)

    # Plotting
    plt.figure(figsize=(15, 10))
    for x_spline, y_spline in splines:
        plt.plot(x_spline, y_spline, 'b-')

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
    app.run(debug=True)
