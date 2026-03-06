// ============================================================
// Overture Maps DuckDB Sandbox — Explorer
// Interactive file partition visualizer using Leaflet
// Loaded as a classic <script> after Leaflet.
// ============================================================

(function () {
  'use strict';

  // ============================================================
  // Type → Theme Mapping (for STAC URLs)
  // ============================================================
  const TYPE_TO_THEME = {
    place: 'places',
    building: 'buildings',
    building_part: 'buildings',
    address: 'addresses',
    segment: 'transportation',
    connector: 'transportation',
    division: 'divisions',
    division_area: 'divisions',
    division_boundary: 'divisions',
    bathymetry: 'base',
    infrastructure: 'base',
    land: 'base',
    land_cover: 'base',
    land_use: 'base',
    water: 'base'
  };

  // ============================================================
  // Preset Cities
  // ============================================================
  const PRESETS = {
    'salt-lake-city': { label: 'Salt Lake City', west: -112.101, south: 40.699, east: -111.740, north: 40.853 },
    'new-york':       { label: 'New York',       west: -74.260,  south: 40.477, east: -73.700,  north: 40.917 },
    'london':         { label: 'London',         west: -0.510,   south: 51.286, east: 0.334,    north: 51.692 },
    'tokyo':          { label: 'Tokyo',          west: 139.560,  south: 35.523, east: 139.920,  north: 35.817 },
    'sao-paulo':      { label: 'São Paulo',      west: -46.826,  south: -23.733, east: -46.365, north: -23.357 },
    'sydney':         { label: 'Sydney',         west: 150.920,  south: -33.980, east: 151.340, north: -33.720 }
  };

  // ============================================================
  // State
  // ============================================================
  let map = null;
  let fileRectangles = [];
  let queryRectangle = null;
  let allFiles = [];
  let initialized = false;
  let drawHandler = null;

  // ============================================================
  // Coordinate clamping helpers
  // ============================================================
  function clampLat(v) { return Math.max(-90, Math.min(90, v)); }
  function clampLon(v) { return Math.max(-180, Math.min(180, v)); }
  function clampBbox(bbox) {
    return {
      west: clampLon(bbox.west),
      south: clampLat(bbox.south),
      east: clampLon(bbox.east),
      north: clampLat(bbox.north)
    };
  }

  // ============================================================
  // Initialize Explorer (called after setup completes)
  // ============================================================
  window.initExplorer = function () {
    if (initialized) {
      var types = getSelectedTypes();
      if (types.length > 0) loadTypeBboxes(types);
      return;
    }
    initialized = true;

    map = L.map('explorer-map').setView([20, 0], 2);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 19
    }).addTo(map);

    // Re-render map when explorer section is toggled open
    var explorerDetails = document.querySelector('#explorer-section details');
    if (explorerDetails) {
      explorerDetails.addEventListener('toggle', function () {
        if (this.open) {
          setTimeout(function () { map.invalidateSize(); }, 150);
        }
      });
    }

    document.getElementById('type-checkboxes').addEventListener('change', function () {
      var types = getSelectedTypes();
      if (types.length > 0) loadTypeBboxes(types);
    });

    document.getElementById('bbox-select').addEventListener('change', function () {
      const val = this.value;
      if (drawHandler) {
        drawHandler.disable();
        drawHandler = null;
      }
      if (val === 'custom') {
        drawHandler = new L.Draw.Rectangle(map, {
          shapeOptions: {
            color: '#e65100',
            weight: 3,
            opacity: 0.9,
            fillColor: '#ff6d00',
            fillOpacity: 0.15,
            dashArray: '6 4'
          }
        });
        drawHandler.enable();
        return;
      }
      if (val === '') {
        document.getElementById('bbox-west').value = '';
        document.getElementById('bbox-south').value = '';
        document.getElementById('bbox-east').value = '';
        document.getElementById('bbox-north').value = '';
        clearQueryBbox();
        return;
      }
      const preset = PRESETS[val];
      if (preset) {
        document.getElementById('bbox-west').value = preset.west;
        document.getElementById('bbox-south').value = preset.south;
        document.getElementById('bbox-east').value = preset.east;
        document.getElementById('bbox-north').value = preset.north;
        applyQueryBbox(preset);
      }
    });

    map.on(L.Draw.Event.CREATED, function (e) {
      const bounds = e.layer.getBounds();
      const west = clampLon(parseFloat(bounds.getWest().toFixed(3)));
      const south = clampLat(parseFloat(bounds.getSouth().toFixed(3)));
      const east = clampLon(parseFloat(bounds.getEast().toFixed(3)));
      const north = clampLat(parseFloat(bounds.getNorth().toFixed(3)));

      document.getElementById('bbox-west').value = west;
      document.getElementById('bbox-south').value = south;
      document.getElementById('bbox-east').value = east;
      document.getElementById('bbox-north').value = north;

      applyQueryBbox({ west, south, east, north });
      drawHandler = null;
    });

    document.getElementById('btn-apply-custom-bbox').addEventListener('click', function () {
      var west = parseFloat(document.getElementById('bbox-west').value);
      var south = parseFloat(document.getElementById('bbox-south').value);
      var east = parseFloat(document.getElementById('bbox-east').value);
      var north = parseFloat(document.getElementById('bbox-north').value);
      if (isNaN(west) || isNaN(south) || isNaN(east) || isNaN(north)) {
        alert('Please enter valid numeric coordinates for all four bbox fields.');
        return;
      }
      west = clampLon(west);
      east = clampLon(east);
      south = clampLat(south);
      north = clampLat(north);
      document.getElementById('bbox-west').value = west;
      document.getElementById('bbox-south').value = south;
      document.getElementById('bbox-east').value = east;
      document.getElementById('bbox-north').value = north;
      applyQueryBbox({ west, south, east, north });
    });

    // Clear button for custom bbox mode
    document.getElementById('btn-clear-custom-bbox').addEventListener('click', function () {
      document.getElementById('bbox-west').value = '';
      document.getElementById('bbox-south').value = '';
      document.getElementById('bbox-east').value = '';
      document.getElementById('bbox-north').value = '';
      clearQueryBbox();
      if (drawHandler) { drawHandler.disable(); }
      drawHandler = new L.Draw.Rectangle(map, {
        shapeOptions: {
          color: '#e65100',
          weight: 3,
          opacity: 0.9,
          fillColor: '#ff6d00',
          fillOpacity: 0.15,
          dashArray: '6 4'
        }
      });
      drawHandler.enable();
    });

    loadTypeBboxes(getSelectedTypes());
  };

  // ============================================================
  // Get selected types from checkboxes
  // ============================================================
  function getSelectedTypes() {
    return Array.from(document.querySelectorAll('#type-checkboxes input:checked')).map(function (cb) { return cb.value; });
  }

  // ============================================================
  // Load file bboxes for one or more collection types
  // ============================================================
  async function loadTypeBboxes(types) {
    const conn = window.duckdbConn;
    if (!conn || !window.setupComplete) return;
    if (!Array.isArray(types) || types.length === 0) return;

    const fileListEl = document.getElementById('file-list');

    clearFileRectangles();
    clearQueryBbox();
    fileListEl.innerHTML = '';

    try {
      const t0 = performance.now();
      const inList = types.map(function (t) { return "'" + t + "'"; }).join(', ');
      const result = await conn.query(`
        SELECT
          id,
          collection,
          assets.aws.alternate.s3.href AS href,
          bbox.xmin AS xmin,
          bbox.ymin AS ymin,
          bbox.xmax AS xmax,
          bbox.ymax AS ymax
        FROM overture_collections
        WHERE collection IN (${inList})
        ORDER BY collection, id
      `);

      allFiles = result.toArray().map(r => {
        const obj = r.toJSON();
        const href = String(obj.href);
        return {
          id: String(obj.id),
          collection: String(obj.collection),
          filename: href.split('/').pop() || String(obj.id),
          href: href,
          xmin: Number(obj.xmin),
          ymin: Number(obj.ymin),
          xmax: Number(obj.xmax),
          ymax: Number(obj.ymax)
        };
      });

      const elapsed = Math.round(performance.now() - t0);
      console.log(`[explorer] Loaded ${allFiles.length} files for types [${types.join(', ')}] (${elapsed} ms)`);

      renderFileBboxes(allFiles);
    } catch (err) {
      console.error('[explorer] Failed to load file bboxes:', err);
    }
  }

  // ============================================================
  // Render file bounding boxes on the map
  // ============================================================
  function renderFileBboxes(files) {
    clearFileRectangles();

    const bounds = L.latLngBounds();

    for (const file of files) {
      const shortName = file.filename.match(/^(part-\d+)/)?.[1] || file.filename;
      const rect = L.rectangle(
        [[file.ymin, file.xmin], [file.ymax, file.xmax]],
        {
          color: '#3366cc',
          weight: 1,
          opacity: 0.6,
          fillColor: '#3366cc',
          fillOpacity: 0.08,
          className: 'file-bbox'
        }
      );

      rect.bindTooltip(
        `<strong>${shortName}</strong>`,
        { sticky: true }
      );

      rect.fileData = file;
      rect.addTo(map);
      fileRectangles.push(rect);

      bounds.extend([[file.ymin, file.xmin], [file.ymax, file.xmax]]);
    }

    if (files.length > 0) {
      map.fitBounds(bounds, { padding: [20, 20] });
    }
  }

  // ============================================================
  // Apply a query bounding box
  // ============================================================
  async function applyQueryBbox(bbox) {
    const { west, south, east, north } = bbox;

    if (queryRectangle) {
      map.removeLayer(queryRectangle);
    }
    queryRectangle = L.rectangle(
      [[south, west], [north, east]],
      {
        color: '#e65100',
        weight: 3,
        opacity: 0.9,
        fillColor: '#ff6d00',
        fillOpacity: 0.15,
        dashArray: '6 4'
      }
    );
    queryRectangle.bindTooltip('Query bounding box', { sticky: true });
    queryRectangle.addTo(map);

    const intersecting = [];
    const nonIntersecting = [];

    for (const rect of fileRectangles) {
      const f = rect.fileData;
      const overlaps = f.xmax >= west && f.xmin <= east && f.ymax >= south && f.ymin <= north;
      if (overlaps) {
        intersecting.push(rect);
        rect.setStyle({
          color: '#1a47b8',
          weight: 2,
          opacity: 0.9,
          fillColor: '#3366cc',
          fillOpacity: 0.2
        });
      } else {
        nonIntersecting.push(rect);
        rect.setStyle({
          color: '#999999',
          weight: 1,
          opacity: 0.3,
          fillColor: '#999999',
          fillOpacity: 0.03
        });
      }
    }

    map.fitBounds([[south, west], [north, east]], { padding: [50, 50] });

    const fileListEl = document.getElementById('file-list');
    const intersectingFiles = intersecting.map(r => r.fileData);

    if (intersectingFiles.length === 0) {
      fileListEl.innerHTML = '<p class="placeholder" style="padding:1rem;">No files intersect this bounding box.</p>';
      document.getElementById('query-from-where').value = '-- No files intersect this bounding box';
      if (window.sandboxAutoResize) window.sandboxAutoResize(document.getElementById('query-from-where'));
      return;
    }

    // Build STAC link info — group by collection for multi-type support
    const types = getSelectedTypes();
    const release = window.latestVersion;

    // Render table with cache buttons
    renderFileTable(fileListEl, intersectingFiles, release);

    // Show FROM/WHERE SQL fragment in the locked query zone
    const urlList = intersectingFiles.map(f => `    '${f.href}'`).join(',\n');
    const fromWhereFragment =
      `FROM read_parquet([\n${urlList}\n])\nWHERE bbox.xmin <= ${east}\n  AND bbox.xmax >= ${west}\n  AND bbox.ymin <= ${north}\n  AND bbox.ymax >= ${south}`;
    document.getElementById('query-from-where').value = fromWhereFragment;
    if (window.sandboxAutoResize) window.sandboxAutoResize(document.getElementById('query-from-where'));
  }

  // ============================================================
  // Render file table
  // ============================================================
  function renderFileTable(fileListEl, files, release) {
    let html = `<p style="padding:0.5rem 0;font-size:0.85rem;color:var(--om-color-text-muted);">
      <strong>${files.length}</strong> of ${fileRectangles.length} files intersect this bounding box
    </p>`;
    html += '<div class="table-wrapper" style="max-height:none;"><table><thead><tr>';
    html += '<th>Type</th><th>Partition</th><th>Bbox</th><th>Cache</th>';
    html += '</tr></thead><tbody>';

    for (const f of files) {
      const shortName = f.filename.match(/^(part-\d+)/)?.[1] || f.filename;
      const theme = TYPE_TO_THEME[f.collection] || f.collection;
      const stacUrl = `https://stac.overturemaps.org/${release}/${theme}/${f.collection}/${f.id}/${f.id}.json`;
      html += '<tr>';
      html += `<td>${escapeHtml(f.collection)}</td>`;
      html += `<td title="${escapeHtml(f.href)}"><a href="${escapeHtml(stacUrl)}" target="_blank" style="color:var(--om-link-color);">${escapeHtml(shortName)}</a></td>`;
      html += `<td style="font-size:0.7rem;">${f.xmin.toFixed(1)}, ${f.ymin.toFixed(1)}, ${f.xmax.toFixed(1)}, ${f.ymax.toFixed(1)}</td>`;
      html += `<td><button class="btn btn-primary cache-run-btn" data-href="${escapeHtml(f.href)}" style="font-size:0.7rem;padding:0.15rem 0.5rem;">Cache</button></td>`;
      html += '</tr>';
    }

    html += '</tbody><tfoot><tr>';
    html += '<td colspan="3"></td>';
    html += '<td><button id="btn-cache-all" class="btn btn-primary" style="font-size:0.7rem;padding:0.15rem 0.5rem;">Cache All</button></td>';
    html += '</tr></tfoot></table></div>';
    fileListEl.innerHTML = html;

    // Wire up individual Cache buttons
    fileListEl.querySelectorAll('.cache-run-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        runCacheQuery(this);
      });
    });

    // Wire up Cache All button
    var btnAll = document.getElementById('btn-cache-all');
    if (btnAll) {
      btnAll.addEventListener('click', async function () {
        this.disabled = true;
        this.innerHTML = '<span class="btn-spinner"></span>';
        var buttons = Array.from(fileListEl.querySelectorAll('.cache-run-btn:not(:disabled):not(#btn-cache-all)'));
        var batchSize = 6;
        var tAll = performance.now();
        console.log(`[cache] Starting Cache All: ${buttons.length} files in batches of ${batchSize}`);
        for (var i = 0; i < buttons.length; i += batchSize) {
          var batch = buttons.slice(i, i + batchSize);
          var batchNum = Math.floor(i / batchSize) + 1;
          var totalBatches = Math.ceil(buttons.length / batchSize);
          console.log(`[cache] Batch ${batchNum}/${totalBatches} (${batch.length} files)...`);
          var tBatch = performance.now();
          await Promise.all(batch.map(function (b) { return runCacheQuery(b); }));
          console.log(`[cache] Batch ${batchNum} done (${Math.round(performance.now() - tBatch)} ms)`);
        }
        var totalElapsed = Math.round(performance.now() - tAll);
        console.log(`[cache] Cache All complete: ${buttons.length} files cached in ${totalElapsed} ms`);
        this.textContent = 'Done';
      });
    }
  }

  // ============================================================
  // Clear query bbox overlay
  // ============================================================
  function clearQueryBbox() {
    if (queryRectangle) {
      map.removeLayer(queryRectangle);
      queryRectangle = null;
    }

    for (const rect of fileRectangles) {
      rect.setStyle({
        color: '#3366cc',
        weight: 1,
        opacity: 0.6,
        fillColor: '#3366cc',
        fillOpacity: 0.08
      });
    }

    document.getElementById('query-from-where').value = '-- Select a type and bounding box in the Explorer above';
    if (window.sandboxAutoResize) window.sandboxAutoResize(document.getElementById('query-from-where'));
    document.getElementById('file-list').innerHTML = '';
  }

  async function runCacheQuery(btn) {
    var href = btn.dataset.href;
    var localName = href.split('/').pop();

    btn.disabled = true;
    btn.innerHTML = '<span class="btn-spinner"></span>';

    try {
      var tQuery = performance.now();
      console.log(`[cache] Fetching parquet footer for ${localName}...`);
      // Query the full URL directly — DuckDB-WASM auto-detects HTTPS and
      // uses HEAD + range requests to read only the parquet footer.
      // registerFileURL is not needed and can interfere with this behavior.
      await window.duckdbConn.query("SELECT 1 FROM read_parquet('" + href + "') LIMIT 0");
      var elapsed = Math.round(performance.now() - tQuery);
      console.log(`[cache] \u2713 Cached ${localName} (${elapsed} ms)`);

      btn.textContent = '\u2713';
      btn.style.opacity = '0.5';
      btn.style.cursor = 'default';
    } catch (err) {
      var elapsed = Math.round(performance.now() - (tQuery || performance.now()));
      console.error(`[cache] \u2717 Failed ${localName} after ${elapsed} ms:`, err.message);
      btn.textContent = '\u2717';
      btn.style.background = 'var(--om-color-error)';
      btn.title = err.message;
    }
  }

  // ============================================================
  // Clear file rectangles
  // ============================================================
  function clearFileRectangles() {
    for (const rect of fileRectangles) {
      map.removeLayer(rect);
    }
    fileRectangles = [];
    allFiles = [];
  }

  // ============================================================
  // HTML Escaping (local copy to avoid dependency)
  // ============================================================
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

})();
