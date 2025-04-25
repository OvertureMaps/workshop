# 3. GeoParquet + DuckDB

| [<< 2. Data Access](2-accessing-data.md) | [Home](README.md) | [4. GERS >>](4-gers.md) |

**Contents**

- [3. GeoParquet + DuckDB](#3-geoparquet--duckdb)
    - [1. Querying the Places Theme](#1-querying-the-places-theme)
    - [2. Querying the Addresses and Transportation Themes](#2-querying-the-addresses-and-transportation-themes)

As a cloud-native geospatial format, GeoParquet allows us to access discrete chunks of the data without having to first read or download _all_ of Overture.

We'll use DuckDB for the next part.

You can either [install the latest version of DuckDB](https://duckdb.org/docs/installation/?version=stable&environment=cli&platform=macos&download_method=package_manager) on your machine, or use [MotherDuck](//motherduck.com) to run queries directly in the browser. Note that

### 1. Querying the Places Theme

_Tip: When launching DuckDB, specify a persistent DB, like this: `duckdb my_db.duckdb`. Now you can create tables and access them later._

1. Obtain a bounding box of interest (<https://boundingbox.klokantech.com>) is a great tool for creating a bounding box. Specifically, it lets you copy the coordinates in the following format (DublinCore) which is very human-readable.
Here's a bounding box around us today:

    ```python
    westlimit=-79.941;
    southlimit=32.773;
    eastlimit=-79.924;
    northlimit=32.781;
    ```

1. Be sure to run `INSTALL spatial;` and `LOAD spatial;` before running the query. DuckDB does not automatically load the spatial extension.

1. A basic places query looks like this:

    ```sql
    SELECT
        id,
        names.primary as name,
        confidence,
        geometry
    FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
    WHERE
        bbox.xmin BETWEEN -79.941 AND -79.924
        AND bbox.ymin BETWEEN 32.773 AND 32.781
    LIMIT 10;
    ```

1. When you run that in DuckDB, you should get back something similar to this:

    ```sql
    ┌──────────────────────────────────┬────────────────────────────────────┬────────────────────┬────────────────────────────────┐
    │                id                │                name                │     confidence     │            geometry            │
    │             varchar              │              varchar               │       double       │            geometry            │
    ├──────────────────────────────────┼────────────────────────────────────┼────────────────────┼────────────────────────────────┤
    │ 08f44d070e68d30003b32089f445080d │ Limehouse Street                   │ 0.8941256830601093 │ POINT (-79.9372113 32.7734121) │
    │ 08f44d070e6d019803900b540a2a4236 │ Berkeley Baptist Church            │ 0.3184402924451666 │ POINT (-79.936934 32.774703)   │
    │ 08f44d070a98216d03b3c8e193348df2 │ Belvedere Charleston               │ 0.9793990828827596 │ POINT (-79.9402982 32.7772198) │
    │ 08f44d070e6d8c7003981419755cd4bb │ Burbages Grocery                   │ 0.9793990828827596 │ POINT (-79.9373814 32.7757701) │
    │ 08f44d070ad639090352e4ad39523c21 │ Charleston 1857                    │ 0.8941256830601093 │ POINT (-79.9380699 32.7771415) │
    │ 08f44d070ad4294103fee6d3c0e9b095 │ Clemson Architecture Center        │ 0.7579666160849773 │ POINT (-79.937327 32.777646)   │
    │ 08f44d070ad40c4003a6d288954d52c6 │ Housing Authority                  │ 0.2803234501347709 │ POINT (-79.937309 32.777705)   │
    │ 08f44d070a98364203a7f195a05a05fb │ CoLife                             │ 0.5185185185185185 │ POINT (-79.94036 32.77778)     │
    │ 08f44d070a8a1b2503877d7227d53709 │ Ammons Dental By Design            │               0.77 │ POINT (-79.94092 32.77945)     │
    │ 08f44d070a8a1b2503e6eeb3bc1ab13e │ Wentworth Street Dental Associates │               0.77 │ POINT (-79.94092 32.77945)     │
    ├──────────────────────────────────┴────────────────────────────────────┴────────────────────┴────────────────────────────────┤
    │ 10 rows                                                                                                           4 columns │
    └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
    ```

    > [!NOTE] Results might look slightly different in the MotherDuck UI. Try ST_ASTEXT(geometry) to see the Point.

    Notice the type of the geometry column is `geometry`. This is DuckDB recognizing the geoparquet metadata and handling the column type properly.

1. Consult the [places schema](https://docs.overturemaps.org/schema/reference/places/place/) to learn more about which columns can be accessed and their data types.

1. Notice the `confidence` column. This is a score between 0 and 1 that indicates how likely it is that a place exists. Rather than download all of the data and run statistics, we can let DuckDB do all of the heavy lifting:

    ```sql
    SELECT
        round(confidence, 1) AS confidence,
        count(1)
    FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
    WHERE
        bbox.xmin BETWEEN -79.941 AND -79.924
        AND bbox.ymin BETWEEN 32.773 AND 32.781
        GROUP BY 1
        ORDER BY confidence DESC
   ```

1. Going one step further, we can explore the distribution of places with H3 cells, calculated from the bounding box column. The following query uses the `h3_latlng_to_cell_string` function to convert the bounding box to H3 cells, and then counts the number of places in each cell. It writes the results to a CSV file.

    ```sql
    INSTALL h3 from community;
    LOAD h3;

    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 11) as h3,
            count(1) AS places
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
        WHERE
            bbox.xmin BETWEEN -79.941 AND -79.924
            AND bbox.ymin BETWEEN 32.773 AND 32.781
            AND confidence > 0.7
        GROUP BY 1
    ) TO 'charleston_places_h3.csv';
    ```

    > [!NOTE] This probably will not work in MotherDuck

1. Now drag the resulting CSV file into [kepler.gl](//kepler.gl) to see the results.

1. While that is interesting, let's just scale it up a bit:

    ```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 8) as h3,
            count(1) AS places
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
        WHERE
            bbox.xmin BETWEEN -83.354 AND -78.541
            AND bbox.ymin BETWEEN 32.0335 AND 35.2155
            AND confidence > 0.7
        GROUP BY 1
    ) TO 'south_carolina_place_density.csv';
    ```

1. Going further, just remove all of the bounding box constraints. This will give us a global view of places in Overture. We probably shouldn't all run this at the same time, but you get the idea.

    ```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 5) as h3,
            count(1) AS places
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
        WHERE
            confidence > 0.7
        GROUP BY 1
    ) TO 'global_place_density.csv';
    ```

### 2. Querying the Addresses and Transportation Themes

1. Overture Addresses

    > [!WARNING] This is a much larger theme, so the query requires significantly more bandwidth. The results should be the same as what's visualized on the documentation page: <https://docs.overturemaps.org/guides/addresses/>

    ```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 5) as h3,
            count(1) AS addresses
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=addresses/type=address/*')
        GROUP BY 1
    ) TO 'global_overture_address_density.csv';
    ```

1. Or we can use _connectors_ as a proxy for road complexity in the transportation theme:

    ```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 8) as h3,
            count(1) AS road_complexity
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=transportation/type=connector/*')
        WHERE
            bbox.xmin BETWEEN -83.354 AND -78.541
            AND bbox.ymin BETWEEN 32.0335 AND 35.2155
        GROUP BY 1
    ) TO 'south_carolina_transportation_connector_density.csv';
    ```

The takeaway here is that we can get a pretty good idea of what Overture data looks like without having to download it all first.
