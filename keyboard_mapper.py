"""
Keyboard Mapper Module
======================
Translates computer QWERTY keyboard into an accessible 2-octave musical keyboard.
Eliminates OS auto-repeat jitter, tracks physical key states, and manages
octave shifting and velocity dynamics.
"""

from typing import Optional, Dict, Tuple
from config import DEFAULT_OCTAVE, DEFAULT_VELOCITY, get_note_name

# Relative semitone offsets from the base octave root C
# Lower Octave (Root C to B)
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

# Upper Octave (C+1 octave to C+2 octaves)
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

# Combined dictionary mapping character to semitone offset
KEY_SEMITONE_OFFSETS: Dict[str, int] = {**LOWER_OCTAVE_MAP, **UPPER_OCTAVE_MAP}


class KeyboardMapper:
    """Manages QWERTY musical note translation, octave shifts, and velocity."""

    def __init__(self, base_octave: int = DEFAULT_OCTAVE, base_velocity: int = DEFAULT_VELOCITY):
        self.base_octave = base_octave      # Middle C = C4 (MIDI 60)
        self.velocity = base_velocity        # Default 100 (1-127)
        self._active_keys: Dict[int, int] = {}  # key_code -> midi_note

    def is_musical_key(self, char: str) -> bool:
        """Checks if a character belongs to the 2-octave QWERTY matrix."""
        return char.lower() in KEY_SEMITONE_OFFSETS if char else False

    def get_base_midi_root(self) -> int:
        """Calculates root MIDI note number for base octave (e.g. Octave 4 -> MIDI 60)."""
        return (self.base_octave + 1) * 12

    def process_key_down(self, key_code: int, key_char: Optional[str]) -> Optional[Tuple[int, int]]:
        """
        Translates key press into (midi_note, velocity).
        Ignores OS repeat events if key is already physically depressed.
        """
        # If key is already actively playing, ignore OS auto-repeat
        if key_code in self._active_keys:
            return None

        if not key_char:
            return None

        char = key_char.lower()
        if char in KEY_SEMITONE_OFFSETS:
            semitone_offset = KEY_SEMITONE_OFFSETS[char]
            midi_note = self.get_base_midi_root() + semitone_offset
            # Clamp to MIDI standards (0-127)
            midi_note = max(0, min(127, midi_note))
            self._active_keys[key_code] = midi_note
            return midi_note, self.velocity

        return None

    def process_key_up(self, key_code: int) -> Optional[int]:
        """
        Processes key release.
        Returns the released midi_note if the key was actively sounding.
        """
        return self._active_keys.pop(key_code, None)

    def octave_up(self) -> Tuple[int, bool]:
        """Shifts base octave up (max Octave 8). Returns (new_octave, changed)."""
        if self.base_octave < 8:
            self.base_octave += 1
            return self.base_octave, True
        return self.base_octave, False

    def octave_down(self) -> Tuple[int, bool]:
        """Shifts base octave down (min Octave 1). Returns (new_octave, changed)."""
        if self.base_octave > 1:
            self.base_octave -= 1
            return self.base_octave, True
        return self.base_octave, False

    def velocity_up(self, step: int = 10) -> Tuple[int, bool]:
        """Increases velocity (max 127). Returns (new_velocity, changed)."""
        new_val = min(127, self.velocity + step)
        if new_val != self.velocity:
            self.velocity = new_val
            return self.velocity, True
        return self.velocity, False

    def velocity_down(self, step: int = 10) -> Tuple[int, bool]:
        """Decreases velocity (min 1). Returns (new_velocity, changed)."""
        new_val = max(1, self.velocity - step)
        if new_val != self.velocity:
            self.velocity = new_val
            return self.velocity, True
        return self.velocity, False

    def release_all_keys(self) -> Dict[int, int]:
        """Releases and clears all held keys (used on Stop / Panic)."""
        released = dict(self._active_keys)
        self._active_keys.clear()
        return released

    def get_note_label(self, midi_note: int, lang: str = "ar") -> str:
        """Returns human-friendly musical note description."""
        return get_note_name(midi_note, lang)
