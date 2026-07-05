// Voice control — front end for the backend "Hey Jarvis" assistant.
//
// Two input paths converge on the same backend interpreter (/api/voice/command):
//   1) the always-listening wake word (openWakeWord + Whisper, Python side)
//   2) this mic button (browser Web Speech API) for click-to-talk
// The interpreter LLM-parses the transcript into an action; we confirm, then
// execute via /api/voice/execute. This replaces the old client-side keyword
// matcher, so the mic now has full control of the app.

let _voiceRecognition = null;
let _voiceActive = false;
let _voicePollTimer = null;

async function toggleVoiceCapture() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  const btn = document.getElementById('voiceMicBtn');
  if (!SR) {
    showToast('Click-to-talk needs Chrome/Edge. Enable "Hey Jarvis" in Settings for hands-free voice.', 'warning');
    return;
  }
  if (_voiceActive) { try { _voiceRecognition.stop(); } catch {} return; }

  _voiceRecognition = new SR();
  _voiceRecognition.lang = 'en-US';
  _voiceRecognition.interimResults = false;
  _voiceRecognition.maxAlternatives = 1;
  _voiceRecognition.onstart = () => { _voiceActive = true; if (btn) btn.classList.add('listening'); showToast('Listening…', 'info'); };
  _voiceRecognition.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      showToast('Microphone permission denied. Allow mic access, or use "Hey Jarvis" in Settings.', 'error');
    } else if (e.error !== 'no-speech') {
      showToast('Voice error: ' + e.error, 'error');
    }
  };
  _voiceRecognition.onend = () => { _voiceActive = false; if (btn) btn.classList.remove('listening'); };
  _voiceRecognition.onresult = (e) => sendVoiceTranscript(e.results[0][0].transcript);
  _voiceRecognition.start();
}

// Send a transcript (from the mic here, or anywhere) to the backend interpreter.
async function sendVoiceTranscript(text) {
  text = (text || '').trim();
  if (!text) return;
  showToast(`Heard: "${text}"`, 'info');
  try {
    const parsed = await api.voiceCommand(text, false);  // execute=false → confirm first
    if (parsed.status === 'no_agent') {
      showToast(parsed.message || 'No agent available to understand that.', 'error');
      return;
    }
    if (parsed.status === 'unrecognized' || parsed.action === 'none') {
      showToast(`Didn't catch a command in "${text}"`, 'warning');
      return;
    }
    showVoiceConfirm(parsed);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function showVoiceConfirm(parsed) {
  const params = Object.entries(parsed.params || {})
    .map(([k, v]) => `<div style="font-size:12px"><span style="color:var(--text-muted)">${escapeHtml(k)}:</span> ${escapeHtml(String(v))}</div>`)
    .join('');
  showModal('🎙 Voice command', `
    <p style="font-size:13px;margin-bottom:6px">Heard: <em>"${escapeHtml(parsed.transcript || '')}"</em></p>
    <p style="font-size:14px;margin-bottom:8px"><strong>${escapeHtml(parsed.label || parsed.action)}</strong></p>
    ${params}
  `, `
    <button class="btn btn-sm btn-ghost" onclick="closeModal()">Cancel</button>
    <button class="btn btn-sm btn-primary" onclick='confirmVoiceAction(${JSON.stringify({action: parsed.action, params: parsed.params}).replace(/'/g, "&#39;")})'>Confirm</button>
  `);
}

async function confirmVoiceAction(parsed) {
  closeModal();
  try {
    const result = await api.voiceExecute(parsed.action, parsed.params || {});
    if (result.status === 'ok' || result.status === 'completed') {
      if (result.navigate) { navigate(result.navigate); }
      showToast(`✓ ${describeVoiceResult(parsed.action, result)}`, 'success');
    } else if (result.status === 'unconfigured') {
      showToast(result.message || 'Not configured', 'warning');
    } else {
      showToast(result.message || `Action ${parsed.action} failed`, 'error');
    }
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function describeVoiceResult(action, r) {
  switch (action) {
    case 'navigate': return `Opened ${r.navigate}`;
    case 'create_schedule': return 'Schedule created';
    case 'start_orchestration': return 'Orchestration started';
    case 'add_journal': return 'Journal entry added';
    case 'create_goal': return 'Goal created';
    case 'create_task': return 'Task created';
    case 'run_skill': return `Ran ${r.skill}`;
    case 'refresh_news': return `News refreshed (${r.topics} topics)`;
    case 'generate_image': return 'Image generated';
    default: return 'Done';
  }
}

// Reflect the backend wake-word service state on the mic button.
async function pollVoiceState() {
  const btn = document.getElementById('voiceMicBtn');
  if (!btn) return;
  try {
    const s = await api.voiceState();
    btn.classList.toggle('wake-active', s.enabled && s.state !== 'unavailable');
    btn.title = s.enabled
      ? `Hey Jarvis: ${s.state}${s.last_transcript ? ' — last: ' + s.last_transcript : ''}`
      : 'Voice command (click to talk)';
    if (s.enabled && s.last_result && s.last_result.status === 'pending_confirm'
        && s.last_transcript && s.last_transcript !== window._lastVoiceHandled) {
      window._lastVoiceHandled = s.last_transcript;
      showVoiceConfirm({ ...s.last_result, transcript: s.last_transcript });
    }
  } catch { /* voice endpoints not available */ }
}

window.addEventListener('DOMContentLoaded', () => {
  clearInterval(_voicePollTimer);
  _voicePollTimer = setInterval(pollVoiceState, 4000);
  setTimeout(pollVoiceState, 1500);
});
