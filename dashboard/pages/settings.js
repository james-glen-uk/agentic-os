async function renderSettings() {
  const content = document.getElementById('pageContent');
  content.innerHTML = `
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Configure Agentic OS behavior</p>
      </div>
      <button class="btn btn-primary" onclick="saveAllSettings()">💾 Save All</button>
    </div>
    <div id="settingsForm"><div class="loading"><div class="loading-spinner"></div></div></div>
  `;

  try {
    const settings = await api.getSettings();
    const prefs = settings.agent_preferences || {};
    const dashboard = settings.dashboard || {};
    const limits = settings.free_tier_limits || {};
    const apiKeys = settings.api_keys || {};
    const routing = settings.routing || {};

    document.getElementById('settingsForm').innerHTML = `
      <div class="card">
        <div class="card-header"><span class="card-title">🤖 Agent Preferences</span></div>
        <div class="grid grid-3">
          ${['opencode', 'hermes', 'gemini', 'claude'].map(a => `
            <div class="card" style="padding:14px">
              <div class="flex items-center gap-2 mb-2">
                <div class="agent-dot ${prefs[a] && prefs[a].enabled !== false ? 'online' : 'offline'}" style="width:10px;height:10px"></div>
                <strong style="font-size:13px">${a}</strong>
              </div>
              <label class="switch" style="margin:8px 0">
                <input type="checkbox" id="agent_${a}" ${prefs[a] && prefs[a].enabled !== false ? 'checked' : ''} onchange="toggleAgent('${a}')">
                <span class="switch-slider"></span>
              </label>
              <div class="form-group" style="margin-bottom:0;margin-top:8px">
                <label class="form-label">Binary Path</label>
                <input id="bin_${a}" class="form-input" value="${escapeHtml((prefs[a] && prefs[a].binary) || a)}" style="font-size:12px">
              </div>
            </div>
          `).join('')}
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">🧭 Routing & Fallback</span></div>
        <div class="form-row">
          <div class="form-group">
            <label class="switch" style="width:auto;display:flex;align-items:center;gap:10px">
              <input type="checkbox" id="routeFreeOnly" ${routing.free_only ? 'checked' : ''}>
              <span class="switch-slider" style="position:relative;display:inline-block;width:40px;height:22px"></span>
              <span style="font-size:13px">Free-only mode (never route to paid agents like Claude Code)</span>
            </label>
          </div>
          <div class="form-group">
            <label class="form-label">Fallback ordering</label>
            <select id="routePrefer" class="form-select">
              <option value="cost" ${routing.prefer !== 'quality' ? 'selected' : ''}>Cost — free agents first</option>
              <option value="quality" ${routing.prefer === 'quality' ? 'selected' : ''}>Quality — Claude Code first</option>
            </select>
          </div>
        </div>
        <p style="font-size:12px;color:var(--text-muted)">Every agent call tries a fallback chain: your chosen agent first, then the others (open circuits and offline agents last). A call only fails when every agent is exhausted.</p>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">🖥 Desktop App</span></div>
        <div id="desktopSettings"><div class="loading"><div class="loading-spinner"></div></div></div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">🎙 Voice — "Hey Jarvis"</span></div>
        <div id="voiceSettings"><div class="loading"><div class="loading-spinner"></div></div></div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">🎨 Dashboard</span></div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Port</label>
            <input id="setPort" class="form-input" type="number" value="${dashboard.port || 8080}">
          </div>
          <div class="form-group">
            <label class="form-label">Host</label>
            <input id="setHost" class="form-input" value="${escapeHtml(dashboard.host || '127.0.0.1')}">
          </div>
        </div>
        <div class="form-group">
          <label class="switch" style="width:auto;display:flex;align-items:center;gap:10px">
            <input type="checkbox" id="setDarkMode" ${dashboard.dark_mode !== false ? 'checked' : ''}>
            <span class="switch-slider" style="position:relative;display:inline-block;width:40px;height:22px"></span>
            <span style="font-size:13px">Dark Mode</span>
          </label>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">🔑 API Keys</span></div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Gemini API Key</label>
            <input id="keyGemini" class="form-input" type="password" value="${escapeHtml(apiKeys.gemini || '')}" placeholder="Enter Gemini API key">
          </div>
          <div class="form-group">
            <label class="form-label">OpenRouter API Key</label>
            <input id="keyOpenrouter" class="form-input" type="password" value="${escapeHtml(apiKeys.openrouter || '')}" placeholder="Enter OpenRouter API key">
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header"><span class="card-title">💰 Free Tier Limits</span></div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Gemini Flash — Requests/Day</label>
            <input id="limGReqs" class="form-input" type="number" value="${(limits.gemini_flash && limits.gemini_flash.requests_per_day) || 1500}">
          </div>
          <div class="form-group">
            <label class="form-label">Gemini Flash — Tokens/Day</label>
            <input id="limGTokens" class="form-input" type="number" value="${(limits.gemini_flash && limits.gemini_flash.tokens_per_day) || 1000000}">
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">OpenRouter Free — Requests/Day</label>
            <input id="limORReqs" class="form-input" type="number" value="${(limits.openrouter_free && limits.openrouter_free.requests_per_day) || 100}">
          </div>
          <div class="form-group">
            <label class="form-label">OpenRouter Free — Tokens/Day</label>
            <input id="limORTokens" class="form-input" type="number" value="${(limits.openrouter_free && limits.openrouter_free.tokens_per_day) || 200000}">
          </div>
        </div>
      </div>

      <div class="card" style="border-color:var(--red)">
        <div class="card-header"><span class="card-title" style="color:var(--red)">⚠ Danger Zone</span></div>
        <p style="font-size:13px;color:var(--text-secondary);margin-bottom:12px">Reset all settings to factory defaults.</p>
        <button class="btn btn-danger" onclick="resetSettings()">Reset to Defaults</button>
      </div>
    `;
    loadDesktopSettings();
    loadVoiceSettings(settings);
  } catch (err) {
    document.getElementById('settingsForm').innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠</div><div class="empty-state-title">${escapeHtml(err.message)}</div></div>`;
  }
}

async function loadVoiceSettings(settings) {
  const el = document.getElementById('voiceSettings');
  if (!el) return;
  const autoExec = ((settings || {}).voice || {}).auto_execute || false;
  try {
    const v = await api.voiceState();
    const toggle = (id, label, checked, disabled, handler) => `
      <label class="switch" style="width:auto;display:flex;align-items:center;gap:10px;margin:6px 0;${disabled ? 'opacity:.5' : ''}">
        <input type="checkbox" id="${id}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''} onchange="${handler}">
        <span class="switch-slider" style="position:relative;display:inline-block;width:40px;height:22px"></span>
        <span style="font-size:13px">${label}</span>
      </label>`;
    el.innerHTML = `
      <div style="font-size:12px;margin-bottom:8px">
        Status: <strong>${v.available ? (v.enabled ? 'listening for "Hey Jarvis"' : 'ready') : 'unavailable'}</strong>
      </div>
      ${toggle('voiceEnabled', 'Enable always-on "Hey Jarvis" wake word', v.enabled, !v.available, 'toggleVoiceWake()')}
      ${toggle('voiceAutoExec', 'Auto-run commands without confirmation', autoExec, false, 'saveVoiceAutoExec()')}
      <p style="font-size:12px;color:var(--text-muted);margin-top:6px">
        ${v.available
          ? 'Say "Hey Jarvis" then a command — e.g. "schedule a daily standup at 9am", "start an orchestration to plan a launch", "add a journal note". You can also click the mic in the title bar to talk. Commands ask for confirmation unless auto-run is on.'
          : `⚠ Voice deps not installed. Run <code>${v.install_hint || 'pip install -r requirements-voice.txt'}</code> to enable the wake word. The mic button (Chrome/Edge) still works.`}
      </p>`;
  } catch (err) {
    el.innerHTML = `<div style="font-size:12px;color:var(--text-muted)">Voice service not available.</div>`;
  }
}

async function toggleVoiceWake() {
  const on = document.getElementById('voiceEnabled').checked;
  try {
    const s = on ? await api.voiceEnable() : await api.voiceDisable();
    if (on && s.state === 'unavailable') {
      showToast(s.error || 'Voice deps not installed', 'warning');
    } else {
      showToast(on ? 'Hey Jarvis is listening' : 'Wake word off', 'success');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function saveVoiceAutoExec() {
  const auto = document.getElementById('voiceAutoExec').checked;
  try {
    await api.updateSettings({ voice: { auto_execute: auto } });
    showToast('Voice preference saved', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function loadDesktopSettings() {
  const el = document.getElementById('desktopSettings');
  if (!el) return;
  try {
    const s = await api.getStartupSettings();
    const row = (id, label, checked, disabled) => `
      <label class="switch" style="width:auto;display:flex;align-items:center;gap:10px;margin:6px 0;${disabled ? 'opacity:.5' : ''}">
        <input type="checkbox" id="${id}" ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''} onchange="saveDesktopSettings()">
        <span class="switch-slider" style="position:relative;display:inline-block;width:40px;height:22px"></span>
        <span style="font-size:13px">${label}</span>
      </label>`;
    el.innerHTML = `
      ${row('sysStartOnBoot', 'Start Agentic OS when I sign in to Windows', s.start_on_boot, !s.supported)}
      ${row('sysMinimizeTray', 'Minimize to the system tray instead of closing', s.minimize_to_tray, false)}
      ${row('sysLaunchMin', 'Launch minimized (straight to tray, no window)', s.launch_minimized, false)}
      <p style="font-size:12px;color:var(--text-muted);margin-top:6px">${s.supported
        ? 'Start-on-boot adds a per-user Windows startup entry that launches the app minimized to the tray.'
        : '⚠ Start-on-boot is only available in the packaged desktop app on Windows.'}</p>
    `;
  } catch (err) {
    el.innerHTML = `<div style="font-size:12px;color:var(--red)">${escapeHtml(err.message)}</div>`;
  }
}

async function saveDesktopSettings() {
  try {
    const r = await api.updateStartupSettings({
      start_on_boot: document.getElementById('sysStartOnBoot').checked,
      minimize_to_tray: document.getElementById('sysMinimizeTray').checked,
      launch_minimized: document.getElementById('sysLaunchMin').checked,
    });
    showToast('Desktop settings saved', 'success');
  } catch (err) {
    showToast(err.message, 'error');
    loadDesktopSettings();
  }
}

function toggleAgent(name) {
  const cb = document.getElementById(`agent_${name}`);
  const card = cb.closest('.card');
  const dot = card.querySelector('.agent-dot');
  dot.className = `agent-dot ${cb.checked ? 'online' : 'offline'}`;
}

async function saveAllSettings() {
  try {
    const settings = {
      agent_preferences: {
        opencode: { enabled: document.getElementById('agent_opencode').checked, binary: document.getElementById('bin_opencode').value },
        hermes: { enabled: document.getElementById('agent_hermes').checked, binary: document.getElementById('bin_hermes').value },
        gemini: { enabled: document.getElementById('agent_gemini').checked, binary: document.getElementById('bin_gemini').value },
        claude: { enabled: document.getElementById('agent_claude').checked, binary: document.getElementById('bin_claude').value },
      },
      routing: {
        free_only: document.getElementById('routeFreeOnly').checked,
        prefer: document.getElementById('routePrefer').value,
      },
      dashboard: {
        port: parseInt(document.getElementById('setPort').value) || 8080,
        host: document.getElementById('setHost').value || '127.0.0.1',
        dark_mode: document.getElementById('setDarkMode').checked,
      },
      api_keys: {
        gemini: document.getElementById('keyGemini').value,
        openrouter: document.getElementById('keyOpenrouter').value,
      },
      free_tier_limits: {
        gemini_flash: {
          requests_per_day: parseInt(document.getElementById('limGReqs').value) || 1500,
          tokens_per_day: parseInt(document.getElementById('limGTokens').value) || 1000000,
        },
        openrouter_free: {
          requests_per_day: parseInt(document.getElementById('limORReqs').value) || 100,
          tokens_per_day: parseInt(document.getElementById('limORTokens').value) || 200000,
        },
      },
    };
    await api.updateSettings(settings);
    showToast('Settings saved successfully', 'success');
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function resetSettings() {
  showModal('Reset to Defaults', `
    <div class="card" style="background:var(--red-dim);border-color:transparent">
      <div class="flex items-center gap-2"><span style="font-size:18px">⚠</span><div><strong style="font-size:13px">Warning</strong><div style="font-size:12px;color:var(--text-secondary);margin-top:2px">This will reset all settings to factory defaults and cannot be undone.</div></div></div>
    </div>
  `, `
    <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
    <button class="btn btn-danger" onclick="confirmReset()">Reset</button>
  `);
}

async function confirmReset() {
  const defaults = {
    theme: 'dark',
    agent_preferences: { opencode: { enabled: true, binary: 'opencode' }, hermes: { enabled: true, binary: 'hermes' }, gemini: { enabled: true, binary: 'gemini', model: 'gemini-2.5-flash' }, claude: { enabled: true, binary: 'claude' } },
    dashboard: { port: 8080, host: '127.0.0.1', dark_mode: true },
    api_keys: { gemini: '', openrouter: '' },
    free_tier_limits: { gemini_flash: { requests_per_day: 1500, tokens_per_day: 1000000 }, openrouter_free: { requests_per_day: 100, tokens_per_day: 200000 } },
  };
  try {
    await api.updateSettings(defaults);
    closeModal();
    showToast('Settings reset to defaults', 'success');
    renderSettings();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}
