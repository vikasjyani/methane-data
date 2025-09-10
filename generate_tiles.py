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

def get_color_for_value(value, min_val=1800, max_val=1900):
    """Maps a methane value to a color from blue to red."""
    if pd.isna(value) or value < min_val:
        return None  # Transparent for no data or low values

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
    """Generates a single map tile for the given zoom, x, y, and month."""

    # Create a blank, transparent tile
    img = Image.new('RGBA', (TILE_SIZE, TILE_SIZE), (255, 255, 255, 0))

    # Get the geographic bounding box for the tile
    lat_min, lon_min, lat_max, lon_max = tile_coords_to_latlon_bbox(z, x, y)

    data_found = False

    for file_path in parquet_files:
        try:
            df = pd.read_parquet(file_path, columns=['latitude', 'longitude', month_column])

            df_in_tile = df[
                (df['latitude'] >= lat_min) & (df['latitude'] <= lat_max) &
                (df['longitude'] >= lon_min) & (df['longitude'] <= lon_max)
            ]

            if not df_in_tile.empty:
                draw = ImageDraw.Draw(img)
                for _, row in df_in_tile.iterrows():
                    color = get_color_for_value(row[month_column])
                    if color:
                        data_found = True
                        tile_x_float, tile_y_float = latlon_to_tile_coords(row['latitude'], row['longitude'], z)
                        pixel_x = int((tile_x_float - x) * TILE_SIZE)
                        pixel_y = int((tile_y_float - y) * TILE_SIZE)
                        draw.rectangle([pixel_x, pixel_y, pixel_x + 1, pixel_y + 1], fill=color)

        except Exception as e:
            pass

    tile_dir = f'tiles/{z}/{x}'
    os.makedirs(tile_dir, exist_ok=True)

    tile_path = f'{tile_dir}/{y}.png'
    img.save(tile_path)
    return tile_path, img, data_found

if __name__ == '__main__':
    print("This script is intended to be used as a module.")
    # Example usage:
    # print("Searching for a tile with data to generate...")
    # all_files = get_all_parquet_files()
    # test_month = '2023_12_01'

    # found_data = False
    # # Loop through some tile coordinates over India at zoom level 5
    # for x in range(24, 28):
    #     for y in range(14, 18):
    #         print(f"Trying tile z=5, x={x}, y={y}...")
    #         tile_path, generated_image, data_found = generate_tile(5, x, y, test_month, all_files)
    #         if data_found:
    #             print(f"\nSUCCESS: Found data and generated tile at: {tile_path}")
    #             found_data = True
    #             break
    #     if found_data:
    #         break

    # if not found_data:
    #     print("\nCould not find any data in the tested tile range.")
