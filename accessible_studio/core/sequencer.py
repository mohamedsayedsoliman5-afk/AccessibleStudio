"""
AccessibleStudio Core - Multi-Track Sequencer & Transport Clock
==============================================================
Manages 16 independent tracks, high-precision microsecond transport clock,
4-beat audible count-in, synchronized GM metronome, smart quantization,
and per-track undo history.
"""

import time
import threading
from typing import List, Dict, Tuple, Optional, Any

from accessible_studio.config import (
    MAX_TRACKS,
    DEFAULT_BPM,
    MIN_BPM,
    MAX_BPM,
    METRONOME_CHANNEL,
    METRONOME_HIGH_NOTE,
    METRONOME_LOW_NOTE,
    METRONOME_VELOCITY_HIGH,
    METRONOME_VELOCITY_LOW,
    GM_INSTRUMENTS
)
from accessible_studio.accessibility.speech import speech


class Track:
    """Represents a single MIDI track with its own instrument, volume, pan, and event list."""

    def __init__(self, track_id: int, channel: int):
        self.track_id = track_id
        self.channel = channel
        self.program = 0      # 0 = Acoustic Grand Piano
        self.volume = 100     # CC#7 (0-127)
        self.pan = 64         # CC#10 (0=Left, 64=Center, 127=Right)
        self.muted = False
        self.solo = False

        # Events: [event_type ('note_on'/'note_off'), note, velocity, timestamp_ms, channel]
        self.events: List[List[Any]] = []
        self._undo_stack: List[List[List[Any]]] = []

    def add_event(self, event_type: str, note: int, velocity: int, timestamp_ms: float):
        self.events.append([event_type, note, velocity, timestamp_ms, self.channel])

    def save_undo_state(self):
        if len(self._undo_stack) >= 12:
            self._undo_stack.pop(0)
        self._undo_stack.append([list(evt) for evt in self.events])

    def undo(self) -> bool:
        if self._undo_stack:
            self.events = self._undo_stack.pop()
            return True
        return False

    def get_duration_ms(self) -> float:
        if not self.events:
            return 0.0
        return max(evt[3] for evt in self.events)

    def clear(self):
        self.save_undo_state()
        self.events.clear()


class Sequencer:
    """Multi-Track MIDI Sequencer & Transport Engine."""

    # Transport States
    STOPPED = 0
    PLAYING = 1
    RECORDING = 2
    COUNTING_IN = 3

    def __init__(self, synth_engine, num_tracks: int = 8):
        self.synth = synth_engine
        self.num_tracks = min(MAX_TRACKS, num_tracks)
        self.tracks: List[Track] = []

        for i in range(self.num_tracks):
            # Channels 0-8 and 10-15 (Channel 9 is dedicated GM Drums)
            ch = i if i < 9 else i + 1
            self.tracks.append(Track(i, ch))

        self.active_track_idx = 0
        self.state = self.STOPPED

        # Musical clock
        self.bpm = DEFAULT_BPM
        self.playhead_ms = 0.0
        self.loop_length_ms = 4000.0
        self.loop_enabled = False
        self.metronome_enabled = True

        self._start_time = 0.0
        self._count_in_start = 0.0
        self._last_metronome_beat = -1
        self._playback_cursors: List[int] = [0] * self.num_tracks
        self._active_sounding_notes: Dict[Tuple[int, int], bool] = {}

        self._lock = threading.Lock()
        self._running = True
        self._transport_thread = threading.Thread(target=self._transport_loop, daemon=True, name="Sequencer-Clock")
        self._transport_thread.start()

    def start_recording(self):
        """Initiates recording with 4-beat audible count-in."""
        with self._lock:
            self._silence_sounding_notes()
            self.tracks[self.active_track_idx].save_undo_state()
            self.state = self.COUNTING_IN
            self._count_in_start = time.perf_counter()
            self._last_metronome_beat = -1
            self.playhead_ms = 0.0
            speech.play_earcon("record")

    def start_playback(self):
        """Starts multi-track playback."""
        with self._lock:
            if self.state in [self.PLAYING, self.RECORDING]:
                return
            self._silence_sounding_notes()
            self.state = self.PLAYING
            self._start_time = time.perf_counter() - (self.playhead_ms / 1000.0)
            self._reset_playback_cursors()
            self._last_metronome_beat = -1
            speech.play_earcon("play")

    def stop(self):
        """Stops playback or recording."""
        with self._lock:
            prev_state = self.state
            self.state = self.STOPPED
            self._silence_sounding_notes()
            speech.play_earcon("stop")

            if prev_state == self.RECORDING:
                rec_duration = self.tracks[self.active_track_idx].get_duration_ms()
                bar_ms = self.get_ms_per_bar()
                if rec_duration > 0:
                    bars = max(1, int((rec_duration + bar_ms - 1) // bar_ms))
                    self.loop_length_ms = bars * bar_ms

    def toggle_play_stop(self):
        if self.state in [self.PLAYING, self.RECORDING, self.COUNTING_IN]:
            self.stop()
        else:
            self.start_playback()

    def rewind_to_start(self):
        with self._lock:
            self.playhead_ms = 0.0
            self._reset_playback_cursors()
            if self.state == self.PLAYING:
                self._start_time = time.perf_counter()
            speech.speak("البداية: المازورة 1" if speech.language == "ar" else "Rewind to Bar 1", interrupt=True)

    def toggle_metronome(self) -> bool:
        self.metronome_enabled = not self.metronome_enabled
        status_text = speech.get_text("metronome_on") if self.metronome_enabled else speech.get_text("metronome_off")
        speech.speak(status_text, interrupt=True)
        return self.metronome_enabled

    def get_ms_per_beat(self) -> float:
        return 60000.0 / self.bpm

    def get_ms_per_bar(self) -> float:
        return self.get_ms_per_beat() * 4.0

    def get_bar_beat(self) -> Tuple[int, int]:
        ms_per_beat = self.get_ms_per_beat()
        total_beats = int(self.playhead_ms // ms_per_beat)
        bar = (total_beats // 4) + 1
        beat = (total_beats % 4) + 1
        return bar, beat

    def adjust_bpm(self, delta: int) -> int:
        new_bpm = max(MIN_BPM, min(MAX_BPM, self.bpm + delta))
        if new_bpm != self.bpm:
            self.bpm = new_bpm
            speech.speak(speech.get_text("tempo_changed", bpm=self.bpm), interrupt=True)
        return self.bpm

    def record_note_on(self, note: int, velocity: int):
        ch = self.tracks[self.active_track_idx].channel
        self.synth.note_on(ch, note, velocity)
        if self.state == self.RECORDING:
            with self._lock:
                self.tracks[self.active_track_idx].add_event(
                    "note_on", note, velocity, self.playhead_ms
                )

    def record_note_off(self, note: int):
        ch = self.tracks[self.active_track_idx].channel
        self.synth.note_off(ch, note)
        if self.state == self.RECORDING:
            with self._lock:
                self.tracks[self.active_track_idx].add_event(
                    "note_off", note, 0, self.playhead_ms
                )

    def select_track(self, track_idx: int):
        if 0 <= track_idx < self.num_tracks and track_idx != self.active_track_idx:
            self.active_track_idx = track_idx
            self.announce_track_info()

    def select_next_track(self):
        idx = (self.active_track_idx + 1) % self.num_tracks
        self.select_track(idx)

    def select_prev_track(self):
        idx = (self.active_track_idx - 1) % self.num_tracks
        self.select_track(idx)

    def announce_track_info(self):
        track = self.tracks[self.active_track_idx]
        inst = GM_INSTRUMENTS[track.program]
        inst_name = inst["ar"] if speech.language == "ar" else inst["en"]
        num_notes = len(track.events) // 2
        msg = f"المسار {self.active_track_idx + 1}: {inst_name}. مستوى الصوت {int(track.volume / 1.27)}%. النوتات المسجلة: {num_notes}" if speech.language == "ar" else f"Track {self.active_track_idx + 1}: {inst_name}. Volume {int(track.volume / 1.27)}%. Recorded notes: {num_notes}"
        speech.speak(msg, interrupt=True)

    def change_track_program(self, delta: int):
        track = self.tracks[self.active_track_idx]
        track.program = (track.program + delta) % 128
        self.synth.program_change(track.channel, track.program)
        inst = GM_INSTRUMENTS[track.program]
        name = inst["ar"] if speech.language == "ar" else inst["en"]
        speech.speak(f"الآلة: {name}" if speech.language == "ar" else f"Instrument: {name}", interrupt=True)

    def set_track_program(self, program_num: int):
        track = self.tracks[self.active_track_idx]
        track.program = max(0, min(127, program_num))
        self.synth.program_change(track.channel, track.program)
        inst = GM_INSTRUMENTS[track.program]
        name = inst["ar"] if speech.language == "ar" else inst["en"]
        speech.speak(f"تم اختيار: {name}" if speech.language == "ar" else f"Selected: {name}", interrupt=True)

    def adjust_track_volume(self, delta: int):
        track = self.tracks[self.active_track_idx]
        track.volume = max(0, min(127, track.volume + delta))
        self.synth.set_volume(track.channel, track.volume)
        pct = int((track.volume / 127.0) * 100)
        speech.speak(f"مستوى الصوت: {pct}%" if speech.language == "ar" else f"Volume: {pct}%", interrupt=True)

    def adjust_track_pan(self, delta: int):
        track = self.tracks[self.active_track_idx]
        track.pan = max(0, min(127, track.pan + delta))
        self.synth.set_pan(track.channel, track.pan)
        pan_name = "في المنتصف" if 58 <= track.pan <= 70 else (f"يمين {track.pan}" if track.pan > 70 else f"يسار {track.pan}")
        speech.speak(f"التوزيع: {pan_name}" if speech.language == "ar" else f"Pan: {track.pan}", interrupt=True)

    def toggle_track_mute(self):
        track = self.tracks[self.active_track_idx]
        track.muted = not track.muted
        state_str = "مكتوم" if track.muted else "نشط"
        speech.speak(f"المسار {self.active_track_idx + 1}: {state_str}", interrupt=True)

    def toggle_track_solo(self):
        track = self.tracks[self.active_track_idx]
        track.solo = not track.solo
        state_str = "معزول" if track.solo else "غير معزول"
        speech.speak(f"المسار {self.active_track_idx + 1}: {state_str}", interrupt=True)

    def undo_active_track(self) -> bool:
        track = self.tracks[self.active_track_idx]
        if track.undo():
            speech.speak(speech.get_text("undo_success", track_num=self.active_track_idx + 1), interrupt=True)
            return True
        else:
            speech.speak(speech.get_text("undo_empty"), interrupt=True)
            return False

    def clear_active_track(self):
        track = self.tracks[self.active_track_idx]
        track.clear()
        speech.speak(speech.get_text("track_cleared", track_num=self.active_track_idx + 1), interrupt=True)

    def quantize_track(self, track_idx: int, grid_division: int = 16):
        track = self.tracks[track_idx]
        if not track.events:
            speech.speak(speech.get_text("quantize_empty"), interrupt=True)
            return

        track.save_undo_state()
        ms_per_grid = 60000.0 / (self.bpm * (grid_division / 4.0))

        # Quantize note_on events and preserve relative note lengths
        on_times = {}
        for evt in track.events:
            etype, note, vel, t_ms, ch = evt
            if etype == "note_on":
                quantized_t = round(t_ms / ms_per_grid) * ms_per_grid
                on_times[note] = (t_ms, quantized_t)
                evt[3] = quantized_t
            elif etype == "note_off":
                if note in on_times:
                    orig_on, quant_on = on_times[note]
                    dur = max(20.0, t_ms - orig_on)
                    evt[3] = quant_on + dur

        track.events.sort(key=lambda e: e[3])
        speech.play_earcon("quantize")
        speech.speak(speech.get_text("quantize_success", grid=grid_division), interrupt=True)

    def _transport_loop(self):
        while self._running:
            now = time.perf_counter()
            if self.state == self.COUNTING_IN:
                self._handle_count_in(now)
            elif self.state in [self.PLAYING, self.RECORDING]:
                self._handle_playback_and_recording(now)
            time.sleep(0.001)

    def _handle_count_in(self, now: float):
        ms_per_beat = self.get_ms_per_beat()
        elapsed_ms = (now - self._count_in_start) * 1000.0
        current_beat = int(elapsed_ms // ms_per_beat)

        if current_beat > self._last_metronome_beat and current_beat < 4:
            self._last_metronome_beat = current_beat
            note = METRONOME_HIGH_NOTE if current_beat == 0 else METRONOME_LOW_NOTE
            vel = METRONOME_VELOCITY_HIGH if current_beat == 0 else METRONOME_VELOCITY_LOW
            self.synth.note_on(METRONOME_CHANNEL, note, vel)
            speech.speak(str(current_beat + 1), interrupt=True)

            def _off(n=note):
                time.sleep(0.04)
                self.synth.note_off(METRONOME_CHANNEL, n)
            threading.Thread(target=_off, daemon=True).start()

        if elapsed_ms >= (4 * ms_per_beat):
            with self._lock:
                self.state = self.RECORDING
                self._start_time = time.perf_counter()
                self.playhead_ms = 0.0
                self._last_metronome_beat = -1
                self._reset_playback_cursors()

    def _handle_playback_and_recording(self, now: float):
        self.playhead_ms = (now - self._start_time) * 1000.0

        # Metronome Tick
        if self.metronome_enabled:
            ms_per_beat = self.get_ms_per_beat()
            current_beat = int(self.playhead_ms // ms_per_beat)
            if current_beat > self._last_metronome_beat:
                self._last_metronome_beat = current_beat
                beat_in_bar = current_beat % 4
                note = METRONOME_HIGH_NOTE if beat_in_bar == 0 else METRONOME_LOW_NOTE
                vel = METRONOME_VELOCITY_HIGH if beat_in_bar == 0 else METRONOME_VELOCITY_LOW
                self.synth.note_on(METRONOME_CHANNEL, note, vel)

                def _off(n=note):
                    time.sleep(0.04)
                    self.synth.note_off(METRONOME_CHANNEL, n)
                threading.Thread(target=_off, daemon=True).start()

        # Multi-Track Playback Dispatcher
        has_solo = any(t.solo for t in self.tracks)
        for i, track in enumerate(self.tracks):
            if track.muted:
                continue
            if has_solo and not track.solo:
                continue
            if self.state == self.RECORDING and i == self.active_track_idx:
                continue  # Active recording track is monitored live via QWERTY

            c_idx = self._playback_cursors[i]
            while c_idx < len(track.events):
                evt = track.events[c_idx]
                etype, note, vel, t_ms, ch = evt
                if t_ms <= self.playhead_ms:
                    if etype == "note_on":
                        scaled_vel = int(vel * (track.volume / 127.0))
                        self.synth.note_on(ch, note, scaled_vel)
                        self._active_sounding_notes[(ch, note)] = True
                    elif etype == "note_off":
                        self.synth.note_off(ch, note)
                        self._active_sounding_notes.pop((ch, note), None)
                    c_idx += 1
                else:
                    break
            self._playback_cursors[i] = c_idx

    def _reset_playback_cursors(self):
        self._playback_cursors = [0] * self.num_tracks

    def _silence_sounding_notes(self):
        for (ch, note) in list(self._active_sounding_notes.keys()):
            self.synth.note_off(ch, note)
        self._active_sounding_notes.clear()

    def close(self):
        self._running = False
        self._silence_sounding_notes()
