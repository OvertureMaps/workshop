# [Fused.io](fused.io)

<img src="../img/fused-overture-udf.png" class="r-stretch">

Fused ingests and repartitions Overture data while adding specific metadata for their platform. The resulting files are hosted on source.coop:

```
https://data.source.coop/fused/overture/2025-03-19-1/
```

<<<

### Visualizing Overture Data with Fused
1. In a new browser window, navigate to the Fused [Overture Maps Example UDF](https://www.fused.io/workbench/catalog/Overture_Maps_Example-64071fb8-2c96-4015-adb9-596c3bac6787).
2. Click "Add to UDF Builder" in the upper right.
3. In the left-hand panel, you can adjust the **Parameters** to view different Overture data types.
    - `buildings > building`
    - `places > place`
    - `transportation > segment`

<<<

1. Hover over features on the map to see the complete, raw, Overture data. Fused is actually fetching the complete Overture feature and adding it to the map in your browser, not a pre-computed or tiled version of it.
2. If you zoom all the way out, you can see the spatial partitioning of the data. This is a helpful analytical view in itself, showing Overture data density.

    ![image](../img/fused-overture-udf-rowgroups.png)

    _This particular view of Overture data has been re-partitioned by Fused and is hosted on [source.coop](//source.coop)_

3. A few things to investigate
    - How does the density of the data compare between addresses and buildings?
    - Zoom in on some places and buildings to see all of their metadata.

> [!IMPORTANT] Now that we've seen what's in the data, let's talk about GeoParquet.
