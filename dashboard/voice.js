// Voice control — push-to-talk via the Web Speech API.
// The recognition result is handed to handleVoiceTranscript(), which matches
// an intent and asks for confirmation before doing anything. matchVoiceIntent()
// is a pure function so the routing can be tested without a microphone.

let _voiceRecognition = null;
let _voiceActive = false;
let _voiceSkillsCache = null;

// Spoken aliases → dashboard page key
const VOICE_NAV = {
  dashboard: 'dashboard', home: 'dashboard', chat: 'chat', skills: 'skills',
  'skills hub': 'skills', memory: 'memory', brain: 'memory', scheduler: 'scheduler',
  audit: 'audit', news: 'news', 'news oracle': 'news', orchestration: 'orchestration',
  orchestrate: 'orchestration', kanban: 'kanban', board: 'kanban', goals: 'goals',
  journal: 'journal', artifacts: 'artifacts', 'artifact library': 'artifacts',
  'agent health': 'agent-health', 'smart router': 'smart-router', cost: 'cost',
  'cost analytics': 'cost', errors: 'errors', settings: 'settings',
};

function _words(s) {
  return (s || '').toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter(Boolean);
}

// Pure intent matcher. skills = array of {name}. Returns an intent object.
function matchVoiceIntent(text, skills) {
  const norm = (text || '').toLowerCase().trim();
  const w = new Set(_words(norm));
  if (!norm) return { action: 'none', confidence: 0, heard: text };

  // "refresh news" / "update news"
  if ((w.has('refresh') || w.has('update') || w.has('fetch')) && w.has('news')) {
    return { action: 'news_refresh', label: 'Refresh the News Oracle', confidence: 'high', heard: text };
  }

  // Best skill match by name-word overlap
  const runTrigger = w.has('run') || w.has('execute') || w.has('start');
  let best = null;
  for (const s of (skills || [])) {
    const sw = _words(s.name.replace(/-/g, ' '));
    const overlap = sw.filter(x => w.has(x)).length;
    const score = overlap / Math.max(sw.length, 1);
    if (overlap > 0 && (!best || score > best.score)) best = { name: s.name, score, overlap };
  }
  const skillIntent = (best && (best.score >= 0.5 || (runTrigger && best.overlap >= 1)))
    ? { action: 'run_skill', target: best.name, label: `Run the "${best.name}" skill`,
        confidence: best.score >= 0.5 ? 'high' : 'medium', heard: text }
    : null;

  // A run/execute/start verb means the user wants to *do* something → prefer
  // the skill over merely navigating to a page.
  if (runTrigger && skillIntent) return skillIntent;

  // "go to / open / show <page>"
  const navTrigger = w.has('go') || w.has('open') || w.has('show') || w.has('navigate');
  let bestNav = null;
  for (const [alias, key] of Object.entries(VOICE_NAV)) {
    if (norm.includes(alias)) {
      if (!bestNav || alias.length > bestNav.alias.length) bestNav = { alias, key };
    }
  }
  if (bestNav && (navTrigger || bestNav.alias.length > 4)) {
    return { action: 'navigate', target: bestNav.key,
             label: `Open ${bestNav.key.replace('-', ' ')}`, confidence: 'high', heard: text };
  }

  if (skillIntent) return skillIntent;
  return { action: 'none', confidence: 0, heard: text };
}

async function _voiceSkills() {
  if (_voiceSkillsCache) return _voiceSkillsCache;
  try { _voiceSkillsCache = (await api.getSkills()) || []; } catch { _voiceSkillsCache = []; }
  return _voiceSkillsCache;
}

// Match a transcript and, if confident, ask before acting. Returns the intent.
async function handleVoiceTranscript(text) {
  const intent = matchVoiceIntent(text, await _voiceSkills());
  if (intent.action === 'none') {
    showToast(`Didn't catch a command in "${text}"`, 'warning');
    return intent;
  }
  // Never guess: always confirm before doing anything.
  showModal('🎙 Voice command', `
    <p style="font-size:13px;margin-bottom:6px">Heard: <em>"${escapeHtml(text)}"</em></p>
    <p style="font-size:14px"><strong>${escapeHtml(intent.label)}</strong></p>
  `, `
    <button class="btn btn-sm btn-ghost" onclick="closeModal()">Cancel</button>
    <button class="btn btn-sm btn-primary" onclick="closeModal();executeVoiceIntent(${JSON.stringify(intent).replace(/"/g, '&quot;')})">Confirm</button>
  `);
  return intent;
}

async function executeVoiceIntent(intent) {
  try {
    if (intent.action === 'navigate') {
      navigate(intent.target);
    } else if (intent.action === 'news_refresh') {
      showToast('Refreshing news…', 'info');
      await api.refreshNews();
      navigate('news');
      showToast('News refreshed', 'success');
    } else if (intent.action === 'run_skill') {
      showToast(`Running ${intent.target}…`, 'info');
      const r = await api.runSkill(intent.target, '', 'auto');
      showToast(`${intent.target} ${r.status === 'completed' ? 'done → Artifacts' : 'failed'}`,
                r.status === 'completed' ? 'success' : 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function toggleVoiceCapture() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById('voiceMicBtn');
  if (!SR) {
    showToast('Voice not supported in this browser (try Chrome or Edge)', 'warning');
    return;
  }
  if (_voiceActive) { try { _voiceRecognition.stop(); } catch {} return; }

  _voiceRecognition = new SR();
  _voiceRecognition.lang = 'en-US';
  _voiceRecognition.interimResults = false;
  _voiceRecognition.maxAlternatives = 1;
  _voiceRecognition.onstart = () => { _voiceActive = true; if (btn) btn.classList.add('listening'); showToast('Listening…', 'info'); };
  _voiceRecognition.onerror = (e) => { showToast('Voice error: ' + e.error, 'error'); };
  _voiceRecognition.onend = () => { _voiceActive = false; if (btn) btn.classList.remove('listening'); };
  _voiceRecognition.onresult = (e) => {
    const transcript = e.results[0][0].transcript;
    handleVoiceTranscript(transcript);
  };
  _voiceRecognition.start();
}
