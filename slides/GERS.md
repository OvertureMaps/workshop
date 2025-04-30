## Global Entity Reference System (GERS)

- Universal framework for structuring & matching map data across systems
- GERS IDs identify real world entities such as road segments
- Simplifies integrating & exchanging data layers

<<<

## How does GERS Work?

<ul>
    <li class="fragment">Overture assigns a unique ID to <strong>discrete map entities</strong><br>These could be buildings, road segments, places, or addresses.</li>
    <li class="fragment">Overture maintains open-source matching and conflation libraries to ensure that the ID remains stable across releases.</li>
    <li class="fragment">Each Overture release is the latest _reference map_ for these IDs.</li>
    <li class="fragment">The reference map is <em>global</em> and <em>open</em>.</li>
</ul>

<<<

<img src="../img/gers-layers.png" class="r-stretch">

<<<

## Global Entity Reference **System**

GERS is not just a stable ID. The "S" stands for system.

<ol>
    <li class="fragment">The reference map</li>
    <li class="fragment">Global registry of all GERS IDs ever published</li>
    <li class="fragment">Data Changelog based describing changes to entities across releases.</li>
    <li class="fragment">Bridge files for easy mappings of source IDs to GERS IDs.</li>
    <li class="fragment">Onboarding Services that let anyone easily associate their data with GERS.</li>
</ol>
