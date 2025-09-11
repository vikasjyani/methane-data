# Methane Data Visualization

This web application provides an interactive map to visualize methane gas concentration data across India from 2014 to 2023. Users can explore the data by zooming in on the map and selecting states and districts directly on the map to view detailed statistics.

## Features

- **Interactive Map**: A tile-based map of India using Leaflet.js.
- **Data Layers**: Methane concentration data is overlaid on the map, with colors representing the intensity of emissions.
- **State and District Selection**: Click on any state and then on a district to view detailed information and trends.
- **Dynamic Statistics**: A panel that displays methane statistics for the selected region.
- **On-the-Fly Tile Generation**: Map tiles are generated from the source Parquet data and cached for performance.
- **Time-Series Animation**: Play through months and years to watch methane patterns evolve.

## How to Run

1.  **Install Dependencies**:
    Make sure you have Python 3 and `pip` installed. Then, install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Application**:
    Start the Flask web server with the following command:
    ```bash
    python app.py
    ```

3.  **View in Browser**:
    Open your web browser and navigate to:
    [http://127.0.0.1:5001/](http://127.0.0.1:5001/)

## Project Structure

-   `app.py`: The main Flask application that serves the web pages and API endpoints.
-   `generate_tiles.py`: A module for processing the Parquet data and generating map tiles.
-   `data_parquet/`: Contains the raw methane data in Parquet format, organized by state and district.
-   `geojson/`: Contains GeoJSON files for state and district boundaries.
-   `states/`: Contains pre-aggregated JSON data for state and district statistics.
-   `tiles/<year>/<month>/`: Cache directories where generated map tiles are stored by year and month.
-   `templates/`: Contains the `index.html` file for the main web page.
-   `static/`: Contains the CSS (`styles.css`) and JavaScript (`scripts.js`) for the frontend.
-   `metadata/`: Contains metadata about the dataset.
-   `version.json`: Application version information.
-   `requirements.txt`: A list of the open-source Python packages required to run the application.
-   `docs/parquet_schema.md`: Overview of the Parquet file structure and column descriptions.
