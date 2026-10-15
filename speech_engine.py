import queue
import threading
import ctypes
import sys


class SpeechEngine:
    def __init__(self, lang: str = "ar"):
        self.lang = lang
        self.last_spoken = ""
        self._tolk = None
        self._nvda_dll = None
        self._queue = queue.Queue()
        self._running = True

        try:
            from cytolk import tolk
            tolk.load()
            self._tolk = tolk
        except Exception:
            self._tolk = None

        if self._tolk is None and sys.platform == "win32":
            for dll_name in ("nvdaControllerClient64.dll", "nvdaControllerClient32.dll"):
                try:
                    dll = ctypes.windll.LoadLibrary(dll_name)
                    if dll.nvdaController_testIfRunning() == 0:
                        self._nvda_dll = dll
                        break
                except Exception:
                    pass

        self._worker = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker.start()

    def _speech_worker(self):
        sapi_voice = None
        tts_engine = None

        if sys.platform == "win32":
            try:
                import comtypes.client
                sapi_voice = comtypes.client.CreateObject("SAPI.SpVoice")
            except Exception:
                try:
                    import win32com.client
                    sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
                except Exception:
                    sapi_voice = None

        if sapi_voice is None:
            try:
                import pyttsx3
                tts_engine = pyttsx3.init()
                tts_engine.setProperty("rate", 195)
            except Exception:
                tts_engine = None

        while self._running:
            try:
                text, interrupt = self._queue.get(timeout=0.08)
            except queue.Empty:
                continue

            if not self._running:
                break

            try:
                if sapi_voice is not None:
                    flags = 3 if interrupt else 1
                    sapi_voice.Speak(text, flags)
                elif tts_engine is not None:
                    tts_engine.say(text)
                    tts_engine.runAndWait()
            except Exception:
                pass

    def speak(self, text: str, interrupt: bool = True):
        if not text:
            return
        self.last_spoken = text
        print(f"[TTS] {text}")

        if self._tolk is not None:
            try:
                self._tolk.output(text, interrupt=interrupt)
                return
            except Exception:
                pass

        if self._nvda_dll is not None:
            try:
                if interrupt:
                    self._nvda_dll.nvdaController_cancelSpeech()
                self._nvda_dll.nvdaController_speakText(ctypes.c_wchar_p(text))
                return
            except Exception:
                pass

        if interrupt:
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    break
        self._queue.put((text, interrupt))

    def play_earcon(self, synth, kind: str):
        if synth is None:
            return
        if kind == "record_start":
            synth.schedule_preview_notes(9, [(76, 115, 0.0, 0.07), (76, 125, 0.08, 0.16)])
        elif kind == "record_stop":
            synth.schedule_preview_notes(9, [(77, 105, 0.0, 0.12)])
        elif kind == "boundary":
            synth.schedule_preview_notes(9, [(75, 95, 0.0, 0.07)])
        elif kind == "quantize":
            synth.schedule_preview_notes(0, [(72, 95, 0.0, 0.06), (76, 95, 0.06, 0.12), (79, 105, 0.12, 0.22)])
        elif kind == "undo":
            synth.schedule_preview_notes(0, [(79, 90, 0.0, 0.07), (72, 90, 0.07, 0.16)])
        elif kind == "redo":
            synth.schedule_preview_notes(0, [(72, 90, 0.0, 0.07), (79, 90, 0.07, 0.16)])
        elif kind == "click_high":
            synth.schedule_preview_notes(9, [(76, 122, 0.0, 0.045)])
        elif kind == "click_low":
            synth.schedule_preview_notes(9, [(77, 96, 0.0, 0.045)])

    def shutdown(self):
        self._running = False
        if self._tolk is not None:
            try:
                self._tolk.unload()
            except Exception:
                pass
