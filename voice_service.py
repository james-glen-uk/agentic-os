"""Agentic OS — "Hey Jarvis" voice service.

Always-listening wake-word detection (openWakeWord, pretrained `hey_jarvis`)
+ local speech-to-text (faster-whisper). Runs in a background thread and
hands each recognized command to a callback (the command interpreter).

The heavy audio/ML deps are OPTIONAL: without them the service reports
`unavailable` with a clear "what to install" message, and the rest of the
app is unaffected. The real audio methods are isolated so the state machine
and command pipeline can be tested without a microphone.
"""
import importlib.util
import threading
import time
from datetime import datetime, timezone

VOICE_DEPS = ["openwakeword", "faster_whisper", "sounddevice", "numpy"]
SAMPLE_RATE = 16000
COMMAND_SECONDS = 5  # how long to record after the wake word fires


def _now():
    return datetime.now(timezone.utc).isoformat()


class VoiceService:
    def __init__(self, on_transcript=None):
        # states: idle | listening | awake | processing | unavailable
        self.state = "idle"
        self.enabled = False
        self.last_transcript = ""
        self.last_result = None
        self.last_heard_at = None
        self.error = ""
        self.on_transcript = on_transcript
        self._thread = None
        self._running = False

    # ─── availability / status ────────────────────────────────────
    def availability(self) -> dict:
        missing = [m for m in VOICE_DEPS if importlib.util.find_spec(m) is None]
        return {"available": not missing, "missing": missing}

    def status(self) -> dict:
        avail = self.availability()
        return {
            "state": self.state,
            "enabled": self.enabled,
            "wake_word": "Hey Jarvis",
            "last_transcript": self.last_transcript,
            "last_result": self.last_result,
            "last_heard_at": self.last_heard_at,
            "error": self.error,
            "available": avail["available"],
            "missing": avail["missing"],
            "install_hint": "pip install -r requirements-voice.txt" if avail["missing"] else "",
        }

    # ─── lifecycle ────────────────────────────────────────────────
    def start(self) -> dict:
        avail = self.availability()
        if not avail["available"]:
            self.state = "unavailable"
            self.error = "Missing voice dependencies: " + ", ".join(avail["missing"])
            return self.status()
        if self._running:
            return self.status()
        self._running = True
        self.enabled = True
        self.error = ""
        self.state = "listening"
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        return self.status()

    def stop(self) -> dict:
        self._running = False
        self.enabled = False
        if self.state != "unavailable":
            self.state = "idle"
        return self.status()

    # ─── the command pipeline (testable entry point) ──────────────
    def feed_transcript(self, transcript: str) -> dict:
        """Run a recognized command through the handler. Used by the
        wake-word loop AND by external callers (browser fallback, tests)."""
        transcript = (transcript or "").strip()
        self.last_transcript = transcript
        self.last_heard_at = _now()
        prev = self.state
        self.state = "processing"
        try:
            if self.on_transcript and transcript:
                self.last_result = self.on_transcript(transcript)
            else:
                self.last_result = {"status": "empty"}
        except Exception as e:  # never let a bad command kill the listener
            self.last_result = {"status": "error", "message": str(e)}
        finally:
            self.state = "listening" if self._running else (prev if prev != "processing" else "idle")
        return self.last_result

    # ─── real audio loop (only runs when deps present + started) ───
    def _loop(self):
        try:
            oww, whisper = self._load_models()
            stream = self._open_mic()
            try:
                while self._running:
                    frame = self._read_frame(stream)
                    if frame is None:
                        continue
                    if self._wake_detected(oww, frame):
                        self.state = "awake"
                        audio = self._record_command(stream)
                        text = self._transcribe(whisper, audio)
                        if text.strip():
                            self.feed_transcript(text)
                        self.state = "listening"
            finally:
                self._close_mic(stream)
        except Exception as e:
            self.error = str(e)
            self.state = "unavailable"
            self._running = False

    # These wrap the ML/audio libs; replaced in tests. Imported lazily so the
    # module loads fine without the optional deps installed.
    def _load_models(self):
        from openwakeword.model import Model
        from faster_whisper import WhisperModel
        oww = Model(wakeword_models=["hey_jarvis"])
        whisper = WhisperModel("base.en", device="cpu", compute_type="int8")
        return oww, whisper

    def _open_mic(self):
        import sounddevice as sd
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                                blocksize=1280)
        stream.start()
        return stream

    def _read_frame(self, stream):
        data, _ = stream.read(1280)
        import numpy as np
        return np.frombuffer(data, dtype="int16").flatten()

    def _wake_detected(self, oww, frame) -> bool:
        scores = oww.predict(frame)
        return any(v >= 0.5 for v in scores.values())

    def _record_command(self, stream):
        import numpy as np
        chunks = []
        for _ in range(int(SAMPLE_RATE * COMMAND_SECONDS / 1280)):
            data, _ = stream.read(1280)
            chunks.append(np.frombuffer(data, dtype="int16").flatten())
        return np.concatenate(chunks) if chunks else np.array([], dtype="int16")

    def _transcribe(self, whisper, audio) -> str:
        import numpy as np
        samples = audio.astype("float32") / 32768.0
        segments, _ = whisper.transcribe(samples, language="en")
        return " ".join(s.text for s in segments).strip()


# Process-wide singleton, wired up by server.py.
_service = None

def get_service(on_transcript=None) -> "VoiceService":
    global _service
    if _service is None:
        _service = VoiceService(on_transcript=on_transcript)
    elif on_transcript is not None:
        _service.on_transcript = on_transcript
    return _service
