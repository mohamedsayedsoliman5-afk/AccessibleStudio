"""
Automated Test Suite for AccessibleStudio DAW v2.0
==================================================
Verifies all modular engines: configuration, piano keyboard mapping,
multi-track sequencing, smart quantization, undo/redo, drum grid presets,
MIDI compilation, and master WAV rendering.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from accessible_studio.config import (
    GM_INSTRUMENTS,
    GM_DRUMS,
    STEP_DRUM_INSTRUMENTS,
    STRINGS,
    get_note_name
)
from accessible_studio.accessibility.speech import speech
from accessible_studio.accessibility.piano_keys import PianoKeyboardMapper
from accessible_studio.core.midi_synth import MidiSynthEngine
from accessible_studio.core.sequencer import Sequencer, Track
from accessible_studio.core.drum_grid import DrumGridSequencer
from accessible_studio.core.exporter import ProjectExporter


def test_config():
    print("[1/7] Testing config & localization...")
    assert len(GM_INSTRUMENTS) == 128, f"Expected 128 GM instruments, got {len(GM_INSTRUMENTS)}"
    assert len(STEP_DRUM_INSTRUMENTS) >= 8, "Expected at least 8 drum pieces in step sequencer"
    assert "ar" in STRINGS and "en" in STRINGS, "Missing localization tables"
    assert get_note_name(60, "en") == "C 4"
    assert get_note_name(60, "ar") == "دو 4"
    print("  -> Config & localization passed.")


def test_keyboard_mapper():
    print("[2/7] Testing piano keyboard mapper & debounce...")
    km = PianoKeyboardMapper(base_octave=4, base_velocity=100)

    # Test Middle C (Z -> MIDI 60)
    note_vel = km.process_key_down("z", "z")
    assert note_vel is not None
    note, vel = note_vel
    assert note == 60, f"Expected MIDI 60 for 'z', got {note}"
    assert vel == 100

    # Test auto-repeat suppression (same key while held)
    rep = km.process_key_down("z", "z")
    assert rep is None, "Failed to suppress OS key repeat!"

    # Test release
    rel_note = km.process_key_up("z")
    assert rel_note == 60, f"Expected release note 60, got {rel_note}"

    # Test Upper Octave (Q -> MIDI 72 = C5)
    note_vel_q = km.process_key_down("q", "q")
    assert note_vel_q is not None and note_vel_q[0] == 72, f"Expected MIDI 72 for 'q', got {note_vel_q}"
    km.process_key_up("q")

    # Test Octave Shifting
    new_oct, changed = km.octave_up()
    assert changed and new_oct == 5
    note_vel_z5 = km.process_key_down("z", "z")
    assert note_vel_z5[0] == 72
    km.process_key_up("z")

    # Reset
    km.octave_down()
    print("  -> Piano keyboard mapper passed.")


def test_synth_engine():
    print("[3/7] Testing MIDI synthesis engine & mixing...")
    synth = MidiSynthEngine()
    synth.set_volume(0, 95)
    synth.set_pan(0, 30)
    synth.program_change(0, 4)  # Rhodes Electric Piano
    synth.note_on(0, 60, 100)
    synth.note_off(0, 60)
    synth.panic()
    print("  -> MIDI synthesis engine passed.")
    return synth


def test_sequencer_quantization_undo(synth):
    print("[4/7] Testing multi-track sequencer, smart quantization, and undo...")
    seq = Sequencer(synth, num_tracks=8)
    seq.bpm = 120
    track = seq.tracks[0]

    track.add_event("note_on", 60, 100, 23.0)
    track.add_event("note_off", 60, 0, 110.0)
    track.add_event("note_on", 64, 90, 132.0)
    track.add_event("note_off", 64, 0, 240.0)

    # Quantize to 16th grid (snap to multiples of 125ms: 0ms, 125ms...)
    seq.quantize_track(0, grid_division=16)

    # Note 1 should snap to 0.0ms
    assert track.events[0][3] == 0.0, f"Quantization failed: expected 0.0, got {track.events[0][3]}"
    # Note 2 should snap to 125.0ms
    assert track.events[2][3] == 125.0, f"Quantization failed: expected 125.0, got {track.events[2][3]}"

    # Test Undo
    assert seq.undo_active_track() is True, "Undo failed!"
    assert track.events[0][3] == 23.0, "Undo did not restore original unquantized timestamp!"

    seq.close()
    print("  -> Sequencer & Smart Quantization passed.")


def test_drum_grid(synth):
    print("[5/7] Testing 16-step rhythmic drum sequencer & presets...")
    drums = DrumGridSequencer(synth)

    # Toggle hit on step 0
    drums.toggle_current_hit()
    assert drums.grid[0][0] is True
    drums.toggle_current_hit()
    assert drums.grid[0][0] is False

    # Load Arabic Maqsum preset
    assert drums.load_preset("maqsum") is True
    assert drums.grid[0][0] is True  # Dum on beat 1
    assert drums.grid[1][4] is True  # Tak on beat 2

    # Render to MIDI events
    events = drums.render_to_track_events(bpm=120.0, bars=2)
    assert len(events) > 0, "No events generated from drum pattern!"
    assert events[0][0] == "note_on"
    print("  -> Drum Grid passed.")


def test_export(synth):
    print("[6/7] Testing multi-track MIDI compilation and WAV audio export...")
    seq = Sequencer(synth, num_tracks=8)
    seq.bpm = 120

    # Add musical phrase on Track 1 (Piano)
    t1 = seq.tracks[0]
    t1.program = 0
    t1.add_event("note_on", 60, 100, 0.0)
    t1.add_event("note_off", 60, 0, 250.0)
    t1.add_event("note_on", 64, 100, 250.0)
    t1.add_event("note_off", 64, 0, 500.0)
    t1.add_event("note_on", 67, 100, 500.0)
    t1.add_event("note_off", 67, 0, 1000.0)

    # Add drums on Track 2 (Drums)
    drums = DrumGridSequencer(synth)
    drums.load_preset("maqsum")
    t2 = seq.tracks[1]
    t2.channel = 9
    t2.events = drums.render_to_track_events(bpm=120.0, bars=1)

    exporter = ProjectExporter(seq, synth)
    os.makedirs("exports", exist_ok=True)
    os.makedirs("recordings", exist_ok=True)
    test_base = f"Test_Export_{int(time.time())}"
    midi_file = os.path.join("exports", f"{test_base}.mid")
    wav_file = os.path.join("exports", f"{test_base}.wav")

    exporter._save_midi(midi_file)
    assert os.path.exists(midi_file) and os.path.getsize(midi_file) > 100, "MIDI export failed!"

    exporter._save_wav(midi_file, wav_file)
    assert os.path.exists(wav_file) and os.path.getsize(wav_file) > 1000, "WAV export failed!"

    seq.close()
    print(f"  -> Export passed. Generated: {os.path.basename(midi_file)} ({os.path.getsize(midi_file)} bytes) & {os.path.basename(wav_file)} ({os.path.getsize(wav_file)} bytes)")


def test_speech_and_earcons(synth):
    print("[7/7] Testing speech engine & Earcons...")
    speech.set_synth_callbacks(synth.note_on, synth.note_off)
    speech.play_earcon("play")
    speech.play_earcon("stop")
    speech.play_earcon("record")
    speech.play_earcon("boundary")
    speech.play_earcon("quantize")

    speech.speak("اختبار نطق شاشة التوقف", interrupt=True)
    time.sleep(0.1)
    speech.shutdown()
    print("  -> Speech and Earcon cues passed.")


if __name__ == "__main__":
    print("Starting AccessibleStudio v2.0 Test Suite...\n")
    test_config()
    test_keyboard_mapper()
    synth_inst = test_synth_engine()
    test_sequencer_quantization_undo(synth_inst)
    test_drum_grid(synth_inst)
    test_export(synth_inst)
    test_speech_and_earcons(synth_inst)
    synth_inst.close()
    print("\nALL 7 TEST SUITES PASSED PERFECTLY WITH ZERO ERRORS!")
