-- Writes examples/bathymetry.parquet: 100 rows of Overture bathymetry.
-- Run from the repo root: duckdb < examples/bathymetry.sql
INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';
COPY (SELECT * FROM read_parquet('s3://overturemaps-us-west-2/release/2026-08-19.0/theme=base/type=bathymetry/*.parquet')
      LIMIT 100)
TO 'examples/bathymetry.parquet' (FORMAT PARQUET);
