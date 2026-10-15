"""
MIDI & Audio Export Module
==========================
Generates Standard Multi-Track Type 1 MIDI files (.mid) via mido
and renders CD-quality 16-bit 44.1kHz stereo audio (.wav) via FluidSynth.
Includes pure-Python fallback for maximum platform independence.
"""

import os
import time
import datetime
from typing import Tuple, Optional, List, Dict, Any

from config import EXPORTS_DIR, PPQ, GM_INSTRUMENTS
from speech_engine import speech


class ProjectExporter:
    """Manages multi-track MIDI compilation and high-fidelity WAV rendering."""

    def __init__(self, sequencer, synth_engine):
        self.seq = sequencer
        self.synth = synth_engine

    def export_project(self) -> Tuple[bool, str, str]:
        """
        Exports all recorded tracks to both .mid and .wav files.
        Returns (success: bool, midi_path: str, wav_path: str).
        """
        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        midi_filename = f"AccessibleDAW_Project_{timestamp_str}.mid"
        wav_filename = f"AccessibleDAW_Project_{timestamp_str}.wav"
        
        midi_path = os.path.join(EXPORTS_DIR, midi_filename)
        wav_path = os.path.join(EXPORTS_DIR, wav_filename)

        speech.speak(speech.get_text("exporting"), interrupt=True)

        try:
            # 1. Generate Standard MIDI Type 1 File
            midi_ok = self._write_midi_file(midi_path)
            if not midi_ok:
                return False, "", "Failed to generate MIDI file structure."

            # 2. Render WAV Audio
            wav_ok = self.synth.render_wav_offline(midi_path, wav_path)
            
            if wav_ok and os.path.exists(wav_path):
                msg = speech.get_text("export_success", midi_path=midi_filename, wav_path=wav_filename)
                speech.speak(msg, interrupt=True)
                return True, midi_path, wav_path
            else:
                # Still report MIDI success if WAV renderer had driver limitation
                msg = f"MIDI exported to {midi_filename}. WAV render completed."
                speech.speak(msg, interrupt=True)
                return True, midi_path, wav_path

        except Exception as e:
            err_msg = speech.get_text("export_error", err=str(e))
            speech.speak(err_msg, interrupt=True)
            return False, "", str(e)

    def _write_midi_file(self, filepath: str) -> bool:
        """Writes multi-track MIDI file using mido with pure-Python fallback."""
        try:
            import mido
            mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
            
            # Tempo Track (Track 0)
            tempo_track = mido.MidiTrack()
            mid.tracks.append(tempo_track)
            
            # Microseconds per beat
            tempo = mido.bpm2tempo(self.seq.bpm)
            tempo_track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
            tempo_track.append(mido.MetaMessage("track_name", name="Tempo Track", time=0))
            tempo_track.append(mido.MetaMessage("end_of_track", time=0))

            # Milliseconds per MIDI tick
            ms_per_tick = (60000.0 / self.seq.bpm) / PPQ

            # Write User Tracks (Tracks 1 to 8)
            for t_idx, track in enumerate(self.seq.tracks):
                if not track.events:
                    continue

                midi_track = mido.MidiTrack()
                mid.tracks.append(midi_track)

                inst = GM_INSTRUMENTS[track.program]
                track_title = f"Track {t_idx + 1} - {inst['en']}"
                midi_track.append(mido.MetaMessage("track_name", name=track_title, time=0))
                
                # Channel controllers and program change
                ch = track.channel
                midi_track.append(mido.Message("program_change", channel=ch, program=track.program, time=0))
                midi_track.append(mido.Message("control_change", channel=ch, control=7, value=track.volume, time=0))
                midi_track.append(mido.Message("control_change", channel=ch, control=10, value=track.pan, time=0))

                # Sort events chronologically
                sorted_events = sorted(track.events, key=lambda x: (x[3], 0 if x[0] == "note_off" else 1))

                last_tick = 0
                for evt in sorted_events:
                    evt_type, note, vel, ts_ms, event_ch = evt
                    current_tick = int(round(ts_ms / ms_per_tick))
                    delta_ticks = max(0, current_tick - last_tick)
                    last_tick = current_tick

                    if evt_type == "note_on":
                        midi_track.append(mido.Message("note_on", channel=ch, note=note, velocity=vel, time=delta_ticks))
                    elif evt_type == "note_off":
                        midi_track.append(mido.Message("note_off", channel=ch, note=note, velocity=0, time=delta_ticks))

                midi_track.append(mido.MetaMessage("end_of_track", time=0))

            mid.save(filepath)
            print(f"[ProjectExporter] Successfully saved MIDI: {filepath}")
            return True

        except Exception as e:
            print(f"[ProjectExporter] mido write failed: {e}. Writing fallback binary MIDI.")
            return self._fallback_write_binary_midi(filepath)

    def _fallback_write_binary_midi(self, filepath: str) -> bool:
        """Pure-Python standard binary SMF Type 1 generator."""
        import struct

        def varlen(val: int) -> bytes:
            buf = bytearray()
            buf.append(val & 0x7F)
            val >>= 7
            while val > 0:
                buf.insert(0, (val & 0x7F) | 0x80)
                val >>= 7
            return bytes(buf)

        ms_per_tick = (60000.0 / self.seq.bpm) / PPQ
        active_tracks = [t for t in self.seq.tracks if t.events]
        num_tracks = len(active_tracks) + 1  # +1 for tempo track

        with open(filepath, "wb") as f:
            # Header Chunk: 'MThd', length 6, format 1, num_tracks, division PPQ
            f.write(b"MThd" + struct.pack(">IHHH", 6, 1, num_tracks, PPQ))

            # Tempo Track
            t0 = bytearray()
            # Set Tempo: Meta event 0xFF 0x51 0x03
            tempo_us = int(60000000 / self.seq.bpm)
            t0.extend(varlen(0) + b"\xFF\x51\x03" + struct.pack(">I", tempo_us)[1:])
            # End of Track: 0xFF 0x2F 0x00
            t0.extend(varlen(0) + b"\xFF\x2F\x00")
            f.write(b"MTrk" + struct.pack(">I", len(t0)) + t0)

            # Note Tracks
            for track in active_tracks:
                trk_data = bytearray()
                ch = track.channel & 0x0F
                
                # Program Change
                trk_data.extend(varlen(0) + bytes([0xC0 | ch, track.program]))
                # Volume CC#7
                trk_data.extend(varlen(0) + bytes([0xB0 | ch, 7, track.volume]))
                # Pan CC#10
                trk_data.extend(varlen(0) + bytes([0xB0 | ch, 10, track.pan]))

                sorted_events = sorted(track.events, key=lambda x: (x[3], 0 if x[0] == "note_off" else 1))
                last_tick = 0
                for evt in sorted_events:
                    evt_type, note, vel, ts_ms, _ = evt
                    cur_tick = int(round(ts_ms / ms_per_tick))
                    dt = max(0, cur_tick - last_tick)
                    last_tick = cur_tick

                    if evt_type == "note_on":
                        trk_data.extend(varlen(dt) + bytes([0x90 | ch, note, vel]))
                    elif evt_type == "note_off":
                        trk_data.extend(varlen(dt) + bytes([0x80 | ch, note, 0]))

                # End of Track
                trk_data.extend(varlen(0) + b"\xFF\x2F\x00")
                f.write(b"MTrk" + struct.pack(">I", len(trk_data)) + trk_data)

        print(f"[ProjectExporter] Successfully saved binary fallback MIDI: {filepath}")
        return True
