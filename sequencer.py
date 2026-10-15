import copy
import json
import time
import config


class Track:
    def __init__(self, track_id: int, channel: int, program: int):
        self.track_id = track_id
        self.channel = channel
        self.program = program
        self.volume = 105
        self.pan = 64
        self.reverb = 40
        self.muted = False
        self.solo = False
        self.events = []


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

        self.active_track_idx = 0
        self.state = "IDLE"
        self._start_perf = 0.0
        self._last_pos_sec = 0.0
        self._last_beat_idx = -1
        self._open_recorded_notes = {}
        self._undo_stack = []
        self._redo_stack = []

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
        snapshot = [copy.deepcopy(tr.events) for tr in self.tracks]
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 32:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            self.speech.play_earcon(self.synth, "boundary")
            self.speech.speak("لا توجد خطوات سابقة للتراجع عنها")
            return
        current_snapshot = [copy.deepcopy(tr.events) for tr in self.tracks]
        self._redo_stack.append(current_snapshot)
        prev_snapshot = self._undo_stack.pop()
        self.synth.all_notes_off()
        for idx, ev_list in enumerate(prev_snapshot):
            self.tracks[idx].events = ev_list
        self.speech.play_earcon(self.synth, "undo")
        self.speech.speak("تم التراجع عن آخر تعديل")

    def redo(self):
        if not self._redo_stack:
            self.speech.play_earcon(self.synth, "boundary")
            self.speech.speak("لا توجد خطوات لاحقة للإعادة")
            return
        current_snapshot = [copy.deepcopy(tr.events) for tr in self.tracks]
        self._undo_stack.append(current_snapshot)
        next_snapshot = self._redo_stack.pop()
        self.synth.all_notes_off()
        for idx, ev_list in enumerate(next_snapshot):
            self.tracks[idx].events = ev_list
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
            "tracks": [
                {
                    "track_id": tr.track_id,
                    "channel": tr.channel,
                    "program": tr.program,
                    "volume": tr.volume,
                    "pan": tr.pan,
                    "reverb": tr.reverb,
                    "muted": tr.muted,
                    "solo": tr.solo,
                    "events": tr.events,
                }
                for tr in self.tracks
            ],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.speech.speak("تم حفظ جلسة العمل بنجاح")

    def load_session(self, filepath: str = config.SESSION_FILE):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.push_undo_state()
            self.bpm = data.get("bpm", config.DEFAULT_BPM)
            self.bars = data.get("bars", 4)
            self.loop_enabled = data.get("loop_enabled", True)
            self.metronome_enabled = data.get("metronome_enabled", True)
            self.synth.set_maqam(data.get("maqam_idx", 0), data.get("maqam_root", 0))
            for idx, tr_data in enumerate(data.get("tracks", [])):
                if idx < len(self.tracks):
                    tr = self.tracks[idx]
                    tr.program = tr_data.get("program", tr.program)
                    tr.volume = tr_data.get("volume", 105)
                    tr.pan = tr_data.get("pan", 64)
                    tr.reverb = tr_data.get("reverb", 40)
                    tr.muted = tr_data.get("muted", False)
                    tr.solo = tr_data.get("solo", False)
                    tr.events = tr_data.get("events", [])
                    self.synth.set_instrument(tr.channel, tr.program)
                    self.synth.set_volume(tr.channel, tr.volume)
                    self.synth.set_pan(tr.channel, tr.pan)
                    self.synth.set_reverb(tr.channel, tr.reverb)
            self.speech.speak("تم استرجاع جلسة العمل المحفوظة")
        except FileNotFoundError:
            self.speech.speak("لا يوجد ملف جلسة محفوظ مسبقاً")
