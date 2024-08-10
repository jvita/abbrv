from flask import Flask, render_template, request, jsonify
import numpy as np
from scipy import interpolate
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# Define spline knot points for each character
char_splines = {
    'a': [(0, 0), (1, 2), (2, 2), (2, 0), (1, 0)],
    'b': [(0, 0), (0, 2), (1, 3), (2, 2), (2, 1), (1, 0), (0, 0)],
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
    t_new = np.linspace(0, 1, num_points)
    
    # Choose interpolation method based on the number of points
    if len(points) < 4:
        # Use linear interpolation if there are less than 4 points
        x_interp = interpolate.interp1d(t, x, kind='linear', fill_value='extrapolate')
        y_interp = interpolate.interp1d(t, y, kind='linear', fill_value='extrapolate')
    else:
        # Use cubic interpolation if there are at least 4 points
        x_interp = interpolate.interp1d(t, x, kind='cubic', fill_value='extrapolate')
        y_interp = interpolate.interp1d(t, y, kind='cubic', fill_value='extrapolate')
    
    return x_interp(t_new), y_interp(t_new)

def text_to_splines(text):
    lines = text.split('\n')  # Split by newlines to handle multiple lines
    splines = []
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
                        x_offset_line += max(x) + space_width  # Fixed space between words

        # Move to next line if the current line exceeds max width
        if x_offset_line > max_width:
            x_offset_line = 0
            y_offset -= line_height  # Move down for the next line

        # Update y_offset for each new line
        y_offset -= line_height

    # Calculate the number of lines
    num_lines = len(lines)
    return splines, num_lines


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        text = request.form.get('text', '')
        splines, num_lines = text_to_splines(text)

        # Determine plot height based on the number of lines
        plot_height = 2 + num_lines * 4  # Adjust the height based on the number of lines
        plt.figure(figsize=(15, plot_height))  # Fixed width, dynamic height
        
        for x, y in splines:
            plt.plot(x, y, c='k')
        plt.axis('off')

        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()
        plt.close()  # Close the figure to free up memory

        return jsonify({'plot_url': plot_url})
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)