async function renderNews() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">News Oracle</h1>
        <p class="page-subtitle">Trending topics, refreshed daily — one click to content</p>
      </div>
      <div class="btn-group">
        <select id="newsDateSelect" class="form-select" onchange="loadNews(this.value)" style="display:none"></select>
        <button class="btn btn-primary" id="newsRefreshBtn" onclick="refreshNewsFeeds()">🔄 Refresh Feeds</button>
      </div>
    </div>
    <div id="newsMeta" style="margin-bottom:14px"></div>
    <div id="newsTopics" class="grid grid-2"></div>
  `;
  await loadNews();
}

async function loadNews(date) {
  const grid = document.getElementById('newsTopics');
  const meta = document.getElementById('newsMeta');
  if (!grid) return;
  grid.innerHTML = renderSkeleton(4);
  try {
    const data = await api.getNewsTopics(date);

    const sel = document.getElementById('newsDateSelect');
    if (sel && (data.available_dates || []).length) {
      sel.style.display = '';
      sel.innerHTML = data.available_dates.map(d =>
        `<option value="${d}" ${d === data.date ? 'selected' : ''}>${d}</option>`).join('');
    }

    if (!data.topics || !data.topics.length) {
      meta.innerHTML = '';
      grid.innerHTML = '<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-state-icon">📰</div><div class="empty-state-title">No topics yet</div><div class="empty-state-desc">Click "Refresh Feeds" to pull the latest news, or wait for the daily 07:00 run.</div></div></div>';
      return;
    }

    const stale = data.age_hours !== null && data.age_hours > 26;
    meta.innerHTML = `
      <span class="badge">${escapeHtml(data.date || '')}</span>
      <span class="badge" style="${stale ? 'background:var(--yellow-dim);color:var(--yellow)' : ''}">
        ${data.age_hours !== null ? (stale ? '⚠ ' : '') + data.age_hours + 'h old' : 'age unknown'}
      </span>
      <span class="badge" style="opacity:.7">${data.entry_count || 0} stories from ${data.feed_count || 0} feeds</span>
    `;

    grid.innerHTML = data.topics.map(t => `
      <div class="card" style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;align-items:flex-start;gap:10px">
          <span class="badge" style="flex-shrink:0">#${t.rank}</span>
          <div>
            <strong style="font-size:14px;line-height:1.4">${escapeHtml(t.title)}</strong>
            ${t.summary ? `<p style="font-size:12px;color:var(--text-secondary);margin:6px 0 0">${escapeHtml(t.summary)}</p>` : ''}
          </div>
          ${t.count > 1 ? `<span class="badge" style="margin-left:auto;flex-shrink:0">${t.count} stories</span>` : ''}
        </div>
        <div style="display:flex;flex-direction:column;gap:4px">
          ${(t.headlines || []).map(h => `
            <a href="${escapeHtml(h.link)}" target="_blank" rel="noopener" style="font-size:12px;color:var(--text-secondary);text-decoration:none">
              ↗ ${escapeHtml(h.title)} <span style="color:var(--text-muted)">· ${escapeHtml(h.source || '')}</span>
            </a>`).join('')}
        </div>
        <div class="btn-group" style="margin-top:auto">
          <button class="btn btn-sm" id="seo-${t.rank}" onclick="runTopicSkill('seo-article', ${t.rank})">📝 SEO Article</button>
          <button class="btn btn-sm" id="social-${t.rank}" onclick="runTopicSkill('social-drafts', ${t.rank})">📣 Social Drafts</button>
        </div>
      </div>
    `).join('');

    window._newsTopics = data.topics;
  } catch (err) {
    grid.innerHTML = `<div style="grid-column:1/-1"><div class="empty-state"><div class="empty-state-icon">⚠</div><div class="empty-state-title">${escapeHtml(err.message)}</div></div></div>`;
  }
}

async function refreshNewsFeeds() {
  const btn = document.getElementById('newsRefreshBtn');
  btn.disabled = true; btn.textContent = '⏳ Fetching feeds...';
  try {
    await api.refreshNews();
    showToast('News refreshed', 'success');
    await loadNews();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = '🔄 Refresh Feeds';
  }
}

async function runTopicSkill(skillName, rank) {
  const topic = (window._newsTopics || []).find(t => t.rank === rank);
  if (!topic) { showToast('Topic not found — refresh the page', 'error'); return; }
  const btn = document.getElementById(`${skillName === 'seo-article' ? 'seo' : 'social'}-${rank}`);
  const original = btn.textContent;
  btn.disabled = true; btn.textContent = '⏳ Working...';
  try {
    const context = [
      `Topic: ${topic.title}`,
      topic.summary ? `Summary: ${topic.summary}` : '',
      topic.keywords && topic.keywords.length ? `Keywords: ${topic.keywords.join(', ')}` : '',
      'Source headlines:',
      ...(topic.headlines || []).map(h => `- ${h.title} (${h.link})`),
    ].filter(Boolean).join('\n');

    const result = await api.runSkill(skillName, context, 'auto', topic.title);
    if (result.status === 'completed') {
      showToast(`${skillName} done via ${result.agent} — saved to Artifacts`, 'success');
      if (result.artifact_id) openArtifactFromNews(result.artifact_id);
    } else {
      showToast(`${skillName} failed on all agents — see Error Dashboard`, 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = original;
  }
}

async function openArtifactFromNews(artifactId) {
  try {
    const a = await api.getArtifact(artifactId);
    showModal(escapeHtml(a.title), `
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px;font-size:11px">
        <span class="badge">${escapeHtml(a.skill)}</span>
        <span class="badge" style="opacity:.7">${escapeHtml(a.agent || '')}</span>
      </div>
      <pre style="white-space:pre-wrap;font-size:12px;max-height:50vh;overflow:auto;background:var(--bg-secondary);padding:12px;border-radius:8px">${escapeHtml(a.content || '')}</pre>
    `, `
      <button class="btn" onclick="closeModal();navigate('artifacts')">📦 Open Library</button>
      <button class="btn btn-primary" onclick="closeModal()">Close</button>
    `);
  } catch (err) {
    showToast(err.message, 'error');
  }
}
