import time
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
    pygame.K_z: 61,
    pygame.K_x: 60,
    pygame.K_c: 62,
    pygame.K_v: 63,
    pygame.K_b: 54,
    pygame.K_n: 64,
    pygame.K_m: 36,
    pygame.K_COMMA: 38,
    pygame.K_PERIOD: 42,
    pygame.K_q: 61,
    pygame.K_w: 60,
    pygame.K_e: 62,
    pygame.K_r: 63,
    pygame.K_t: 54,
    pygame.K_y: 36,
    pygame.K_u: 38,
    pygame.K_i: 42,
    pygame.K_o: 46,
    pygame.K_p: 39,
}


class KeyboardMapper:
    def __init__(self):
        self.base_octave = 4
        self.transpose = 0
        self.velocity = 110
        self.chord_mode_idx = 0
        self.arp_mode_idx = 0
        self.scale_lock = False
        self.pressed_keys = {}
        self.mouse_active_note = None
        self._arp_step = 0
        self._arp_last_time = 0.0
        self._arp_active_note = None

    def get_base_midi_note(self) -> int:
        return (self.base_octave + 1) * 12 + self.transpose

    def snap_to_maqam_scale(self, midi_note: int, synth) -> int:
        if not self.scale_lock:
            return midi_note
        maqam = config.MAQAMAT[synth.maqam_idx]
        allowed = maqam["scale_degrees"]
        rel = (midi_note - synth.maqam_root) % 12
        nearest = min(allowed, key=lambda d: abs(d - rel))
        return midi_note - rel + nearest

    def get_midi_notes(self, key: int, synth, is_drum_track: bool = False):
        if is_drum_track:
            if key in DRUM_KEY_MAP:
                return [DRUM_KEY_MAP[key]]
            if key in MUSICAL_KEY_MAP:
                return [35 + (MUSICAL_KEY_MAP[key] % 25)]
            return []

        if key not in MUSICAL_KEY_MAP:
            return []
        raw_note = self.get_base_midi_note() + MUSICAL_KEY_MAP[key]
        base_note = self.snap_to_maqam_scale(raw_note, synth)
        intervals = config.CHORD_MODES[self.chord_mode_idx]["intervals"]
        return [max(0, min(127, self.snap_to_maqam_scale(base_note + iv, synth))) for iv in intervals]

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

    def cycle_arp_mode(self, synth):
        self.release_all_pressed(synth)
        self.arp_mode_idx = (self.arp_mode_idx + 1) % len(config.ARP_MODES)
        return config.ARP_MODES[self.arp_mode_idx]

    def adjust_velocity(self, delta: int):
        self.velocity = max(20, min(127, self.velocity + delta))
        return self.velocity

    def update_arpeggiator(self, synth, sequencer):
        if self.arp_mode_idx == 0 or not self.pressed_keys:
            if self._arp_active_note is not None:
                ch, n = self._arp_active_note
                synth.note_off(ch, n)
                sequencer.record_note_off(n)
                self._arp_active_note = None
            return

        active_ch = sequencer.active_track.channel
        if active_ch == 9:
            return

        step_sec = sequencer.beat_duration / 4.0
        now = time.perf_counter()
        if now - self._arp_last_time < step_sec:
            return
        self._arp_last_time = now

        if self._arp_active_note is not None:
            ch, prev_n = self._arp_active_note
            synth.note_off(ch, prev_n)
            sequencer.record_note_off(prev_n)
            self._arp_active_note = None

        held_notes = sorted({n for _, (ch, notes) in self.pressed_keys.items() for n in notes})
        if not held_notes:
            return

        if self.arp_mode_idx == 4:
            root = held_notes[0]
            degs = config.MAQAMAT[synth.maqam_idx]["scale_degrees"]
            pool = [min(127, root + d) for d in degs] + [min(127, root + 12)]
        elif len(held_notes) == 1:
            r = held_notes[0]
            pool = [r, min(127, self.snap_to_maqam_scale(r + 4, synth)), min(127, r + 7), min(127, r + 12)]
        else:
            pool = held_notes

        if self.arp_mode_idx == 2:
            pool = list(reversed(pool))
        elif self.arp_mode_idx == 3 and len(pool) > 2:
            pool = pool + list(reversed(pool[1:-1]))

        note_to_play = pool[self._arp_step % len(pool)]
        self._arp_step += 1
        synth.note_on(active_ch, note_to_play, self.velocity)
        sequencer.record_note_on(note_to_play, self.velocity)
        self._arp_active_note = (active_ch, note_to_play)

    def release_all_pressed(self, synth):
        for key, (ch, notes) in list(self.pressed_keys.items()):
            for n in notes:
                synth.note_off(ch, n)
        self.pressed_keys.clear()
        if self._arp_active_note is not None:
            ch, n = self._arp_active_note
            synth.note_off(ch, n)
            self._arp_active_note = None
        if self.mouse_active_note is not None:
            ch, note = self.mouse_active_note
            synth.note_off(ch, note)
            self.mouse_active_note = None
