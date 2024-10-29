from flask import Flask, render_template, request, jsonify, session, Response
import numpy as np
import json
from scipy.interpolate import CubicSpline, BSpline
import os
import re
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import io

app = Flask(__name__)

# from flask_debugtoolbar import DebugToolbarExtension
# app.config['SECRET_KEY'] = 'lorem ipsum'
# app.config['DEBUG_TB_PROFILER_ENABLED'] = True  # Enable the profiler
# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False  # Optional: avoid toolbar intercepting redirects

# app.debug = True  # Required for debug toolbar to work
# toolbar = DebugToolbarExtension(app)

# File paths for single-character and multi-character splines
SYSTEMS_FOLDER = 'static/data/systems'
current_system = None
systems = {}

@app.route('/spline', methods=['POST'])
def spline():
    points = request.json['points']
    if not points:
        return jsonify({'spline': []})

    points = np.array(points)
    x = points[:, 0] * 152 - 76
    y = points[:, 1] * 152 - 76
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

@app.route('/set_selected_system', methods=['POST'])
def set_selected_system():
    system = request.json.get('system')
    session['selected_system'] = system  # Store the selected system in the session
    return jsonify(success=True)

@app.route('/available_systems', methods=['GET'])
def available_systems():
    system_names = []
    for filename in os.listdir(SYSTEMS_FOLDER):
        if filename.endswith('.zip'):
            name = filename.replace('.zip', '')  # Get the system name (without the .zip extension)
            system_names.append(name)
    return jsonify(system_names)

@app.route('/load_system_data/<system_name>', methods=['GET'])
def load_system_data(system_name):
    # This only sends the data for local download

    global systems
    if system_name in systems:
        return jsonify(systems[system_name])  # Return the system data as JSON
    else:
        return jsonify({'error': 'System not found'}), 404

@app.route('/save_system/<system_name>', methods=['POST'])
def save_system(system_name):
    # Parse the incoming JSON data
    system_dict = request.json

    systems[system_name] = system_dict

    # Ensure the dictionary has the required keys
    required_keys = ['glyphs', 'modes', 'rules', 'phrases']
    for key in required_keys:
        if key not in system_dict:
            return jsonify({"error": f"Missing key: {key}"}), 400

    # Create the static/data/systems directory if it doesn't exist
    output_dir = os.path.join('static', 'data', 'systems')
    os.makedirs(output_dir, exist_ok=True)

    # Path for the ZIP file
    zip_filename = os.path.join(output_dir, f'{system_name}.zip')

    # Create a temporary directory to store the JSON files
    temp_dir = 'temp_json_files'
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Save each entry as a JSON file
        for key in required_keys:
            file_path = os.path.join(temp_dir, f'{key}.json')
            with open(file_path, 'w') as f:
                json.dump(system_dict[key], f, indent=4)

        # Create a ZIP file and add the JSON files to it
        with zipfile.ZipFile(zip_filename, 'w') as zipf:
            for key in required_keys:
                file_path = os.path.join(temp_dir, f'{key}.json')
                zipf.write(file_path, arcname=f'{key}.json')

        return jsonify({"message": f"System saved as {system_name}.zip"}), 200

    finally:
        # Clean up the temporary directory and files
        for key in required_keys:
            file_path = os.path.join(temp_dir, f'{key}.json')
            if os.path.exists(file_path):
                os.remove(file_path)
        os.rmdir(temp_dir)

# Writer code
def load_json_file(filename):
    if not os.path.isfile(filename):
        with open(filename, 'w') as f:
            f.write(json.dumps({}))

    with open(filename, 'r') as f:
        return json.load(f)

def get_data():
    global systems

    # Loop through all files in DATA_FOLDER
    for filename in os.listdir(SYSTEMS_FOLDER):
        if filename.endswith('.zip'):
            system_name = filename.replace('.zip', '')  # Get the system name (without the .zip extension)
            systems[system_name] = {}

            # Open the zip file
            zip_path = os.path.join(SYSTEMS_FOLDER, filename)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # Iterate over each file inside the zip (skip directories)
                for zip_info in zf.infolist():
                    if not zip_info.is_dir():  # Only process files, not directories
                        with zf.open(zip_info) as file:
                            file_content = file.read().decode('utf-8')  # Assuming the files are in text (JSON)
                            parsed_data = json.loads(file_content)  # Parse the JSON file

                            # Store data based on the filename
                            if 'glyphs' in zip_info.filename:
                                systems[system_name]['glyphs'] = parsed_data
                            elif 'phrases' in zip_info.filename:
                                systems[system_name]['phrases'] = parsed_data
                            elif 'modes' in zip_info.filename:
                                systems[system_name]['modes'] = parsed_data
                            elif 'rules' in zip_info.filename:
                                systems[system_name]['rules'] = parsed_data

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

def split_text_with_linebreaks(text, max_width):
    # Split by lines first to preserve existing line breaks
    lines = text.splitlines()
    result = []

    for line in lines:
        # words = line.split()
        words = split_into_words(line)
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

def add_spaces_around_punctuation(text):
    # Define a regex pattern to match punctuation and digits
    pattern = r'(\d|[!\"#$%&\'()*+,-./:;<=>?@[\\\]^_`{|}~])'

    # Substitute with spaces before and after the matched characters
    spaced_text = re.sub(pattern, r' \1 ', text)

    # Return the modified text, stripping any extra spaces at the ends
    return spaced_text.strip()

def process_text(text, applied_rules, system):

    text = text.lower()

    # remove unsupported punctuation
    for p in ["'"]:
        text = text.replace(p, '')
    for p in ['/', '\\', '-']:
        text = text.replace(p, ' ')

    text = add_spaces_around_punctuation(text)

    # Apply all user-defined rules
    for rule in system['rules']:
        if rule['name'] not in applied_rules: continue

        text = re.sub(rule["regex"], rule["replacement"], text)

    # Also apply the rules to phrases_dict so that it detects the modified phrases
    modified_phrases_dict = {}

    for k, v in system['phrases'].items():
        for rule in system['rules']:
            if rule['name'] not in applied_rules: continue

            k = re.sub(rule["regex"], rule["replacement"], k)

        modified_phrases_dict[k] = v

    return text, modified_phrases_dict

def tokenize_string(word, system):
    """
    Tokenizes a single word using a dictionary of regular expressions and corresponding lists of arrays.
    The function searches for the tokenization with the fewest possible tokens and prioritizes the largest actual match.
    If multiple tokenizations have the same number of tokens, it prioritizes the largest token.
    If tokenizations have the same largest token, it prioritizes the one using the longest regex pattern for that token.
    If regex patterns for the largest token are the same length, it checks the lengths of regex patterns for the remaining tokens.
    """
    # Pre-compile all regular expressions for efficiency
    regex_dict = {k: v for k, v in list(system['glyphs'].items())[17:]}
    regex_dict.update({
        v['pattern']: v['points'] for v in system['modes'].values()
    })
    regex_dict = {re.compile(pattern): value for pattern, value in regex_dict.items()}

    # Cache results to avoid recalculating for the same word (Memoization)
    memo = {}

    def compare_regex_lengths(tokenization_a, tokenization_b):
        """Helper function to compare regex pattern lengths for two tokenizations."""
        for (regex_a, regex_b) in zip(tokenization_a, tokenization_b):
            if len(regex_a) != len(regex_b):
                return len(regex_a) > len(regex_b)
        return False  # If all regexes are the same length, consider them equal

    def find_best_tokenization(start):
        # Base case: if we've reached the end of the word, return an empty list
        if start == len(word):
            return [], 0, 0, []  # (tokenization, number of tokens, length of largest token, list of regex patterns)

        # If this start point is already computed, return the cached result
        if start in memo:
            return memo[start]

        best_tokenization = None
        fewest_tokens = float('inf')
        longest_token_length = 0
        regex_list_for_best_tokenization = []

        # Try to find the best match at this starting point
        for pattern, array_list in regex_dict.items():
            match = pattern.match(word, start)
            if match:
                match_length = len(match.group())
                remaining_tokens, remaining_count, largest_remaining_token, remaining_regex_list = find_best_tokenization(start + match_length)

                current_largest_token = max(match_length, largest_remaining_token)
                current_regex_list = [pattern.pattern] + remaining_regex_list
                candidate_tokenization = [array_list] + remaining_tokens

                candidate_token_count = 1 + remaining_count

                # Select candidate with fewer tokens
                if candidate_token_count < fewest_tokens:
                    fewest_tokens = candidate_token_count
                    longest_token_length = current_largest_token
                    regex_list_for_best_tokenization = current_regex_list
                    best_tokenization = candidate_tokenization

                # If the same number of tokens, select the one with the longest single token
                elif candidate_token_count == fewest_tokens:
                    if current_largest_token > longest_token_length:
                        longest_token_length = current_largest_token
                        regex_list_for_best_tokenization = current_regex_list
                        best_tokenization = candidate_tokenization
                    # If the largest token length is the same, check regex length for the largest token
                    elif current_largest_token == longest_token_length:
                        # If the first regex is longer, prefer this tokenization
                        if len(current_regex_list[0]) > len(regex_list_for_best_tokenization[0]):
                            regex_list_for_best_tokenization = current_regex_list
                            best_tokenization = candidate_tokenization
                        # If the first regex is the same length, compare subsequent regex patterns
                        elif len(current_regex_list[0]) == len(regex_list_for_best_tokenization[0]):
                            if compare_regex_lengths(current_regex_list, regex_list_for_best_tokenization):
                                regex_list_for_best_tokenization = current_regex_list
                                best_tokenization = candidate_tokenization

        # Cache the result
        memo[start] = (best_tokenization, fewest_tokens, longest_token_length, regex_list_for_best_tokenization)
        return memo[start]

    # Start the recursive search from the beginning of the word
    final_tokenization, _, _, _ = find_best_tokenization(0)
    return final_tokenization
    
def tokenize_with_multi_words(text, system, multi_word_tokens, abbrv_words=False):
    """
    Tokenizes the text by first finding multi-word tokens, then tokenizing the remaining words.
    Returns a list of lists, where each inner list contains tokens for one word or phrase.
    """

    regex_list = list(system['glyphs'].keys())[17:]
    regex_list += [p['pattern'] for p in system['modes'].values()]

    # Step 1: Find multi-word tokens
    if abbrv_words:
        text_with_placeholders, multi_word_matches = find_multi_word_tokens(text, multi_word_tokens)
    else:
        text_with_placeholders = text
        multi_word_matches = []

    # Step 2: Tokenize remaining single words using tokenize_string()
    remaining_words = text_with_placeholders.split()
    all_tokens = []
    
    for word in remaining_words:
        if word == "§":
            # This is a placeholder for a multi-word token
            all_tokens.append(system['phrases'][multi_word_matches.pop(0)])  # Keep multi-word as a single token list
        else:
            # Tokenize the remaining word and append the token list for that word
            all_tokens.extend([tokenize_string(word, system)])

    return all_tokens

def find_multi_word_tokens(text, multi_word_tokens):
    """
    Finds and extracts multi-word tokens from the text.
    Returns the text with multi-word tokens replaced by placeholders and the list of multi-word matches.
    """
    matches = []
    # Escape special regex characters in the multi-word tokens
    escaped_tokens = [re.escape(token) for token in multi_word_tokens]
    
    # Create a regex pattern that matches any of the multi-word tokens
    multi_word_pattern = re.compile(r'\b(' + '|'.join(escaped_tokens) + r')\b')
    
    # Replace multi-word tokens with a placeholder and store them in the matches list
    def replace_multi_word(match):
        matches.append(match.group())  # tokenization should be a list of lists
        return "§"  # Placeholder for multi-word token

    # Replace multi-word tokens in the text
    new_text = multi_word_pattern.sub(replace_multi_word, text)
    
    return new_text, matches

def tokens_to_splines(tokens, token_map):

    splines = []
    for word_tokens in tokens:
        tmp = []
        for t in word_tokens:
            tmp.extend(token_map[t])
        splines.append(tmp)

    return splines

def merge_word_splines(text_splines):
    # Initialize a list to store the concatenated points for each word
    words = []

    print(f'{len(text_splines)=}')

    # Initialize the shift to [0, 0] for the first character
    for word_splines in text_splines:
        print(f'{len(word_splines)=}')
        current_word = []
        current_shift = np.array([0, 0])
        # Process each array in the list of arrays for the current character
        for gi, glyph_splines in enumerate(word_splines):
            print(f'{len(glyph_splines)=}')
            for points in glyph_splines:
                print(f'{points=}')
                shifted_points = np.array(points)
                if gi != 0:
                    # If not the first character in the word, shift the first array so that its first point is at [0, 0]
                    # shifted_points -= shifted_points[0]
                    shifted_points -= glyph_splines[0][0]
                current_word.append(shifted_points + current_shift)

        # Update the shift to the last point of the last array in the current character
            current_shift = current_word[-1][-1]  # Last point of the last array

        words.append(current_word)  # Add the current word to the words list

    return words


@app.route('/generate_splines/<system_name>', methods=['POST'])
def generate_splines(system_name):
    """
    Plots words as splines, handles line breaks by shifting each line downward.

    - text: Input text from user.
    - space_between_words: Horizontal space between words.
    - line_spacing: Vertical space between lines.
    """

    text = request.form['text']
    if not text:
        return jsonify({'image': None})

    space_between_words, line_spacing = 0.2, 0.2

    client_system = json.loads(request.form.get('system'))

    # all_mappings = client_system['glyphs']
    # all_mappings.update(client_system['phrases'])
    # all_mappings.update(
    #     {v['pattern']: v['points'] for v in client_system['modes'].values()}
    #     )
    
    # all_mappings = {
    #     k: [np.array(p) for p in l] for k,l in all_mappings.items()
    # }

    abbrv_words = 'abbrv_words' in request.form
    show_dots = 'show_dots' in request.form
    show_knots = 'show_knot_points' in request.form
    show_baselines = 'show_baselines' in request.form
    modes = request.form.getlist('modes')
    client_system['modes'] = {k:v for k,v in client_system['modes'].items() if k in modes}
    rules = request.form.getlist('rules')

    text, modified_phrases_dict = process_text(text, rules, client_system)

    plt.figure(figsize=(8, 8))  # Initialize figure

    # Variables to track positions for each line
    current_vertical_offset, right_most_point, left_most_point = 0, 0, 0
    line_positions = []  # Store y-positions of each line

    # Process each line of the text
    for line in text.splitlines():
        if not len(line):  # empty line
            current_vertical_offset -= line_spacing
            continue

        splines = tokenize_with_multi_words(
            line, client_system, modified_phrases_dict, abbrv_words
            )

        word_splines = merge_word_splines(splines)

        current_shift = np.array([0, 0])
        line_x_pos, splines_to_plot = 0, []

        # Process each word in the line
        for word in word_splines:
            xmin = word[0][:, 0].min()

            for points in word:
                shifted_points = points
                shifted_points[:, 0] -= xmin  # handle negative shift in first char
                shifted_points += current_shift

                # Update line and overall horizontal boundaries
                line_x_pos = max(shifted_points[:, 0].max(), line_x_pos)
                right_most_point = max(shifted_points[:, 0].max(), right_most_point)
                left_most_point = min(shifted_points[:, 0].min(), left_most_point)

                splines_to_plot.append(shifted_points)

            # Shift for the next word
            current_shift = np.array([line_x_pos + space_between_words, 0])

        # Calculate vertical bounds for current line
        highest_point_current_line = max(p[:, 1].max() for p in splines_to_plot)
        lowest_point_current_line = min(p[:, 1].min() for p in splines_to_plot)

        # Adjust vertical offset for the current line
        current_vertical_offset -= highest_point_current_line

        # Plot the splines for this lini
        for points in splines_to_plot:
            shifted_points = points + np.array([0, current_vertical_offset])
            plot_spline(shifted_points, show_dots, show_knots)  # Reusable plot helper function

        # Adjust vertical offset for the next line
        line_positions.append(current_vertical_offset)
        current_vertical_offset += lowest_point_current_line - line_spacing

    xlims = [left_most_point - space_between_words, right_most_point + space_between_words]

    if show_baselines:
        # Plot baseline for each line
        plot_baselines(line_positions, xlims)

    plt.xlim(xlims)
    plt.gca().set_aspect('equal', adjustable='box')
    plt.axis('off')
    # Save and return the SVG plot
    return jsonify({'image': save_plot_as_svg()})

# Helper functions
def plot_spline(points, show_dots=True, show_knots=False):
    """Plots individual splines."""
    if points.shape[0] == 1 and show_dots:
        plt.plot(points[:, 0], points[:, 1], 'ko', markersize=1.0)
    else:
        x, y = interpolate_points(points)
        plt.plot(x, y, 'k', linewidth=2, solid_capstyle='round')

    if show_knots:
        plt.plot(points[:, 0], points[:, 1], 'ro', markersize=3.0)


def plot_baselines(line_positions, xlims):
    """Plots light-grey baselines for each line."""
    for v in line_positions:
        plt.plot(xlims, [v, v], '--', color='lightgrey', zorder=0)


def save_plot_as_svg():
    """Saves the current plot as an SVG and returns its content."""
    img = io.BytesIO()
    plt.savefig(img, format='svg', bbox_inches='tight')
    img.seek(0)
    svg_content = img.getvalue().decode()
    plt.close()  # Close the figure after saving to free memory
    return svg_content

@app.route('/')
@app.route('/write')
def write():
    return render_template('writer.html')

@app.route('/draft')
def draft():
    # execute_on_refresh()
    return render_template('drafter.html')

@app.route('/rules')
def rules():
    # execute_on_refresh()
    return render_template('rules.html')

@app.route('/help')
def help():
    # execute_on_refresh()
    return render_template('help.html')


if __name__ == '__main__':
    get_data()
    app.run(debug=True)
