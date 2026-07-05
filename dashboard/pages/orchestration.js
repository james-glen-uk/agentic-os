let _orchPollTimer = null;

async function renderOrchestration() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">Orchestration</h1>
        <p class="page-subtitle">Give a goal to your AI company — it decomposes, delegates, and delivers</p>
      </div>
      <button class="btn" onclick="loadOrchestrations()">🔄 Refresh</button>
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="card-header"><span class="card-title">🏛 The Org</span></div>
      <div id="orgRoles" class="grid grid-3"></div>
    </div>

    <div class="card" style="margin-bottom:16px">
      <div class="form-group">
        <label class="form-label">Goal</label>
        <textarea id="orchGoal" class="form-input" rows="2" placeholder="e.g. Draft a go-to-market plan for a developer tool launch"></textarea>
      </div>
      <div class="form-row" style="align-items:flex-end">
        <div class="form-group" style="max-width:160px">
          <label class="form-label">Max subtasks</label>
          <input id="orchMax" class="form-input" type="number" value="4" min="1" max="8">
        </div>
        <button class="btn btn-primary" id="orchRunBtn" onclick="startOrchestration()">🚀 Orchestrate</button>
      </div>
    </div>

    <div id="orchActive"></div>
    <h2 style="font-size:15px;margin:18px 0 10px">Recent runs</h2>
    <div id="orchRuns" class="grid grid-2"></div>
  `;
  await Promise.all([loadRoles(), loadOrchestrations()]);
}

async function loadRoles() {
  const el = document.getElementById('orgRoles');
  if (!el) return;
  try {
    const roles = (await api.getRoles()).roles || [];
    const icons = { ceo: '👔', cto: '🛠', researcher: '🔬', builder: '⚙️', reviewer: '🔍' };
    el.innerHTML = roles.map(r => `
      <div class="card" style="padding:12px">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
          <span style="font-size:18px">${icons[r.name] || '🤖'}</span>
          <strong style="text-transform:capitalize">${escapeHtml(r.name)}</strong>
          <span class="badge" style="margin-left:auto">${escapeHtml(r.primary)}</span>
        </div>
        <p style="font-size:11px;color:var(--text-secondary);margin:0">${escapeHtml(r.summary || '')}</p>
      </div>
    `).join('');
  } catch (err) {
    el.innerHTML = `<div class="empty-state-title">${escapeHtml(err.message)}</div>`;
  }
}

async function startOrchestration() {
  const goal = document.getElementById('orchGoal').value.trim();
  if (!goal) { showToast('Enter a goal first', 'warning'); return; }
  const max = parseInt(document.getElementById('orchMax').value) || 4;
  const btn = document.getElementById('orchRunBtn');
  btn.disabled = true; btn.textContent = '⏳ Starting...';
  try {
    const run = await api.startOrchestration(goal, max);
    showToast('Orchestration started', 'success');
    document.getElementById('orchGoal').value = '';
    pollOrchestration(run.id);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '🚀 Orchestrate';
  }
}

function statusBadge(status) {
  const map = {
    planning: ['var(--yellow)', '🧠 planning'], running: ['var(--accent)', '⚙️ running'],
    completed: ['var(--green)', '✓ completed'], failed: ['var(--red)', '✕ failed'],
    pending: ['var(--text-muted)', 'pending'], done: ['var(--green)', '✓ done'],
    skipped: ['var(--text-muted)', 'skipped'],
  };
  const [color, label] = map[status] || ['var(--text-muted)', status];
  return `<span class="badge" style="color:${color}">${label}</span>`;
}

function renderRunDetail(run) {
  const roleIcons = { ceo: '👔', cto: '🛠', researcher: '🔬', builder: '⚙️', reviewer: '🔍' };
  return `
    <div class="card" style="border-color:var(--accent-dim)">
      <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <strong style="font-size:14px">${escapeHtml(run.goal)}</strong>
        <span style="margin-left:auto">${statusBadge(run.status)}</span>
      </div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;font-size:11px;margin-bottom:12px">
        <span class="badge" style="opacity:.7">${run.calls_made} agent calls</span>
        <span class="badge" style="opacity:.7">$${(run.spend_usd || 0).toFixed(3)}</span>
        <span class="badge" style="opacity:.7">${run.subtasks.length} subtasks</span>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">
        ${run.subtasks.map(st => `
          <div style="display:flex;align-items:flex-start;gap:10px;padding:8px;background:var(--bg-secondary);border-radius:8px">
            <span style="font-size:16px">${roleIcons[st.role] || '🤖'}</span>
            <div style="flex:1;min-width:0">
              <div style="display:flex;align-items:center;gap:8px">
                <strong style="font-size:12px;text-transform:capitalize">${escapeHtml(st.role)}</strong>
                <span style="font-size:12px;color:var(--text-secondary)">${escapeHtml(st.title)}</span>
                <span style="margin-left:auto">${statusBadge(st.status)}</span>
              </div>
              ${st.output_preview ? `<p style="font-size:11px;color:var(--text-muted);margin:4px 0 0;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical">${escapeHtml(st.output_preview)}</p>` : ''}
              ${st.artifact_id ? `<a href="#" onclick="event.preventDefault();openOrchArtifact('${st.artifact_id}')" style="font-size:11px;color:var(--accent)">📦 view output</a>` : ''}
            </div>
          </div>
        `).join('')}
      </div>
      ${run.artifact_id && run.status === 'completed' ? `
        <button class="btn btn-primary btn-sm" style="margin-top:12px" onclick="openOrchArtifact('${run.artifact_id}')">📄 View Final Deliverable</button>
      ` : ''}
      ${run.error ? `<p style="color:var(--red);font-size:12px;margin-top:8px">${escapeHtml(run.error)}</p>` : ''}
    </div>
  `;
}

async function pollOrchestration(runId) {
  clearInterval(_orchPollTimer);
  const active = document.getElementById('orchActive');
  const tick = async () => {
    try {
      const run = await api.getOrchestration(runId);
      if (active) active.innerHTML = renderRunDetail(run);
      if (run.status === 'completed' || run.status === 'failed') {
        clearInterval(_orchPollTimer);
        loadOrchestrations();
      }
    } catch { clearInterval(_orchPollTimer); }
  };
  await tick();
  _orchPollTimer = setInterval(tick, 2000);
}

async function loadOrchestrations() {
  const el = document.getElementById('orchRuns');
  if (!el) return;
  try {
    const runs = (await api.listOrchestrations()).runs || [];
    if (!runs.length) {
      el.innerHTML = '<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-state-icon">🏛</div><div class="empty-state-title">No runs yet</div><div class="empty-state-desc">Give your AI company a goal above.</div></div></div>';
      return;
    }
    el.innerHTML = runs.map(run => `
      <div class="card" style="cursor:pointer" onclick="pollOrchestration('${run.id}')">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <strong style="font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escapeHtml(run.goal)}</strong>
          <span style="margin-left:auto;flex-shrink:0">${statusBadge(run.status)}</span>
        </div>
        <div style="font-size:11px;color:var(--text-muted)">${(run.created || '').slice(0, 16).replace('T', ' ')} · ${run.subtasks.length} subtasks · $${(run.spend_usd || 0).toFixed(3)}</div>
      </div>
    `).join('');
  } catch (err) {
    el.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state-title">${escapeHtml(err.message)}</div></div>`;
  }
}

async function openOrchArtifact(artifactId) {
  try {
    const a = await api.getArtifact(artifactId);
    showModal(escapeHtml(a.title), `
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;font-size:11px">
        <span class="badge">${escapeHtml(a.skill)}</span>
        <span class="badge" style="opacity:.7">${escapeHtml(a.agent || '')}</span>
      </div>
      <pre style="white-space:pre-wrap;font-size:12px;max-height:55vh;overflow:auto;background:var(--bg-secondary);padding:12px;border-radius:8px">${escapeHtml(a.content || '')}</pre>
    `, `
      <button class="btn" onclick="closeModal();navigate('artifacts')">📦 Library</button>
      <button class="btn btn-primary" onclick="closeModal()">Close</button>
    `);
  } catch (err) {
    showToast(err.message, 'error');
  }
}
