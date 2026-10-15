import os
import sys
import json
import queue
import threading
import ctypes
import config


class SpeechEngine:
    def __init__(self, lang: str = "ar"):
        self.lang = lang
        self.last_spoken = ""
        self.rate = 2
        self.volume = 100
        self.preferred_voice_id = ""
        self.preferred_voice_name = "Default"
        self.available_voices = []
        self.current_voice_idx = 0
        self.use_screen_reader_first = True

        self._load_user_settings()

        self._tolk = None
        self._nvda_dll = None
        self._queue = queue.Queue()
        self._cmd_queue = queue.Queue()
        self._running = True

        app_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
        if sys.platform == "win32":
            candidates = [
                os.path.join(app_dir, "nvdaControllerClient64.dll"),
                os.path.join(app_dir, "nvdaControllerClient32.dll"),
                "nvdaControllerClient64.dll",
                "nvdaControllerClient32.dll",
            ]
            for dll_path in candidates:
                try:
                    dll = ctypes.windll.LoadLibrary(dll_path)
                    dll.nvdaController_testIfRunning.restype = ctypes.c_long
                    if dll.nvdaController_testIfRunning() == 0:
                        dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                        dll.nvdaController_speakText.restype = ctypes.c_long
                        dll.nvdaController_cancelSpeech.restype = ctypes.c_long
                        self._nvda_dll = dll
                        print(f"[SpeechEngine] Connected directly to running NVDA via {os.path.basename(dll_path)}")
                        break
                except Exception:
                    pass

        if self._nvda_dll is None:
            try:
                from cytolk import tolk
                tolk.load()
                if tolk.detect_screen_reader():
                    self._tolk = tolk
                else:
                    tolk.unload()
            except Exception:
                self._tolk = None

        self._ready_event = threading.Event()
        self._worker = threading.Thread(target=self._speech_worker, daemon=True)
        self._worker.start()
        self._ready_event.wait(timeout=1.5)

    def _load_user_settings(self):
        if os.path.isfile(config.SETTINGS_FILE):
            try:
                with open(config.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.preferred_voice_id = data.get("voice_id", "")
                self.preferred_voice_name = data.get("voice_name", "Default")
                self.rate = int(data.get("speech_rate", 2))
                self.lang = data.get("lang", self.lang)
                self.use_screen_reader_first = bool(data.get("use_screen_reader_first", True))
            except Exception:
                pass

    def save_user_settings(self):
        data = {
            "voice_id": self.preferred_voice_id,
            "voice_name": self.preferred_voice_name,
            "speech_rate": self.rate,
            "lang": self.lang,
            "use_screen_reader_first": self.use_screen_reader_first,
        }
        try:
            with open(config.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _discover_all_windows_voices(self, sapi_voice, create_object_fn):
        tokens = []
        seen_ids = set()

        try:
            std_voices = sapi_voice.GetVoices()
            for i in range(std_voices.Count):
                tok = std_voices.Item(i)
                tid = tok.Id
                tname = tok.GetDescription()
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    tokens.append((tid, tname, tok))
        except Exception:
            pass

        onecore_reg_paths = [
            r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices",
            r"HKEY_CURRENT_USER\SOFTWARE\Microsoft\Speech_OneCore\Voices",
            r"HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Speech_OneCore\Voices",
        ]
        for reg_path in onecore_reg_paths:
            try:
                cat = create_object_fn("SAPI.SpObjectTokenCategory")
                cat.SetId(reg_path, False)
                oc_tokens = cat.EnumerateTokens()
                for i in range(oc_tokens.Count):
                    tok = oc_tokens.Item(i)
                    tid = tok.Id
                    tname = tok.GetDescription()
                    if tid not in seen_ids:
                        seen_ids.add(tid)
                        tokens.append((tid, tname, tok))
            except Exception:
                continue

        return tokens

    def _select_best_initial_voice(self, tokens):
        if not tokens:
            return -1

        if self.preferred_voice_id:
            for idx, (tid, tname, _) in enumerate(tokens):
                if tid == self.preferred_voice_id or self.preferred_voice_name.lower() in tname.lower():
                    return idx

        for idx, (tid, tname, tok) in enumerate(tokens):
            low = (tid + " " + tname).lower()
            if any(k in low for k in ("arabic", "ar-", "hoda", "naayf", "salma", "shakir", "tarik", "laila", "maged", "zariyah")):
                return idx

        for idx, (tid, tname, _) in enumerate(tokens):
            low = tname.lower()
            if "david" not in low:
                return idx

        return 0

    def _speech_worker(self):
        sapi_voice = None
        tts_engine = None
        voice_tokens = []

        if sys.platform == "win32":
            try:
                import comtypes
                import comtypes.client
                comtypes.CoInitialize()
                sapi_voice = comtypes.client.CreateObject("SAPI.SpVoice")
                voice_tokens = self._discover_all_windows_voices(sapi_voice, comtypes.client.CreateObject)
            except Exception:
                try:
                    import pythoncom
                    import win32com.client
                    pythoncom.CoInitialize()
                    sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
                    voice_tokens = self._discover_all_windows_voices(sapi_voice, win32com.client.Dispatch)
                except Exception:
                    sapi_voice = None

        if sapi_voice is not None and voice_tokens:
            self.available_voices = [(tid, tname) for tid, tname, _ in voice_tokens]
            best_idx = self._select_best_initial_voice(voice_tokens)
            if 0 <= best_idx < len(voice_tokens):
                self.current_voice_idx = best_idx
                tid, tname, tok = voice_tokens[best_idx]
                try:
                    sapi_voice.Voice = tok
                    self.preferred_voice_id = tid
                    self.preferred_voice_name = tname
                except Exception:
                    pass
            try:
                sapi_voice.Rate = self.rate
                sapi_voice.Volume = self.volume
            except Exception:
                pass
        else:
            try:
                import pyttsx3
                tts_engine = pyttsx3.init()
                voices = tts_engine.getProperty("voices") or []
                self.available_voices = [(v.id, v.name) for v in voices]
                best_idx = 0
                for i, (vid, vname) in enumerate(self.available_voices):
                    low = (vid + " " + vname).lower()
                    if self.preferred_voice_id and vid == self.preferred_voice_id:
                        best_idx = i
                        break
                    if "david" not in low:
                        best_idx = i
                if self.available_voices:
                    self.current_voice_idx = best_idx
                    vid, vname = self.available_voices[best_idx]
                    tts_engine.setProperty("voice", vid)
                    self.preferred_voice_id = vid
                    self.preferred_voice_name = vname
                tts_engine.setProperty("rate", 180 + self.rate * 15)
            except Exception:
                tts_engine = None

        self._ready_event.set()

        while self._running:
            while not self._cmd_queue.empty():
                try:
                    cmd, val = self._cmd_queue.get_nowait()
                    if cmd == "set_voice" and voice_tokens and sapi_voice is not None:
                        idx = val % len(voice_tokens)
                        tid, tname, tok = voice_tokens[idx]
                        sapi_voice.Voice = tok
                        self.current_voice_idx = idx
                        self.preferred_voice_id = tid
                        self.preferred_voice_name = tname
                        self.save_user_settings()
                    elif cmd == "set_voice" and tts_engine is not None and self.available_voices:
                        idx = val % len(self.available_voices)
                        vid, vname = self.available_voices[idx]
                        tts_engine.setProperty("voice", vid)
                        self.current_voice_idx = idx
                        self.preferred_voice_id = vid
                        self.preferred_voice_name = vname
                        self.save_user_settings()
                    elif cmd == "set_rate":
                        self.rate = max(-5, min(8, int(val)))
                        if sapi_voice is not None:
                            sapi_voice.Rate = self.rate
                        elif tts_engine is not None:
                            tts_engine.setProperty("rate", 180 + self.rate * 15)
                        self.save_user_settings()
                except Exception:
                    pass

            try:
                text, interrupt = self._queue.get(timeout=0.05)
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

    def cycle_voice(self, delta: int = 1):
        if not self.available_voices:
            self.speak("لا توجد أصوات إضافية مكتشفة، يتم القراءة عبر قارئ الشاشة")
            return
        self.use_screen_reader_first = False
        next_idx = (self.current_voice_idx + delta) % len(self.available_voices)
        self.current_voice_idx = next_idx
        tid, tname = self.available_voices[next_idx]
        self.preferred_voice_id = tid
        self.preferred_voice_name = tname
        self._cmd_queue.put(("set_voice", next_idx))
        self.speak(f"الصوت الحالي: {tname}", interrupt=True)

    def toggle_screen_reader_priority(self):
        self.use_screen_reader_first = not self.use_screen_reader_first
        self.save_user_settings()
        if self.use_screen_reader_first:
            self.speak("الأولوية لقارئ الشاشة النشط NVDA أو JAWS")
        else:
            self.speak(f"الأولوية لصوت النظام المحدد: {self.preferred_voice_name}")

    def adjust_rate(self, delta: int):
        new_rate = max(-5, min(8, self.rate + delta))
        self._cmd_queue.put(("set_rate", new_rate))
        self.speak(f"سرعة الناطق {new_rate:+d}")

    def speak(self, text: str, interrupt: bool = True):
        if not text:
            return
        self.last_spoken = text
        print(f"[TTS: {self.preferred_voice_name}] {text}")

        if self.use_screen_reader_first:
            if self._nvda_dll is not None:
                try:
                    if interrupt:
                        self._nvda_dll.nvdaController_cancelSpeech()
                    self._nvda_dll.nvdaController_speakText(ctypes.c_wchar_p(str(text)))
                    return
                except Exception:
                    pass

            if self._tolk is not None:
                try:
                    self._tolk.output(text, interrupt=interrupt)
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
            synth.schedule_preview_notes(9, [(76, 118, 0.0, 0.07), (76, 126, 0.08, 0.16)])
        elif kind == "record_stop":
            synth.schedule_preview_notes(9, [(77, 108, 0.0, 0.12)])
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
