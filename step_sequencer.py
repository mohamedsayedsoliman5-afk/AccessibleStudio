"""
16-Step Drum Grid Sequencer Module
==================================
Specifically engineered for blind and visually impaired musicians.
Enables full non-visual creation of drum patterns using Left/Right arrow
navigation, Up/Down drum piece selection, and Spacebar toggle with instant
speech feedback and auditory earcons.
"""

import time
import threading
from typing import List, Dict, Optional, Any

from config import (
    STEP_DRUM_INSTRUMENTS,
    METRONOME_CHANNEL,
    DEFAULT_BPM
)
from speech_engine import speech


class StepSequencer:
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
        
        # Cursor positions (0-indexed)
        self.current_step = 0
        self.current_drum = 0
        self.velocity = 110

    def toggle_mode(self) -> bool:
        """Toggles Step Sequencer Mode on/off (F5)."""
        self.is_active = not self.is_active
        if self.is_active:
            speech.play_earcon("play")
            speech.speak(speech.get_text("step_mode_enter"), interrupt=True)
            # Announce initial position
            self.announce_current_step()
        else:
            speech.play_earcon("stop")
            speech.speak(speech.get_text("step_mode_exit"), interrupt=True)
        return self.is_active

    def move_step(self, delta: int):
        """Navigates Left/Right across the 16 steps."""
        new_step = self.current_step + delta
        if 0 <= new_step < self.num_steps:
            self.current_step = new_step
            self.announce_current_step()
        else:
            speech.play_earcon("boundary")
            speech.speak(speech.get_text("boundary_reached"), interrupt=True)

    def move_drum(self, delta: int):
        """Navigates Up/Down across the drum pieces."""
        new_drum = self.current_drum + delta
        if 0 <= new_drum < self.num_drums:
            self.current_drum = new_drum
            self.announce_current_drum()
            # Preview the drum sound immediately so the musician hears the piece
            self.preview_current_drum()
        else:
            speech.play_earcon("boundary")
            speech.speak(speech.get_text("boundary_reached"), interrupt=True)

    def toggle_current_hit(self):
        """Toggles the drum hit on/off at current step (Spacebar)."""
        inst = self.instruments[self.current_drum]
        is_on = not self.grid[self.current_drum][self.current_step]
        self.grid[self.current_drum][self.current_step] = is_on

        drum_name = inst["ar"] if speech.get_language() == "ar" else inst["en"]
        step_display = self.current_step + 1

        if is_on:
            # Play immediate drum sound
            self.preview_current_drum()
            speech.play_earcon("step_on")
            msg = speech.get_text("drum_toggled_on", drum_name=drum_name, step=step_display)
            speech.speak(msg, interrupt=True)
        else:
            speech.play_earcon("step_off")
            msg = speech.get_text("drum_toggled_off", drum_name=drum_name, step=step_display)
            speech.speak(msg, interrupt=True)

    def preview_current_drum(self):
        """Plays an immediate audio preview of the currently selected drum."""
        note = self.instruments[self.current_drum]["note"]
        self.synth.note_on(METRONOME_CHANNEL, note, self.velocity)
        
        def _off(n=note):
            time.sleep(0.08)
            self.synth.note_off(METRONOME_CHANNEL, n)
        threading.Thread(target=_off, daemon=True).start()

    def announce_current_step(self):
        """Reads the step number and all active drum pieces sounding on this step."""
        step_display = self.current_step + 1
        active_names = []
        lang = speech.get_language()
        
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
        """Reads the drum name and its status (On/Off) at the current step."""
        inst = self.instruments[self.current_drum]
        lang = speech.get_language()
        name = inst["ar"] if lang == "ar" else inst["en"]
        is_on = self.grid[self.current_drum][self.current_step]
        
        if lang == "ar":
            state_str = "مفعّل" if is_on else "معطّل"
        else:
            state_str = "On" if is_on else "Off"

        msg = speech.get_text("drum_selected", drum_name=name, state=state_str)
        speech.speak(msg, interrupt=True)

    def clear_grid(self):
        """Clears all steps across all drums."""
        for d in range(self.num_drums):
            for s in range(self.num_steps):
                self.grid[d][s] = False
        lang = speech.get_language()
        msg = "تم تفريغ شبكة الإيقاع بالكامل" if lang == "ar" else "Drum grid cleared"
        speech.speak(msg, interrupt=True)

    # -----------------------------------------------------------------------
    # Built-in Rhythmic Presets for Instant Music Production
    # -----------------------------------------------------------------------
    def load_preset(self, preset_name: str):
        """Loads popular rhythm presets into the 16-step grid."""
        self.clear_grid()
        lang = speech.get_language()

        if preset_name == "maqsum":
            # Traditional Oriental Maqsum Rhythm on Darbuka (Dum & Tek)
            # Dum (index 6, note 64), Tek (index 7, note 63)
            # Steps (0-indexed 16th notes):
            # Dum: 0, 8 (Beats 1 and 3)
            # Tek: 3, 6, 12 (Syncopated oriental accents)
            self.grid[6][0] = True   # Dum
            self.grid[7][3] = True   # Tek
            self.grid[7][6] = True   # Tek
            self.grid[6][8] = True   # Dum
            self.grid[7][12] = True  # Tek
            # Add subtle Closed Hi-Hat (index 2) on 8th notes (0, 2, 4, 6, 8, 10, 12, 14)
            for s in range(0, 16, 2):
                self.grid[2][s] = True
            msg = "تم تحميل إيقاع المقسوم الشرقي" if lang == "ar" else "Loaded Oriental Maqsum rhythm"
            speech.speak(msg, interrupt=True)

        elif preset_name == "four_on_floor":
            # Electronic Four-on-the-Floor (Kick on 0, 4, 8, 12; Snare on 4, 12; Hat on 2, 6, 10, 14)
            for s in [0, 4, 8, 12]:
                self.grid[0][s] = True  # Kick
            for s in [4, 12]:
                self.grid[1][s] = True  # Snare
                self.grid[4][s] = True  # Clap
            for s in [2, 6, 10, 14]:
                self.grid[3][s] = True  # Open Hat
            msg = "تم تحميل إيقاع الديسكو الإلكتروني" if lang == "ar" else "Loaded Four-on-the-Floor rhythm"
            speech.speak(msg, interrupt=True)

        elif preset_name == "rock":
            # Standard Rock Beat (Kick on 0, 8; Snare on 4, 12; Closed Hat on all even steps)
            self.grid[0][0] = True   # Kick
            self.grid[0][8] = True   # Kick
            self.grid[0][10] = True  # Syncopated Kick
            self.grid[1][4] = True   # Snare
            self.grid[1][12] = True  # Snare
            for s in range(0, 16, 2):
                self.grid[2][s] = True  # Closed Hat
            msg = "تم تحميل إيقاع الروك الكلاسيكي" if lang == "ar" else "Loaded Classic Rock rhythm"
            speech.speak(msg, interrupt=True)

    def render_to_track_events(self, bpm: float, bars: int = 4) -> List[List[Any]]:
        """
        Converts the 16-step grid into timestamped MIDI events for a track.
        Returns list of [event_type, note, velocity, timestamp_ms, channel].
        """
        ms_per_step = (60000.0 / bpm) / 4.0  # 16th note in ms
        step_duration_ms = ms_per_step * 0.8
        events: List[List[Any]] = []

        for bar in range(bars):
            bar_offset_ms = bar * (ms_per_step * 16)
            for step in range(self.num_steps):
                step_start_ms = bar_offset_ms + (step * ms_per_step)
                for d_idx in range(self.num_drums):
                    if self.grid[d_idx][step]:
                        note = self.instruments[d_idx]["note"]
                        events.append(["note_on", note, self.velocity, step_start_ms, METRONOME_CHANNEL])
                        events.append(["note_off", note, 0, step_start_ms + step_duration_ms, METRONOME_CHANNEL])

        # Sort chronologically
        events.sort(key=lambda x: (x[3], 0 if x[0] == "note_off" else 1))
        return events
