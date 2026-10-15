"""
AccessibleStudio - Main Application Entry Point
==============================================
Production standalone Digital Audio Workstation for blind musicians.
Initializes logging, audio synthesis, multi-track sequencing, screen reader
bridge, and the native accessible desktop window.
"""

import os
import sys
import datetime
import traceback

# Ensure application search path includes current directory
app_dir = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    app_dir = os.path.dirname(sys.executable)
    os.chdir(app_dir)

sys.path.insert(0, app_dir)

from accessible_studio.config import STRINGS, DEFAULT_OCTAVE, DEFAULT_VELOCITY
from accessible_studio.accessibility.speech import speech
from accessible_studio.accessibility.piano_keys import PianoKeyboardMapper
from accessible_studio.core.midi_synth import MidiSynthEngine
from accessible_studio.core.sequencer import Sequencer
from accessible_studio.core.drum_grid import DrumGridSequencer
from accessible_studio.core.exporter import ProjectExporter
from accessible_studio.ui.main_window import AccessibleStudioWindow


def setup_diagnostics():
    """Sets up dual logging to studio_debug.log and console."""
    log_file_path = os.path.join(app_dir, "studio_debug.log")
    try:
        log_f = open(log_file_path, "a", encoding="utf-8")
        class DualWriter:
            def __init__(self, orig_stream, log):
                self.orig = orig_stream
                self.log = log
            def write(self, s):
                if self.orig:
                    try: self.orig.write(s)
                    except Exception: pass
                try:
                    self.log.write(s)
                    self.log.flush()
                except Exception: pass
            def flush(self):
                if self.orig:
                    try: self.orig.flush()
                    except Exception: pass
                try: self.log.flush()
                except Exception: pass

        sys.stdout = DualWriter(sys.stdout, log_f)
        sys.stderr = DualWriter(sys.stderr, log_f)
    except Exception:
        pass


def main():
    setup_diagnostics()
    print("=" * 60)
    print(f"[{datetime.datetime.now()}] AccessibleStudio v2.0 Starting...")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {app_dir}")
    print("=" * 60)

    try:
        # 1. Initialize Audio Synth Engine
        synth = MidiSynthEngine()

        # 2. Connect Earcon Callbacks to Speech Engine
        speech.set_synth_callbacks(synth.note_on, synth.note_off)

        # 3. Initialize Musical Keyboard Matrix
        keyboard = PianoKeyboardMapper(base_octave=DEFAULT_OCTAVE, base_velocity=DEFAULT_VELOCITY)

        # 4. Initialize Multi-Track Sequencer
        sequencer = Sequencer(synth, num_tracks=8)

        # 5. Initialize 16-Step Drum Grid
        drum_grid = DrumGridSequencer(synth)

        # 6. Initialize Project Exporter
        exporter = ProjectExporter(sequencer, synth)

        # 7. Launch Native Accessible Desktop Window
        app_window = AccessibleStudioWindow(
            sequencer=sequencer,
            synth_engine=synth,
            drum_grid=drum_grid,
            keyboard_mapper=keyboard,
            exporter=exporter
        )
        app_window.run()

    except Exception as err:
        crash_log = os.path.join(app_dir, "crash.log")
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now()}] CRITICAL RUNTIME ERROR:\n")
            traceback.print_exc(file=f)
        print(f"[FATAL ERROR]: {err}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
