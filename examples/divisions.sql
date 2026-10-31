-- Prints 100 Overture division rows as JSON, one per line, geometry as GeoJSON.
-- duckdb < examples/divisions.sql | overture-schema validate --type division --show-field id -
INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';
COPY (SELECT ST_AsGeoJSON(geometry) AS geometry, * EXCLUDE geometry
      FROM read_parquet('s3://overturemaps-us-west-2/release/2026-08-19.0/theme=divisions/type=division/*.parquet')
      LIMIT 100)
TO '/dev/stdout' (FORMAT JSON, ARRAY false);
