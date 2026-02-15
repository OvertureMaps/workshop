# 3. GeoParquet + DuckDB

| [<< 2. Data Access](2-accessing-data.md) | [Home](README.md) | [4. GERS >>](4-gers.md) |

- [3. GeoParquet + DuckDB](#3-geoparquet--duckdb)

As a cloud-native geospatial format, GeoParquet allows us to access discrete chunks of the data without having to first read or download _all_ of Overture. DuckDB allows us to write SQL queries that can take advantage of the optimizations and efficiencies of the underlying GeoParquet format.

### Setup instructions

First, refer to the [setup instructions here](https://labs.overturemaps.org/workshop/#workshop-setup). 

If you're running through these queries locally using DuckDB, be sure to specify a database, such as `duckdb workshop.dbb`, so that you save tables and views that will persist in a future session. Another option is to attach the following database in DuckDB to access the latest Overture data. 

```sql
LOAD spatial;
ATTACH 'https://labs.overturemaps.org/data/latest.dbb' as overture;

-- Now you can just reference `overture.place` for type=place features
SELECT count(1) from overture.place;
```

You can also run these queries in a Github codespace. [See the Codespace instructions here](https://labs.overturemaps.org/workshop/#workshop-setup)

## Querying the Places Theme

**These examples use the latest.dbb example shown above.**

1. Obtain a bounding box of interest (<https://boundingbox.klokantech.com>) is a great tool for creating a bounding box. Specifically, it lets you copy the coordinates in the following format which is very human-readable.

    Here's a bounding box for Salt Lake City:

    ```python
    westlimit=-112.101;
    southlimit=40.699;
    eastlimit=-111.740;
    northlimit=40.853;
    ```

2. A basic places query looks like this. *Note: Be sure to run `INSTALL spatial;` and `LOAD spatial;` before running the query. DuckDB does not automatically load the spatial extension.* 

    ```sql
    SELECT
        id,
        names.primary as name,
        confidence,
        geometry
    FROM overture.place
    WHERE
        bbox.xmin BETWEEN -112.101 AND -111.740
        AND bbox.ymin BETWEEN 40.699 AND 40.853
    LIMIT 10;
    ```

This gives you 10 places in Salt Lake City. Notice the type of the geometry column is `geometry`. This is DuckDB recognizing the geoparquet metadata and handling the column type properly.

```
┌──────────────────────────────────────┬──────────────────────────────────┬─────────────────────┬─────────────────────────────────┐
│                  id                  │               name               │     confidence      │            geometry             │
│               varchar                │             varchar              │       double        │            geometry             │
├──────────────────────────────────────┼──────────────────────────────────┼─────────────────────┼─────────────────────────────────┤
│ 4bd8a53a-8ef2-441c-8023-2b1dbede3f00 │ Eastwood Elementary School       │  0.9500626074407351 │ POINT (-111.7937475 40.6996334) │
│ 581db44d-5677-451f-bf46-c3c4f8d52087 │ REI                              │                0.77 │ POINT (-111.794148 40.700257)   │
│ a6dcea2c-c1c8-4e6e-927c-9ee9f4f2c61c │ Savers                           │               0.862 │ POINT (-111.7946003 40.7018864) │
│ ba66ae03-9cf8-4483-8c05-b1bfe6b36547 │ Savers Community Donation Center │                0.77 │ POINT (-111.7946003 40.7018864) │
│ a5bbee83-876d-453e-81e1-a79eb5482533 │ Grandeur Peak                    │  0.9500626074407351 │ POINT (-111.7597509 40.7069893) │
│ 517e8ba3-2b24-426f-af80-f99b4617aaed │ Grandeur Peak Trailhead          │  0.9500626074407351 │ POINT (-111.7958617 40.7075576) │
│ 81343112-7346-4c11-8007-10c6fd2818f1 │ Parley's Canyon                  │ 0.32347911067676516 │ POINT (-111.780685 40.719567)   │
│ 6316e033-5826-47c3-ad85-f45059ff53db │ Deer Valley Park City Utah       │  0.6392360292383872 │ POINT (-111.7756324 40.7221476) │
│ 1dfe1542-bc0f-40a5-974e-b886b6ccd2ef │ Whitney Resevior Utah            │  0.9735918045043945 │ POINT (-111.7750733 40.7227894) │
│ 56ce9f70-2190-44bc-9e87-91e5c4efbbfa │ Salt Lake County Sheriff's Range │  0.9735918045043945 │ POINT (-111.7554226 40.7350332) │
├──────────────────────────────────────┴──────────────────────────────────┴─────────────────────┴─────────────────────────────────┤
│ 10 rows                                                                                                               4 columns │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```


3. Consult the [places schema](https://docs.overturemaps.org/schema/reference/places/place/) to learn more about which columns can be accessed and their data types. Notice the `confidence` column. This is a score between 0 and 1 that indicates how likely it is that a place exists. Rather than download all of the data and run statistics, we can let DuckDB do all of the heavy lifting:

    ```sql
    SELECT
        round(confidence, 1) AS confidence,
        count(1)
    FROM overture.place
    WHERE
        bbox.xmin BETWEEN -112.101 AND -111.740
        AND bbox.ymin BETWEEN 40.699 AND 40.853
        GROUP BY 1
        ORDER BY confidence DESC;
   ```

4. Going one step further, we can explore the distribution of places with H3 cells, calculated from the bounding box column. The following query uses the `h3_latlng_to_cell_string` function to convert the bounding box to H3 cells, and then counts the number of places in each cell. It writes the results to a CSV file.

    ```sql
    INSTALL h3 from community;
    LOAD h3;

    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 9) as h3,
            count(1) AS places
        FROM overture.place
        WHERE
            bbox.xmin BETWEEN -112.101 AND -111.740
            AND bbox.ymin BETWEEN 40.699 AND 40.853
            AND confidence > 0.7
        GROUP BY 1
    ) TO 'slc_h3_density.csv';
    ```

Now drag the resulting CSV file into [kepler.gl](//kepler.gl) to see the results.

5. Now let's scale that query using a bounding box that includes all of Utah. You can also remove all of the bounding box contraints to get a global view of places in Overture. 

```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 8) as h3,
            count(1) AS places
        FROM overture.place
        WHERE
            bbox.xmin BETWEEN -114.0529 AND -109.0416
            AND bbox.ymin BETWEEN 36.9978 AND 42.0017
            AND confidence > 0.7
        GROUP BY 1
    ) TO 'utah_places_density.csv';
```

## Querying the Addresses and Transportation Themes

1. Overture Addresses

Let's explore address density in Salt Lake City. You can read more about Overture's Addresses theme [here](https://docs.overturemaps.org/guides/addresses/). 

```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 5) as h3,
            count(1) AS addresses
        FROM overture.address
        WHERE
            bbox.xmin BETWEEN -112.101 AND -111.740
            AND bbox.ymin BETWEEN 40.699 AND 40.853
        GROUP BY 1
    ) TO 'slc_address_density.csv';
```

2. Overture Transportation 

We can use the `connector` type as a proxy for road complexity in the [Overture Transportation](https://docs.overturemaps.org/guides/transportation/) theme.

```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 8) as h3,
            count(1) AS road_complexity
        FROM overture.connector
        WHERE
            bbox.xmin BETWEEN -112.101 AND -111.740
            AND bbox.ymin BETWEEN 40.699 AND 40.853
        GROUP BY 1
    ) TO 'slc_transportation_connector_density.csv';
```

The takeaway here is that we can get a pretty good idea of what Overture data looks like without having to download it all first.

---
[Next: Working with the Global Entity Reference System >>](4-gers.md)
