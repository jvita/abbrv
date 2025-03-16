from flask import Flask, render_template, request, jsonify, session
import json
import os
import zipfile

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

# @app.route('/available_systems', methods=['GET'])
# def available_systems():
#     system_names = []
#     for filename in os.listdir(SYSTEMS_FOLDER):
#         if filename.endswith('.zip'):
#             name = filename.replace('.zip', '')  # Get the system name (without the .zip extension)
#             system_names.append(name)
#     return jsonify(system_names)

# @app.route('/load_system_data/<system_name>', methods=['GET'])
# def load_system_data(system_name):
#     get_data()  # force re-load from zip files
#     # This only sends the data for local download

#     global systems
#     if system_name in systems:
#         return jsonify(systems[system_name])  # Return the system data as JSON
#     else:
#         return jsonify({'error': 'System not found'}), 404

# @app.route('/save_system/<system_name>', methods=['POST'])
# def save_system(system_name):
#     # Parse the incoming JSON data
#     system_dict = request.json

#     systems[system_name] = system_dict

#     # Ensure the dictionary has the required keys
#     required_keys = ['glyphs', 'modes', 'rules', 'phrases']
#     for key in required_keys:
#         if key not in system_dict:
#             return jsonify({"error": f"Missing key: {key}"}), 400

#     # Create the static/data/systems directory if it doesn't exist
#     output_dir = os.path.join('static', 'data', 'systems')
#     os.makedirs(output_dir, exist_ok=True)

#     # Path for the ZIP file
#     zip_filename = os.path.join(output_dir, f'{system_name}.zip')

#     # Create a temporary directory to store the JSON files
#     temp_dir = 'temp_json_files'
#     os.makedirs(temp_dir, exist_ok=True)

#     try:
#         # Save each entry as a JSON file
#         for key in required_keys:
#             file_path = os.path.join(temp_dir, f'{key}.json')
#             with open(file_path, 'w') as f:
#                 json.dump(system_dict[key], f, indent=4)

#         # Create a ZIP file and add the JSON files to it
#         with zipfile.ZipFile(zip_filename, 'w') as zipf:
#             for key in required_keys:
#                 file_path = os.path.join(temp_dir, f'{key}.json')
#                 zipf.write(file_path, arcname=f'{key}.json')

#         return jsonify({"message": f"System saved as {system_name}.zip"}), 200

#     finally:
#         # Clean up the temporary directory and files
#         for key in required_keys:
#             file_path = os.path.join(temp_dir, f'{key}.json')
#             if os.path.exists(file_path):
#                 os.remove(file_path)
#         os.rmdir(temp_dir)

# def get_data():
#     global systems

#     # Loop through all files in DATA_FOLDER
#     for filename in os.listdir(SYSTEMS_FOLDER):
#         if filename.endswith('.zip'):
#             system_name = filename.replace('.zip', '')  # Get the system name (without the .zip extension)
#             systems[system_name] = {}

#             # Open the zip file
#             zip_path = os.path.join(SYSTEMS_FOLDER, filename)
#             with zipfile.ZipFile(zip_path, 'r') as zf:
#                 # Iterate over each file inside the zip (skip directories)
#                 for zip_info in zf.infolist():
#                     if not zip_info.is_dir():  # Only process files, not directories
#                         with zf.open(zip_info) as file:
#                             file_content = file.read().decode('utf-8')  # Assuming the files are in text (JSON)
#                             parsed_data = json.loads(file_content)  # Parse the JSON file

#                             # Store data based on the filename
#                             if 'glyphs' in zip_info.filename:
#                                 systems[system_name]['glyphs'] = parsed_data
#                             elif 'phrases' in zip_info.filename:
#                                 systems[system_name]['phrases'] = parsed_data
#                             elif 'modes' in zip_info.filename:
#                                 systems[system_name]['modes'] = parsed_data
#                             elif 'rules' in zip_info.filename:
#                                 systems[system_name]['rules'] = parsed_data

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
    # get_data()
    app.run(debug=True)
