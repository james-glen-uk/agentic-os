const pageCache = {};

const PAGE_BASE = '/dashboard/pages/';

// ─── Single source of truth for the sidebar nav, page titles, and icons ───
const NAV = [
  { section: 'Primary', items: [
    { key: 'chat', label: 'AI Chat', breadcrumb: 'Multi-agent conversations',
      icon: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z' },
    { key: 'dashboard', label: 'Dashboard', breadcrumb: 'Overview',
      icon: 'M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z' },
  ]},
  { section: 'Agents', items: [
    { key: 'skills', label: 'Skills Hub', breadcrumb: 'Browse & execute skills', badge: 'skillCount',
      icon: 'M13 2 3 14h7l-1 8 10-12h-7l1-8z' },
    { key: 'memory', label: 'Memory', breadcrumb: 'Shared brain context',
      icon: 'M12 2a7 7 0 0 1 7 7c0 3-2 4-2 6H7c0-2-2-3-2-6a7 7 0 0 1 7-7zM9 18h6M10 21h4' },
    { key: 'scheduler', label: 'Scheduler', breadcrumb: 'Automated workflows',
      icon: 'M12 8v4l3 3M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z' },
    { key: 'audit', label: 'Audit Log', breadcrumb: 'System activity trail',
      icon: 'M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v1H9zM9 12h6M9 16h6M9 8h6' },
  ]},
  { section: 'Workflow', items: [
    { key: 'news', label: 'News Oracle', breadcrumb: 'Trending topics → one-click content',
      icon: 'M4 5h16v14H4zM8 9h8M8 12h8M8 15h5' },
    { key: 'kanban', label: 'Kanban Board', breadcrumb: 'Multi-agent task management',
      icon: 'M4 4h4v16H4zM10 4h4v10h-4zM16 4h4v7h-4z' },
    { key: 'goals', label: 'Goals', breadcrumb: 'Project targets and progress',
      icon: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10zM12 11a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z' },
    { key: 'journal', label: 'Journal', breadcrumb: 'Daily entries and notes',
      icon: 'M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4zM9 8h6M9 12h6' },
    { key: 'artifacts', label: 'Artifacts', breadcrumb: 'Saved skill outputs',
      icon: 'M21 8 12 3 3 8l9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8' },
  ]},
  { section: 'Monitoring', items: [
    { key: 'agent-health', label: 'Agent Health', breadcrumb: 'Real-time agent monitoring',
      icon: 'M3 12h4l2-5 4 10 2-5h6' },
    { key: 'smart-router', label: 'Smart Router', breadcrumb: 'Task routing intelligence',
      icon: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM16 8l-2.5 6L8 16l2.5-6L16 8z' },
    { key: 'learning-analytics', label: 'Learning Analytics', breadcrumb: 'Skill improvement tracking',
      icon: 'M3 3v18h18M8 17V9M13 17V5M18 17v-6' },
    { key: 'session-replay', label: 'Session Replay', breadcrumb: 'Conversation history playback',
      icon: 'M3 12a9 9 0 1 0 3-6.7M3 4v5h5M10 9l6 3-6 3V9' },
    { key: 'errors', label: 'Error Dashboard', breadcrumb: 'System errors & circuit breaker',
      icon: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01' },
  ]},
  { section: 'Management', items: [
    { key: 'cost', label: 'Cost Analytics', breadcrumb: 'Usage & spending',
      icon: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zM15 9.5c-.6-1-1.7-1.5-3-1.5-1.7 0-3 .9-3 2s1.3 1.7 3 2 3 1 3 2-1.3 2-3 2c-1.3 0-2.4-.5-3-1.5M12 6v2M12 16v2' },
    { key: 'plugins', label: 'Plugin Registry', breadcrumb: 'Manage plugins',
      icon: 'M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0V8zM12 18v4' },
    { key: 'backups', label: 'Backups', breadcrumb: 'Disaster recovery',
      icon: 'M3 7a9 3.2 0 0 1 18 0v10a9 3.2 0 0 1-18 0zM3 7a9 3.2 0 0 0 18 0M3 12a9 3.2 0 0 0 18 0' },
    { key: 'prompts', label: 'Prompt Library', breadcrumb: 'Reusable templates',
      icon: 'M4 4h16v12H4zM8 8l3 3-3 3M13 14h4M8 20h8' },
    { key: 'standards', label: 'Standards', breadcrumb: 'Project conventions',
      icon: 'M12 3l7 4v5c0 5-3.5 7.5-7 9-3.5-1.5-7-4-7-9V7l7-4zM9 12l2 2 4-4' },
  ]},
  { section: 'System', items: [
    { key: 'settings', label: 'Settings', breadcrumb: 'Configuration',
      icon: 'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z' },
    { key: 'setup-wizard', label: 'Setup Wizard', breadcrumb: 'Guided configuration',
      icon: 'M15 4V2M15 10V8M11 6h2M19 6h2M17.2 4.2l-1 1M17.2 7.8l-1-1M3 21 12.8 11.2M12.8 11.2l1.4 1.4' },
  ]},
];

const NAV_INDEX = new Map(NAV.flatMap(s => s.items.map(i => [i.key, i])));

// Pages that get a contextual secondary sidebar. `load`/`onNew` are looked up
// by name on `window` at call time (not stored directly) so this config can
// be defined before the page scripts that implement them are lazy-loaded.
const SUBMENUS = {
  chat:      { title: 'Conversations', newLabel: '+ New chat',  load: 'loadChatSubmenu',      onNew: 'newConversation' },
  skills:    { title: 'Skills',        newLabel: null,          load: 'loadSkillsSubmenu' },
  memory:    { title: 'Brain files',   newLabel: null,          load: 'loadMemorySubmenu' },
  journal:   { title: 'Entries',       newLabel: '+ Today',     load: 'loadJournalSubmenu',   onNew: 'journalSubmenuNewToday' },
  artifacts: { title: 'Artifacts',     newLabel: null,          load: 'loadArtifactsSubmenu' },
  prompts:   { title: 'Prompts',       newLabel: null,          load: 'loadPromptsSubmenu' },
};

function renderSidebarNav() {
  const el = document.getElementById('sidebarNav');
  el.innerHTML = NAV.map(group => `
    <div class="sidebar-section"><div class="sidebar-section-label">${group.section}</div></div>
    ${group.items.map(item => `
      <a href="#${item.key}" class="nav-item" data-page="${item.key}">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" class="nav-icon-svg"><path d="${item.icon}"/></svg>
        <span class="nav-label">${item.label}</span>
        ${item.badge ? `<span class="nav-badge" id="${item.badge}">0</span>` : ''}
      </a>
    `).join('')}
  `).join('');
}

async function loadPage(name) {
  if (pageCache[name]) return pageCache[name];
  try {
    await loadScript(`${PAGE_BASE}${name}.js`);
    pageCache[name] = true;
  } catch (err) {
    showToast(`Failed to load page: ${name}`, 'error');
    throw err;
  }
}

function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
    const script = document.createElement('script');
    script.src = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.body.appendChild(script);
  });
}

function applySubmenuState(hash) {
  const submenu = SUBMENUS[hash];
  const aside = document.getElementById('secondarySidebar');
  if (!submenu) {
    aside.hidden = true;
    return;
  }
  aside.hidden = false;
  document.getElementById('secondaryTitle').textContent = submenu.title;
  const newLink = document.getElementById('secondaryNewLink');
  if (submenu.newLabel) {
    newLink.style.display = '';
    newLink.textContent = submenu.newLabel;
    newLink.onclick = () => { const fn = window[submenu.onNew]; if (typeof fn === 'function') fn(); };
  } else {
    newLink.style.display = 'none';
    newLink.onclick = null;
  }
  const list = document.getElementById('secondaryList');
  const loadFn = window[submenu.load];
  if (typeof loadFn === 'function') {
    loadFn();
  } else {
    list.innerHTML = renderSkeleton(3);
  }
}

function toggleSecondarySidebar() {
  // Transient per-view collapse only — re-navigating (or clicking the same
  // nav item again) re-evaluates SUBMENUS and shows it again if applicable.
  document.getElementById('secondarySidebar').hidden = true;
}

function toggleRightPanel() {
  const aside = document.getElementById('rightPanel');
  const opening = aside.hidden;
  aside.hidden = !opening;
  localStorage.setItem('rightPanelCollapsed', !opening);
  if (opening) loadBackgroundTasks();
}

async function loadBackgroundTasks() {
  const aside = document.getElementById('rightPanel');
  if (aside.hidden) return;
  const body = document.getElementById('rightPanelBody');
  try {
    const [board, eventsRes] = await Promise.all([
      api.getKanbanBoard('in_progress'),
      api.getSchedulerEvents(10).catch(() => ({ events: [] })),
    ]);
    const inProgress = (board.columns && board.columns.in_progress) || [];
    const cutoff = Date.now() - 30 * 60 * 1000;
    const recentEvents = (eventsRes.events || []).filter(e => e.timestamp && new Date(e.timestamp).getTime() >= cutoff);

    const items = [];
    inProgress.forEach(t => items.push({
      name: t.title, tag: t.assignee || 'unassigned', status: 'In progress',
    }));
    recentEvents.forEach(e => items.push({
      name: e.skill || e.action || 'scheduler event', tag: e.trigger || 'scheduler',
      status: `ran ${timeAgo(e.timestamp)}`,
    }));

    body.innerHTML = items.length ? items.map(t => `
      <div class="task-item">
        <div class="task-item-name">${escapeHtml(t.name)}</div>
        <div class="task-item-meta">
          <span class="task-item-tag mono">${escapeHtml(t.tag)}</span>
          <span class="task-item-status">${escapeHtml(t.status)}</span>
        </div>
      </div>
    `).join('') : `<div class="empty-state-desc">Nothing running right now</div>`;
  } catch {
    body.innerHTML = `<div class="empty-state-desc">Failed to load background tasks</div>`;
  }
}

async function navigate(page) {
  const hash = page || window.location.hash.slice(1) || 'dashboard';
  if (!hash) { window.location.hash = 'dashboard'; return; }

  if (typeof window.__pageUnload === 'function') {
    try { window.__pageUnload(); } catch { /* ignore */ }
  }
  window.__pageUnload = null;

  // Show loading bar
  const bar = document.getElementById('topLoadingBar');
  if (bar) { bar.classList.add('active'); bar.style.width = '30%'; }

  document.querySelectorAll('.nav-item, .bottom-nav-item').forEach(el => el.classList.remove('active'));
  const navItem = document.querySelector(`[data-page="${hash}"]`);
  if (navItem) navItem.classList.add('active');

  const info = NAV_INDEX.get(hash) || { label: 'Unknown', breadcrumb: '' };
  document.getElementById('pageTitle').textContent = info.label;
  document.getElementById('pageBreadcrumb').textContent = info.breadcrumb;

  const content = document.getElementById('pageContent');
  content.innerHTML = `<div class="loading"><div class="loading-spinner"></div><span>Loading ${info.label}...</span></div>`;

  try {
    await loadPage(hash);
    const renderFn = window[`render${capitalize(hash.replace(/-./g, m => m[1].toUpperCase()))}`];
    if (renderFn) {
      content.innerHTML = '';
      content.className = 'page-content page-enter';
      if (bar) bar.style.width = '70%';
      await renderFn();
      if (bar) { bar.style.width = '100%'; setTimeout(() => { bar.style.width = '0'; bar.classList.remove('active'); }, 400); }
      applySubmenuState(hash);
    } else {
      content.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔍</div><div class="empty-state-title">Page not found</div><div class="empty-state-desc">The page "${hash}" doesn't have a render function</div></div>`;
      if (bar) { bar.style.width = '0'; bar.classList.remove('active'); }
      document.getElementById('secondarySidebar').hidden = true;
    }
  } catch (err) {
    content.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠</div><div class="empty-state-title">Failed to load</div><div class="empty-state-desc">${escapeHtml(err.message)}</div><button class="btn btn-primary mt-3" onclick="navigate('dashboard')">Go to Dashboard</button></div>`;
    if (bar) { bar.style.width = '0'; bar.classList.remove('active'); }
    document.getElementById('secondarySidebar').hidden = true;
  }
}

function capitalize(str) { return str.charAt(0).toUpperCase() + str.slice(1); }

function focusGlobalSearch() {
  const input = document.getElementById('globalSearch');
  if (input) { input.focus(); input.scrollIntoView({ block: 'nearest' }); }
}

async function updateAgentStatus() {
  const dot = document.getElementById('titlebarAgentDot');
  const text = document.getElementById('titlebarAgentText');
  try {
    const status = await api.getStatus();
    const agents = status.agents || [];
    const online = agents.filter(a => a.status === 'online').length;
    const total = agents.length;
    if (online === total) { dot.className = 'titlebar-status-dot online'; text.textContent = `${online}/${total} agents online`; }
    else if (online > 0) { dot.className = 'titlebar-status-dot warning'; text.textContent = `${online}/${total} agents online`; }
    else { dot.className = 'titlebar-status-dot offline'; text.textContent = 'All agents offline'; }

    const badge = document.getElementById('skillCount');
    if (badge && status.skills_count !== undefined) badge.textContent = status.skills_count;
  } catch {
    dot.className = 'titlebar-status-dot offline';
    text.textContent = 'Disconnected';
  }
}

window.addEventListener('hashchange', () => navigate());
window.addEventListener('DOMContentLoaded', () => {
  renderSidebarNav();
  document.getElementById('titlebarHost').textContent = window.location.host;
  loadUIState();
  navigate(window.location.hash.slice(1) || 'dashboard');
  updateAgentStatus();
  setInterval(updateAgentStatus, 15000);
  setInterval(loadBackgroundTasks, 20000);
});
