async function renderBench() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">Benchmark</h1>
        <p class="page-subtitle">Score your agents on a shared eval set — the leaderboard feeds quality routing</p>
      </div>
      <button class="btn btn-primary" id="benchRunBtn" onclick="runBench()">▶ Run Benchmark</button>
    </div>
    <div id="benchTasks" style="margin-bottom:16px"></div>
    <div id="benchBoard"></div>
  `;
  await Promise.all([loadBenchTasks(), loadBenchResults()]);
}

async function loadBenchTasks() {
  const el = document.getElementById('benchTasks');
  if (!el) return;
  try {
    const tasks = (await api.getBenchTasks()).tasks || [];
    el.innerHTML = `<div style="font-size:12px;color:var(--text-muted)">${tasks.length} tasks: ${tasks.map(t => escapeHtml(t.name)).join(' · ')}</div>`;
  } catch { el.innerHTML = ''; }
}

async function runBench() {
  const btn = document.getElementById('benchRunBtn');
  btn.disabled = true; btn.textContent = '⏳ Running (uses real agent calls)…';
  try {
    await api.runBench();
    showToast('Benchmark complete', 'success');
    await loadBenchResults();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '▶ Run Benchmark';
  }
}

async function loadBenchResults() {
  const el = document.getElementById('benchBoard');
  if (!el) return;
  try {
    const res = await api.getBenchResults();
    const board = res.leaderboard || [];
    if (!board.length) {
      el.innerHTML = '<div class="empty-state"><div class="empty-state-icon">🏁</div><div class="empty-state-title">No results yet</div><div class="empty-state-desc">Run the benchmark to score your online agents.</div></div>';
      return;
    }
    const medal = ['🥇', '🥈', '🥉'];
    const icons = { opencode: '🔧', hermes: '⚡', gemini: '🧠', claude: '🤖' };
    el.innerHTML = `
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">Last run: ${(res.ran_at || '').slice(0, 16).replace('T', ' ')} · ${res.task_count} tasks</div>
      <div class="table-wrapper"><table>
        <thead><tr><th>#</th><th>Agent</th><th>Avg Score</th><th>Avg Latency</th><th>Cost</th></tr></thead>
        <tbody>
          ${board.map((r, i) => `
            <tr>
              <td>${medal[i] || (i + 1)}</td>
              <td>${icons[r.agent] || '🤖'} <strong>${escapeHtml(r.agent)}</strong></td>
              <td><div style="display:flex;align-items:center;gap:8px"><div style="flex:1;max-width:120px;height:8px;background:var(--bg-secondary);border-radius:4px;overflow:hidden"><div style="width:${r.avg_score}%;height:100%;background:var(--green)"></div></div><span>${r.avg_score}</span></div></td>
              <td>${r.avg_latency}s</td>
              <td>${r.cost ? '$' + r.cost.toFixed(3) : '$0'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table></div>
      <p style="font-size:12px;color:var(--text-muted);margin-top:10px">Set <strong>Routing → Quality</strong> in Settings to route to the top-ranked agent first.</p>
    `;
  } catch (err) {
    el.innerHTML = `<div class="empty-state-title">${escapeHtml(err.message)}</div>`;
  }
}
