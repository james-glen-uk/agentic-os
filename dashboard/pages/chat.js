async function renderChat() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">AI Chat</h1>
        <p class="page-subtitle">Talk to opencode, Hermes, Gemini CLI, and Claude Code</p>
      </div>
      <div class="btn-group">
        <button class="btn" onclick="deleteActiveConversation()">🗑 Delete conversation</button>
        <button class="btn" onclick="refreshChat()">🔄 Refresh</button>
      </div>
    </div>
    <div class="chat-layout">
      <div class="chat-main">
        <div class="chat-agent-row" id="chatAgentRow">
          <div class="chat-agent-pill active" data-agent="opencode" onclick="selectAgent('opencode')">
            <div class="agent-dot online"></div><span>opencode</span>
          </div>
          <div class="chat-agent-pill" data-agent="hermes" onclick="selectAgent('hermes')">
            <div class="agent-dot online"></div><span>Hermes</span>
          </div>
          <div class="chat-agent-pill" data-agent="gemini" onclick="selectAgent('gemini')">
            <div class="agent-dot offline"></div><span>Gemini CLI</span>
          </div>
          <div class="chat-agent-pill" data-agent="claude" onclick="selectAgent('claude')">
            <div class="agent-dot offline"></div><span>Claude Code</span>
          </div>
          <div style="flex:1"></div>
          <div id="chatAgentStatus" class="mono" style="font-size:11px;color:var(--text3)">opencode • ready</div>
        </div>
        <div id="chatMessages" class="chat-messages">
          <div class="chat-welcome">
            <div class="chat-welcome-icon">💬</div>
            <div class="chat-welcome-title">Agentic OS Chat</div>
            <div class="chat-welcome-desc">Pick an agent above and start a conversation.<br>Each agent has different capabilities — choose the right one for your task.</div>
            <div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;justify-content:center">
              <button class="btn btn-sm" onclick="sendQuickPrompt('opencode','Check the system status and running processes')">🔍 System Check</button>
              <button class="btn btn-sm" onclick="sendQuickPrompt('hermes','What did I work on recently?')">🧠 Recall Memory</button>
              <button class="btn btn-sm" onclick="sendQuickPrompt('gemini','Research the latest trends in AI agents')">📊 Research</button>
              <button class="btn btn-sm" onclick="sendQuickPrompt('claude','Review this project structure and suggest one improvement')">🤖 Claude Code</button>
            </div>
          </div>
        </div>
        <div class="chat-input-area">
          <div class="chat-agent-indicator" id="chatAgentIndicator">opencode</div>
          <textarea id="chatInput" class="chat-input" rows="1" placeholder="Type a message..." onkeydown="handleChatKey(event)"></textarea>
          <button class="btn btn-primary btn-icon" onclick="sendChatMessage()" id="chatSendBtn" title="Send">➤</button>
        </div>
      </div>
    </div>
  `;

  window._currentAgent = 'opencode';
  window._activeConversationId = null;
  document.getElementById('chatInput').focus();

  // Update agent status indicators
  try {
    const status = await api.getStatus();
    (status.agents || []).forEach(a => {
      const el = document.querySelector(`.chat-agent-pill[data-agent="${a.name}"]`);
      if (el) {
        const dot = el.querySelector('.agent-dot');
        dot.className = `agent-dot ${a.status}`;
      }
    });
    updateAgentStatusText();
  } catch {}

  await initChatConversations();
}

async function initChatConversations() {
  try {
    const { conversations } = await api.getConversations();
    if (conversations.length === 0) {
      await newConversation();
    } else {
      await selectConversation(conversations[0].id);
    }
  } catch {
    renderChatHistory([]);
  }
}

// ─── Secondary sidebar: conversation list ───────────────────────
async function loadChatSubmenu() {
  const list = document.getElementById('secondaryList');
  if (!list) return;
  list.innerHTML = renderSkeleton(3);
  try {
    const { conversations } = await api.getConversations();
    list.innerHTML = conversations.length ? conversations.map(c => `
      <div class="secondary-item ${c.id === window._activeConversationId ? 'active' : ''}" onclick="selectConversation('${c.id}')">
        <div class="secondary-item-title">${escapeHtml(c.title)}</div>
        <div class="secondary-item-meta">${timeAgo(c.updated)} · ${c.message_count} msgs</div>
        <button class="secondary-item-delete" onclick="event.stopPropagation();deleteConversation('${c.id}')" title="Delete">✕</button>
      </div>
    `).join('') : `<div class="empty-state-desc">No conversations yet</div>`;
  } catch {
    list.innerHTML = `<div class="empty-state-desc">Failed to load conversations</div>`;
  }
}

async function newConversation() {
  const conv = await api.createConversation();
  window._activeConversationId = conv.id;
  renderChatHistory([]);
  await loadChatSubmenu();
}

async function selectConversation(id) {
  window._activeConversationId = id;
  try {
    const conv = await api.getConversation(id);
    renderChatHistory(conv.messages || []);
  } catch {
    renderChatHistory([]);
  }
  await loadChatSubmenu();
}

async function deleteConversation(id) {
  if (!confirm('Delete this conversation? This cannot be undone.')) return;
  await api.deleteConversation(id);
  if (id === window._activeConversationId) {
    const { conversations } = await api.getConversations();
    if (conversations.length) {
      await selectConversation(conversations[0].id);
    } else {
      await newConversation();
    }
  } else {
    await loadChatSubmenu();
  }
  showToast('Conversation deleted', 'success');
}

function deleteActiveConversation() {
  if (window._activeConversationId) deleteConversation(window._activeConversationId);
}

function selectAgent(agent) {
  window._currentAgent = agent;
  document.querySelectorAll('.chat-agent-pill').forEach(el => el.classList.remove('active'));
  document.querySelector(`.chat-agent-pill[data-agent="${agent}"]`).classList.add('active');
  document.getElementById('chatAgentIndicator').textContent = agent;
  document.getElementById('chatInput').focus();
  updateAgentStatusText();
}

function updateAgentStatusText() {
  const el = document.getElementById('chatAgentStatus');
  if (el && window._currentAgent) {
    const agentEl = document.querySelector(`.chat-agent-pill[data-agent="${window._currentAgent}"]`);
    const dot = agentEl ? agentEl.querySelector('.agent-dot').className : 'offline';
    el.textContent = `${window._currentAgent} • ${dot === 'agent-dot online' ? 'online' : 'offline'}`;
  }
}

function handleChatKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChatMessage();
  }
  autoResizeTextarea(e.target);
}

function autoResizeTextarea(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 150) + 'px';
}

async function sendChatMessage() {
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;

  const agent = window._currentAgent || 'opencode';
  input.value = '';
  input.style.height = 'auto';

  if (!window._activeConversationId) await newConversation();

  addChatMessage('user', message, agent);
  const typingId = showTypingIndicator(agent);

  try {
    // Client-side timeout: 200s (slightly more than Hermes' 180s backend timeout)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 200000);
    const r = await api.chat(agent, message, window._activeConversationId, controller);
    clearTimeout(timeoutId);
    removeTypingIndicator(typingId);
    addChatMessage('assistant', r.response.content, r.response.agent || agent);
    loadChatSubmenu();
  } catch (err) {
    removeTypingIndicator(typingId);
    const msg = err.name === 'AbortError' ? 'Request timed out after 200s' : err.message;
    addChatMessage('assistant', `⚠ Error: ${msg}`, agent);
  }
}

function addChatMessage(role, content, agent) {
  const container = document.getElementById('chatMessages');
  const welcome = container.querySelector('.chat-welcome');
  if (welcome) welcome.style.display = 'none';

  const msg = document.createElement('div');
  msg.className = `chat-message ${role}`;
  msg.innerHTML = `
    <div class="chat-message-avatar">${role === 'user' ? '👤' : '🤖'}</div>
    <div class="chat-message-body">
      <div class="chat-message-header">
        <span class="chat-message-agent">${role === 'user' ? 'You' : agent}</span>
        <span class="chat-message-time">just now</span>
      </div>
      <div class="chat-message-content">${escapeHtml(content)}</div>
    </div>
  `;
  container.appendChild(msg);
  container.scrollTop = container.scrollHeight;
}

function showTypingIndicator(agent) {
  const container = document.getElementById('chatMessages');
  const id = 'typing-' + Date.now();
  const div = document.createElement('div');
  div.className = 'chat-message assistant';
  div.id = id;
  div.innerHTML = `
    <div class="chat-message-avatar">🤖</div>
    <div class="chat-message-body">
      <div class="chat-message-header">
        <span class="chat-message-agent">${agent}</span>
      </div>
      <div class="typing-indicator"><span></span><span></span><span></span></div>
    </div>
  `;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

async function refreshChat() {
  if (window._activeConversationId) await selectConversation(window._activeConversationId);
}

function renderChatHistory(messages) {
  const container = document.getElementById('chatMessages');
  if (!container) return;
  const welcome = container.querySelector('.chat-welcome');

  container.querySelectorAll('.chat-message').forEach(el => el.remove());

  if (!messages || messages.length === 0) {
    if (welcome) welcome.style.display = '';
    return;
  }
  if (welcome) welcome.style.display = 'none';

  messages.forEach(msg => {
    const div = document.createElement('div');
    div.className = `chat-message ${msg.role}`;
    div.innerHTML = `
      <div class="chat-message-avatar">${msg.role === 'user' ? '👤' : '🤖'}</div>
      <div class="chat-message-body">
        <div class="chat-message-header">
          <span class="chat-message-agent">${msg.role === 'user' ? 'You' : msg.agent}</span>
          <span class="chat-message-time">${timeAgo(msg.timestamp)}</span>
        </div>
        <div class="chat-message-content">${escapeHtml(msg.content)}</div>
      </div>
    `;
    container.appendChild(div);
  });
  container.scrollTop = container.scrollHeight;
}

function sendQuickPrompt(agent, message) {
  selectAgent(agent);
  document.getElementById('chatInput').value = message;
  sendChatMessage();
}
