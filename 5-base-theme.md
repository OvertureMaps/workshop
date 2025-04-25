# 5. The Base Theme

| [<< 4. GERS](4-gers.md) | [Home](README.md) | >> |

**Contents**
- [5. The Base Theme](#5-the-base-theme)
    - [1. Mountain Peaks](#1-mountain-peaks)
    - [2. Water Features](#2-water-features)


_Base_ contains other geospatial data that someone building a map service needs for a complete map. Currently, this includes:

1. Bathymetry & LandCover
2. Land & Water (Oceans, Lakes, Rivers, Mountains, etc.)
3. Landuse (Parks, Residential, Commercial, Schools, Airports, etc.)
4. Infrastructure (Power lines, barriers, stoplights, etc.)

This data is sourced primarily from OpenStreetMap and Overture performs basic classification of the features based on their OSM tags. This data undergoes many QA checks in this process.

### 1. Mountain Peaks

1. The following query extracts all of the peaks with names and elevations from OpenStreetMap.

    ```sql
    LOAD spatial;
    CREATE TABLE na_peaks AS (
        SELECT
            names.primary as name,
            elevation,
            geometry,
            bbox
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=base/type=land/*.parquet')
        WHERE
            subtype = 'physical'
            AND class IN ('peak','volcano')
            AND names.primary IS NOT NULL
            AND elevation IS NOT NULL
            AND bbox.xmin BETWEEN -175 AND -48
            AND bbox.ymin BETWEEN 10 AND 85
    );
    ```

    Write this out to a GeoJSON file:

    ```sql
    COPY(
        SELECT
            name,
            elevation,
            geometry
        FROM na_peaks
    ) TO 'na_peaks.geojson' WITH (FORMAT GDAL, DRIVER GeoJSON);
    ```

2. We can build an h3-gridded DEM for the World from this table:

    ```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 7) as h3,
            max(elevation) as _max,
            min(elevation) as _min,
            avg(elevation) as _avg
        FROM na_peaks
        GROUP BY 1
    ) TO 'na_dem_h3_hi.csv';
    ```

    ![North America Low resolution DEM](img/na_dem_lo.jpg)

### 2. Water Features

A little demo with water features...
