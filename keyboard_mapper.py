import pygame
import config

LOWER_ROW_OFFSETS = {
    pygame.K_z: (0, "Z"),
    pygame.K_s: (1, "S"),
    pygame.K_x: (2, "X"),
    pygame.K_d: (3, "D"),
    pygame.K_c: (4, "C"),
    pygame.K_v: (5, "V"),
    pygame.K_g: (6, "G"),
    pygame.K_b: (7, "B"),
    pygame.K_h: (8, "H"),
    pygame.K_n: (9, "N"),
    pygame.K_j: (10, "J"),
    pygame.K_m: (11, "M"),
    pygame.K_COMMA: (12, ","),
    pygame.K_l: (13, "L"),
    pygame.K_PERIOD: (14, "."),
    pygame.K_SEMICOLON: (15, ";"),
    pygame.K_SLASH: (16, "/"),
}

UPPER_ROW_OFFSETS = {
    pygame.K_q: (12, "Q"),
    pygame.K_2: (13, "2"),
    pygame.K_w: (14, "W"),
    pygame.K_3: (15, "3"),
    pygame.K_e: (16, "E"),
    pygame.K_r: (17, "R"),
    pygame.K_5: (18, "5"),
    pygame.K_t: (19, "T"),
    pygame.K_6: (20, "6"),
    pygame.K_y: (21, "Y"),
    pygame.K_7: (22, "7"),
    pygame.K_u: (23, "U"),
    pygame.K_i: (24, "I"),
    pygame.K_9: (25, "9"),
    pygame.K_o: (26, "O"),
    pygame.K_0: (27, "0"),
    pygame.K_p: (28, "P"),
    pygame.K_LEFTBRACKET: (29, "["),
    pygame.K_EQUALS: (30, "="),
    pygame.K_RIGHTBRACKET: (31, "]"),
}

MUSICAL_KEY_MAP = {}
OFFSET_TO_KEY_LABEL = {}
for k, (off, lbl) in LOWER_ROW_OFFSETS.items():
    MUSICAL_KEY_MAP[k] = off
    OFFSET_TO_KEY_LABEL[off] = lbl
for k, (off, lbl) in UPPER_ROW_OFFSETS.items():
    MUSICAL_KEY_MAP[k] = off
    OFFSET_TO_KEY_LABEL[off] = lbl

DRUM_KEY_MAP = {
    pygame.K_z: 36,
    pygame.K_x: 38,
    pygame.K_c: 42,
    pygame.K_v: 46,
    pygame.K_b: 39,
    pygame.K_n: 61,
    pygame.K_m: 60,
    pygame.K_COMMA: 62,
    pygame.K_PERIOD: 54,
    pygame.K_q: 61,
    pygame.K_w: 60,
    pygame.K_e: 62,
    pygame.K_r: 54,
    pygame.K_t: 36,
    pygame.K_y: 38,
    pygame.K_u: 42,
    pygame.K_i: 46,
}


class KeyboardMapper:
    def __init__(self):
        self.base_octave = 4
        self.transpose = 0
        self.velocity = 105
        self.chord_mode_idx = 0
        self.pressed_keys = {}
        self.mouse_active_note = None

    def get_base_midi_note(self) -> int:
        return (self.base_octave + 1) * 12 + self.transpose

    def get_midi_notes(self, key: int, is_drum_track: bool = False):
        if is_drum_track:
            if key in DRUM_KEY_MAP:
                return [DRUM_KEY_MAP[key]]
            if key in MUSICAL_KEY_MAP:
                return [35 + (MUSICAL_KEY_MAP[key] % 25)]
            return []

        if key not in MUSICAL_KEY_MAP:
            return []
        base_note = self.get_base_midi_note() + MUSICAL_KEY_MAP[key]
        intervals = config.CHORD_MODES[self.chord_mode_idx]["intervals"]
        return [max(0, min(127, base_note + iv)) for iv in intervals]

    def shift_octave(self, delta: int, synth):
        self.release_all_pressed(synth)
        self.base_octave = max(1, min(7, self.base_octave + delta))
        return self.base_octave

    def shift_transpose(self, delta: int, synth):
        self.release_all_pressed(synth)
        self.transpose = max(-12, min(12, self.transpose + delta))
        return self.transpose

    def cycle_chord_mode(self, synth):
        self.release_all_pressed(synth)
        self.chord_mode_idx = (self.chord_mode_idx + 1) % len(config.CHORD_MODES)
        return config.CHORD_MODES[self.chord_mode_idx]

    def adjust_velocity(self, delta: int):
        self.velocity = max(20, min(127, self.velocity + delta))
        return self.velocity

    def release_all_pressed(self, synth):
        for key, (ch, notes) in list(self.pressed_keys.items()):
            for n in notes:
                synth.note_off(ch, n)
        self.pressed_keys.clear()
        if self.mouse_active_note is not None:
            ch, note = self.mouse_active_note
            synth.note_off(ch, note)
            self.mouse_active_note = None
