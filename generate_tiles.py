"""Utility to generate raster tiles from district Parquet files.

Usage:
    python generate_tiles.py 2014 1 --outdir tiles
This will read all Parquet files under ``data_parquet`` and produce
GeoTIFFs and PNG tiles for January 2014.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import rasterio
from rasterio.transform import from_origin
from rasterio.features import rasterize

GRID_RES = 0.01  # degrees per pixel
NODATA = -9999.0


def get_all_parquet_files(base_dir: str = "data_parquet"):
    """Yield every Parquet file under ``base_dir``."""
    for root, _, files in os.walk(base_dir):
        for f in files:
            if f.endswith(".parquet"):
                yield Path(root) / f


def rasterize_parquet(parquet_path: Path, date_col: str, out_tif: Path) -> Path:
    """Rasterize a single Parquet file for ``date_col``.

    Parameters
    ----------
    parquet_path: Path
        Input Parquet file containing ``latitude``, ``longitude`` and a column
        named like ``YYYY_MM_DD``.
    date_col: str
        Column to rasterize (e.g. ``"2014_01_01"``).
    out_tif: Path
        Output GeoTIFF path.
    """
    df = pd.read_parquet(parquet_path)
    if date_col not in df.columns:
        raise ValueError(f"{date_col} not found in {parquet_path}")

    df = df[["latitude", "longitude", date_col]].rename(
        columns={"latitude": "lat", "longitude": "lon", date_col: "value"}
    )
    df.dropna(subset=["lat", "lon"], inplace=True)

    geometry = [Point(xy) for xy in zip(df["lon"], df["lat"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    x_res = y_res = GRID_RES
    minx, miny, maxx, maxy = gdf.total_bounds
    minx -= x_res / 2
    maxx += x_res / 2
    miny -= y_res / 2
    maxy += y_res / 2

    width = int(np.ceil((maxx - minx) / x_res))
    height = int(np.ceil((maxy - miny) / y_res))
    transform = from_origin(minx, maxy, x_res, y_res)

    shapes = ((geom, val) for geom, val in zip(gdf.geometry, gdf["value"]))
    raster_data = np.full((height, width), NODATA, dtype=np.float32)
    raster = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=NODATA,
        out=raster_data,
        dtype=np.float32,
    )

    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": raster.dtype,
        "crs": "EPSG:4326",
        "transform": transform,
        "nodata": NODATA,
    }
    out_tif.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_tif, "w", **meta) as dst:
        dst.write(raster, 1)
    return out_tif


def tiles_from_tif(tif_path: Path, out_dir: Path, zoom: str = "0-5") -> None:
    """Generate XYZ tiles from ``tif_path`` using ``gdal2tiles.py``."""
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["gdal2tiles.py", "-z", str(zoom), str(tif_path), str(out_dir)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, help="Year, e.g. 2014")
    parser.add_argument("month", type=int, help="Month number (1-12)")
    parser.add_argument("--outdir", default="tiles", help="Output directory")
    parser.add_argument("--zoom", default="0-5", help="Zoom levels for gdal2tiles")
    args = parser.parse_args()

    date_col = f"{args.year}_{args.month:02d}_01"
    outdir = Path(args.outdir) / str(args.year) / f"{args.month:02d}"

    for pq in get_all_parquet_files():
        district = pq.stem
        tif_path = outdir / f"{district}.tif"
        tile_dir = outdir / district
        rasterize_parquet(pq, date_col, tif_path)
        tiles_from_tif(tif_path, tile_dir, args.zoom)


if __name__ == "__main__":
    main()
