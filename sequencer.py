"""
Multi-Track MIDI Sequencer & Looper Engine
==========================================
High-precision multi-track recording, playback, overdubbing, and smart quantization.
Features an accessible 4-beat count-in, synchronized metronome on GM Percussion,
and undo history for each track.
"""

import time
import threading
from typing import List, Dict, Tuple, Optional, Any

from config import (
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
from speech_engine import speech


class Track:
    """Represents a single MIDI track with its own instrument, volume, pan, and events."""

    def __init__(self, track_id: int, channel: int):
        self.track_id = track_id
        self.channel = channel
        self.program = 0      # Instrument 0 = Grand Piano
        self.volume = 100     # CC#7 (0-127)
        self.pan = 64         # CC#10 (0=Left, 64=Center, 127=Right)
        self.muted = False
        self.solo = False
        
        # Events: [event_type ('note_on'/'note_off'), note, velocity, timestamp_ms, channel]
        self.events: List[List[Any]] = []
        self._undo_stack: List[List[List[Any]]] = []

    def add_event(self, event_type: str, note: int, velocity: int, timestamp_ms: float):
        """Appends a musical event with precise timestamp."""
        self.events.append([event_type, note, velocity, timestamp_ms, self.channel])

    def save_undo_state(self):
        """Stores a snapshot of current events for undo."""
        # Limit undo history to 10 passes to conserve memory
        if len(self._undo_stack) >= 10:
            self._undo_stack.pop(0)
        self._undo_stack.append([list(evt) for evt in self.events])

    def undo(self) -> bool:
        """Restores previous event state."""
        if self._undo_stack:
            self.events = self._undo_stack.pop()
            return True
        return False

    def clear(self):
        """Clears all events on this track."""
        self.save_undo_state()
        self.events.clear()

    def is_audible(self, any_solo_active: bool) -> bool:
        """Determines if this track should produce sound given mute and solo states."""
        if any_solo_active:
            return self.solo and not self.muted
        return not self.muted

    def get_duration_ms(self) -> float:
        """Returns the timestamp of the last recorded event."""
        if not self.events:
            return 0.0
        return max(evt[3] for evt in self.events)


class Sequencer:
    """Real-time Multi-Track Sequencer and Transport Engine."""

    # Transport States
    STOPPED = 0
    PLAYING = 1
    COUNTING_IN = 2
    RECORDING = 3

    def __init__(self, synth_engine):
        self.synth = synth_engine
        self.bpm = DEFAULT_BPM
        self.active_track_idx = 0
        self.tracks: List[Track] = [Track(i, i) for i in range(MAX_TRACKS)]
        
        # Transport state
        self.state = self.STOPPED
        self.metronome_enabled = True
        self.loop_enabled = False
        self.loop_length_ms = 8000.0  # Default 4 bars at 120 BPM
        
        # Timing variables
        self.playhead_ms = 0.0
        self._start_time = 0.0
        self._count_in_start = 0.0
        self._last_metronome_beat = -1
        
        # Playback cursor indices per track to avoid O(N) scanning
        self._playback_indices = [0] * MAX_TRACKS
        self._actively_sounding_notes: Dict[Tuple[int, int], bool] = {}
        
        # Engine thread
        self._lock = threading.Lock()
        self._running = True
        self._transport_thread = threading.Thread(target=self._transport_loop, daemon=True, name="Sequencer-Clock")
        self._transport_thread.start()

    # -----------------------------------------------------------------------
    # Transport Control Methods
    # -----------------------------------------------------------------------
    def start_recording(self):
        """Initiates recording with 4-beat audible count-in."""
        with self._lock:
            # Stop existing playback if active
            self._silence_sounding_notes()
            
            # Save undo snapshot for active track before new recording pass
            self.tracks[self.active_track_idx].save_undo_state()
            
            self.state = self.COUNTING_IN
            self._count_in_start = time.perf_counter()
            self._last_metronome_beat = -1
            self.playhead_ms = 0.0

    def start_playback(self):
        """Starts multi-track playback from current playhead position or 0."""
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
        """Stops playback or recording and silences active notes."""
        with self._lock:
            prev_state = self.state
            self.state = self.STOPPED
            self._silence_sounding_notes()
            speech.play_earcon("stop")
            
            if prev_state == self.RECORDING:
                # Update loop length automatically to fit recording to clean musical bars
                rec_duration = self.tracks[self.active_track_idx].get_duration_ms()
                bar_ms = self.get_ms_per_bar()
                if rec_duration > 0:
                    bars = max(1, int((rec_duration + bar_ms - 1) // bar_ms))
                    self.loop_length_ms = bars * bar_ms
                
                evt_count = len(self.tracks[self.active_track_idx].events)
                msg = speech.get_text("rec_stopped", count=evt_count)
                speech.speak(msg, interrupt=True)
                
            elif prev_state == self.PLAYING:
                bar, beat = self.get_bar_beat()
                msg = speech.get_text("playback_stopped", bar=bar, beat=beat)
                speech.speak(msg, interrupt=True)

    def toggle_play_stop(self):
        """Spacebar action: Play or Stop."""
        if self.state == self.STOPPED:
            self.start_playback()
        else:
            self.stop()

    def toggle_loop(self) -> bool:
        """Toggles looping mode on/off."""
        self.loop_enabled = not self.loop_enabled
        key = "loop_on" if self.loop_enabled else "loop_off"
        speech.speak(speech.get_text(key), interrupt=True)
        return self.loop_enabled

    def toggle_metronome(self) -> bool:
        """Toggles audible metronome click."""
        self.metronome_enabled = not self.metronome_enabled
        key = "metronome_on" if self.metronome_enabled else "metronome_off"
        speech.speak(speech.get_text(key), interrupt=True)
        return self.metronome_enabled

    # -----------------------------------------------------------------------
    # Musical Math & Helpers
    # -----------------------------------------------------------------------
    def get_ms_per_beat(self) -> float:
        return 60000.0 / self.bpm

    def get_ms_per_bar(self) -> float:
        return self.get_ms_per_beat() * 4.0  # Standard 4/4 Time Signature

    def get_bar_beat(self) -> Tuple[int, int]:
        """Calculates current (Bar, Beat) starting at (1, 1)."""
        ms_per_beat = self.get_ms_per_beat()
        total_beats = int(self.playhead_ms // ms_per_beat)
        bar = (total_beats // 4) + 1
        beat = (total_beats % 4) + 1
        return bar, beat

    def adjust_bpm(self, delta: int) -> int:
        """Adjusts tempo within safety limits."""
        new_bpm = max(MIN_BPM, min(MAX_BPM, self.bpm + delta))
        if new_bpm != self.bpm:
            self.bpm = new_bpm
            # Adjust loop length proportionally
            bar_ms = self.get_ms_per_bar()
            bars = max(1, round(self.loop_length_ms / (60000.0 / (self.bpm - delta) * 4)))
            self.loop_length_ms = bars * bar_ms
            speech.speak(speech.get_text("tempo_changed", bpm=self.bpm), interrupt=True)
        return self.bpm

    # -----------------------------------------------------------------------
    # Live Input Recording Hook
    # -----------------------------------------------------------------------
    def record_note_on(self, note: int, velocity: int):
        """Called when user presses a key on the active track."""
        ch = self.tracks[self.active_track_idx].channel
        self.synth.note_on(ch, note, velocity)
        
        if self.state == self.RECORDING:
            with self._lock:
                self.tracks[self.active_track_idx].add_event(
                    "note_on", note, velocity, self.playhead_ms
                )

    def record_note_off(self, note: int):
        """Called when user releases a key on the active track."""
        ch = self.tracks[self.active_track_idx].channel
        self.synth.note_off(ch, note)
        
        if self.state == self.RECORDING:
            with self._lock:
                self.tracks[self.active_track_idx].add_event(
                    "note_off", note, 0, self.playhead_ms
                )

    # -----------------------------------------------------------------------
    # High-Precision Clock & Playback Thread
    # -----------------------------------------------------------------------
    def _transport_loop(self):
        """Main real-time transport clock running with microsecond precision."""
        while self._running:
            now = time.perf_counter()

            if self.state == self.COUNTING_IN:
                self._handle_count_in(now)
            elif self.state in [self.PLAYING, self.RECORDING]:
                self._handle_playback_and_recording(now)

            # Sleep 1ms to maintain low CPU load while preserving sub-millisecond precision
            time.sleep(0.001)

    def _handle_count_in(self, now: float):
        """Executes 4 audible count-in beats prior to recording start."""
        ms_per_beat = self.get_ms_per_beat()
        elapsed_ms = (now - self._count_in_start) * 1000.0
        current_beat = int(elapsed_ms // ms_per_beat)

        if current_beat > self._last_metronome_beat and current_beat < 4:
            self._last_metronome_beat = current_beat
            # Beat 0 is high woodblock, 1, 2, 3 are low woodblocks
            note = METRONOME_HIGH_NOTE if current_beat == 0 else METRONOME_LOW_NOTE
            vel = METRONOME_VELOCITY_HIGH if current_beat == 0 else METRONOME_VELOCITY_LOW
            self.synth.note_on(METRONOME_CHANNEL, note, vel)
            # Announce beat number
            speech.speak(str(current_beat + 1), interrupt=True)
            
            # Auto note-off in 40ms
            def _off(n=note):
                time.sleep(0.04)
                self.synth.note_off(METRONOME_CHANNEL, n)
            threading.Thread(target=_off, daemon=True).start()

        # If 4 beats finished, seamlessly switch to RECORDING mode at timestamp 0ms
        if elapsed_ms >= (4 * ms_per_beat):
            with self._lock:
                self.state = self.RECORDING
                self._start_time = time.perf_counter()
                self.playhead_ms = 0.0
                self._last_metronome_beat = -1
                self._reset_playback_cursors()
                speech.play_earcon("rec_start")
                msg = speech.get_text("rec_started", track_num=self.active_track_idx + 1)
                speech.speak(msg, interrupt=True)

    def _handle_playback_and_recording(self, now: float):
        """Processes scheduled events and metronome pulses."""
        self.playhead_ms = (now - self._start_time) * 1000.0

        # Metronome Click Processing
        if self.metronome_enabled:
            ms_per_beat = self.get_ms_per_beat()
            current_beat = int(self.playhead_ms // ms_per_beat)
            if current_beat > self._last_metronome_beat:
                self._last_metronome_beat = current_beat
                is_bar_downbeat = (current_beat % 4 == 0)
                note = METRONOME_HIGH_NOTE if is_bar_downbeat else METRONOME_LOW_NOTE
                vel = METRONOME_VELOCITY_HIGH if is_bar_downbeat else METRONOME_VELOCITY_LOW
                self.synth.note_on(METRONOME_CHANNEL, note, vel)

                def _off(n=note):
                    time.sleep(0.035)
                    self.synth.note_off(METRONOME_CHANNEL, n)
                threading.Thread(target=_off, daemon=True).start()

        # Loop boundary check
        if self.loop_enabled and self.playhead_ms >= self.loop_length_ms:
            with self._lock:
                self.playhead_ms = 0.0
                self._start_time = time.perf_counter()
                self._reset_playback_cursors()
                self._last_metronome_beat = -1
                return

        # Check tracks for due playback events
        any_solo = any(t.solo for t in self.tracks)
        
        for t_idx, track in enumerate(self.tracks):
            # In RECORDING mode, don't play back the track currently being recorded (overdubbing listens to new live input)
            if self.state == self.RECORDING and t_idx == self.active_track_idx:
                continue

            if not track.is_audible(any_solo):
                continue

            cursor = self._playback_indices[t_idx]
            events = track.events
            num_events = len(events)

            while cursor < num_events:
                evt = events[cursor]
                evt_type, note, vel, timestamp, ch = evt
                
                if timestamp <= self.playhead_ms:
                    if evt_type == "note_on":
                        self.synth.note_on(ch, note, vel)
                        self._actively_sounding_notes[(ch, note)] = True
                    elif evt_type == "note_off":
                        self.synth.note_off(ch, note)
                        self._actively_sounding_notes.pop((ch, note), None)
                    cursor += 1
                else:
                    break

            self._playback_indices[t_idx] = cursor

    def _reset_playback_cursors(self):
        """Resets event playback pointers to start."""
        self._playback_indices = [0] * MAX_TRACKS

    def _silence_sounding_notes(self):
        """Silences any notes triggered by the sequencer."""
        for ch, note in list(self._actively_sounding_notes.keys()):
            self.synth.note_off(ch, note)
        self._actively_sounding_notes.clear()

    # -----------------------------------------------------------------------
    # Track Navigation & Manipulation
    # -----------------------------------------------------------------------
    def select_track(self, track_idx: int):
        """Switches active track (0 to MAX_TRACKS - 1)."""
        if 0 <= track_idx < MAX_TRACKS and track_idx != self.active_track_idx:
            self.active_track_idx = track_idx
            track = self.tracks[track_idx]
            inst = GM_INSTRUMENTS[track.program]
            inst_name = inst["ar"] if speech.get_language() == "ar" else inst["en"]
            speech.play_earcon("track_switch")
            msg = speech.get_text("track_selected", track_num=track_idx + 1, inst_name=inst_name)
            speech.speak(msg, interrupt=True)

    def change_track_program(self, delta: int):
        """Switches instrument on active track (Tab / Shift+Tab)."""
        track = self.tracks[self.active_track_idx]
        new_prog = (track.program + delta) % 128
        track.program = new_prog
        self.synth.program_change(track.channel, new_prog)
        
        inst = GM_INSTRUMENTS[new_prog]
        inst_name = inst["ar"] if speech.get_language() == "ar" else inst["en"]
        msg = speech.get_text("program_changed", inst_name=inst_name)
        speech.speak(msg, interrupt=True)

    def adjust_track_volume(self, delta: int):
        """Adjusts volume on active track (Up/Down Arrows)."""
        track = self.tracks[self.active_track_idx]
        new_vol = max(0, min(127, track.volume + delta))
        if new_vol != track.volume:
            track.volume = new_vol
            self.synth.set_volume(track.channel, new_vol)
            pct = int((new_vol / 127.0) * 100)
            speech.speak(speech.get_text("volume_changed", volume=f"{pct}%"), interrupt=True)
        else:
            speech.play_earcon("boundary")

    def adjust_track_pan(self, delta: int):
        """Adjusts stereo panning on active track (Left/Right Arrows)."""
        track = self.tracks[self.active_track_idx]
        new_pan = max(0, min(127, track.pan + delta))
        if new_pan != track.pan:
            track.pan = new_pan
            self.synth.set_pan(track.channel, new_pan)
            if new_pan == 64:
                msg = speech.get_text("pan_center")
            elif new_pan < 64:
                val = int(((64 - new_pan) / 64.0) * 100)
                msg = speech.get_text("pan_left", val=f"{val}%")
            else:
                val = int(((new_pan - 64) / 63.0) * 100)
                msg = speech.get_text("pan_right", val=f"{val}%")
            speech.speak(msg, interrupt=True)
        else:
            speech.play_earcon("boundary")

    def toggle_track_solo(self):
        """Toggles solo on active track (F7)."""
        track = self.tracks[self.active_track_idx]
        track.solo = not track.solo
        key = "solo_on" if track.solo else "solo_off"
        speech.speak(speech.get_text(key, track_num=self.active_track_idx + 1), interrupt=True)

    def toggle_track_mute(self):
        """Toggles mute on active track (F8)."""
        track = self.tracks[self.active_track_idx]
        track.muted = not track.muted
        key = "mute_on" if track.muted else "mute_off"
        speech.speak(speech.get_text(key, track_num=self.active_track_idx + 1), interrupt=True)

    def undo_active_track(self):
        """Undoes last recording or quantization on active track (F9)."""
        track = self.tracks[self.active_track_idx]
        if track.undo():
            speech.speak(speech.get_text("undo_done", track_num=self.active_track_idx + 1), interrupt=True)
        else:
            speech.speak(speech.get_text("undo_empty"), interrupt=True)

    def clear_active_track(self):
        """Clears active track (F10)."""
        track = self.tracks[self.active_track_idx]
        track.clear()
        speech.speak(speech.get_text("track_cleared", track_num=self.active_track_idx + 1), interrupt=True)

    def announce_track_info(self):
        """Reads detailed info for active track (F2)."""
        track = self.tracks[self.active_track_idx]
        inst = GM_INSTRUMENTS[track.program]
        inst_name = inst["ar"] if speech.get_language() == "ar" else inst["en"]
        vol_pct = int((track.volume / 127.0) * 100)
        
        if track.pan == 64:
            pan_str = speech.get_text("pan_center")
        elif track.pan < 64:
            pan_str = speech.get_text("pan_left", val=f"{int(((64 - track.pan) / 64.0) * 100)}%")
        else:
            pan_str = speech.get_text("pan_right", val=f"{int(((track.pan - 64) / 63.0) * 100)}%")

        status_parts = []
        if track.solo:
            status_parts.append(speech.get_text("solo_on", track_num=""))
        if track.muted:
            status_parts.append(speech.get_text("mute_on", track_num=""))
        status_str = ", ".join(status_parts) if status_parts else ""

        msg = speech.get_text(
            "track_info",
            track_num=self.active_track_idx + 1,
            inst_name=inst_name,
            volume=vol_pct,
            pan=pan_str,
            status=status_str
        )
        speech.speak(msg, interrupt=True)

    # -----------------------------------------------------------------------
    # Smart Quantization
    # -----------------------------------------------------------------------
    def quantize_track(self, track_id: int, grid_division: int = 16) -> bool:
        """
        Mathematical quantization snapping note timestamps to nearest grid division.
        grid_division: 4 (quarter note), 8 (eighth note), 16 (sixteenth note), 32 (thirty-second note).
        """
        if track_id < 0 or track_id >= MAX_TRACKS:
            return False

        track = self.tracks[track_id]
        if not track.events:
            return False

        with self._lock:
            track.save_undo_state()
            
            # Grid duration in ms = (60000 / BPM) * (4 / grid_division)
            grid_interval_ms = (60000.0 / self.bpm) * (4.0 / grid_division)
            min_note_duration_ms = grid_interval_ms * 0.4

            # Pair note_on with corresponding note_off events
            notes_paired: List[Dict[str, Any]] = []
            pending_notes: Dict[Tuple[int, int], List[Any]] = {}  # (ch, note) -> [evt]

            for evt in track.events:
                evt_type, note, vel, ts, ch = evt
                if evt_type == "note_on" and vel > 0:
                    pending_notes[(ch, note)] = evt
                elif evt_type == "note_off" or (evt_type == "note_on" and vel == 0):
                    if (ch, note) in pending_notes:
                        on_evt = pending_notes.pop((ch, note))
                        notes_paired.append({
                            "note": note,
                            "velocity": on_evt[2],
                            "channel": ch,
                            "on_ts": on_evt[3],
                            "off_ts": ts
                        })

            # Reconstruct quantized events
            quantized_events: List[List[Any]] = []
            for item in notes_paired:
                orig_on = item["on_ts"]
                orig_off = item["off_ts"]
                duration = max(min_note_duration_ms, orig_off - orig_on)

                # Snap note_on to closest grid line
                new_on = round(orig_on / grid_interval_ms) * grid_interval_ms
                new_off = new_on + duration

                quantized_events.append(["note_on", item["note"], item["velocity"], new_on, item["channel"]])
                quantized_events.append(["note_off", item["note"], 0, new_off, item["channel"]])

            # Sort events chronologically
            quantized_events.sort(key=lambda x: (x[3], 0 if x[0] == "note_off" else 1))
            track.events = quantized_events

        speech.play_earcon("quantize")
        speech.speak(speech.get_text("quantized", track_num=track_id + 1, grid=grid_division), interrupt=True)
        return True

    def close(self):
        """Stops the transport engine."""
        self._running = False
        self.stop()
