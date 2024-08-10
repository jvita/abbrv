from flask import Flask, render_template, request, jsonify
import numpy as np
from scipy.interpolate import CubicSpline

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io
import base64

app = Flask(__name__)

# Define spline knot points for each character
char_splines = {
    'a': [(0, 0), (1, 0)],
    'b': [(0.00, 0.00), (0.09, 0.04), (0.18, 0.09), (0.27, 0.13), (0.36, 0.17), (0.45, 0.22), (0.55, 0.26), (0.64, 0.30), (0.73, 0.35), (0.82, 0.39), (0.91, 0.43), (0.91, 0.48), (0.91, 0.52), (0.91, 0.57), (0.91, 0.61), (0.91, 0.65), (0.91, 0.70), (0.91, 0.74), (0.91, 0.78), (0.91, 0.83), (0.91, 0.87), (0.91, 0.91), (0.82, 0.96), (0.73, 1.00), (0.64, 1.00), (0.55, 1.00), (0.45, 1.00), (0.36, 1.00), (0.27, 1.00), (0.18, 0.96), (0.09, 0.91), (0.09, 0.87), (0.09, 0.83), (0.09, 0.78), (0.09, 0.74), (0.09, 0.70), (0.09, 0.65), (0.09, 0.61), (0.09, 0.57), (0.09, 0.52), (0.09, 0.48), (0.09, 0.43), (0.18, 0.39), (0.27, 0.35), (0.36, 0.30), (0.45, 0.26), (0.55, 0.22), (0.64, 0.17), (0.73, 0.13), (0.82, 0.09), (0.91, 0.04), (1.00, 0.00)],
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

def interpolate_points(points, num_points=1000):
    if len(points) < 2:
        return np.array([]), np.array([])  # Return empty arrays if there are not enough points

    x, y = zip(*points)
    t = np.linspace(0, 1, len(points))

    # Use CubicSpline with natural boundary conditions
    x_spline = CubicSpline(t, x, bc_type='not-a-knot')
    y_spline = CubicSpline(t, y, bc_type='not-a-knot')

    t_new = np.linspace(0, 1, num_points)
    return x_spline(t_new), y_spline(t_new)

def text_to_splines(text):
    lines = text.split('\n')  # Split by newlines to handle multiple lines
    splines = []
    knot_points = []  # To store knot points for optional display
    y_offset = 0
    max_width = 15  # Max width of the plot
    line_height = 4  # Fixed height for each line of text
    space_width = 2  # Fixed width for spaces

    for line_index, line in enumerate(lines):
        words = line.split(' ')  # Split each line into words
        x_offset_line = 0  # Reset x_offset for each new line

        for word in words:
            if word:  # Ignore empty words (consecutive spaces)
                points = word_to_spline(word)
                if points:
                    # Adjust x-coordinates and y-coordinates for line height
                    adjusted_points = [(x + x_offset_line, y + y_offset) for x, y in points]
                    x, y = interpolate_points(adjusted_points)
                    if len(x) > 0 and len(y) > 0:  # Only plot if there are valid points
                        splines.append((x, y))
                        knot_points.extend(adjusted_points)  # Add knot points for display
                        x_offset_line += max(x) + space_width  # Fixed space between words

        # Move to next line if the current line exceeds max width
        if x_offset_line > max_width:
            x_offset_line = 0
            y_offset -= line_height  # Move down for the next line

        # Update y_offset for each new line
        y_offset -= line_height

    # Calculate the number of lines
    num_lines = len(lines)
    return splines, knot_points, num_lines

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form.get('text', '')
        show_knots = request.form.get('show_knots', 'false') == 'true'
        splines, knot_points, num_lines = text_to_splines(text)

        # Determine plot height based on the number of lines
        plot_height = 2 + num_lines * 4  # Adjust the height based on the number of lines
        plt.figure(figsize=(15, plot_height))  # Fixed width, dynamic height

        for x, y in splines:
            plt.plot(x, y, c='k')
        
        if show_knots:
            knot_x, knot_y = zip(*knot_points) if knot_points else ([], [])
            plt.scatter(knot_x, knot_y, c='r', s=10)  # Plot knot points as red dots

        plt.axis('off')

        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()  # Close the figure to free up memory

        return jsonify({'plot_url': plot_url})
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
