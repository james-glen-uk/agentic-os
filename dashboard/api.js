const api = {
  async get(path) {
    const r = await fetch(path);
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `Request failed: ${r.status}`); }
    return r.json();
  },
  async post(path, body = {}, controller) {
    const opts = { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
    if (controller) opts.signal = controller.signal;
    const r = await fetch(path, opts);
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `Request failed: ${r.status}`); }
    return r.json();
  },
  async put(path, body = {}) {
    const r = await fetch(path, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `Request failed: ${r.status}`); }
    return r.json();
  },
  async patch(path, body = {}) {
    const r = await fetch(path, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `Request failed: ${r.status}`); }
    return r.json();
  },
  async del(path) {
    const r = await fetch(path, { method: 'DELETE' });
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || `Request failed: ${r.status}`); }
    return r.json();
  },
  getStatus: () => api.get('/api/status'),
  getBrain: () => api.get('/api/brain'),
  getBrainFile: (name) => api.get(`/api/brain/${encodeURIComponent(name)}`),
  updateBrainFile: (name, content) => api.put(`/api/brain/${encodeURIComponent(name)}`, { content }),
  getSkills: () => api.get('/api/skills'),
  getSkill: (name) => api.get(`/api/skills/${encodeURIComponent(name)}`),
  runSkill: (name, input = '', agent = 'auto', topic = '') => api.post(`/api/skills/${encodeURIComponent(name)}/run`, { input, agent, topic }),
  getSkillEval: (name) => api.get(`/api/skills/${encodeURIComponent(name)}/eval`),
  getJobs: () => api.get('/api/scheduler/jobs'),
  createJob: (job) => api.post('/api/scheduler/jobs', job),
  deleteJob: (id) => api.del(`/api/scheduler/jobs/${encodeURIComponent(id)}`),
  getAudit: (limit = 100) => api.get(`/api/audit?limit=${limit}`),
  getCost: () => api.get('/api/cost'),
  recordCost: (data) => api.post('/api/cost/record', data),
  getPlugins: () => api.get('/api/plugins'),
  installPlugin: (name) => api.post('/api/plugins/install', { name }),
  getBackups: () => api.get('/api/backups'),
  createBackup: () => api.post('/api/backup'),
  restoreBackup: (file) => api.post('/api/backup/restore', { file }),
  exportSaveFile: () => api.post('/api/export'),
  listExports: () => api.get('/api/exports'),
  importSaveFile: (file, apply) => api.post('/api/import', { file, apply }),
  getPrompts: () => api.get('/api/prompts'),
  getSettings: () => api.get('/api/settings'),
  updateSettings: (settings) => api.put('/api/settings', { settings }),
  getStandards: () => api.get('/api/standards'),
  discoverStandards: () => api.post('/api/standards/discover'),
  chat: (agent, message, conversationId, controller) =>
    api.post('/api/chat', { agent, message, conversation_id: conversationId || undefined }, controller),
  getChatHistory: () => api.get('/api/chat/history'),
  getConversations: () => api.get('/api/conversations'),
  createConversation: (title) => api.post('/api/conversations', { title }),
  getConversation: (id) => api.get(`/api/conversations/${encodeURIComponent(id)}`),
  deleteConversation: (id) => api.del(`/api/conversations/${encodeURIComponent(id)}`),
  // Kanban
  getKanbanBoard: (status) => api.get(status ? `/api/kanban/board?status=${encodeURIComponent(status)}` : '/api/kanban/board'),
  getKanbanTask: (id) => api.get(`/api/kanban/tasks/${encodeURIComponent(id)}`),
  createKanbanTask: (data) => api.post('/api/kanban/tasks', data),
  updateKanbanTask: (id, data) => api.patch(`/api/kanban/tasks/${encodeURIComponent(id)}`, data),
  completeKanbanTask: (id, summary) => api.post(`/api/kanban/tasks/${encodeURIComponent(id)}/complete`, { summary }),
  blockKanbanTask: (id, reason) => api.post(`/api/kanban/tasks/${encodeURIComponent(id)}/block`, { reason }),
  unblockKanbanTask: (id) => api.post(`/api/kanban/tasks/${encodeURIComponent(id)}/unblock`, {}),
  addKanbanComment: (id, message) => api.post(`/api/kanban/tasks/${encodeURIComponent(id)}/comments`, { message }),
  linkKanbanTasks: (parentId, childId) => api.post('/api/kanban/links', { parent_id: parentId, child_id: childId }),
  unlinkKanbanTasks: (parentId, childId) => api.del(`/api/kanban/links?parent_id=${encodeURIComponent(parentId)}&child_id=${encodeURIComponent(childId)}`),
  dispatchKanban: () => api.post('/api/kanban/dispatch', {}),
  specifyKanbanTask: (id) => api.post(`/api/kanban/tasks/${encodeURIComponent(id)}/specify`, {}),
  decomposeKanbanTask: (id) => api.post(`/api/kanban/tasks/${encodeURIComponent(id)}/decompose`, {}),
  buildKanbanTask: (id) => api.post(`/api/kanban/tasks/${encodeURIComponent(id)}/build`, {}),
  previewKanbanBuild: (id, file) => api.get(`/api/kanban/tasks/${encodeURIComponent(id)}/preview${file ? '?file=' + encodeURIComponent(file) : ''}`),
  // Goals
  getGoals: () => api.get('/api/goals'),
  createGoal: (data) => api.post('/api/goals', data),
  updateGoal: (id, data) => api.put(`/api/goals/${encodeURIComponent(id)}`, data),
  deleteGoal: (id) => api.del(`/api/goals/${encodeURIComponent(id)}`),
  // Journal
  getJournalEntries: () => api.get('/api/journal/entries'),
  getJournalEntry: (date) => api.get(`/api/journal/entries/${encodeURIComponent(date)}`),
  saveJournalEntry: (date, content) => api.put(`/api/journal/entries/${encodeURIComponent(date)}`, { content }),
  searchJournal: (query) => api.get(`/api/journal/search?q=${encodeURIComponent(query)}`),
  // Agent Health
  getAgentHealth: () => api.get('/api/agents/health'),
  getAgentStats: (name) => api.get(`/api/agents/${encodeURIComponent(name)}/stats`),
  refreshAgentHealth: () => api.post('/api/agents/health/refresh', {}),
  // Smart Router
  suggestRouter: (task) => api.post('/api/router/suggest', { task }),
  routeTask: (task, agent) => api.post('/api/router/route', { task, agent }),
  // Learning Analytics
  getSkillAnalytics: () => api.get('/api/analytics/skills'),
  getTrendAnalytics: () => api.get('/api/analytics/trends'),
  // Session Replay
  listSessions: () => api.get('/api/sessions/list'),
  getSessionReplay: (id) => api.get(`/api/sessions/${encodeURIComponent(id)}/replay`),
  // v0.3.0: Scheduler Events
  getSchedulerEvents: (limit) => api.get(`/api/scheduler/events?limit=${limit || 50}`),
  triggerJob: (id) => api.post(`/api/scheduler/trigger/${encodeURIComponent(id)}`, {}),
  sendWebhook: (data) => api.post('/api/webhook', data),
  // v0.3.0: Error Tracking
  getErrors: (limit, category) => api.get(`/api/errors?limit=${limit || 50}${category ? `&category=${encodeURIComponent(category)}` : ''}`),
  reportError: (data) => api.post('/api/errors/report', data),
  clearErrors: () => api.del('/api/errors'),
  // v0.3.0: Circuit Breaker
  getCircuitBreaker: () => api.get('/api/circuit-breaker'),
  tripCircuitBreaker: (agent) => api.post('/api/circuit-breaker/trip', { agent }),
  resetCircuitBreaker: (agent) => api.post('/api/circuit-breaker/reset', { agent }),
  // News Oracle
  getNewsTopics: (date) => api.get(`/api/news/topics${date ? '?date=' + encodeURIComponent(date) : ''}`),
  refreshNews: () => api.post('/api/news/refresh', {}),
  // Benchmark
  getBenchTasks: () => api.get('/api/bench/tasks'),
  runBench: (agents) => api.post('/api/bench/run', agents ? { agents } : {}),
  getBenchResults: () => api.get('/api/bench/results'),
  // Orchestration
  getRoles: () => api.get('/api/roles'),
  startOrchestration: (goal, max_subtasks) => api.post('/api/orchestrate', { goal, max_subtasks }),
  listOrchestrations: () => api.get('/api/orchestrate'),
  getOrchestration: (id) => api.get(`/api/orchestrate/${encodeURIComponent(id)}`),
  // Artifact Library
  getArtifacts: (params = {}) => {
    const qs = Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== '')
      .map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join('&');
    return api.get(`/api/artifacts${qs ? '?' + qs : ''}`);
  },
  getArtifact: (id) => api.get(`/api/artifacts/${encodeURIComponent(id)}`),
  updateArtifact: (id, data) => api.patch(`/api/artifacts/${encodeURIComponent(id)}`, data),
  deleteArtifact: (id) => api.del(`/api/artifacts/${encodeURIComponent(id)}`),
  // v0.3.0: PWA
  getManifest: () => api.get('/manifest.json'),
};
