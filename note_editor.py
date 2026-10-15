import config


class AccessibleNoteEditor:
    def __init__(self, sequencer, synth, speech):
        self.sequencer = sequencer
        self.synth = synth
        self.speech = speech
        self.active = False
        self.selected_idx = 0

    def _extract_note_pairs(self, track):
        events = sorted(track.events, key=lambda e: e["time"])
        open_map = {}
        pairs = []
        for idx, ev in enumerate(events):
            if ev["type"] == "note_on":
                open_map[ev["note"]] = (idx, ev)
            elif ev["type"] == "note_off" and ev["note"] in open_map:
                on_idx, on_ev = open_map.pop(ev["note"])
                pairs.append((on_ev, ev))
        return pairs

    def toggle_mode(self):
        self.active = not self.active
        tr = self.sequencer.active_track
        pairs = self._extract_note_pairs(tr)
        if self.active:
            self.selected_idx = 0
            if not pairs:
                self.speech.speak(f"تم فتح محرر النوتات لتراك {tr.track_id + 1}، التراك فارغ حالياً")
            else:
                self.speech.speak(f"تم فتح محرر النوتات لتراك {tr.track_id + 1}، إجمالي {len(pairs)} نوتة")
                self.announce_current_note(preview=True)
        else:
            self.speech.speak("تم إغلاق محرر النوتات والعودة لوضع العزف")

    def announce_current_note(self, preview: bool = True):
        tr = self.sequencer.active_track
        pairs = self._extract_note_pairs(tr)
        if not pairs:
            self.speech.speak("لا توجد نوتات مسجلة في هذا التراك")
            return
        self.selected_idx = max(0, min(len(pairs) - 1, self.selected_idx))
        on_ev, off_ev = pairs[self.selected_idx]
        note_num = on_ev["note"]
        if tr.channel == 9:
            piece_name = next((p["ar"] for p in config.DRUM_PIECES if p["note"] == note_num), f"إيقاع {note_num}")
            desc = piece_name
        else:
            n_name = config.NOTE_NAMES_AR[note_num % 12]
            octv = (note_num // 12) - 1
            desc = f"{n_name} أوكتاف {octv}"

        beat_pos = (on_ev["time"] / self.sequencer.beat_duration) + 1.0
        dur_ms = int(max(0.05, off_ev["time"] - on_ev["time"]) * 1000)
        if preview:
            self.synth.schedule_preview_notes(tr.channel, [(note_num, on_ev["vel"], 0.0, 0.22)])
        self.speech.speak(
            f"نوتة {self.selected_idx + 1} من {len(pairs)}: {desc}، عند النبضة {beat_pos:.2f}، مدتها {dur_ms} ملي ثانية"
        )

    def navigate(self, delta: int):
        tr = self.sequencer.active_track
        pairs = self._extract_note_pairs(tr)
        if not pairs:
            self.speech.speak("التراك فارغ")
            return
        self.selected_idx = (self.selected_idx + delta) % len(pairs)
        self.announce_current_note(preview=True)

    def transpose_selected_note(self, semitones: int):
        tr = self.sequencer.active_track
        pairs = self._extract_note_pairs(tr)
        if not pairs:
            return
        self.sequencer.push_undo_state()
        pairs = self._extract_note_pairs(tr)
        self.selected_idx = max(0, min(len(pairs) - 1, self.selected_idx))
        on_ev, off_ev = pairs[self.selected_idx]
        new_note = max(0, min(127, on_ev["note"] + semitones))
        on_ev["note"] = new_note
        off_ev["note"] = new_note
        self.announce_current_note(preview=True)

    def nudge_selected_timing(self, delta_steps: int):
        tr = self.sequencer.active_track
        pairs = self._extract_note_pairs(tr)
        if not pairs:
            return
        self.sequencer.push_undo_state()
        pairs = self._extract_note_pairs(tr)
        self.selected_idx = max(0, min(len(pairs) - 1, self.selected_idx))
        on_ev, off_ev = pairs[self.selected_idx]
        step_sec = self.sequencer.beat_duration / 4.0
        shift = delta_steps * step_sec
        dur = max(0.05, off_ev["time"] - on_ev["time"])
        new_start = max(0.0, min(self.sequencer.loop_duration - dur - 0.01, on_ev["time"] + shift))
        on_ev["time"] = round(new_start, 5)
        off_ev["time"] = round(new_start + dur, 5)
        tr.events.sort(key=lambda e: e["time"])
        self.announce_current_note(preview=True)

    def delete_selected_note(self):
        tr = self.sequencer.active_track
        pairs = self._extract_note_pairs(tr)
        if not pairs:
            self.speech.speak("لا توجد نوتة لحذفها")
            return
        self.sequencer.push_undo_state()
        pairs = self._extract_note_pairs(tr)
        self.selected_idx = max(0, min(len(pairs) - 1, self.selected_idx))
        on_ev, off_ev = pairs[self.selected_idx]
        if on_ev in tr.events:
            tr.events.remove(on_ev)
        if off_ev in tr.events:
            tr.events.remove(off_ev)
        remaining = len(self._extract_note_pairs(tr))
        self.selected_idx = max(0, min(remaining - 1, self.selected_idx))
        self.speech.speak(f"تم حذف النوتة، متبقي {remaining} نوتة في التراك")
