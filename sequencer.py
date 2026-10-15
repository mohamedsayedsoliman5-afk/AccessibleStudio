import copy
import json
import time
import config


class Track:
    def __init__(self, track_id: int, channel: int, program: int):
        self.track_id = track_id
        self.channel = channel
        self.program = program
        self.volume = 108
        self.pan = 64
        self.reverb = 42
        self.delay = 24
        self.cutoff = 110
        self.drive = 0
        self.muted = False
        self.solo = False
        self.patterns = [[] for _ in range(4)]
        self._active_pattern_ref = 0

    @property
    def events(self):
        return self.patterns[self._active_pattern_ref]

    @events.setter
    def events(self, val):
        self.patterns[self._active_pattern_ref] = val


class Sequencer:
    def __init__(self, synth, speech):
        self.synth = synth
        self.speech = speech
        self.bpm = config.DEFAULT_BPM
        self.bars = 4
        self.beats_per_bar = 4
        self.loop_enabled = True
        self.metronome_enabled = True
        self.quantize_div_idx = 2

        self.current_pattern_idx = 0
        self.song_chain_mode = False
        self.copied_pattern_buffer = None

        self.tracks = []
        for idx in range(8):
            ch = 9 if idx == 7 else idx
            prog = config.DEFAULT_TRACK_PROGRAMS[idx]
            tr = Track(idx, ch, prog)
            self.tracks.append(tr)
            self.synth.set_instrument(ch, prog)
            self.synth.set_volume(ch, tr.volume)
            self.synth.set_pan(ch, tr.pan)
            self.synth.set_reverb(ch, tr.reverb)
            self.synth.set_delay(ch, tr.delay)
            self.synth.set_cutoff(ch, tr.cutoff)
            self.synth.set_drive(ch, tr.drive)

        self.active_track_idx = 0
        self.state = "IDLE"
        self._start_perf = 0.0
        self._last_pos_sec = 0.0
        self._last_beat_idx = -1
        self._open_recorded_notes = {}
        self._undo_stack = []
        self._redo_stack = []

    def select_pattern(self, pat_idx: int, announce: bool = True):
        self.synth.all_notes_off()
        self.current_pattern_idx = pat_idx % 4
        for tr in self.tracks:
            tr._active_pattern_ref = self.current_pattern_idx
        if announce:
            pat_names = ["A (المقدمة)", "B (الكوبليه)", "C (القرار)", "D (الصولو)"]
            self.speech.speak(f"تم الانتقال إلى المقطع الموسيقي {pat_names[self.current_pattern_idx]}")

    def copy_current_pattern(self):
        self.copied_pattern_buffer = [copy.deepcopy(tr.events) for tr in self.tracks]
        pat_let = ["A", "B", "C", "D"][self.current_pattern_idx]
        self.speech.speak(f"تم نسخ جميع تراكات المقطع {pat_let}")

    def paste_to_current_pattern(self):
        if not self.copied_pattern_buffer:
            self.speech.speak("لا يوجد مقطع منسوخ في الحافظة")
            return
        self.push_undo_state()
        for idx, evs in enumerate(self.copied_pattern_buffer):
            self.tracks[idx].events = copy.deepcopy(evs)
        pat_let = ["A", "B", "C", "D"][self.current_pattern_idx]
        self.speech.speak(f"تم لصق التراكات في المقطع {pat_let}")

    @property
    def active_track(self) -> Track:
        return self.tracks[self.active_track_idx]

    @property
    def beat_duration(self) -> float:
        return 60.0 / float(self.bpm)

    @property
    def loop_duration(self) -> float:
        return self.bars * self.beats_per_bar * self.beat_duration

    def get_playhead_progress(self) -> float:
        if self.state in ("IDLE", "COUNT_IN") or self.loop_duration <= 0:
            return 0.0
        return max(0.0, min(1.0, self._last_pos_sec / self.loop_duration))

    def get_bar_beat_display(self):
        if self.state == "COUNT_IN":
            return 0, max(1, self._last_beat_idx + 1)
        if self.state == "IDLE":
            return 1, 1
        total_beats = int(self._last_pos_sec / self.beat_duration)
        bar = (total_beats // self.beats_per_bar) + 1
        beat = (total_beats % self.beats_per_bar) + 1
        return bar, beat

    def push_undo_state(self):
        snapshot = [[copy.deepcopy(p) for p in tr.patterns] for tr in self.tracks]
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 32:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            self.speech.play_earcon(self.synth, "boundary")
            self.speech.speak("لا توجد خطوات سابقة للتراجع عنها")
            return
        current_snapshot = [[copy.deepcopy(p) for p in tr.patterns] for tr in self.tracks]
        self._redo_stack.append(current_snapshot)
        prev_snapshot = self._undo_stack.pop()
        self.synth.all_notes_off()
        for idx, pat_list in enumerate(prev_snapshot):
            self.tracks[idx].patterns = pat_list
        self.speech.play_earcon(self.synth, "undo")
        self.speech.speak("تم التراجع عن آخر تعديل")

    def redo(self):
        if not self._redo_stack:
            self.speech.play_earcon(self.synth, "boundary")
            self.speech.speak("لا توجد خطوات لاحقة للإعادة")
            return
        current_snapshot = [[copy.deepcopy(p) for p in tr.patterns] for tr in self.tracks]
        self._undo_stack.append(current_snapshot)
        next_snapshot = self._redo_stack.pop()
        self.synth.all_notes_off()
        for idx, pat_list in enumerate(next_snapshot):
            self.tracks[idx].patterns = pat_list
        self.speech.play_earcon(self.synth, "redo")
        self.speech.speak("تمت إعادة الخطوة")

    def is_track_audible(self, track: Track) -> bool:
        any_solo = any(t.solo for t in self.tracks)
        if any_solo:
            return track.solo and not track.muted
        return not track.muted

    def toggle_play(self):
        if self.state in ("PLAYING", "RECORDING", "COUNT_IN"):
            self.stop()
            self.speech.speak("إيقاف التشغيل")
        else:
            self.state = "PLAYING"
            self._start_perf = time.perf_counter()
            self._last_pos_sec = 0.0
            self._last_beat_idx = -1
            self.speech.speak("تشغيل التراكات")

    def toggle_record(self):
        if self.state in ("RECORDING", "COUNT_IN"):
            self._finalize_open_recorded_notes(self._last_pos_sec)
            self.state = "PLAYING"
            self.speech.play_earcon(self.synth, "record_stop")
            self.speech.speak(f"تم حفظ التسجيل على تراك {self.active_track_idx + 1}، جاري الاستماع")
        else:
            self.push_undo_state()
            self.synth.all_notes_off()
            self.state = "COUNT_IN"
            self._start_perf = time.perf_counter()
            self._last_pos_sec = 0.0
            self._last_beat_idx = -1
            self.speech.speak(f"استعداد للتسجيل على تراك {self.active_track_idx + 1}، أربع عدات")

    def stop(self):
        if self.state == "RECORDING":
            self._finalize_open_recorded_notes(self._last_pos_sec)
        self.state = "IDLE"
        self._last_pos_sec = 0.0
        self.synth.all_notes_off()

    def record_note_on(self, note: int, vel: int):
        if self.state != "RECORDING":
            return
        pos = (time.perf_counter() - self._start_perf) % self.loop_duration
        self._open_recorded_notes[note] = (vel, pos)
        self.active_track.events.append({
            "type": "note_on",
            "note": int(note),
            "vel": int(vel),
            "time": round(pos, 5),
        })
        self.active_track.events.sort(key=lambda e: e["time"])

    def record_note_off(self, note: int):
        if self.state != "RECORDING":
            return
        if note not in self._open_recorded_notes:
            return
        vel, start_pos = self._open_recorded_notes.pop(note)
        pos = (time.perf_counter() - self._start_perf) % self.loop_duration
        if pos <= start_pos:
            pos = min(self.loop_duration - 0.005, start_pos + 0.1)
        self.active_track.events.append({
            "type": "note_off",
            "note": int(note),
            "vel": 0,
            "time": round(pos, 5),
        })
        self.active_track.events.sort(key=lambda e: e["time"])

    def toggle_piano_roll_note_at(self, track_idx: int, norm_time: float, midi_note: int):
        self.push_undo_state()
        tr = self.tracks[track_idx]
        step_sec = self.beat_duration / 4.0
        target_t = round((norm_time * self.loop_duration) / step_sec) * step_sec
        target_end = min(self.loop_duration - 0.005, target_t + step_sec * 0.85)

        for i, ev in enumerate(list(tr.events)):
            if ev["type"] == "note_on" and ev["note"] == midi_note and abs(ev["time"] - target_t) < (step_sec * 0.5):
                tr.events.remove(ev)
                for off_ev in list(tr.events):
                    if off_ev["type"] == "note_off" and off_ev["note"] == midi_note and off_ev["time"] >= target_t:
                        tr.events.remove(off_ev)
                        break
                return

        tr.events.append({"type": "note_on", "note": int(midi_note), "vel": 108, "time": round(target_t, 5)})
        tr.events.append({"type": "note_off", "note": int(midi_note), "vel": 0, "time": round(target_end, 5)})
        tr.events.sort(key=lambda e: (e["time"], 0 if e["type"] == "note_off" else 1))
        self.synth.schedule_preview_notes(tr.channel, [(midi_note, 108, 0.0, 0.16)])

    def _finalize_open_recorded_notes(self, current_pos: float):
        for note, (vel, start_pos) in list(self._open_recorded_notes.items()):
            end_pos = max(start_pos + 0.08, min(self.loop_duration - 0.004, current_pos))
            self.active_track.events.append({
                "type": "note_off",
                "note": int(note),
                "vel": 0,
                "time": round(end_pos, 5),
            })
        self._open_recorded_notes.clear()
        self.active_track.events.sort(key=lambda e: e["time"])

    def cycle_quantize_division(self):
        self.quantize_div_idx = (self.quantize_div_idx + 1) % len(config.QUANTIZE_DIVISIONS)
        q_info = config.QUANTIZE_DIVISIONS[self.quantize_div_idx]
        self.speech.speak(f"شبكة الضبط الإيقاعي: {q_info['ar']}")

    def quantize_active_track(self):
        tr = self.active_track
        if not tr.events:
            self.speech.speak("التراك الحالي فارغ لا توجد نوتات لضبطها")
            return

        self.push_undo_state()
        div = config.QUANTIZE_DIVISIONS[self.quantize_div_idx]["div"]
        step_sec = (self.beat_duration * 4.0) / float(div)

        for ev in tr.events:
            snapped = round(ev["time"] / step_sec) * step_sec
            if ev["type"] == "note_off":
                snapped = min(self.loop_duration - 0.002, max(0.02, snapped))
            else:
                snapped = min(self.loop_duration - 0.02, max(0.0, snapped))
            ev["time"] = round(snapped, 5)

        tr.events.sort(key=lambda e: (e["time"], 0 if e["type"] == "note_off" else 1))
        self.speech.play_earcon(self.synth, "quantize")
        q_name = config.QUANTIZE_DIVISIONS[self.quantize_div_idx]["ar"]
        self.speech.speak(f"تم الضبط الإيقاعي لتراك {self.active_track_idx + 1} على شبكة {q_name}")

    def clear_active_track(self):
        if not self.active_track.events:
            self.speech.speak(f"تراك {self.active_track_idx + 1} فارغ بالفعل")
            return
        self.push_undo_state()
        self.synth.all_notes_off(self.active_track.channel)
        self.active_track.events.clear()
        self._open_recorded_notes.clear()
        self.speech.speak(f"تم مسح جميع النغمات في تراك {self.active_track_idx + 1}")

    def update(self):
        if self.state == "IDLE":
            return

        now = time.perf_counter()
        elapsed = now - self._start_perf

        if self.state == "COUNT_IN":
            beat_idx = int(elapsed / self.beat_duration)
            if beat_idx > self._last_beat_idx:
                self._last_beat_idx = beat_idx
                if beat_idx < 4:
                    kind = "click_high" if beat_idx == 0 else "click_low"
                    self.speech.play_earcon(self.synth, kind)
                else:
                    self.state = "RECORDING"
                    self._start_perf = now
                    self._last_pos_sec = 0.0
                    self._last_beat_idx = -1
                    self.speech.play_earcon(self.synth, "record_start")
            return

        loop_len = self.loop_duration
        if not self.loop_enabled and elapsed >= loop_len:
            self.stop()
            self.speech.speak("انتهى تشغيل التراك")
            return

        curr_pos = elapsed % loop_len
        beat_idx = int(curr_pos / self.beat_duration)

        if self.metronome_enabled and beat_idx != self._last_beat_idx:
            self._last_beat_idx = beat_idx
            kind = "click_high" if (beat_idx % self.beats_per_bar == 0) else "click_low"
            self.speech.play_earcon(self.synth, kind)

        if curr_pos < self._last_pos_sec:
            self._trigger_events_in_window(self._last_pos_sec, loop_len)
            self._finalize_open_recorded_notes(loop_len)
            self.synth.all_notes_off()
            if self.song_chain_mode and self.state == "PLAYING":
                for p_step in range(1, 5):
                    cand = (self.current_pattern_idx + p_step) % 4
                    if any(len(t.patterns[cand]) > 0 for t in self.tracks):
                        self.select_pattern(cand, announce=False)
                        break
            self._trigger_events_in_window(0.0, curr_pos)
        else:
            self._trigger_events_in_window(self._last_pos_sec, curr_pos)

        self._last_pos_sec = curr_pos

    def _trigger_events_in_window(self, t_start: float, t_end: float):
        for tr in self.tracks:
            if not self.is_track_audible(tr) or not tr.events:
                continue
            for ev in tr.events:
                ev_t = ev["time"]
                if t_start <= ev_t < t_end:
                    if ev["type"] == "note_on":
                        self.synth.note_on(tr.channel, ev["note"], ev["vel"])
                    elif ev["type"] == "note_off":
                        self.synth.note_off(tr.channel, ev["note"])

    def save_session(self, filepath: str = config.SESSION_FILE):
        data = {
            "bpm": self.bpm,
            "bars": self.bars,
            "loop_enabled": self.loop_enabled,
            "metronome_enabled": self.metronome_enabled,
            "maqam_idx": self.synth.maqam_idx,
            "maqam_root": self.synth.maqam_root,
            "current_pattern_idx": self.current_pattern_idx,
            "song_chain_mode": self.song_chain_mode,
            "tracks": [
                {
                    "track_id": tr.track_id,
                    "channel": tr.channel,
                    "program": tr.program,
                    "volume": tr.volume,
                    "pan": tr.pan,
                    "reverb": tr.reverb,
                    "delay": tr.delay,
                    "cutoff": tr.cutoff,
                    "drive": tr.drive,
                    "muted": tr.muted,
                    "solo": tr.solo,
                    "patterns": tr.patterns,
                }
                for tr in self.tracks
            ],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.speech.speak("تم حفظ المشروع بالكامل بنجاح")

    def load_session(self, filepath: str = config.SESSION_FILE):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.push_undo_state()
            self.bpm = data.get("bpm", config.DEFAULT_BPM)
            self.bars = data.get("bars", 4)
            self.loop_enabled = data.get("loop_enabled", True)
            self.metronome_enabled = data.get("metronome_enabled", True)
            self.song_chain_mode = data.get("song_chain_mode", False)
            self.synth.set_maqam(data.get("maqam_idx", 1), data.get("maqam_root", 0))
            for idx, tr_data in enumerate(data.get("tracks", [])):
                if idx < len(self.tracks):
                    tr = self.tracks[idx]
                    tr.program = tr_data.get("program", tr.program)
                    tr.volume = tr_data.get("volume", 108)
                    tr.pan = tr_data.get("pan", 64)
                    tr.reverb = tr_data.get("reverb", 42)
                    tr.delay = tr_data.get("delay", 24)
                    tr.cutoff = tr_data.get("cutoff", 110)
                    tr.drive = tr_data.get("drive", 0)
                    tr.muted = tr_data.get("muted", False)
                    tr.solo = tr_data.get("solo", False)
                    if "patterns" in tr_data:
                        tr.patterns = tr_data["patterns"]
                    elif "events" in tr_data:
                        tr.patterns[0] = tr_data["events"]
                    self.synth.set_instrument(tr.channel, tr.program)
                    self.synth.set_volume(tr.channel, tr.volume)
                    self.synth.set_pan(tr.channel, tr.pan)
                    self.synth.set_reverb(tr.channel, tr.reverb)
                    self.synth.set_delay(tr.channel, tr.delay)
                    self.synth.set_cutoff(tr.channel, tr.cutoff)
                    self.synth.set_drive(tr.channel, tr.drive)
            self.select_pattern(data.get("current_pattern_idx", 0), announce=False)
            self.speech.speak("تم استرجاع جلسة العمل المحفوظة")
        except FileNotFoundError:
            self.speech.speak("لا يوجد ملف جلسة محفوظ مسبقاً")
