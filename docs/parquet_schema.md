# Parquet Schema

Each district's methane data is stored in a separate Parquet file located under `data_parquet/<STATE>/<DISTRICT>.parquet`.

## Columns

- `latitude` (`float64`): Latitude of the grid point.
- `longitude` (`float64`): Longitude of the grid point.
- `YYYY_MM_01` (`float64`): Monthly average methane concentration in parts per billion (ppb).
  - Columns exist from `2014_01_01` through `2022_12_01`.
  - Values may contain `NaN` where data is unavailable.

Only values greater than zero are considered valid when computing map colors or statistics.
