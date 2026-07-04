async function renderArtifacts() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">Artifact Library</h1>
        <p class="page-subtitle">Every skill output, saved and searchable</p>
      </div>
      <button class="btn" onclick="loadArtifacts()">🔄 Refresh</button>
    </div>
    <div class="card" style="margin-bottom:16px">
      <div class="form-row">
        <div class="form-group" style="flex:2">
          <input id="artSearch" class="form-input" placeholder="Search artifacts..." oninput="debounceArtifacts()">
        </div>
        <div class="form-group">
          <select id="artSkillFilter" class="form-select" onchange="loadArtifacts()">
            <option value="">All skills</option>
          </select>
        </div>
        <div class="form-group" style="display:flex;align-items:center">
          <label class="switch" style="width:auto;display:flex;align-items:center;gap:8px">
            <input type="checkbox" id="artBookmarkedOnly" onchange="loadArtifacts()">
            <span class="switch-slider" style="position:relative;display:inline-block;width:40px;height:22px"></span>
            <span style="font-size:13px">⭐ Bookmarked</span>
          </label>
        </div>
      </div>
    </div>
    <div id="artifactGrid" class="grid grid-3"></div>
  `;
  await loadArtifacts();
}

let _artDebounce = null;
function debounceArtifacts() {
  clearTimeout(_artDebounce);
  _artDebounce = setTimeout(loadArtifacts, 300);
}

async function loadArtifacts() {
  const grid = document.getElementById('artifactGrid');
  if (!grid) return;
  grid.innerHTML = renderSkeleton(6);
  try {
    const q = (document.getElementById('artSearch') || {}).value || '';
    const skill = (document.getElementById('artSkillFilter') || {}).value || '';
    const marked = (document.getElementById('artBookmarkedOnly') || {}).checked;
    const data = await api.getArtifacts({ q, skill, bookmarked: marked ? true : undefined });
    const artifacts = data.artifacts || [];

    // Populate skill filter (preserving selection) from unfiltered listing
    const filterEl = document.getElementById('artSkillFilter');
    if (filterEl && filterEl.options.length <= 1) {
      const all = await api.getArtifacts({});
      const skills = [...new Set((all.artifacts || []).map(a => a.skill))].sort();
      filterEl.innerHTML = '<option value="">All skills</option>' +
        skills.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
      filterEl.value = skill;
    }

    if (!artifacts.length) {
      grid.innerHTML = '<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-state-icon">📦</div><div class="empty-state-title">No artifacts yet</div><div class="empty-state-desc">Run a skill — its full output lands here automatically.</div></div></div>';
      return;
    }
    grid.innerHTML = artifacts.map(a => `
      <div class="card" style="cursor:pointer;display:flex;flex-direction:column;gap:8px" onclick="openArtifact('${a.id}')">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px">
          <strong style="font-size:13px;line-height:1.4">${escapeHtml(a.title)}</strong>
          <button class="btn btn-sm" style="flex-shrink:0" onclick="event.stopPropagation();toggleArtifactBookmark('${a.id}', ${!a.bookmarked})" title="${a.bookmarked ? 'Remove bookmark' : 'Bookmark'}">${a.bookmarked ? '⭐' : '☆'}</button>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap;font-size:11px">
          <span class="badge">${escapeHtml(a.skill)}</span>
          <span class="badge" style="opacity:.7">${escapeHtml(a.agent || '')}</span>
          ${(a.tags || []).map(t => `<span class="badge" style="background:var(--accent-dim)">${escapeHtml(t)}</span>`).join('')}
        </div>
        <p style="font-size:12px;color:var(--text-secondary);margin:0;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical">${escapeHtml(a.preview || '')}</p>
        <div style="font-size:11px;color:var(--text-muted)">${(a.created || '').slice(0, 16).replace('T', ' ')}${a.source_topic ? ' · 📰 ' + escapeHtml(a.source_topic) : ''}</div>
      </div>
    `).join('');
  } catch (err) {
    grid.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-state-icon">⚠</div><div class="empty-state-title">${escapeHtml(err.message)}</div></div></div>`;
  }
}

async function openArtifact(id) {
  try {
    const a = await api.getArtifact(id);
    showModal(escapeHtml(a.title), `
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;font-size:11px">
        <span class="badge">${escapeHtml(a.skill)}</span>
        <span class="badge" style="opacity:.7">${escapeHtml(a.agent || '')}</span>
        ${a.source_topic ? `<span class="badge">📰 ${escapeHtml(a.source_topic)}</span>` : ''}
      </div>
      <div class="form-group">
        <label class="form-label">Tags (comma-separated)</label>
        <input id="artTagsInput" class="form-input" value="${escapeHtml((a.tags || []).join(', '))}">
      </div>
      <pre style="white-space:pre-wrap;font-size:12px;max-height:45vh;overflow:auto;background:var(--bg-secondary);padding:12px;border-radius:8px">${escapeHtml(a.content || '')}</pre>
    `, `
      <button class="btn" onclick="saveArtifactTags('${a.id}')">💾 Save Tags</button>
      <button class="btn btn-danger" onclick="deleteArtifactConfirm('${a.id}')">🗑 Delete</button>
      <button class="btn btn-primary" onclick="closeModal()">Close</button>
    `);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function toggleArtifactBookmark(id, bookmarked) {
  try {
    await api.updateArtifact(id, { bookmarked });
    showToast(bookmarked ? 'Bookmarked' : 'Bookmark removed', 'success');
    loadArtifacts();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function saveArtifactTags(id) {
  try {
    const tags = document.getElementById('artTagsInput').value
      .split(',').map(t => t.trim()).filter(Boolean);
    await api.updateArtifact(id, { tags });
    showToast('Tags saved', 'success');
    closeModal();
    loadArtifacts();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteArtifactConfirm(id) {
  if (!confirm('Delete this artifact permanently?')) return;
  try {
    await api.deleteArtifact(id);
    showToast('Artifact deleted', 'success');
    closeModal();
    loadArtifacts();
  } catch (err) {
    showToast(err.message, 'error');
  }
}
