"""
AccessibleStudio Core - Project Exporter (MIDI & High-Fidelity WAV)
==================================================================
Compiles multi-track sequences into standard MIDI Format 1 files (.mid)
and renders audio into 16-bit 44.1kHz Stereo WAV files (.wav).
Runs in a background thread to prevent UI freezing during export.
"""

import os
import datetime
import threading
from typing import Optional, Callable

from accessible_studio.config import EXPORTS_DIR, SAMPLE_RATE, GM_INSTRUMENTS
from accessible_studio.accessibility.speech import speech


class ProjectExporter:
    """Handles project compilation to Standard MIDI (.mid) and master WAV (.wav)."""

    def __init__(self, sequencer, synth_engine):
        self.sequencer = sequencer
        self.synth = synth_engine
        os.makedirs(EXPORTS_DIR, exist_ok=True)

    def export_project(self, base_filename: Optional[str] = None, on_complete: Optional[Callable] = None):
        """Asynchronously exports active project to both MIDI and WAV files."""
        speech.speak(speech.get_text("exporting"), interrupt=True)

        def _worker():
            try:
                now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                name = base_filename if base_filename else f"AccessibleDAW_Project_{now_str}"
                midi_path = os.path.join(EXPORTS_DIR, f"{name}.mid")
                wav_path = os.path.join(EXPORTS_DIR, f"{name}.wav")

                # 1. Export Standard MIDI File
                self._save_midi(midi_path)

                # 2. Render Audio WAV
                self._save_wav(midi_path, wav_path)

                # Announce Completion
                speech.play_earcon("export")
                success_msg = speech.get_text(
                    "export_success",
                    midi_file=os.path.basename(midi_path),
                    wav_file=os.path.basename(wav_path)
                )
                speech.speak(success_msg, interrupt=True)
                print(f"[ProjectExporter] Export finished: {midi_path} and {wav_path}")

                if on_complete:
                    on_complete(midi_path, wav_path)

            except Exception as e:
                err_msg = speech.get_text("export_error", error=str(e))
                speech.speak(err_msg, interrupt=True)
                print(f"[ProjectExporter] Error during export: {e}")

        threading.Thread(target=_worker, daemon=True, name="ProjectExporter-Thread").start()

    def _save_midi(self, output_midi_path: str):
        """Compiles multi-track events into a Standard MIDI Format 1 file."""
        import mido

        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo = mido.bpm2tempo(self.sequencer.bpm)

        # Track 0: Conductor & Tempo Track
        conductor = mido.MidiTrack()
        mid.tracks.append(conductor)
        conductor.append(mido.MetaMessage("track_name", name="AccessibleStudio Project", time=0))
        conductor.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
        conductor.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))
        conductor.append(mido.MetaMessage("end_of_track", time=0))

        # Instrument Tracks
        ms_per_tick = (60000.0 / self.sequencer.bpm) / 480.0

        for t_idx, track in enumerate(self.sequencer.tracks):
            midi_track = mido.MidiTrack()
            mid.tracks.append(midi_track)

            inst = GM_INSTRUMENTS[track.program]
            t_name = f"Track {t_idx + 1} - {inst['en']}"
            midi_track.append(mido.MetaMessage("track_name", name=t_name, time=0))

            # Channel setup controllers
            midi_track.append(mido.Message("program_change", channel=track.channel, program=track.program, time=0))
            midi_track.append(mido.Message("control_change", channel=track.channel, control=7, value=track.volume, time=0))
            midi_track.append(mido.Message("control_change", channel=track.channel, control=10, value=track.pan, time=0))

            # Sort track events by timestamp
            sorted_events = sorted(track.events, key=lambda e: e[3])
            last_event_tick = 0

            for evt in sorted_events:
                etype, note, vel, t_ms, ch = evt
                abs_tick = int(t_ms / ms_per_tick)
                delta_ticks = max(0, abs_tick - last_event_tick)
                last_event_tick = abs_tick

                if etype == "note_on":
                    midi_track.append(mido.Message("note_on", channel=ch, note=note, velocity=vel, time=delta_ticks))
                elif etype == "note_off":
                    midi_track.append(mido.Message("note_off", channel=ch, note=note, velocity=0, time=delta_ticks))

            midi_track.append(mido.MetaMessage("end_of_track", time=480))

        mid.save(output_midi_path)
        print(f"[ProjectExporter] Successfully saved MIDI: {output_midi_path}")

    def _save_wav(self, midi_path: str, output_wav_path: str):
        """Renders project audio to standard WAV file."""
        success = self.synth.render_wav_offline(midi_path, output_wav_path)
        if not success:
            raise RuntimeError("Audio synthesis engine failed to render WAV.")
