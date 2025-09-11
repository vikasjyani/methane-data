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

@app.route('/tiles/<int:year>/<int:month>/<int:z>/<int:x>/<int:y>.png')
def serve_tile(year, month, z, x, y):
    """Serves a map tile for a given year and month, generating if absent."""
    tile_dir = f'tiles/{year}/{month}/{z}/{x}'
    tile_path = f'{tile_dir}/{y}.png'

    if not os.path.exists(tile_path):
        print(f"Generating tile {year}/{month}/{z}/{x}/{y}...")
        generate_tiles.generate_tile(year, month, z, x, y, ALL_PARQUET_FILES)

    return send_from_directory(tile_dir, f'{y}.png')

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


@app.route('/api/color_range/<int:year>/<int:month>')
def color_range(year, month):
    """Return global min/max methane for legend creation."""
    column = f"{year:04d}_{month:02d}_01"
    min_val, max_val = generate_tiles.get_global_min_max(column, tuple(ALL_PARQUET_FILES))
    return jsonify({'min': min_val, 'max': max_val})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
