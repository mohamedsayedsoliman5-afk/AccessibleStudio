import config


class StepSequencer:
    def __init__(self, sequencer, synth, speech):
        self.sequencer = sequencer
        self.synth = synth
        self.speech = speech
        self.active = False
        self.current_step = 0
        self.current_drum_idx = 0
        self.preset_idx = -1
        self.grid = {piece["note"]: [0] * 16 for piece in config.DRUM_PIECES}

    def toggle_mode(self):
        self.active = not self.active
        if self.active:
            drum_name = config.DRUM_PIECES[self.current_drum_idx]["ar"]
            self.speech.speak(
                f"منظم إيقاع الطبول مفتوح، خطوة {self.current_step + 1} من 16، الآلة {drum_name}"
            )
        else:
            self.sync_to_drum_track()
            self.speech.speak("تم إغلاق منظم الطبول وتحديث تراك 8")

    def move_step(self, delta: int):
        self.current_step = (self.current_step + delta) % 16
        active_hits = []
        for p in config.DRUM_PIECES:
            vel = self.grid[p["note"]][self.current_step]
            if vel > 0:
                active_hits.append(p["ar"])
                self.synth.note_on(9, p["note"], vel)
        hits_str = "، ".join(active_hits) if active_hits else "فارغة"
        self.speech.speak(f"خطوة {self.current_step + 1}: {hits_str}")

    def move_drum_piece(self, delta: int):
        self.current_drum_idx = (self.current_drum_idx + delta) % len(config.DRUM_PIECES)
        piece = config.DRUM_PIECES[self.current_drum_idx]
        vel = self.grid[piece["note"]][self.current_step]
        if vel >= 120:
            state_str = "قوية"
        elif vel >= 90:
            state_str = "متوسطة"
        elif vel > 0:
            state_str = "خفيفة"
        else:
            state_str = "غير مفعلة"
        self.synth.note_on(9, piece["note"], 105)
        self.speech.speak(f"{piece['ar']}، في خطوة {self.current_step + 1} {state_str}")

    def toggle_step_at(self, drum_idx: int, step_idx: int):
        self.current_drum_idx = drum_idx % len(config.DRUM_PIECES)
        self.current_step = step_idx % 16
        self.toggle_current_step_hit()

    def toggle_current_step_hit(self):
        self.sequencer.push_undo_state()
        piece = config.DRUM_PIECES[self.current_drum_idx]
        note = piece["note"]
        current_val = self.grid[note][self.current_step]
        if current_val == 0:
            new_val = 100
            level_name = "تفعيل ضربة متوسطة"
        elif current_val == 100:
            new_val = 126
            level_name = "ضربة قوية أكسنت"
        elif current_val >= 120:
            new_val = 65
            level_name = "ضربة خفيفة"
        else:
            new_val = 0
            level_name = "إلغاء الضربة"

        self.grid[note][self.current_step] = new_val
        if new_val > 0:
            self.synth.note_on(9, note, new_val)
        self.sync_to_drum_track()
        self.speech.speak(f"{level_name} لآلة {piece['ar']} في خطوة {self.current_step + 1}")

    def load_next_preset(self):
        self.sequencer.push_undo_state()
        self.preset_idx = (self.preset_idx + 1) % len(config.RHYTHM_PRESETS)
        preset = config.RHYTHM_PRESETS[self.preset_idx]
        for note in self.grid:
            self.grid[note] = [0] * 16
        for note, pattern in preset["grid"].items():
            if note in self.grid:
                self.grid[note] = list(pattern[:16])
        self.sync_to_drum_track()
        self.speech.speak(f"تم تحميل إيقاع {preset['name_ar']} في تراك الطبول")

    def sync_to_drum_track(self):
        drum_track = self.sequencer.tracks[7]
        drum_track.events.clear()

        step_duration = self.sequencer.beat_duration / 4.0
        for bar in range(self.sequencer.bars):
            bar_offset = bar * 16 * step_duration
            for step_idx in range(16):
                t_on = bar_offset + (step_idx * step_duration)
                t_off = t_on + (step_duration * 0.65)
                for piece in config.DRUM_PIECES:
                    note = piece["note"]
                    vel = self.grid[note][step_idx]
                    if vel > 0:
                        drum_track.events.append({
                            "type": "note_on",
                            "note": note,
                            "vel": int(vel),
                            "time": round(t_on, 5),
                        })
                        drum_track.events.append({
                            "type": "note_off",
                            "note": note,
                            "vel": 0,
                            "time": round(t_off, 5),
                        })

        drum_track.events.sort(key=lambda e: (e["time"], 0 if e["type"] == "note_off" else 1))
