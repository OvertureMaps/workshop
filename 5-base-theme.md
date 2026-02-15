# 5. The Base Theme

| [<< 4. GERS](4-gers.md) | [Home](README.md) | >> |

**Contents**
- [5. The Base Theme](#5-the-base-theme)


Overture's Base theme contains other geospatial data that someone building a map service needs for a complete map. Currently, this includes:

1. Bathymetry & LandCover
2. Land & Water (Oceans, Lakes, Rivers, Mountains, etc.)
3. Landuse (Parks, Residential, Commercial, Schools, Airports, etc.)
4. Infrastructure (Power lines, barriers, stoplights, etc.)

This data is sourced primarily from OpenStreetMap and Overture performs basic classification of the features based on their OSM tags. This data undergoes many QA checks in this process.

### Setup instructions

First, refer to the [setup instructions here](https://labs.overturemaps.org/workshop/#workshop-setup). 

If you're running through these queries locally using DuckDB, be sure to specify a database, such as `duckdb workshop.dbb`, so that you save tables and views that will persist in a future session. Another option is to attach the following database in DuckDB to access the latest Overture data. 

```sql
LOAD spatial;
ATTACH 'https://labs.overturemaps.org/data/latest.dbb' as overture;

-- Now you can just reference `overture.land` for type=land features
SELECT count(1) from overture.land;
```
You can also run these queries in a Github codespace. [See the Codespace instructions here](https://labs.overturemaps.org/workshop/#workshop-setup)

## Mountain Peaks

1. The following query extracts all of the peaks with names and elevations from OpenStreetMap.

```sql
    LOAD spatial;
    CREATE TABLE na_peaks AS (
        SELECT
            names.primary as name,
            elevation,
            geometry,
            bbox
        FROM overture.land
        WHERE
            subtype = 'physical'
            AND class IN ('peak','volcano')
            AND names.primary IS NOT NULL
            AND elevation IS NOT NULL
            AND bbox.xmin BETWEEN -175 AND -48
            AND bbox.ymin BETWEEN 10 AND 85
    );
```

2. Write this out to a GeoJSON file and then build an h3-gridded DEM for the World from the na_peaks table.

```sql
    COPY(
        SELECT
            name,
            elevation,
            geometry
        FROM na_peaks
    ) TO 'na_peaks.geojson' WITH (FORMAT GDAL, DRIVER GeoJSON);
```


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
