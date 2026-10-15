"""
AccessibleStudio Accessibility - Virtual Piano Keyboard Mapper
==============================================================
Maps standard computer QWERTY keyboard into a professional 2-octave
musical keyboard. Suppresses OS auto-repeat jitter, tracks physical
key states, and manages base octave shifts and dynamic velocities.
"""

from typing import Optional, Dict, Tuple
from accessible_studio.config import DEFAULT_OCTAVE, DEFAULT_VELOCITY, get_note_name

# Relative semitone offsets from the base octave root C
LOWER_OCTAVE_MAP: Dict[str, int] = {
    "z": 0,   # C
    "s": 1,   # C#
    "x": 2,   # D
    "d": 3,   # D#
    "c": 4,   # E
    "v": 5,   # F
    "g": 6,   # F#
    "b": 7,   # G
    "h": 8,   # G#
    "n": 9,   # A
    "j": 10,  # A#
    "m": 11,  # B
}

UPPER_OCTAVE_MAP: Dict[str, int] = {
    "q": 12,  # C (+1 Octave)
    "2": 13,  # C#
    "w": 14,  # D
    "3": 15,  # D#
    "e": 16,  # E
    "r": 17,  # F
    "5": 18,  # F#
    "t": 19,  # G
    "6": 20,  # G#
    "y": 21,  # A
    "7": 22,  # A#
    "u": 23,  # B
    "i": 24,  # C (+2 Octaves)
}

KEY_SEMITONE_OFFSETS: Dict[str, int] = {**LOWER_OCTAVE_MAP, **UPPER_OCTAVE_MAP}


class PianoKeyboardMapper:
    """Translates computer QWERTY keyboard events into MIDI Note-On / Note-Off pairs."""

    def __init__(self, base_octave: int = DEFAULT_OCTAVE, base_velocity: int = DEFAULT_VELOCITY):
        self.base_octave = base_octave
        self.velocity = base_velocity
        self._active_keys: Dict[str, int] = {}  # key_token -> midi_note

    def is_musical_key(self, char: str) -> bool:
        return char.lower() in KEY_SEMITONE_OFFSETS if char else False

    def get_base_midi_root(self) -> int:
        return (self.base_octave + 1) * 12

    def process_key_down(self, key_id: str, char_str: Optional[str]) -> Optional[Tuple[int, int]]:
        """
        Translates key press into (midi_note, velocity).
        Ignores OS repeat events if key is already physically depressed.
        """
        char = (char_str or key_id or "").lower()
        if not char:
            return None

        # Auto-repeat debounce
        if char in self._active_keys:
            return None

        if char in KEY_SEMITONE_OFFSETS:
            semitone_offset = KEY_SEMITONE_OFFSETS[char]
            midi_note = max(0, min(127, self.get_base_midi_root() + semitone_offset))
            self._active_keys[char] = midi_note
            return midi_note, self.velocity

        return None

    def process_key_up(self, key_id: str, char_str: Optional[str] = None) -> Optional[int]:
        """Processes key release and returns the sounding MIDI note number."""
        char = (char_str or key_id or "").lower()
        return self._active_keys.pop(char, None)

    def octave_up(self) -> Tuple[int, bool]:
        if self.base_octave < 8:
            self.base_octave += 1
            return self.base_octave, True
        return self.base_octave, False

    def octave_down(self) -> Tuple[int, bool]:
        if self.base_octave > 0:
            self.base_octave -= 1
            return self.base_octave, True
        return self.base_octave, False

    def velocity_up(self, delta: int = 10) -> Tuple[int, bool]:
        new_v = min(127, self.velocity + delta)
        if new_v != self.velocity:
            self.velocity = new_v
            return self.velocity, True
        return self.velocity, False

    def velocity_down(self, delta: int = 10) -> Tuple[int, bool]:
        new_v = max(10, self.velocity - delta)
        if new_v != self.velocity:
            self.velocity = new_v
            return self.velocity, True
        return self.velocity, False

    def release_all_keys(self) -> Dict[str, int]:
        released = dict(self._active_keys)
        self._active_keys.clear()
        return released
