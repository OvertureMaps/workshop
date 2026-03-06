// ============================================================
// Overture Maps DuckDB Sandbox — Core Logic
// Loaded as a classic <script> before the module script.
// The module script sets window.duckdbConn / window.duckdbDB
// after DuckDB-WASM is initialized.
// ============================================================

(function () {
  'use strict';

  // ============================================================
  // State (set by the module script after DuckDB init)
  // ============================================================
  window.duckdbDB = null;
  window.duckdbConn = null;
  window.setupComplete = false;
  window.latestVersion = null;

  // ============================================================
  // DOM References
  // ============================================================
  const loadingOverlay = document.getElementById('loading-overlay');
  const loadingError = document.getElementById('loading-error');
  const duckdbDot = document.getElementById('duckdb-dot');
  const duckdbStatus = document.getElementById('duckdb-status');
  const releaseItem = document.getElementById('release-item');
  const releaseDot = document.getElementById('release-dot');
  const releaseStatus = document.getElementById('release-status');

  const setupEditor = document.getElementById('setup-editor');
  const btnSetup = document.getElementById('btn-setup');
  const setupError = document.getElementById('setup-error');

  const btnQuery = document.getElementById('btn-query');
  const queryError = document.getElementById('query-error');

  const resultsMeta = document.getElementById('results-meta');
  const resultsContainer = document.getElementById('results-container');

  // ============================================================
  // HTML Escaping
  // ============================================================
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ============================================================
  // Cell Value Formatting
  // ============================================================
  function formatCellValue(val) {
    if (val === null || val === undefined) {
      return '<span class="cell-null">NULL</span>';
    }
    if (typeof val === 'bigint') {
      return escapeHtml(String(val));
    }
    if (val instanceof Uint8Array || val instanceof ArrayBuffer) {
      const bytes = val instanceof Uint8Array ? val : new Uint8Array(val);
      const hex = Array.from(bytes.slice(0, 20), b => b.toString(16).padStart(2, '0')).join('');
      return `<span class="cell-object" title="Binary data (${bytes.length} bytes)">${hex}${bytes.length > 20 ? '...' : ''}</span>`;
    }
    if (typeof val === 'object') {
      let json;
      try {
        json = JSON.stringify(val, (_, v) => typeof v === 'bigint' ? String(v) : v);
      } catch {
        json = String(val);
      }
      const truncated = json.length > 120 ? json.substring(0, 120) + '...' : json;
      return `<span class="cell-object" title="${escapeHtml(json)}">${escapeHtml(truncated)}</span>`;
    }
    const str = String(val);
    if (str.length > 200) {
      return `<span title="${escapeHtml(str)}">${escapeHtml(str.substring(0, 200))}...</span>`;
    }
    return escapeHtml(str);
  }

  // ============================================================
  // Results Rendering
  // ============================================================
  function renderResults(rows, timingMs) {
    if (!rows || rows.length === 0) {
      resultsMeta.textContent = '';
      resultsContainer.innerHTML = '<p class="placeholder">Query returned no results.</p>';
      return;
    }

    const columns = Object.keys(rows[0]);
    resultsMeta.textContent = `${rows.length} row${rows.length !== 1 ? 's' : ''} \u00b7 ${timingMs} ms`;

    let html = '<div class="table-wrapper"><table><thead><tr>';
    for (const col of columns) {
      html += `<th>${escapeHtml(col)}</th>`;
    }
    html += '</tr></thead><tbody>';

    for (const row of rows) {
      html += '<tr>';
      for (const col of columns) {
        html += `<td>${formatCellValue(row[col])}</td>`;
      }
      html += '</tr>';
    }
    html += '</tbody></table></div>';
    resultsContainer.innerHTML = html;
  }

  function showError(errorEl, message) {
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
  }

  function hideError(errorEl) {
    errorEl.classList.add('hidden');
    errorEl.textContent = '';
  }

  // ============================================================
  // SQL Preparation
  // ============================================================
  function prepareSQL(raw) {
    let sql = raw.trim();
    if (!sql) return sql;

    if (sql.endsWith(';')) {
      sql = sql.slice(0, -1).trim();
    }

    return sql;
  }

  // ============================================================
  // SQL Statement Splitting
  // ============================================================
  function splitStatements(sql) {
    const statements = [];
    let current = '';
    let inString = false;

    for (let i = 0; i < sql.length; i++) {
      const ch = sql[i];
      if (ch === "'" && !inString) {
        inString = true;
        current += ch;
      } else if (ch === "'" && inString) {
        if (i + 1 < sql.length && sql[i + 1] === "'") {
          current += "''";
          i++;
        } else {
          inString = false;
          current += ch;
        }
      } else if (ch === ';' && !inString) {
        const trimmed = current.trim();
        if (trimmed) {
          statements.push(trimmed);
        }
        current = '';
      } else {
        current += ch;
      }
    }
    const trimmed = current.trim();
    if (trimmed) {
      statements.push(trimmed);
    }

    return statements.filter(s => {
      const lines = s.split('\n').filter(l => !l.trim().startsWith('--') && l.trim() !== '');
      return lines.length > 0;
    });
  }

  // ============================================================
  // STAC Catalog Fetch
  // ============================================================
  async function fetchCatalog() {
    const resp = await fetch('https://stac.overturemaps.org/catalog.json');
    if (!resp.ok) throw new Error(`STAC catalog returned ${resp.status}`);
    const catalog = await resp.json();
    if (!catalog.latest) {
      throw new Error('Could not determine latest release from STAC catalog');
    }
    return catalog;
  }

  // ============================================================
  // Setup Execution
  // ============================================================
  async function runSetup() {
    const db = window.duckdbDB;

    btnSetup.disabled = true;
    btnSetup.innerHTML = '<span class="btn-spinner"></span>Running...';
    hideError(setupError);

    releaseItem.style.display = 'flex';
    releaseDot.className = 'status-dot loading';
    releaseStatus.textContent = 'Running setup...';

    const t0 = performance.now();

    try {
      // Create a fresh connection
      if (window.duckdbConn) await window.duckdbConn.close();
      window.duckdbConn = await db.connect();
      const freshConn = window.duckdbConn;
      console.log(`[setup] Connection created (${Math.round(performance.now() - t0)} ms)`);

      // Fetch catalog (release version + registry manifest) via JS
      const tFetch = performance.now();
      const catalog = await fetchCatalog();
      window.latestVersion = catalog.latest;
      window.registryManifest = catalog.registry?.manifest || [];
      window.registryPath = catalog.registry?.path || '';
      console.log(`[setup] STAC catalog fetched → ${window.latestVersion} (${Math.round(performance.now() - tFetch)} ms)`);
      console.log(`[setup] Registry manifest: ${window.registryManifest.length} entries`);

      // Split and execute each statement from the editor
      const sql = setupEditor.value;
      const statements = splitStatements(sql);

      for (let i = 0; i < statements.length; i++) {
        let stmt = statements[i];
        // Replace the read_json_auto subquery with the JS-resolved value
        stmt = stmt.replace(
          /\(\s*SELECT\s+latest\s+FROM\s+read_json_auto\s*\(\s*'https:\/\/stac\.overturemaps\.org\/catalog\.json'\s*\)\s*\)/is,
          `'${window.latestVersion}'`
        );
        // Replace getvariable('overture_release') in URLs with the literal value
        stmt = stmt.replace(
          /getvariable\s*\(\s*'overture_release'\s*\)/gi,
          `'${window.latestVersion}'`
        );
        const tStmt = performance.now();
        const preview = stmt.replace(/\s+/g, ' ').substring(0, 80);
        console.log(`[setup] Executing statement ${i + 1}/${statements.length}: ${preview}...`);
        await freshConn.query(stmt);
        console.log(`[setup] Statement ${i + 1} done (${Math.round(performance.now() - tStmt)} ms)`);
      }

      window.setupComplete = true;

      console.log(`[setup] Total setup time: ${Math.round(performance.now() - t0)} ms`);

      // Update UI
      releaseDot.className = 'status-dot ready';
      releaseStatus.textContent = `Release: ${window.latestVersion}`;
      btnSetup.textContent = 'Run Setup';
      btnSetup.disabled = false;
      btnQuery.disabled = false;

      // Notify explorer
      if (typeof window.initExplorer === 'function') {
        window.initExplorer();
      }
    } catch (err) {
      releaseDot.className = 'status-dot error';
      releaseStatus.textContent = 'Error';
      showError(setupError, err.message);
      btnSetup.textContent = 'Run Setup';
      btnSetup.disabled = false;
    }
  }

  // ============================================================
  // Query Execution
  // ============================================================
  async function runQuery() {
    if (!window.setupComplete) {
      showError(queryError, 'Please run Setup first (Box 1).');
      return;
    }

    const selectPart = document.getElementById('query-select').value.trim();
    const fromWhereEl = document.getElementById('query-from-where');
    const fromWherePart = fromWhereEl.value.trim();
    const fromWhereDisabled = !document.getElementById('from-where-enabled').checked;
    const extrasPart = document.getElementById('query-extras').value.trim();

    if (!fromWhereDisabled && fromWherePart.startsWith('--')) {
      showError(queryError, 'Select a type and bounding box in the Explorer first.');
      return;
    }

    let parts = [selectPart];
    if (!fromWhereDisabled) parts.push(fromWherePart);
    if (extrasPart) parts.push(extrasPart);
    const rawSQL = parts.join('\n');

    if (!rawSQL.trim()) {
      showError(queryError, 'Please enter a SQL query.');
      return;
    }

    btnQuery.disabled = true;
    btnQuery.innerHTML = '<span class="btn-spinner"></span>Running...';
    hideError(queryError);
    resultsContainer.innerHTML = '<p class="placeholder">Running query...</p>';
    resultsMeta.textContent = '';

    try {
      const tQuery = performance.now();

      let sql = prepareSQL(rawSQL);
      console.log('[query] Prepared SQL');
      console.log('[query] Final SQL:', sql.substring(0, 500) + (sql.length > 500 ? '...' : ''));

      const start = performance.now();

      console.log('[query] Executing...');
      const result = await Promise.race([
        window.duckdbConn.query(sql),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error(
            'Query timed out after 120 seconds. Try a tighter bounding box or more restrictive WHERE clause.'
          )), 120000)
        )
      ]);

      const elapsed = Math.round(performance.now() - start);
      console.log(`[query] Execution done (${elapsed} ms)`);

      const tConvert = performance.now();
      const rows = result.toArray().map(row => {
        const obj = row.toJSON();
        for (const key of Object.keys(obj)) {
          if (typeof obj[key] === 'bigint') {
            obj[key] = Number(obj[key]);
          }
        }
        return obj;
      });
      console.log(`[query] Converted ${rows.length} rows to JSON (${Math.round(performance.now() - tConvert)} ms)`);

      renderResults(rows, elapsed);
    } catch (err) {
      resultsContainer.innerHTML = '<p class="placeholder">Query failed. See error above.</p>';
      resultsMeta.textContent = '';
      showError(queryError, err.message || String(err));
    } finally {
      btnQuery.textContent = 'Run Query';
      btnQuery.disabled = false;
    }
  }

  // ============================================================
  // Tab Key Support
  // ============================================================
  function handleTabKey(e) {
    if (e.key === 'Tab') {
      e.preventDefault();
      const ta = e.target;
      const start = ta.selectionStart;
      const end = ta.selectionEnd;
      ta.value = ta.value.substring(0, start) + '  ' + ta.value.substring(end);
      ta.selectionStart = ta.selectionEnd = start + 2;
    }
  }

  function autoResizeTextarea(el) {
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  // ============================================================
  // Event Handlers
  // ============================================================
  btnSetup.addEventListener('click', runSetup);
  btnQuery.addEventListener('click', runQuery);

  document.getElementById('from-where-enabled').addEventListener('change', function () {
    var el = document.getElementById('query-from-where');
    if (this.checked) {
      el.classList.remove('disabled');
      el.disabled = false;
    } else {
      el.classList.add('disabled');
      el.disabled = true;
    }
  });

  document.getElementById('query-from-where').addEventListener('keydown', (e) => {
    handleTabKey(e);
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  });

  var fromWhereTextarea = document.getElementById('query-from-where');
  fromWhereTextarea.addEventListener('input', function () {
    autoResizeTextarea(this);
  });
  autoResizeTextarea(fromWhereTextarea);

  document.getElementById('query-select').addEventListener('keydown', (e) => {
    handleTabKey(e);
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  });

  document.getElementById('query-extras').addEventListener('keydown', (e) => {
    handleTabKey(e);
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  });

  setupEditor.addEventListener('keydown', (e) => {
    handleTabKey(e);
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runSetup();
    }
  });

  // ============================================================
  // Expose to window for module script and explorer
  // ============================================================
  window.sandboxRunSetup = runSetup;
  window.sandboxRunQuery = runQuery;
  window.sandboxShowError = showError;
  window.sandboxHideError = hideError;
  window.sandboxAutoResize = autoResizeTextarea;

})();
