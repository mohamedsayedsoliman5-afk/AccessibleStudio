"""
Screen Reader & Accessibility Bridge Module
===========================================
Provides instantaneous, interruptible speech output for blind musicians.
Prioritizes CyTolk (direct C-bindings to NVDA, JAWS, SAPI) with non-blocking
fallbacks (SAPI via comtypes, pyttsx3 daemon thread, spd-say, termux-tts).
Includes an auditory Earcon generator for instant non-verbal feedback.
"""

import sys
import os
import time
import queue
import threading
import subprocess
import shutil
from typing import Optional, Callable, Dict, Any

from config import STRINGS, EARCON_CHANNEL, METRONOME_CHANNEL

# ---------------------------------------------------------------------------
# Screen Reader Engine Detection & Setup
# ---------------------------------------------------------------------------
class SpeechEngine:
    """Non-blocking, screen-reader-first speech engine with interruptible queuing."""
    
    def __init__(self, default_lang: str = "ar"):
        self.lang = default_lang
        self.backend_name = "None"
        self._tolk = None
        self._speech_queue: queue.Queue = queue.Queue(maxsize=100)
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._synth_callback: Optional[Callable[[int, int, int], None]] = None
        self._earcon_note_off_callback: Optional[Callable[[int, int], None]] = None
        
        # Try initializing backends in priority order
        self._init_backend()

    def _init_backend(self):
        """Attempt initialization of CyTolk, pyttsx3, or system TTS."""
        # 1. Attempt CyTolk (Direct C-bridge to NVDA / JAWS / Windows SAPI)
        try:
            import cytolk
            from cytolk import tolk
            tolk.load()
            if tolk.is_loaded():
                sr_name = tolk.detect_screen_reader()
                self._tolk = tolk
                self.backend_name = f"CyTolk ({sr_name if sr_name else 'SAPI'})"
                print(f"[SpeechEngine] Loaded CyTolk with active screen reader: {self.backend_name}")
                return
        except Exception as e:
            pass

        # 2. On Windows, try native SAPI through comtypes in a background worker
        if sys.platform == "win32":
            try:
                import comtypes.client
                self.backend_name = "Windows SAPI (comtypes)"
                self._start_worker(self._sapi_worker)
                print(f"[SpeechEngine] Loaded {self.backend_name}")
                return
            except Exception:
                pass

        # 3. Attempt pyttsx3 in dedicated worker thread
        try:
            import pyttsx3
            self.backend_name = "pyttsx3"
            self._start_worker(self._pyttsx3_worker)
            print(f"[SpeechEngine] Loaded {self.backend_name}")
            return
        except Exception:
            pass

        # 4. Check for command-line speech engines (spd-say on Linux, termux-tts-speak on Android)
        if shutil.which("spd-say"):
            self.backend_name = "spd-say (speech-dispatcher)"
            self._start_worker(self._cli_worker_spd)
            print(f"[SpeechEngine] Loaded {self.backend_name}")
            return
            
        if shutil.which("termux-tts-speak"):
            self.backend_name = "termux-tts"
            self._start_worker(self._cli_worker_termux)
            print(f"[SpeechEngine] Loaded {self.backend_name}")
            return

        # 5. Console fallback
        self.backend_name = "Console Print"
        self._start_worker(self._console_worker)
        print(f"[SpeechEngine] Screen reader hardware bridge not active. Using: {self.backend_name}")

    def _start_worker(self, target_loop: Callable):
        """Spawns non-blocking daemon thread for fallback TTS processing."""
        self._worker_thread = threading.Thread(target=target_loop, daemon=True, name="TTS-Worker")
        self._worker_thread.start()

    def set_synth_callbacks(self, note_on_cb: Callable, note_off_cb: Callable):
        """Registers synth callbacks for playing earcons."""
        self._synth_callback = note_on_cb
        self._earcon_note_off_callback = note_off_cb

    def set_language(self, lang: str):
        """Sets active language ('ar' or 'en')."""
        if lang in STRINGS:
            self.lang = lang
            text = STRINGS[lang]["language_switched"]
            self.speak(text, interrupt=True)

    def toggle_language(self):
        """Toggles between Arabic and English."""
        new_lang = "en" if self.lang == "ar" else "ar"
        self.set_language(new_lang)

    def get_language(self) -> str:
        return self.lang

    def get_text(self, key: str, **kwargs) -> str:
        """Retrieves localized string and formats placeholders."""
        template = STRINGS.get(self.lang, STRINGS["ar"]).get(key, "")
        if kwargs and template:
            try:
                return template.format(**kwargs)
            except Exception:
                return template
        return template

    def speak(self, text: str, interrupt: bool = True):
        """
        Pronounces text using the active screen reader.
        Never blocks audio timing or musical event loops.
        """
        if not text:
            return

        # Clean text of any accidental bracket noise or markdown
        clean_text = text.replace("**", "").replace("__", "").replace("`", "")

        # 1. CyTolk Direct C-Path (microseconds execution)
        if self._tolk is not None:
            try:
                if self._tolk.has_speech():
                    self._tolk.speak(clean_text, interrupt)
                    return
            except Exception:
                pass

        # 2. Worker Queue Path (Thread-safe, non-blocking)
        if interrupt:
            # Drain queue immediately to silence preceding speech
            while not self._speech_queue.empty():
                try:
                    self._speech_queue.get_nowait()
                except queue.Empty:
                    break

        try:
            self._speech_queue.put_nowait((clean_text, interrupt))
        except queue.Full:
            pass

    def silence(self):
        """Instantly stops all speech."""
        if self._tolk is not None:
            try:
                self._tolk.silence()
            except Exception:
                pass
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
            except queue.Empty:
                break

    # -----------------------------------------------------------------------
    # Worker Thread Implementations for Safe Non-Blocking Fallbacks
    # -----------------------------------------------------------------------
    def _pyttsx3_worker(self):
        """Dedicated thread for pyttsx3 engine to prevent COM / GIL lockups."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 190)
            while not self._stop_event.is_set():
                try:
                    item = self._speech_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if item is None:
                    break
                text, interrupt = item
                if interrupt:
                    engine.stop()
                engine.say(text)
                engine.runAndWait()
        except Exception as e:
            # Fall back to console if pyttsx3 crashes
            self._console_worker()

    def _sapi_worker(self):
        """Dedicated COM thread for Windows native SAPI."""
        try:
            import comtypes.client
            comtypes.CoInitialize()
            voice = comtypes.client.CreateObject("SAPI.SpVoice")
            # 1 = SVSFlagsAsync, 2 = SVSFPurgeBeforeSpeak
            while not self._stop_event.is_set():
                try:
                    item = self._speech_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if item is None:
                    break
                text, interrupt = item
                flags = 3 if interrupt else 1
                try:
                    voice.Speak(text, flags)
                except Exception:
                    pass
        except Exception:
            self._console_worker()

    def _cli_worker_spd(self):
        """Non-blocking wrapper around Linux spd-say."""
        current_proc = None
        while not self._stop_event.is_set():
            try:
                item = self._speech_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            text, interrupt = item
            if interrupt and current_proc and current_proc.poll() is None:
                try:
                    current_proc.terminate()
                except Exception:
                    pass
            try:
                current_proc = subprocess.Popen(
                    ["spd-say", "-e", "-C", text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                print(f"[Speech]: {text}")

    def _cli_worker_termux(self):
        """Non-blocking wrapper around Android Termux TTS."""
        current_proc = None
        while not self._stop_event.is_set():
            try:
                item = self._speech_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            text, interrupt = item
            if interrupt and current_proc and current_proc.poll() is None:
                try:
                    current_proc.terminate()
                except Exception:
                    pass
            try:
                current_proc = subprocess.Popen(
                    ["termux-tts-speak", text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                print(f"[Speech]: {text}")

    def _console_worker(self):
        """Simple clean console readout for testing environments."""
        while not self._stop_event.is_set():
            try:
                item = self._speech_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            text, _ = item
            print(f"[TTS Output]: {text}")

    # -----------------------------------------------------------------------
    # Auditory Earcon Generator
    # -----------------------------------------------------------------------
    def play_earcon(self, earcon_type: str):
        """
        Fires an instant non-verbal auditory cue for screen-reader efficiency.
        Runs asynchronously in a micro-thread so it doesn't hold up timing.
        """
        if not self._synth_callback:
            return

        def _worker():
            ch = EARCON_CHANNEL
            try:
                if earcon_type == "rec_start":
                    # High ascending double beep: C6 (84) -> G6 (91)
                    self._synth_callback(ch, 84, 110)
                    time.sleep(0.06)
                    self._earcon_note_off_callback(ch, 84)
                    self._synth_callback(ch, 91, 115)
                    time.sleep(0.08)
                    self._earcon_note_off_callback(ch, 91)

                elif earcon_type == "rec_stop":
                    # Descending double beep: G6 (91) -> C6 (84)
                    self._synth_callback(ch, 91, 110)
                    time.sleep(0.06)
                    self._earcon_note_off_callback(ch, 91)
                    self._synth_callback(ch, 84, 95)
                    time.sleep(0.08)
                    self._earcon_note_off_callback(ch, 84)

                elif earcon_type == "play":
                    # Bright quick chirp: E5 (76)
                    self._synth_callback(ch, 76, 100)
                    time.sleep(0.07)
                    self._earcon_note_off_callback(ch, 76)

                elif earcon_type == "stop":
                    # Soft low click: C4 (60)
                    self._synth_callback(ch, 60, 80)
                    time.sleep(0.05)
                    self._earcon_note_off_callback(ch, 60)

                elif earcon_type == "boundary":
                    # Warning low buzzer: C3 (48) with low note
                    self._synth_callback(ch, 48, 110)
                    time.sleep(0.1)
                    self._earcon_note_off_callback(ch, 48)

                elif earcon_type == "quantize":
                    # Rapid ascending arpeggio: C5 (72) -> E5 (76) -> G5 (79) -> C6 (84)
                    for n in [72, 76, 79, 84]:
                        self._synth_callback(ch, n, 105)
                        time.sleep(0.035)
                        self._earcon_note_off_callback(ch, n)

                elif earcon_type == "step_on":
                    # High woodblock on drum channel
                    self._synth_callback(METRONOME_CHANNEL, 76, 115)
                    time.sleep(0.04)
                    self._earcon_note_off_callback(METRONOME_CHANNEL, 76)

                elif earcon_type == "step_off":
                    # Subtle low woodblock on drum channel
                    self._synth_callback(METRONOME_CHANNEL, 77, 60)
                    time.sleep(0.04)
                    self._earcon_note_off_callback(METRONOME_CHANNEL, 77)

                elif earcon_type == "track_switch":
                    # Soft pluck
                    self._synth_callback(ch, 72, 90)
                    time.sleep(0.04)
                    self._earcon_note_off_callback(ch, 72)

            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True, name="Earcon-Player").start()

    def shutdown(self):
        """Clean shutdown of speech threads."""
        self._stop_event.set()
        if self._speech_queue:
            try:
                self._speech_queue.put_nowait(None)
            except Exception:
                pass
        if self._tolk is not None:
            try:
                self._tolk.unload()
            except Exception:
                pass


# Global Singleton Speech Engine instance
speech = SpeechEngine(default_lang="ar")
