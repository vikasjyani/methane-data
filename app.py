import os
from flask import Flask, render_template, send_from_directory, jsonify
import generate_tiles
import json

app = Flask(__name__)

# Pre-load all parquet files to avoid re-scanning the directory on every tile request
ALL_PARQUET_FILES = generate_tiles.get_all_parquet_files()

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/tiles/<int:z>/<int:x>/<int:y>.png')
def serve_tile(z, x, y):
    """Serves a map tile, generating it if it doesn't exist."""
    tile_path = f'tiles/{z}/{x}/{y}.png'

    if not os.path.exists(tile_path):
        # For now, we'll hardcode the month. This will be made dynamic later.
        month_column = '2023_12_01'
        print(f"Generating tile {z}/{x}/{y} for {month_column}...")
        generate_tiles.generate_tile(z, x, y, month_column, ALL_PARQUET_FILES)

    # The tile should be in the 'tiles' directory, which is at the same level as app.py
    # We need to construct the path from the script's directory
    return send_from_directory('tiles', f'{z}/{x}/{y}.png')

@app.route('/geojson/states')
def get_states_geojson():
    """Serves the GeoJSON file for all Indian states."""
    return send_from_directory('geojson', 'india_states.geojson')

@app.route('/geojson/districts/<state_name>')
def get_districts_geojson(state_name):
    """Serves the GeoJSON file for a specific state's districts."""
    filename = f"{state_name.lower().replace(' & ', ' and ')}_districts.geojson"
    return send_from_directory('geojson', filename)

@app.route('/api/stats/<state_name>')
def get_state_stats(state_name):
    """Serves the aggregated statistics for a specific state."""
    filename = f"states/{state_name.lower().replace(' & ', ' and ')}_districts.json"
    with open(filename) as f:
        data = json.load(f)
    return jsonify(data)

@app.route('/api/metadata')
def get_metadata():
    """Serves the main metadata file."""
    with open('metadata/metadata.json') as f:
        data = json.load(f)
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
