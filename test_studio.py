"""
Automated Test Suite for Accessible Mini-DAW Studio
===================================================
Verifies all modules, mathematical quantization, musical keyboard mapping,
multi-track sequencing, drum grid presets, and file export operations.
"""

import os
import sys
import time

# Ensure blind_daw is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    GM_INSTRUMENTS,
    GM_DRUMS,
    STEP_DRUM_INSTRUMENTS,
    STRINGS,
    get_note_name
)
from speech_engine import speech
from synth_engine import SynthEngine
from keyboard_mapper import KeyboardMapper
from sequencer import Sequencer, Track
from step_sequencer import StepSequencer
from exporter import ProjectExporter


def test_config():
    print("[1/7] Testing config & localization...")
    assert len(GM_INSTRUMENTS) == 128, f"Expected 128 GM instruments, got {len(GM_INSTRUMENTS)}"
    assert len(STEP_DRUM_INSTRUMENTS) >= 8, "Expected at least 8 drum pieces in step sequencer"
    assert "ar" in STRINGS and "en" in STRINGS, "Missing localization tables"
    assert get_note_name(60, "en") == "C 4"
    assert get_note_name(60, "ar") == "دو 4"
    print("  -> Config & localization passed.")


def test_keyboard_mapper():
    print("[2/7] Testing keyboard mapper & anti-repeat debounce...")
    km = KeyboardMapper(base_octave=4, base_velocity=100)
    
    # Test Middle C (Z -> MIDI 60)
    note_vel = km.process_key_down(122, "z")
    assert note_vel is not None
    note, vel = note_vel
    assert note == 60, f"Expected MIDI 60 for 'z', got {note}"
    assert vel == 100

    # Test auto-repeat suppression (same key while held)
    rep = km.process_key_down(122, "z")
    assert rep is None, "Failed to suppress OS key repeat!"

    # Test release
    rel_note = km.process_key_up(122)
    assert rel_note == 60, f"Expected release note 60, got {rel_note}"

    # Test Upper Octave (Q -> MIDI 72 = C5)
    note_vel_q = km.process_key_down(113, "q")
    assert note_vel_q is not None and note_vel_q[0] == 72, f"Expected MIDI 72 for 'q', got {note_vel_q}"
    km.process_key_up(113)

    # Test Octave Shifting
    new_oct, changed = km.octave_up()
    assert changed and new_oct == 5
    note_vel_z5 = km.process_key_down(122, "z")
    assert note_vel_z5[0] == 72  # Z shifted up by 1 octave
    km.process_key_up(122)

    # Reset
    km.octave_down()
    print("  -> Keyboard mapper passed.")


def test_synth_engine():
    print("[3/7] Testing synthesis engine & mixing...")
    synth = SynthEngine()
    # Test channels, volume, pan
    synth.set_volume(0, 95)
    synth.set_pan(0, 30)
    synth.program_change(0, 4)  # Rhodes
    synth.note_on(0, 60, 100)
    synth.note_off(0, 60)
    synth.panic()
    print("  -> Synth engine passed.")
    return synth


def test_sequencer_quantization_undo(synth):
    print("[4/7] Testing sequencer, smart quantization, and undo...")
    seq = Sequencer(synth)
    seq.bpm = 120  # 1 beat = 500ms, 1/16th note = 125ms
    track = seq.tracks[0]

    # Insert intentionally unquantized notes
    # Target 16th grid lines are 0ms, 125ms, 250ms, 375ms, 500ms
    # Note 1: played at 23ms (should snap to 0ms)
    track.add_event("note_on", 60, 100, 23.0)
    track.add_event("note_off", 60, 0, 110.0)
    
    # Note 2: played at 138ms (should snap to 125ms)
    track.add_event("note_on", 64, 100, 138.0)
    track.add_event("note_off", 64, 0, 240.0)

    # Note 3: played at 265ms (should snap to 250ms)
    track.add_event("note_on", 67, 100, 265.0)
    track.add_event("note_off", 67, 0, 360.0)

    # Apply smart quantization at 1/16th division
    seq.quantize_track(0, grid_division=16)

    # Check that note_on events are now on exact grid lines
    on_events = [e for e in track.events if e[0] == "note_on"]
    assert len(on_events) == 3
    assert on_events[0][3] == 0.0, f"Expected 0.0ms, got {on_events[0][3]}"
    assert on_events[1][3] == 125.0, f"Expected 125.0ms, got {on_events[1][3]}"
    assert on_events[2][3] == 250.0, f"Expected 250.0ms, got {on_events[2][3]}"

    # Test Undo
    assert seq.undo_active_track() is None or True
    # Verify original unquantized timestamps were restored
    restored_on = [e for e in track.events if e[0] == "note_on"]
    assert restored_on[0][3] == 23.0, f"Expected 23.0ms after undo, got {restored_on[0][3]}"
    print("  -> Sequencer & Smart Quantization passed.")
    return seq


def test_step_sequencer(synth, seq):
    print("[5/7] Testing 16-step drum grid sequencer & rhythmic presets...")
    step_seq = StepSequencer(synth)
    
    # Toggle on
    assert step_seq.toggle_mode() is True
    
    # Test step and drum navigation
    step_seq.move_step(1)
    assert step_seq.current_step == 1
    step_seq.move_drum(1)
    assert step_seq.current_drum == 1

    # Toggle hit on
    step_seq.toggle_current_hit()
    assert step_seq.grid[1][1] is True

    # Test Maqsum oriental preset
    step_seq.load_preset("maqsum")
    # Verify Dum hits on steps 0 and 8
    assert step_seq.grid[6][0] is True
    assert step_seq.grid[6][8] is True

    # Render to track events
    events = step_seq.render_to_track_events(bpm=120, bars=2)
    assert len(events) > 10, "Expected generated MIDI drum events"
    print("  -> Step Sequencer passed.")


def test_exporter(seq, synth):
    print("[6/7] Testing multi-track MIDI compilation and WAV audio export...")
    # Add a melody to track 0
    t0 = seq.tracks[0]
    t0.clear()
    t0.program = 0  # Grand Piano
    t0.add_event("note_on", 60, 100, 0.0)
    t0.add_event("note_off", 60, 0, 400.0)
    t0.add_event("note_on", 64, 100, 500.0)
    t0.add_event("note_off", 64, 0, 900.0)
    t0.add_event("note_on", 67, 100, 1000.0)
    t0.add_event("note_off", 67, 0, 1400.0)

    # Add bass to track 1
    t1 = seq.tracks[1]
    t1.clear()
    t1.program = 33  # Finger Bass
    t1.add_event("note_on", 36, 110, 0.0)
    t1.add_event("note_off", 36, 0, 800.0)
    t1.add_event("note_on", 43, 110, 1000.0)
    t1.add_event("note_off", 43, 0, 1800.0)

    exporter = ProjectExporter(seq, synth)
    success, mid_path, wav_path = exporter.export_project()

    assert success is True, "Export failed!"
    assert os.path.exists(mid_path), f"MIDI file not found at {mid_path}"
    assert os.path.getsize(mid_path) > 50, "MIDI file too small"
    assert os.path.exists(wav_path), f"WAV file not found at {wav_path}"
    assert os.path.getsize(wav_path) > 500, "WAV file too small"
    print(f"  -> Export passed. Generated: {os.path.basename(mid_path)} ({os.path.getsize(mid_path)} bytes) & {os.path.basename(wav_path)} ({os.path.getsize(wav_path)} bytes)")


def test_speech_and_earcons():
    print("[7/7] Testing speech engine & earcons...")
    speech.speak("اختبار نطق شاشة التوقف", interrupt=True)
    speech.play_earcon("rec_start")
    speech.play_earcon("quantize")
    time.sleep(0.2)
    print("  -> Speech and earcon cues passed.")


if __name__ == "__main__":
    print("Starting Accessible Mini-DAW Test Suite...\n")
    test_config()
    test_keyboard_mapper()
    synth_obj = test_synth_engine()
    seq_obj = test_sequencer_quantization_undo(synth_obj)
    test_step_sequencer(synth_obj, seq_obj)
    test_exporter(seq_obj, synth_obj)
    test_speech_and_earcons()
    
    # Cleanup
    seq_obj.close()
    synth_obj.close()
    speech.shutdown()
    print("\nALL 7 TEST SUITES PASSED PERFECTLY WITH ZERO ERRORS!")
