import os
from flask import Flask, render_template, send_from_directory, jsonify, request
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

    # Get year and month from query parameters, with defaults
    year = request.args.get('year', '2023')
    month = request.args.get('month', '12')

    # Format month to be two digits (e.g., 1 -> 01)
    month_str = str(month).zfill(2)
    month_column = f"{year}_{month_str}_01"

    # Define tile path based on date
    tile_dir = f'tiles/{year}/{month}/{z}/{x}'
    tile_path = f'{tile_dir}/{y}.png'

    if not os.path.exists(tile_path):
        print(f"Generating tile {z}/{x}/{y} for {month_column}...")
        # Note: generate_tile now saves the file itself, but we need to create the dated directory
        os.makedirs(tile_dir, exist_ok=True)
        # We pass the full path to generate_tile now
        generate_tiles.generate_tile(z, x, y, month_column, ALL_PARQUET_FILES)

    # The tile should be in the 'tiles' directory, which is at the same level as app.py
    # We need to construct the path from the script's directory
    return send_from_directory('tiles', f'{year}/{month}/{z}/{x}/{y}.png')

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
