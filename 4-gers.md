# 4. The Global Entity Reference System (GERS)

| [<< 3. GeoParquet & DuckDB](3-geoparquet-duckdb.md) | [Home](README.md) | [5. Base Theme >>](5-base-theme.md) |

- [4. The Global Entity Reference System (GERS)](#4-the-global-entity-reference-system-gers)

A GERS ID is a 128-bit unique identifier that Overture keeps stable across data releases and updates. For themes like Buildings, Divisions, Places, and Transportation, Overture performs feature-level conflation to preserve ID stability.

Themes that do not conflate multiple input sources use deterministic hashes to ensure consistent matching from input datasets, such as OpenStreetMap, to an 128-bit ID that is fully compatible with the larger GERS ecosystem.


### Setup instructions

First, refer to the [setup instructions here](https://labs.overturemaps.org/workshop/#workshop-setup). 

If you're running through these queries locally using DuckDB, be sure to specify a database, such as `duckdb workshop.dbb`, so that you save tables and views that will persist in a future session. Another option is to attach the following database in DuckDB to access the latest Overture data. 

```sql
LOAD spatial;
ATTACH 'https://labs.overturemaps.org/data/latest.dbb' as overture;

-- Now you can just reference `overture.division` for type=division features
SELECT count(1) from overture.division;
```
You can also run these queries in a Github codespace. [See the Codespace instructions here](https://labs.overturemaps.org/workshop/#workshop-setup)


## Exploring Overture's Divisions and Hierarchies with GERS

Overture's Divisions theme contains boundaries and points for administrative areas around the world. GERS IDs are intended to be the key to unlock interoperability both inside and outside of Overture data. This example shows how Overture features within the same theme can reference one-another via GERS.

1. Let's create a table for all the `division` entities that are tied to the GERS ID for Salt Lake City.

```sql
    CREATE TABLE slc AS (
        SELECT
            *
        FROM
            overture.division
        WHERE
            -- ID for Salt Lake City, Utah
            id = 'fa6ba2e0-cc93-4f51-bfe9-ef41e33741c9'
    );
```

2. When we query that table, we can see the Divisions hierarchy: Salt Lake City is a locality in Salt Lake County, which is in the region of Utah, within the country of the United States.

```sql
  SELECT
        h.name,
        h.subtype,
        h.division_id
    FROM
        slc
    CROSS JOIN UNNEST(hierarchies[1]) AS t(h);
```

```
┌──────────────────┬──────────┬──────────────────────────────────────┐
│       name       │ subtype  │             division_id              │
│     varchar      │ varchar  │               varchar                │
├──────────────────┼──────────┼──────────────────────────────────────┤
│ South Salt Lake  │ locality │ fa6ba2e0-cc93-4f51-bfe9-ef41e33741c9 │
│ Salt Lake County │ county   │ 53d671bc-c294-44fb-a767-169bffedc5cb │
│ Utah             │ region   │ 506017c0-8932-44b5-b82c-92f9dcffdcf1 │
│ United States    │ country  │ f39eb4af-5206-481b-b19e-bd784ded3f05 │
└──────────────────┴──────────┴──────────────────────────────────────┘
```

3. If we wanted to retrieve the actual polygons for these divisions, we can search the `division_area` type of the divisions theme to obtain these particular division IDs:

```sql
    COPY(
        SELECT
            names.primary AS name,
            subtype,
            id,
            geometry
        FROM
            overture.division_area
        WHERE
            division_id IN (
                SELECT
                    h.division_id
                FROM
                    slc
                CROSS JOIN UNNEST(hierarchies[1]) AS t(h)
            )
    ) TO 'slc_hierarchies.geojson' WITH (FORMAT GDAL, DRIVER GeoJSON);
```

4. Load `slc_hierarchies.geojson` into KeplerGL and you can see the complete hierarchy of divisions:
    ![Salt lake City Hierarchies](img/slc_hierarchy.jpg)


## Working with the Changelog

1. Every Overture release includes a changelog with a high level overview of data added, removed, or changed, based on the ID. The changelog is partitioned by `theme`, `type`, and `change_type`. To identify all of the features added in Salt Lake City, we can use the following query. *Note: If a feature is added or "new" in Overture it does not necessarily mean that feature is "new on the Earth".*

```sql
    SELECT
        id
    FROM
        read_parquet('s3://overturemaps-us-west-2/changelog/2026-01-21.0/theme=places/*/*/*.parquet')
    WHERE
        change_type = 'added'
        AND bbox.xmin > -112.461 AND bbox.xmax < -111.073
        AND bbox.ymin > 40.296 AND bbox.ymax < 40.955
```

This gives us a list of GERS IDs for places in Salt Lake City that were added in the latest release. But what else do we know about these places?

2. To find out more about the places added in the latest release, let's join the IDs from the changelog to the latest places data We'll write the results to a new GeoJSON file.

```sql
    COPY(
        SELECT
            places.id as id,
            names.primary as name,
            categories.primary as category,
            confidence,
            CAST(sources AS JSON) as sources,
            geometry
        FROM
            overture.place places
        JOIN (
            SELECT
                id
            FROM
                read_parquet('s3://overturemaps-us-west-2/changelog/2026-01-21.0/theme=places/*/*/*.parquet')
            WHERE change_type = 'added'
            AND bbox.xmin > -112.461 AND bbox.xmax < -111.073 AND bbox.ymin > 40.296 AND bbox.ymax < 40.955
            ) changelog
        ON places.id = changelog.id
        ORDER BY places.id ASC
        LIMIT 100
    ) TO 'new_places_slc.geojson' WITH (FORMAT GDAL, DRIVER GeoJSON);
```

## Working with Bridge Files

With each release, Overture publishes bridge files that map GERS ID to Source IDs (`record_id`)from the datasets we use to generate the latest released data. We only create and publish bridge files for datasets with a meaningful `record_id`. ML-Derived buildings, for example, do not have stable meaningful input IDs, but place records from Meta have corresponding IDs that reference public Facebook pages.

A feature's `sources` attribute lists the original source of the feature and any additional attributes that Overture has added.



1. Lookup the Facebook pages for the new places in Salt Lake City

We can use access the bridge file for Meta places to connect the published GERS IDs to the `record_id` for Meta's Facebook data.

```sql
    COPY(
        SELECT
            'https://facebook.com/' || cast(bridge.record_id as varchar) AS facebook_page,
            slc_places.*
        FROM ST_READ('new_places_slc.geojson') slc_places JOIN (
            SELECT
                id,
                record_id
            FROM
                read_parquet('s3://overturemaps-us-west-2/bridgefiles/2026-01-21.0/dataset=meta/theme=places/type=place/*')
        ) bridge ON slc_places.id = bridge.id
        LIMIT 100
    ) TO 'new_places_slc_with_fb_pages.geojson' WITH (FORMAT GDAL, Driver GeoJSON);
```

## GERS Onboarding Services

Associating third-party data with GERS usually involves a spatial join between datasets. Many users do this on their own, with their own tools and infrastructure. Overture Maps provides limited hands-on support for GERS-ifying data but several companies within the Overture Maps ecosystem do provide GERS onboarding services. 

1. [Fused](https://www.fused.io/)

2. [Wherobots](https://wherobots.com/)

3. [Esri](https://www.esri.com/en-us/home)


