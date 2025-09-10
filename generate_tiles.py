import math
import os
import json
import pandas as pd
from PIL import Image, ImageDraw
from shapely.geometry import shape, Point

TILE_SIZE = 256
DATA_DIR = 'data_parquet'
GEOJSON_DIR = 'geojson'

def latlon_to_tile_coords(lat, lon, zoom):
    """Converts latitude and longitude to tile coordinates at a given zoom level."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = (lon + 180.0) / 360.0 * n
    ytile = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return xtile, ytile

def tile_coords_to_latlon_bbox(z, x, y):
    """Calculates the geographic bounding box for a given tile coordinate."""
    n = 2.0 ** z
    lon_deg_w = x / n * 360.0 - 180.0
    lon_deg_e = (x + 1) / n * 360.0 - 180.0
    lat_rad_n = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_rad_s = math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n)))
    lat_deg_n = math.degrees(lat_rad_n)
    lat_deg_s = math.degrees(lat_rad_s)
    return (lat_deg_s, lon_deg_w, lat_deg_n, lon_deg_e)

def get_color_for_value(value, min_val, max_val):
    """Maps a methane value to a color from blue to red based on a dynamic range."""
    if pd.isna(value):
        return None

    if max_val == min_val:
        return (255, 0, 0, 150) # Default to red if all values are the same

    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0, min(1, normalized))

    # Use a more informative color gradient: blue -> cyan -> lime -> yellow -> red
    if normalized < 0.25:
        # Blue to Cyan
        g = int(255 * (normalized / 0.25))
        return (0, g, 255, 150)
    elif normalized < 0.5:
        # Cyan to Lime
        b = int(255 * (1 - (normalized - 0.25) / 0.25))
        return (0, 255, b, 150)
    elif normalized < 0.75:
        # Lime to Yellow
        r = int(255 * ((normalized - 0.5) / 0.25))
        return (r, 255, 0, 150)
    else:
        # Yellow to Red
        g = int(255 * (1 - (normalized - 0.75) / 0.25))
        return (255, g, 0, 150)


def get_all_parquet_files():
    """Returns a list of all .parquet files in the data directory."""
    parquet_files = []
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith('.parquet'):
                parquet_files.append(os.path.join(root, file))
    return parquet_files

def calculate_global_min_max(month_column, all_files):
    """Calculates the min and max methane values for the entire dataset for a given month."""
    all_values = []
    for file_path in all_files:
        try:
            df = pd.read_parquet(file_path, columns=[month_column])
            all_values.extend(df[month_column].dropna().tolist())
        except (KeyError, ValueError):
            pass

    if not all_values:
        return {'min': None, 'max': None}

    return {'min': min(all_values), 'max': max(all_values)}


def calculate_state_min_max(state_name, month_column):
    """Calculates the min and max methane values for a given state and month."""
    state_dir = os.path.join(DATA_DIR, state_name)
    if not os.path.isdir(state_dir):
        return {'min': None, 'max': None}

    all_values = []
    for district_file in os.listdir(state_dir):
        if district_file.endswith('.parquet'):
            file_path = os.path.join(state_dir, district_file)
            try:
                df = pd.read_parquet(file_path, columns=[month_column])
                all_values.extend(df[month_column].dropna().tolist())
            except (KeyError, ValueError):
                pass

    if not all_values:
        return {'min': None, 'max': None}

    return {'min': min(all_values), 'max': max(all_values)}

def generate_tile(z, x, y, month_column, parquet_files, min_val, max_val, geo_filter=None):
    """
    Generates a single map tile, optionally clipped to a specific geography,
    using a pre-calculated min/max range for coloring.
    """
    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (255, 255, 255, 0))
    lat_min, lon_min, lat_max, lon_max = tile_coords_to_latlon_bbox(z, x, y)

    filter_shape = shape(geo_filter['geometry']) if geo_filter and 'geometry' in geo_filter else None

    # Single pass to collect and draw points
    for file_path in parquet_files:
        try:
            df = pd.read_parquet(file_path, columns=['latitude', 'longitude', month_column])
            df_in_tile = df[
                (df['latitude'] >= lat_min) & (df['latitude'] <= lat_max) &
                (df['longitude'] >= lon_min) & (df['longitude'] <= lon_max)
            ].dropna(subset=[month_column])

            if df_in_tile.empty:
                continue

            # Perform geographic filtering if a shape is provided
            if filter_shape:
                points = [Point(lon, lat) for lon, lat in zip(df_in_tile['longitude'], df_in_tile['latitude'])]
                mask = [filter_shape.contains(p) for p in points]
                df_in_tile = df_in_tile[mask]

            if not df_in_tile.empty:
                draw = ImageDraw.Draw(img)
                for _, row in df_in_tile.iterrows():
                    color = get_color_for_value(row[month_column], min_val, max_val)
                    if color:
                        tile_x_float, tile_y_float = latlon_to_tile_coords(row['latitude'], row['longitude'], z)
                        pixel_x = int((tile_x_float - x) * TILE_SIZE)
                        pixel_y = int((tile_y_float - y) * TILE_SIZE)
                        draw.rectangle([pixel_x, pixel_y, pixel_x + 1, pixel_y + 1], fill=color)
        except (KeyError, ValueError):
            pass

    # Determine save path based on geography
    year, month, _ = month_column.split('_')
    geo_name = "GLOBAL"
    if geo_filter and 'properties' in geo_filter:
        props = geo_filter['properties']
        if 'DISTRICT' in props:
            geo_name = f"{props['ST_NM']}_{props['DISTRICT']}"
        elif 'ST_NM' in props:
            geo_name = props['ST_NM']
    geo_name = geo_name.replace(' ', '_').replace('&', 'and')

    tile_dir = f'tiles/{geo_name}/{year}/{month}/{z}/{x}'
    os.makedirs(tile_dir, exist_ok=True)
    tile_path = f'{tile_dir}/{y}.png'
    img.save(tile_path)

    return tile_path, img

if __name__ == '__main__':
    print("This script is intended to be used as a module.")
