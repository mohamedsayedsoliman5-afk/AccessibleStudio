"""
AccessibleStudio Core - 16-Step Rhythmic Drum Grid & Beat Machine
=================================================================
Designed specifically for blind musicians to compose and program rhythm
tracks with non-visual step navigation, instant speech announcements,
audio preview hits, and authentic Arabic and Western rhythmic presets.
"""

import time
import threading
from typing import List, Dict, Optional, Any

from accessible_studio.config import STEP_DRUM_INSTRUMENTS, METRONOME_CHANNEL
from accessible_studio.accessibility.speech import speech


class DrumGridSequencer:
    """16-Step Drum Grid Engine with full screen reader audio accessibility."""

    def __init__(self, synth_engine):
        self.synth = synth_engine
        self.is_active = False
        self.num_steps = 16
        self.instruments = STEP_DRUM_INSTRUMENTS
        self.num_drums = len(self.instruments)

        # Grid state: [drum_idx][step_idx] -> bool
        self.grid: List[List[bool]] = [
            [False] * self.num_steps for _ in range(self.num_drums)
        ]

        self.current_step = 0
        self.current_drum = 0
        self.velocity = 110

    def toggle_mode(self) -> bool:
        """Toggles Drum Grid mode on/off (F5)."""
        self.is_active = not self.is_active
        if self.is_active:
            speech.play_earcon("play")
            speech.speak(speech.get_text("step_mode_enter"), interrupt=True)
            self.announce_current_step()
        else:
            speech.play_earcon("stop")
            speech.speak(speech.get_text("step_mode_exit"), interrupt=True)
        return self.is_active

    def move_step(self, delta: int):
        new_step = self.current_step + delta
        if 0 <= new_step < self.num_steps:
            self.current_step = new_step
            self.announce_current_step()
        else:
            speech.play_earcon("boundary")

    def move_drum(self, delta: int):
        new_drum = self.current_drum + delta
        if 0 <= new_drum < self.num_drums:
            self.current_drum = new_drum
            self.announce_current_drum()
            self.preview_current_drum()
        else:
            speech.play_earcon("boundary")

    def toggle_current_hit(self) -> bool:
        """Toggles hit on active drum at current step."""
        is_hit = not self.grid[self.current_drum][self.current_step]
        self.grid[self.current_drum][self.current_step] = is_hit
        inst = self.instruments[self.current_drum]
        lang = speech.language
        name = inst["ar"] if lang == "ar" else inst["en"]

        if is_hit:
            self.preview_current_drum()
            msg = speech.get_text("step_hit_enabled", drum_name=name)
        else:
            msg = speech.get_text("step_hit_disabled", drum_name=name)
        speech.speak(msg, interrupt=True)
        return is_hit

    def preview_current_drum(self):
        note = self.instruments[self.current_drum]["note"]
        self.synth.note_on(METRONOME_CHANNEL, note, self.velocity)
        def _off(n=note):
            time.sleep(0.08)
            self.synth.note_off(METRONOME_CHANNEL, n)
        threading.Thread(target=_off, daemon=True).start()

    def announce_current_step(self):
        step_display = self.current_step + 1
        active_names = []
        lang = speech.language

        for d_idx in range(self.num_drums):
            if self.grid[d_idx][self.current_step]:
                name = self.instruments[d_idx]["ar"] if lang == "ar" else self.instruments[d_idx]["en"]
                active_names.append(name)

        if active_names:
            hits_str = ", ".join(active_names)
        else:
            hits_str = speech.get_text("step_empty")

        msg = speech.get_text("step_info", step=step_display, hits=hits_str)
        speech.speak(msg, interrupt=True)

    def announce_current_drum(self):
        inst = self.instruments[self.current_drum]
        lang = speech.language
        name = inst["ar"] if lang == "ar" else inst["en"]
        status = speech.get_text("step_status_on") if self.grid[self.current_drum][self.current_step] else speech.get_text("step_status_off")
        speech.speak(f"{name}: {status}", interrupt=True)

    def clear_grid(self):
        for d in range(self.num_drums):
            for s in range(self.num_steps):
                self.grid[d][s] = False
        speech.speak(speech.get_text("grid_cleared"), interrupt=True)

    def load_preset(self, preset_name: str) -> bool:
        """Loads rhythmic preset patterns."""
        self.clear_grid()

        # Drum indices: 0=Kick, 1=Snare, 2=ClosedHH, 3=OpenHH, 4=Clap, 5=LowTom, 6=HighTom, 7=Crash
        if preset_name in ["maqsum", "maqsoom"]:
            # Dum on 0, 8, 10; Tak (Snare/Rim) on 4, 12; Hi-hat on 2, 6, 14
            for s in [0, 8, 10]: self.grid[0][s] = True
            for s in [4, 12]: self.grid[1][s] = True
            for s in [2, 6, 14]: self.grid[2][s] = True
            preset_title = "المقسوم الشرقي" if speech.language == "ar" else "Arabic Maqsum"

        elif preset_name == "saidi":
            # Dum on 0, 6, 8; Tak on 4, 12; Hi-hat on 2, 10, 14
            for s in [0, 6, 8]: self.grid[0][s] = True
            for s in [4, 12]: self.grid[1][s] = True
            for s in [2, 10, 14]: self.grid[2][s] = True
            preset_title = "الصعيدي الشرقي" if speech.language == "ar" else "Arabic Saidi"

        elif preset_name == "malfuf":
            # Fast 2/4 rhythm: Dum on 0, Tak on 6, 10; repeat on 8, 14
            for s in [0, 8]: self.grid[0][s] = True
            for s in [6, 14]: self.grid[1][s] = True
            for s in [2, 4, 10, 12]: self.grid[2][s] = True
            preset_title = "الملفوف الشرقي" if speech.language == "ar" else "Arabic Malfuf"

        elif preset_name in ["four_on_floor", "dance", "pop"]:
            # Kick on 0, 4, 8, 12; Snare/Clap on 4, 12; HH on every 2
            for s in [0, 4, 8, 12]: self.grid[0][s] = True
            for s in [4, 12]: self.grid[4][s] = True
            for s in [2, 6, 10, 14]: self.grid[3][s] = True
            preset_title = "إيقاع بوب ودانس" if speech.language == "ar" else "Four on the floor"

        elif preset_name == "rock":
            # Kick on 0, 8, 10; Snare on 4, 12; Closed HH on all evens
            for s in [0, 8, 10]: self.grid[0][s] = True
            for s in [4, 12]: self.grid[1][s] = True
            for s in range(0, 16, 2): self.grid[2][s] = True
            preset_title = "الروك الكلاسيكي" if speech.language == "ar" else "Classic Rock"

        else:
            return False

        msg = speech.get_text("preset_loaded", name=preset_title)
        speech.play_earcon("quantize")
        speech.speak(msg, interrupt=True)
        return True

    def render_to_track_events(self, bpm: float, bars: int = 4) -> List[List[Any]]:
        """Converts active drum pattern into standard MIDI events across specified bars."""
        ms_per_step = (60000.0 / bpm) / 4.0  # 1/16th note step
        pattern_len_ms = 16 * ms_per_step
        events = []

        for b in range(bars):
            bar_offset = b * pattern_len_ms
            for s in range(self.num_steps):
                t_on = bar_offset + (s * ms_per_step)
                t_off = t_on + (ms_per_step * 0.8)

                for d in range(self.num_drums):
                    if self.grid[d][s]:
                        note = self.instruments[d]["note"]
                        events.append(["note_on", note, self.velocity, t_on, METRONOME_CHANNEL])
                        events.append(["note_off", note, 0, t_off, METRONOME_CHANNEL])

        events.sort(key=lambda e: e[3])
        return events
