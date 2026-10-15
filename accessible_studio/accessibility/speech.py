"""
AccessibleStudio Accessibility - Screen Reader Bridge & Auditory Earcons
========================================================================
Specifically engineered for blind audio engineers and musicians.
Integrates directly with NVDA and JAWS in-memory APIs via Tolk / cytolk.
Provides instant, responsive speech with non-blocking queues, interrupt
capability, bilingual Arabic/English strings, and subtle musical Earcons.
"""

import sys
import time
import queue
import threading
from typing import Optional, Callable

from accessible_studio.config import STRINGS, EARCON_CHANNEL


class SpeechBridge:
    """Non-blocking screen reader voice engine with Earcon audio cues."""

    def __init__(self, default_lang: str = "ar"):
        self.language = default_lang
        self.engine_type = "none"
        self._tolk_loaded = False
        self._sapi_engine = None
        self._synth_callbacks = (None, None)  # (note_on_fn, note_off_fn)
        
        self._speech_queue = queue.Queue()
        self._is_running = True
        self._worker_thread = threading.Thread(target=self._speech_worker, daemon=True, name="SpeechBridge-Worker")
        self._worker_thread.start()

        self._init_screen_reader_drivers()

    def _init_screen_reader_drivers(self):
        """Initializes Tolk for NVDA/JAWS, or falls back to SAPI/pyttsx3."""
        if sys.platform == "win32":
            try:
                import cytolk.tolk as tolk
                tolk.load()
                if tolk.is_loaded():
                    self._tolk_loaded = True
                    sr_name = tolk.detect_screen_reader()
                    self.engine_type = f"Tolk ({sr_name if sr_name else 'Active Screen Reader'})"
                    print(f"[SpeechBridge] Connected directly to {self.engine_type}")
                    return
            except Exception as e:
                print(f"[SpeechBridge] Tolk direct bridge note: {e}")

            try:
                import comtypes.client
                self._sapi_engine = comtypes.client.CreateObject("SAPI.SpVoice")
                self.engine_type = "Windows SAPI.SpVoice"
                print("[SpeechBridge] Connected to Windows SAPI Speech Subsystem.")
                return
            except Exception as e:
                print(f"[SpeechBridge] SAPI initialization note: {e}")

        # Cross-platform pyttsx3 fallback
        try:
            import pyttsx3
            self._pyttsx3_engine = pyttsx3.init()
            self._pyttsx3_engine.setProperty("rate", 190)
            self.engine_type = "pyttsx3"
            print("[SpeechBridge] Cross-platform pyttsx3 initialized.")
        except Exception:
            self.engine_type = "Console Print"
            print("[SpeechBridge] Running in console text mode.")

    def set_synth_callbacks(self, note_on: Callable[[int, int, int], None], note_off: Callable[[int, int], None]):
        """Connects synthesis callbacks for rendering auditory Earcons."""
        self._synth_callbacks = (note_on, note_off)

    def speak(self, text: str, interrupt: bool = True):
        """Enqueues speech text. If interrupt is True, stops ongoing speech immediately."""
        if not text:
            return

        if interrupt:
            # Drain queue
            while not self._speech_queue.empty():
                try:
                    self._speech_queue.get_nowait()
                except queue.Empty:
                    break
            self._silence_now()

        self._speech_queue.put((text, interrupt))

    def _silence_now(self):
        if self._tolk_loaded:
            try:
                import cytolk.tolk as tolk
                tolk.silence()
            except Exception:
                pass
        elif self._sapi_engine:
            try:
                # SVSFPurgeBeforeSpeak
                pass
            except Exception:
                pass

    def _speech_worker(self):
        """Processes queued text sequentially."""
        while self._is_running:
            try:
                text, interrupt = self._speech_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                if self._tolk_loaded:
                    import cytolk.tolk as tolk
                    tolk.speak(text, interrupt)
                elif self._sapi_engine:
                    flags = 1 if not interrupt else 2  # SVSFlagsAsync | SVSFPurgeBeforeSpeak
                    self._sapi_engine.Speak(text, flags)
                elif hasattr(self, "_pyttsx3_engine") and self._pyttsx3_engine:
                    self._pyttsx3_engine.say(text)
                    self._pyttsx3_engine.runAndWait()
                else:
                    print(f"[Speech Output]: {text}")
            except Exception as e:
                print(f"[Speech Output Error]: {e} | Text: {text}")

    def play_earcon(self, cue_type: str):
        """Plays subtle, pleasant auditory cue tones."""
        note_on, note_off = self._synth_callbacks
        if not note_on or not note_off:
            return

        def _worker():
            try:
                if cue_type == "play":
                    # Ascending chime C5 -> G5
                    note_on(EARCON_CHANNEL, 72, 85)
                    time.sleep(0.06)
                    note_off(EARCON_CHANNEL, 72)
                    note_on(EARCON_CHANNEL, 79, 90)
                    time.sleep(0.09)
                    note_off(EARCON_CHANNEL, 79)
                elif cue_type == "stop":
                    # Descending cue G4 -> C4
                    note_on(EARCON_CHANNEL, 67, 80)
                    time.sleep(0.06)
                    note_off(EARCON_CHANNEL, 67)
                    note_on(EARCON_CHANNEL, 60, 75)
                    time.sleep(0.08)
                    note_off(EARCON_CHANNEL, 60)
                elif cue_type == "record":
                    # High alert chime
                    for n in (79, 84, 88):
                        note_on(EARCON_CHANNEL, n, 95)
                        time.sleep(0.04)
                        note_off(EARCON_CHANNEL, n)
                elif cue_type == "boundary":
                    # Soft tick
                    note_on(EARCON_CHANNEL, 84, 70)
                    time.sleep(0.03)
                    note_off(EARCON_CHANNEL, 84)
                elif cue_type == "quantize":
                    # Triplet arpeggio
                    for n in (72, 76, 79):
                        note_on(EARCON_CHANNEL, n, 85)
                        time.sleep(0.035)
                        note_off(EARCON_CHANNEL, n)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def get_text(self, key: str, **kwargs) -> str:
        """Retrieves localized template string and formats with parameters."""
        table = STRINGS.get(self.language, STRINGS.get("ar", {}))
        tmpl = table.get(key, key)
        try:
            return tmpl.format(**kwargs)
        except Exception:
            return tmpl

    def toggle_language(self) -> str:
        """Toggles between Arabic and English."""
        self.language = "en" if self.language == "ar" else "ar"
        msg = "تم تغيير لغة النطق إلى اللغة العربية" if self.language == "ar" else "Language switched to English"
        self.speak(msg, interrupt=True)
        return self.language

    def shutdown(self):
        self._is_running = False
        if self._tolk_loaded:
            try:
                import cytolk.tolk as tolk
                tolk.unload()
            except Exception:
                pass


# Global singleton speech instance
speech = SpeechBridge(default_lang="ar")
