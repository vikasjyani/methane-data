import os
import json
from flask import Flask, render_template, send_from_directory, jsonify, request
import generate_tiles
from PIL import Image

app = Flask(__name__)

# Pre-load all parquet files to avoid re-scanning the directory
ALL_PARQUET_FILES = generate_tiles.get_all_parquet_files()
# Cache for min/max data (both global and state-level)
DATA_CACHE = {}

def get_geojson_feature(state_name, district_name=None):
    """Loads the GeoJSON file for a state and returns the specific feature."""
    try:
        filename = f"{state_name.lower().replace(' & ', ' and ')}_districts.geojson"
        filepath = os.path.join('geojson', filename)
        with open(filepath) as f:
            data = json.load(f)

        if district_name:
            for feature in data['features']:
                if feature['properties']['DISTRICT'].upper() == district_name.upper():
                    return feature
            return None
        else:
            return {'type': 'FeatureCollection', 'features': data['features'], 'properties': {'ST_NM': state_name}}
    except FileNotFoundError:
        return None

@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/api/prepare_data')
def prepare_data():
    """Calculates and caches the min/max for a state or global view."""
    state = request.args.get('state')
    year = request.args.get('year', '2023')
    month = request.args.get('month', '12')

    month_str = str(month).zfill(2)
    month_column = f"{year}_{month_str}_01"

    cache_key = f"{state or 'GLOBAL'}-{month_column}"

    if cache_key not in DATA_CACHE:
        print(f"Cache miss for {cache_key}. Calculating min/max...")
        if state:
            min_max_data = generate_tiles.calculate_state_min_max(state, month_column)
        else:
            min_max_data = generate_tiles.calculate_global_min_max(month_column, ALL_PARQUET_FILES)
        DATA_CACHE[cache_key] = min_max_data

    return jsonify(DATA_CACHE[cache_key])

@app.route('/tiles/<int:z>/<int:x>/<int:y>.png')
def serve_tile(z, x, y):
    """Serves a map tile, generating it if it doesn't exist."""
    year = request.args.get('year', '2023')
    month = request.args.get('month', '12')
    state = request.args.get('state')
    district = request.args.get('district')

    month_str = str(month).zfill(2)
    month_column = f"{year}_{month_str}_01"

    geo_filter = None
    geo_name = "GLOBAL"
    if state:
        geo_name = state
        geo_filter = get_geojson_feature(state)
        if district:
            geo_name = f"{state}_{district}"
            geo_filter = get_geojson_feature(state, district)

    geo_name_sanitized = geo_name.replace(' ', '_').replace('&', 'and')
    tile_path_segment = f'{geo_name_sanitized}/{year}/{month}/{z}/{x}/{y}.png'

    if os.path.exists(os.path.join('tiles', tile_path_segment)):
        return send_from_directory('tiles', tile_path_segment)

    cache_key = f"{state or 'GLOBAL'}-{month_column}"
    min_max_data = DATA_CACHE.get(cache_key)

    if not min_max_data or min_max_data.get('min') is None:
        return send_from_directory('static', 'blank_tile.png')

    min_val = min_max_data['min']
    max_val = min_max_data['max']

    print(f"Generating tile {z}/{x}/{y} for {month_column} (State: {state}, District: {district})")
    generate_tiles.generate_tile(z, x, y, month_column, ALL_PARQUET_FILES, min_val, max_val, geo_filter)

    return send_from_directory('tiles', tile_path_segment)

@app.route('/geojson/states')
def get_states_geojson():
    """Serves the GeoJSON file for all Indian states."""
    return send_from_directory('geojson', 'india_states.geojson')

@app.route('/geojson/districts/<state_name>')
def get_districts_geojson(state_name):
    """Serves the GeoJSON file for a specific state's districts."""
    feature = get_geojson_feature(state_name)
    if feature:
        return jsonify(feature)
    return jsonify({"error": "State not found"}), 404

@app.route('/api/stats/<state_name>')
def get_state_stats(state_name):
    """Serves the aggregated statistics for a specific state."""
    filename = f"states/{state_name.lower().replace(' & ', ' and ')}_districts.json"
    try:
        with open(filename) as f:
            data = json.load(f)
        return jsonify(data)
    except FileNotFoundError:
        return jsonify({"error": "Stats not found for state"}), 404

@app.route('/api/metadata')
def get_metadata():
    """Serves the main metadata file."""
    with open('metadata/metadata.json') as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    if not os.path.exists('static/blank_tile.png'):
        img = Image.new('RGBA', (256, 256), (255, 255, 255, 0))
        img.save('static/blank_tile.png')
    app.run(debug=True, port=5001)
