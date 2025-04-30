# 3. GeoParquet + DuckDB

| [<< 2. Data Access](2-accessing-data.md) | [Home](README.md) | [4. GERS >>](4-gers.md) |

- [3. GeoParquet + DuckDB](#3-geoparquet--duckdb)
  - [1. Querying the Places Theme](#1-querying-the-places-theme)
  - [2. Querying the Addresses and Transportation Themes](#2-querying-the-addresses-and-transportation-themes)

As a cloud-native geospatial format, GeoParquet allows us to access discrete chunks of the data without having to first read or download _all_ of Overture. DuckDB allows us to write SQL queries that can take advantage of the optimizations and efficiencies of the underlying GeoParquet format.

You can either [install the latest version of DuckDB](https://duckdb.org/docs/installation/?version=stable&environment=cli&platform=macos&download_method=package_manager) on your machine, or run these queries directly in a Github codespace. [See the Codespace instructions here](https://labs.overturemaps.org/workshop/#workshop-setup)

## 1. Querying the Places Theme

_Tip: When launching DuckDB, specify a persistent DB, like this: ```duckdb my_db.duckdb```. Now you can create tables and access them later._

1. Obtain a bounding box of interest (<https://boundingbox.klokantech.com>) is a great tool for creating a bounding box. Specifically, it lets you copy the coordinates in the following format (DublinCore) which is very human-readable.

    Here's a bounding box for Salt Lake City:

    ```python
    westlimit=-112.101;
    southlimit=40.699;
    eastlimit=-111.740;
    northlimit=40.853;
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
        bbox.xmin BETWEEN -112.101 AND -111.740
        AND bbox.ymin BETWEEN 40.699 AND 40.853
    LIMIT 10;
    ```

1. When you run that in DuckDB, you should get back something similar to this:

    ```sql
    ┌──────────────────────────────────┬─────────────────────────────────────────────────┬─────────────────────┬─────────────────────────────────┐
    │                id                │                      name                       │     confidence      │            geometry             │
    │             varchar              │                     varchar                     │       double        │            geometry             │
    ├──────────────────────────────────┼─────────────────────────────────────────────────┼─────────────────────┼─────────────────────────────────┤
    │ 08f269602b36dd83031c482287a964f3 │ Pleasant Green Park                             │  0.9781719885115729 │ POINT (-112.0945883 40.70094)   │
    │ 08f269602baec0440318ca7ac620e59a │ Magna Elementary School                         │  0.9781719885115729 │ POINT (-112.0948915 40.7039208) │
    │ 08f2696076ca0cb103196ea2d3cb51fd │ Magna Recreation Center                         │  0.9781719885115729 │ POINT (-112.0922502 40.700182)  │
    │ 08f2696076d9cc5203445cb3f7bdb886 │ Magna Outdoor Pool                              │  0.9781719885115729 │ POINT (-112.0933876 40.7013161) │
    │ 08f269602ba5d8900352bf0296a1383c │ The Church of Jesus Christ of Latter-day Saints │  0.9781719885115729 │ POINT (-112.0923506 40.7043022) │
    │ 08f2696076d10243038bc08602417577 │ England Enterprises                             │ 0.29137199434229144 │ POINT (-112.09027 40.7030699)   │
    │ 08f2696076c720da0353d2cd5b65a029 │ The Church of Jesus Christ of Latter-day Saints │  0.9781719885115729 │ POINT (-112.0868382 40.699125)  │
    │ 08f2696076c723b003fb31827fa27bdb │ Spencer 4th Ward Friends                        │ 0.29137199434229144 │ POINT (-112.08689 40.699292)    │
    │ 08f2696076c63a49032c62ac46544e39 │ The Flowers of Faith                            │  0.8936305732484077 │ POINT (-112.0845037 40.6993426) │
    │ 08f2696076d42ccd03af1e08df722d5a │ Arthur Mill                                     │ 0.47268106734434556 │ POINT (-112.0858333 40.7016667) │
    ├──────────────────────────────────┴─────────────────────────────────────────────────┴─────────────────────┴─────────────────────────────────┤
    │ 10 rows                                                                                                                          4 columns │
    └────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

    ```

    Notice the type of the geometry column is `geometry`. This is DuckDB recognizing the geoparquet metadata and handling the column type properly.

1. Consult the [places schema](https://docs.overturemaps.org/schema/reference/places/place/) to learn more about which columns can be accessed and their data types.

1. Notice the `confidence` column. This is a score between 0 and 1 that indicates how likely it is that a place exists. Rather than download all of the data and run statistics, we can let DuckDB do all of the heavy lifting:

    ```sql
    SELECT
        round(confidence, 1) AS confidence,
        count(1)
    FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
    WHERE
        bbox.xmin BETWEEN -112.101 AND -111.740
        AND bbox.ymin BETWEEN 40.699 AND 40.853
        GROUP BY 1
        ORDER BY confidence DESC;
   ```

1. Going one step further, we can explore the distribution of places with H3 cells, calculated from the bounding box column. The following query uses the `h3_latlng_to_cell_string` function to convert the bounding box to H3 cells, and then counts the number of places in each cell. It writes the results to a CSV file.

    ```sql
    INSTALL h3 from community;
    LOAD h3;

    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 9) as h3,
            count(1) AS places
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
        WHERE
            bbox.xmin BETWEEN -112.101 AND -111.740
            AND bbox.ymin BETWEEN 40.699 AND 40.853
            AND confidence > 0.7
        GROUP BY 1
    ) TO 'results/slc_h3_density.csv';
    ```

1. Now drag the resulting CSV file into [kepler.gl](//kepler.gl) to see the results.

1. We can easily scale that query to include all of Utah:

    ```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 8) as h3,
            count(1) AS places
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=places/type=place/*')
        WHERE
            bbox.xmin BETWEEN -114.0529 AND -109.0416
            AND bbox.ymin BETWEEN 36.9978 AND 42.0017
            AND confidence > 0.7
        GROUP BY 1
    ) TO 'utah_places_density.csv';
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
    ) TO 'results/global_place_density.csv';
    ```

## 2. Querying the Addresses and Transportation Themes

1. Overture Addresses

    > [!WARNING] This is a much larger theme, so the query requires significantly more bandwidth. The results should be the same as what's visualized on the documentation page: <https://docs.overturemaps.org/guides/addresses/>

    ```sql
    COPY(
        SELECT
            h3_latlng_to_cell_string(bbox.ymin, bbox.xmin, 5) as h3,
            count(1) AS addresses
        FROM read_parquet('s3://overturemaps-us-west-2/release/2025-04-23.0/theme=addresses/type=address/*')
        GROUP BY 1
    ) TO 'results/global_overture_address_density.csv';
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
    ) TO 'results/south_carolina_transportation_connector_density.csv';
    ```

The takeaway here is that we can get a pretty good idea of what Overture data looks like without having to download it all first.

---
[Next: Working with the Global Entity Reference System >>](4-gers.md)
