import math
import os
import pandas as pd
from PIL import Image, ImageDraw

TILE_SIZE = 256
DATA_DIR = 'data_parquet'

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
        return None  # Transparent for no data

    if max_val == min_val:
        # If all values are the same, return a mid-range color
        return (255, 0, 0, 150) # Red

    # Normalize value to 0-1 range
    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0, min(1, normalized)) # Clamp between 0 and 1

    # Simple blue to red gradient
    red = int(255 * normalized)
    blue = int(255 * (1 - normalized))
    return (red, 0, blue, 150) # RGBA with some transparency

def get_all_parquet_files():
    """Returns a list of all .parquet files in the data directory."""
    parquet_files = []
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith('.parquet'):
                parquet_files.append(os.path.join(root, file))
    return parquet_files

def generate_tile(z, x, y, month_column, parquet_files):
    """Generates a single map tile with a dynamic color gradient."""

    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (255, 255, 255, 0))
    lat_min, lon_min, lat_max, lon_max = tile_coords_to_latlon_bbox(z, x, y)

    # Pass 1: Collect all data points for the tile
    tile_data_points = []
    for file_path in parquet_files:
        try:
            df = pd.read_parquet(file_path, columns=['latitude', 'longitude', month_column])
            df_in_tile = df[
                (df['latitude'] >= lat_min) & (df['latitude'] <= lat_max) &
                (df['longitude'] >= lon_min) & (df['longitude'] <= lon_max)
            ]
            if not df_in_tile.empty:
                # Keep only non-null values for the month
                df_in_tile = df_in_tile.dropna(subset=[month_column])
                if not df_in_tile.empty:
                    tile_data_points.extend(df_in_tile.to_dict('records'))
        except (KeyError, ValueError):
            # Ignore files that don't have the month_column or other read errors
            pass

    # Proceed only if we have data for the tile
    if tile_data_points:
        # Calculate dynamic min and max for this tile
        values = [p[month_column] for p in tile_data_points]
        min_val = min(values)
        max_val = max(values)

        # Pass 2: Draw the points with the dynamic gradient
        draw = ImageDraw.Draw(img)
        for point in tile_data_points:
            color = get_color_for_value(point[month_column], min_val, max_val)
            if color:
                tile_x_float, tile_y_float = latlon_to_tile_coords(point['latitude'], point['longitude'], z)
                pixel_x = int((tile_x_float - x) * TILE_SIZE)
                pixel_y = int((tile_y_float - y) * TILE_SIZE)
                draw.rectangle([pixel_x, pixel_y, pixel_x + 1, pixel_y + 1], fill=color)

    # Save the tile image
    year, month, _ = month_column.split('_')
    tile_dir = f'tiles/{year}/{month}/{z}/{x}'
    os.makedirs(tile_dir, exist_ok=True)
    tile_path = f'{tile_dir}/{y}.png'
    img.save(tile_path)

    # Return the image object for debugging if needed
    return tile_path, img, bool(tile_data_points)

if __name__ == '__main__':
    print("This script is intended to be used as a module.")
