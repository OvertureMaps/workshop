## Global Entity Reference System (GERS)

- Universal framework for structuring & matching map data across systems
- GERS IDs identify real world entities such as road segments
- Simplifies integrating & exchanging data layers

<<<

## How does GERS Work?

Overture assigns a unique ID to **discrete map entities**.

These could be buildings, road segments, places, or addresses.

Overture maintains open-source matching and conflation libraries to ensure that the ID remains stable across releases.

<<<

Each Overture release is the latest _reference map_ for features with GERS IDs.

The reference map is _global_, _open_.

<<<

<img src="../img/gers-layers.png" class="r-stretch">

<<<

## Global Entity Reference **System**

GERS is not just a stable ID. The "S" stands for system.

1. The reference map
2. Global registry of all GERS IDs ever published
3. Data Changelog based describing changes to entities across releases.
4. Bridge files for easy mappings of source IDs to GERS IDs.
5. Onboarding Services that let anyone easily associate their data with GERS.
