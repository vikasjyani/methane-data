"""Flask application serving methane tiles and boundary data."""
from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, render_template, send_from_directory
import geopandas as gpd

APP = Flask(__name__)

BOUNDARY_FILE = Path("DISTRICTs_Corrected") / "DISTRICTs_Corrected.shp"
TILES_DIR = Path("tiles")


@APP.route("/")
def index():
    """Render the Leaflet frontend."""
    return render_template("index.html")


@APP.route("/tiles/<path:filename>")
def tiles(filename: str):
    """Serve pre-generated PNG tiles."""
    return send_from_directory(TILES_DIR, filename)


@APP.route("/geojson/districts")
def geojson_districts():
    """Return all district boundaries as GeoJSON."""
    gdf = gpd.read_file(BOUNDARY_FILE)
    return gdf.to_json()


@APP.route("/metadata/available")
def metadata_available():
    """List available years and months based on tile directory structure."""
    years = sorted({p.parent.parent.name for p in TILES_DIR.rglob("*.png")})
    months = sorted({p.parent.name for p in TILES_DIR.rglob("*.png")})
    return jsonify({"years": years, "months": months})


if __name__ == "__main__":
    APP.run(debug=True)
