async function renderBackups() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">Backups</h1>
        <p class="page-subtitle">System snapshots and disaster recovery</p>
      </div>
      <div class="btn-group">
        <button class="btn" onclick="exportSaveFile()">📦 Export Save File</button>
        <button class="btn btn-primary" onclick="createBackup()">+ New Backup</button>
      </div>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">📦 Save Files (shareable, no secrets)</span></div>
      <p style="font-size:12px;color:var(--text-secondary);margin:0 0 10px">An export bundles your config, skills, roles, and prompts — <strong>excluding API keys and runtime data</strong> — so you can share your setup. Import reports any CLIs or keys the recipient still needs.</p>
      <div id="exportList"></div>
    </div>
    <div id="backupList"><div class="loading"><div class="loading-spinner"></div></div></div>
  `;

  loadExports();
  try {
    const backups = await api.getBackups();
    const container = document.getElementById('backupList');

    if (backups.length === 0) {
      container.innerHTML = '<div class="empty-state"><div class="empty-state-icon">💾</div><div class="empty-state-title">No backups yet</div><div class="empty-state-desc">Create your first backup to protect your system configuration</div><button class="btn btn-primary mt-3" onclick="createBackup()">Create Backup</button></div>';
      return;
    }

    container.innerHTML = `
      <div class="table-wrapper">
        <table>
          <thead><tr><th>Name</th><th>Size</th><th>Created</th><th></th></tr></thead>
          <tbody>
            ${backups.map(b => `
              <tr>
                <td><strong>${escapeHtml(b.name)}</strong></td>
                <td>${formatBytes(b.size)}</td>
                <td style="font-size:12px">${formatDate(b.created)}</td>
                <td><button class="btn btn-sm btn-danger" onclick="restoreBackup('${encodeURIComponent(b.name)}')">Restore</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      <div style="font-size:12px;color:var(--text-muted);text-align:right;margin-top:8px">${backups.length} backup${backups.length !== 1 ? 's' : ''}</div>
    `;
  } catch (err) {
    document.getElementById('backupList').innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠</div><div class="empty-state-title">${escapeHtml(err.message)}</div></div>`;
  }
}

async function loadExports() {
  const el = document.getElementById('exportList');
  if (!el) return;
  try {
    const exports = (await api.listExports()).exports || [];
    if (!exports.length) {
      el.innerHTML = '<div style="font-size:12px;color:var(--text-muted)">No save files yet — click "Export Save File".</div>';
      return;
    }
    el.innerHTML = exports.map(e => `
      <div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)">
        <strong style="font-size:12px;flex:1">${escapeHtml(e.name)}</strong>
        <span style="font-size:11px;color:var(--text-muted)">${formatBytes(e.size)}</span>
        <button class="btn btn-sm" onclick="importSaveFile('${encodeURIComponent(e.name)}')">Import</button>
      </div>
    `).join('');
  } catch (err) {
    el.innerHTML = `<div style="font-size:12px;color:var(--red)">${escapeHtml(err.message)}</div>`;
  }
}

async function exportSaveFile() {
  try {
    const r = await api.exportSaveFile();
    showToast(`Exported ${r.file} (${formatBytes(r.size)})`, 'success');
    loadExports();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function importSaveFile(encodedName) {
  const name = decodeURIComponent(encodedName);
  try {
    // Dry run first to show the dependency report before applying
    const report = await api.importSaveFile(name, false);
    const missing = report.missing_dependencies || {};
    const deps = [
      ...(missing.agent_clis || []).map(a => `CLI: <strong>${escapeHtml(a)}</strong>`),
      ...(missing.api_keys || []).map(k => `API key: <strong>${escapeHtml(k)}</strong>`),
    ];
    showModal('Import Save File', `
      <p style="font-size:13px;margin-bottom:8px">Import <strong>${escapeHtml(name)}</strong>? This overwrites config (brain, skills, agents, prompts) but <strong>never your API keys</strong>.</p>
      ${deps.length
        ? `<div class="card" style="background:var(--yellow-dim);border-color:transparent"><div style="font-size:12px;font-weight:600;margin-bottom:4px">⚠ Still needed after import:</div><div style="font-size:12px">${deps.join('<br>')}</div></div>`
        : `<div style="font-size:12px;color:var(--green)">✓ All dependencies satisfied.</div>`}
    `, `
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="confirmImport('${encodeURIComponent(name)}')">Import</button>
    `);
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function confirmImport(encodedName) {
  const name = decodeURIComponent(encodedName);
  try {
    await api.importSaveFile(name, true);
    closeModal();
    showToast('Save file imported', 'success');
    renderBackups();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function createBackup() {
  try {
    const r = await api.createBackup();
    showToast(`Backup created: ${r.file} (${formatBytes(r.size)})`, 'success');
    renderBackups();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function restoreBackup(encodedName) {
  const name = decodeURIComponent(encodedName);
  showModal('Restore Backup', `
    <p style="font-size:13px;color:var(--text-secondary);margin-bottom:8px">Restore <strong>${escapeHtml(name)}</strong>? This will overwrite current brain, skills, agents, registry, standards, and prompts data.</p>
    <div class="card" style="background:var(--red-dim);border-color:transparent">
      <div class="flex items-center gap-2"><span>⚠</span><span style="font-size:13px;font-weight:500">This action cannot be undone</span></div>
    </div>
  `, `
    <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
    <button class="btn btn-danger" onclick="confirmRestore('${encodeURIComponent(name)}')">Restore</button>
  `);
}

async function confirmRestore(encodedName) {
  const name = decodeURIComponent(encodedName);
  try {
    const r = await api.restoreBackup(name);
    closeModal();
    showToast('Backup restored successfully', 'success');
    renderBackups();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}
