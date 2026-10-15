"""
AccessibleStudio Pro - Automated Comprehensive Test Suite
==========================================================
Verifies all modules: configuration, dual-engine sound synthesis,
Arabic microtonal maqamat, piano keyboard mapping, 8-track sequencer,
smart quantization, undo/redo, 16-step drum machine, session persistence,
and multi-track MIDI & master WAV audio export.
"""

import os
import sys
import time

# Ensure headless operation for CI runners without physical display or audio hardware
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import pygame
pygame.mixer.pre_init(config.SAMPLE_RATE, -16, 2, config.AUDIO_BUFFER)
pygame.init()
if not pygame.mixer.get_init():
    try:
        pygame.mixer.init(frequency=config.SAMPLE_RATE, size=-16, channels=2, buffer=config.AUDIO_BUFFER)
    except Exception as e:
        print(f"[Warning] Pygame mixer init in test: {e}")

from speech_engine import SpeechEngine
from synth_engine import SynthEngine
from keyboard_mapper import KeyboardMapper
from sequencer import Sequencer
from step_sequencer import StepSequencer
from exporter import StudioExporter


def test_config():
    print("[1/7] Testing configuration, GM instruments, and Arabic Maqamat...")
    assert len(config.GM_INSTRUMENTS) == 128, f"Expected 128 GM instruments, got {len(config.GM_INSTRUMENTS)}"
    assert len(config.GM_FAMILIES) == 16, f"Expected 16 GM families, got {len(config.GM_FAMILIES)}"
    assert len(config.MAQAMAT) >= 6, "Expected at least 6 Arabic maqamat"
    assert len(config.DRUM_PIECES) >= 9, "Expected at least 9 drum/percussion pieces"
    assert len(config.RHYTHM_PRESETS) >= 8, "Expected at least 8 rhythm presets"
    assert len(config.CHORD_MODES) >= 5, "Expected at least 5 chord modes"

    # Verify Maqam Rast quarter-tones (-50 cents on degrees 4 and 11)
    rast = next(m for m in config.MAQAMAT if "Rast" in m["name_en"])
    assert rast["cents"][4] == -50.0, "Degree 4 (E-half-flat) in Rast should be -50 cents"
    assert rast["cents"][11] == -50.0, "Degree 11 (B-half-flat) in Rast should be -50 cents"
    print("  -> Configuration & Maqamat database verified.")


def test_keyboard_mapper(synth):
    print("[2/7] Testing keyboard mapper, octave shift, and chord modes...")
    mapper = KeyboardMapper()
    assert mapper.base_octave == 4
    assert mapper.transpose == 0

    # Middle C (Z key -> offset 0 in octave 4 -> MIDI 60)
    notes_z = mapper.get_midi_notes(pygame.K_z, is_drum_track=False)
    assert notes_z == [60], f"Expected [60] for 'Z' key in octave 4, got {notes_z}"

    # Upper octave C5 (Q key -> offset 12 -> MIDI 72)
    notes_q = mapper.get_midi_notes(pygame.K_q, is_drum_track=False)
    assert notes_q == [72], f"Expected [72] for 'Q' key, got {notes_q}"

    # Octave shift (+1) -> Z should become 72
    mapper.shift_octave(1, synth)
    assert mapper.base_octave == 5
    assert mapper.get_midi_notes(pygame.K_z, is_drum_track=False) == [72]

    # Reset octave
    mapper.shift_octave(-1, synth)
    assert mapper.base_octave == 4

    # Transpose (+2 semitones -> D)
    mapper.shift_transpose(2, synth)
    assert mapper.transpose == 2
    assert mapper.get_midi_notes(pygame.K_z, is_drum_track=False) == [62]
    mapper.shift_transpose(-2, synth)

    # Chord mode (Major Triad)
    mapper.chord_mode_idx = 2  # Major Triad [0, 4, 7]
    chord_notes = mapper.get_midi_notes(pygame.K_z, is_drum_track=False)
    assert chord_notes == [60, 64, 67], f"Expected C Major Triad [60, 64, 67], got {chord_notes}"
    mapper.chord_mode_idx = 0  # Reset to Single Note

    # Drum track mapping (Track 8)
    drum_notes = mapper.get_midi_notes(pygame.K_z, is_drum_track=True)
    assert drum_notes == [36], f"Expected Kick drum (36) on 'Z', got {drum_notes}"

    print("  -> Keyboard mapper verified.")
    return mapper


def test_synth_engine():
    print("[3/7] Testing dual synthesis engine (Software Physical Synthesis & Microtuning)...")
    synth = SynthEngine()

    # Test Maqam microtuning cent offsets
    synth.set_maqam(1)  # Maqam Rast
    # E4 is MIDI 64. Root C=60 -> degree = 4 -> offset should be -50.0 cents
    cent_e = synth.get_cent_offset(64, channel=0)
    assert cent_e == -50.0, f"Expected -50 cents for degree 4 in Rast, got {cent_e}"

    # Channel 9 (Drums) should have 0 cent offset always
    cent_drum = synth.get_cent_offset(64, channel=9)
    assert cent_drum == 0.0, "Drums should never be detuned"

    # Test pure physical wave synthesis for various instrument families
    sr = config.SAMPLE_RATE
    dur = 0.15

    # 1. Piano
    wave_piano = synth.synthesize_wave(channel=0, program=0, note=60, duration=dur, sample_rate=sr)
    assert len(wave_piano) > 0 and abs(wave_piano.max()) > 0.01, "Piano waveform generation failed"

    # 2. Plucked Strings / Oud (Karplus-Strong)
    wave_oud = synth.synthesize_wave(channel=0, program=105, note=60, duration=dur, sample_rate=sr)
    assert len(wave_oud) > 0 and abs(wave_oud.max()) > 0.01, "Oud waveform generation failed"

    # 3. Flute / Nay (Filtered breath noise)
    wave_nay = synth.synthesize_wave(channel=0, program=75, note=60, duration=dur, sample_rate=sr)
    assert len(wave_nay) > 0 and abs(wave_nay.max()) > 0.01, "Nay waveform generation failed"

    # 4. Oriental Dum Percussion (Channel 9, Note 61)
    wave_dum = synth.synthesize_wave(channel=9, program=0, note=61, duration=dur, sample_rate=sr)
    assert len(wave_dum) > 0 and abs(wave_dum.max()) > 0.01, "Dum percussion waveform generation failed"

    # 5. Oriental Tak Percussion (Channel 9, Note 60)
    wave_tak = synth.synthesize_wave(channel=9, program=0, note=60, duration=dur, sample_rate=sr)
    assert len(wave_tak) > 0 and abs(wave_tak.max()) > 0.01, "Tak percussion waveform generation failed"

    print("  -> Physical audio synthesis & microtuning verified.")
    return synth


def test_sequencer_and_quantize(synth, speech):
    print("[4/7] Testing 8-track sequencer, playback, and smart quantization...")
    seq = Sequencer(synth, speech)
    assert len(seq.tracks) == 8
    assert seq.tracks[7].channel == 9  # Track 8 is drums
    assert seq.bpm == 120

    tr = seq.active_track
    # Add unquantized notes
    # At 120 BPM, 1 beat = 0.5s. 1/16 note = 0.125s.
    tr.events.append({"type": "note_on", "note": 60, "vel": 100, "time": 0.024})
    tr.events.append({"type": "note_off", "note": 60, "vel": 0, "time": 0.118})
    tr.events.append({"type": "note_on", "note": 64, "vel": 95, "time": 0.138})
    tr.events.append({"type": "note_off", "note": 64, "vel": 0, "time": 0.245})

    # Quantize to 1/16 note (idx 2 in config.QUANTIZE_DIVISIONS)
    seq.quantize_div_idx = 2  # 16th note
    seq.quantize_active_track()

    # Note 1 (at 0.024s) should snap to 0.0s
    assert tr.events[0]["time"] == 0.0, f"Quantization failed: expected 0.0s, got {tr.events[0]['time']}"
    # Note 2 (at 0.138s) should snap to 0.125s
    assert abs(tr.events[2]["time"] - 0.125) < 0.001, f"Quantization failed: expected 0.125s, got {tr.events[2]['time']}"

    # Test Undo
    seq.undo()
    assert tr.events[0]["time"] == 0.024, "Undo did not restore original unquantized timestamp"

    # Test Redo
    seq.redo()
    assert tr.events[0]["time"] == 0.0, "Redo did not re-apply quantization"

    print("  -> Sequencer & Smart Quantization verified.")
    return seq


def test_step_sequencer(seq, synth, speech):
    print("[5/7] Testing 16-step oriental drum sequencer and rhythm presets...")
    step_seq = StepSequencer(seq, synth, speech)

    # Load Egyptian Maqsum preset
    step_seq.load_next_preset()  # loads preset 0: Maqsum
    assert step_seq.preset_idx == 0

    # Maqsum has Dum on step 0
    assert step_seq.grid[61][0] > 0, "Maqsum should have Dum on step 1"
    # Maqsum has Tak on step 4
    assert step_seq.grid[60][4] > 0, "Maqsum should have Tak on beat 2 (step 5)"

    # Sync to Track 8
    step_seq.sync_to_drum_track()
    drum_tr = seq.tracks[7]
    assert len(drum_tr.events) > 0, "Drum track events should be populated from 16-step grid"
    assert drum_tr.events[0]["type"] == "note_on"
    assert drum_tr.events[0]["note"] == 61

    print("  -> 16-step drum sequencer & rhythm presets verified.")
    return step_seq


def test_session_persistence(seq):
    print("[6/7] Testing JSON project session persistence...")
    test_session_file = "test_session_temp.json"
    try:
        seq.save_session(test_session_file)
        assert os.path.exists(test_session_file), "Session file was not created"

        # Modify active track
        orig_events_len = len(seq.tracks[7].events)
        seq.tracks[7].events.clear()
        assert len(seq.tracks[7].events) == 0

        # Load session
        seq.load_session(test_session_file)
        assert len(seq.tracks[7].events) == orig_events_len, "Session load did not restore track events"
        print("  -> Session persistence verified.")
    finally:
        if os.path.exists(test_session_file):
            os.remove(test_session_file)


def test_export_pipeline(seq, synth, speech):
    print("[7/7] Testing multi-track MIDI compilation & Master WAV audio export...")
    os.makedirs(config.EXPORT_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    mid_path = os.path.join(config.EXPORT_DIR, f"test_project_{timestamp}.mid")
    wav_path = os.path.join(config.EXPORT_DIR, f"test_project_{timestamp}.wav")

    try:
        # Export MIDI
        StudioExporter.export_midi(seq, synth, mid_path)
        assert os.path.exists(mid_path), "MIDI export file was not created"
        mid_size = os.path.getsize(mid_path)
        assert mid_size > 50, f"MIDI file suspiciously small ({mid_size} bytes)"

        # Export Master WAV Audio
        StudioExporter.export_wav(seq, synth, wav_path)
        assert os.path.exists(wav_path), "Master WAV export file was not created"
        wav_size = os.path.getsize(wav_path)
        assert wav_size > 1000, f"Master WAV file suspiciously small ({wav_size} bytes)"

        print(f"  -> Export successful! MIDI: {mid_size} bytes, Master WAV: {wav_size} bytes.")
    finally:
        if os.path.exists(mid_path):
            os.remove(mid_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)


if __name__ == "__main__":
    print("============================================================")
    print("AccessibleStudio Pro Automated Test Suite")
    print("============================================================\n")

    speech_inst = SpeechEngine(lang="ar")
    synth_inst = test_synth_engine()
    test_config()
    test_keyboard_mapper(synth_inst)
    seq_inst = test_sequencer_and_quantize(synth_inst, speech_inst)
    test_step_sequencer(seq_inst, synth_inst, speech_inst)
    test_session_persistence(seq_inst)
    test_export_pipeline(seq_inst, synth_inst, speech_inst)

    synth_inst.shutdown()
    speech_inst.shutdown()
    pygame.quit()

    print("\n============================================================")
    print("ALL 7 TEST SUITES PASSED SUCCESSFULLY WITH ZERO ERRORS!")
    print("============================================================")
