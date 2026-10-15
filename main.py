"""
Accessible Desktop Mini-DAW & Live Musical Instrument Studio
============================================================
Specifically engineered for blind and visually impaired musicians.
100% accessible via screen readers (NVDA, JAWS, SAPI, Linux speech-dispatcher)
and auditory Earcons. Built with Pygame event loop, FluidSynth 16-channel mixing,
multi-track recording, smart quantization, and 16-step drum grid sequencer.
"""

import os
import sys
import time

# Ensure dependencies search from current script directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    STRINGS,
    DEFAULT_BPM,
    DEFAULT_OCTAVE,
    DEFAULT_VELOCITY,
    MAX_TRACKS,
    GM_INSTRUMENTS
)
from speech_engine import speech
from synth_engine import SynthEngine
from keyboard_mapper import KeyboardMapper
from sequencer import Sequencer
from step_sequencer import StepSequencer
PYGAME_AVAILABLE = False
PYGAME_IMPORT_ERROR = None
try:
    import pygame
    PYGAME_AVAILABLE = True
except Exception as err:
    PYGAME_IMPORT_ERROR = err
    class _DummyPygame:
        class event:
            Event = object
            @staticmethod
            def get(): return []
        class key:
            @staticmethod
            def get_mods(): return 0
            @staticmethod
            def name(k): return str(k)
        KMOD_CTRL, KMOD_ALT, KMOD_SHIFT = 64, 256, 1
        K_F1, K_F2, K_F3, K_F4, K_F5, K_F6, K_F7, K_F8, K_F9, K_F10, K_F11, K_F12 = range(282, 294)
        K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8 = range(49, 57)
        K_SPACE, K_r, K_m, K_s, K_l, K_q, K_c, K_d, K_k, K_ESCAPE, K_RETURN = 32, 114, 109, 115, 108, 113, 99, 100, 107, 27, 13
        K_UP, K_DOWN, K_LEFT, K_RIGHT = 273, 274, 276, 277
        K_PAGEUP, K_PAGEDOWN, K_HOME, K_END = 280, 281, 278, 279
        K_TAB, K_LEFTBRACKET, K_RIGHTBRACKET = 9, 91, 93
        QUIT, KEYDOWN, KEYUP = 12, 2, 3
        @staticmethod
        def init(): pass
        @staticmethod
        def quit(): pass
        class display:
            @staticmethod
            def set_mode(size): return None
            @staticmethod
            def set_caption(c): pass
            @staticmethod
            def flip(): pass
        class time:
            class Clock:
                def tick(self, fps=120): pass
    pygame = _DummyPygame()

from exporter import ProjectExporter


class AccessibleDAWApp:
    """Main Application Controller & Real-Time Event Loop."""

    def __init__(self, soundfont_path=None):
        print("=" * 60)
        print("Accessible Mini-DAW Studio for Blind Musicians")
        print("Screen-reader-first architecture with bilingual speech & Earcons")
        print("=" * 60)

        # 1. Initialize Audio Synthesis Engine
        self.synth = SynthEngine(soundfont_path=soundfont_path)

        # 2. Connect Speech Engine to Synth for Auditory Earcons
        speech.set_synth_callbacks(self.synth.note_on, self.synth.note_off)

        # 3. Initialize Keyboard Mapper (2-octave QWERTY layout)
        self.keyboard = KeyboardMapper(base_octave=DEFAULT_OCTAVE, base_velocity=DEFAULT_VELOCITY)

        # 4. Initialize Multi-Track Sequencer
        self.sequencer = Sequencer(self.synth)

        # 5. Initialize 16-Step Drum Grid Sequencer
        self.step_sequencer = StepSequencer(self.synth)

        # 6. Initialize MIDI & WAV Exporter
        self.exporter = ProjectExporter(self.sequencer, self.synth)

        self.running = True
        self.is_headless = False
        self.help_mode = False

    def setup_display(self):
        """Initializes Pygame window to capture keyboard events with zero display dependency."""
        if not PYGAME_AVAILABLE:
            self.is_headless = True
            return

        try:
            # Check if running without graphical display server
            if "DISPLAY" not in os.environ and "WAYLAND_DISPLAY" not in os.environ and sys.platform != "win32":
                os.environ["SDL_VIDEODRIVER"] = "dummy"
                self.is_headless = True

            pygame.init()
            pygame.display.set_caption("Accessible Mini-DAW Studio")
            
            # High-contrast accessible window (800x480)
            if not self.is_headless:
                self.screen = pygame.display.set_mode((800, 480))
            else:
                self.screen = pygame.display.set_mode((1, 1))

            self.clock = pygame.time.Clock()
            print("[AccessibleDAWApp] Pygame input matrix initialized successfully.")
        except Exception as e:
            print(f"[AccessibleDAWApp] Pygame initialization fallback: {e}")
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.init()
            self.screen = pygame.display.set_mode((1, 1))
            self.clock = pygame.time.Clock()
            self.is_headless = True

    def announce_welcome(self):
        """Speaks initial welcome message and status to the screen reader."""
        welcome_text = speech.get_text("welcome")
        speech.speak(welcome_text, interrupt=True)

    def run_windows_console_fallback(self):
        """Zero-dependency Windows keyboard polling loop using GetAsyncKeyState."""
        print(f"[AccessibleDAWApp] Pygame graphical subsystem bypassed ({PYGAME_IMPORT_ERROR}).")
        print("[AccessibleDAWApp] Running in High-Precision Windows Native Keyboard Engine...")
        self.announce_welcome()
        print("\nStudio ready. Playing notes via QWERTY keyboard in Windows Native Mode.\nPress F1 for shortcuts manual.\n")

        try:
            import ctypes
            user32 = ctypes.windll.user32
        except Exception as e:
            print(f"[AccessibleDAWApp] Native Windows API unavailable: {e}")
            return

        VK_MAP = {
            0x5A: ("z", pygame.K_z),
            0x53: ("s", pygame.K_s),
            0x58: ("x", pygame.K_x),
            0x44: ("d", pygame.K_d),
            0x43: ("c", pygame.K_c),
            0x56: ("v", pygame.K_v),
            0x47: ("g", pygame.K_g),
            0x42: ("b", pygame.K_b),
            0x48: ("h", pygame.K_h),
            0x4E: ("n", pygame.K_n),
            0x4A: ("j", pygame.K_j),
            0x4D: ("m", pygame.K_m),
            0x51: ("q", pygame.K_q),
            0x32: ("2", pygame.K_2),
            0x57: ("w", pygame.K_w),
            0x33: ("3", pygame.K_3),
            0x45: ("e", pygame.K_e),
            0x52: ("r", pygame.K_r),
            0x35: ("5", pygame.K_5),
            0x54: ("t", pygame.K_t),
            0x36: ("6", pygame.K_6),
            0x59: ("y", pygame.K_y),
            0x37: ("7", pygame.K_7),
            0x55: ("u", pygame.K_u),
            0x49: ("i", pygame.K_i),
            0x20: ("space", pygame.K_SPACE),
            0x1B: ("escape", pygame.K_ESCAPE),
            0x21: ("pageup", pygame.K_PAGEUP),
            0x22: ("pagedown", pygame.K_PAGEDOWN),
            0x24: ("home", pygame.K_HOME),
            0x23: ("end", pygame.K_END),
            0x26: ("up", pygame.K_UP),
            0x28: ("down", pygame.K_DOWN),
            0x25: ("left", pygame.K_LEFT),
            0x27: ("right", pygame.K_RIGHT),
            0x09: ("tab", pygame.K_TAB),
            0x4C: ("l", pygame.K_l),
            0x4B: ("k", pygame.K_k),
            0x31: ("1", pygame.K_1),
            0x33: ("3", pygame.K_3),
            0x34: ("4", pygame.K_4),
            0x38: ("8", pygame.K_8),
            0x70: ("f1", pygame.K_F1),
            0x71: ("f2", pygame.K_F2),
            0x72: ("f3", pygame.K_F3),
            0x73: ("f4", pygame.K_F4),
            0x74: ("f5", pygame.K_F5),
            0x75: ("f6", pygame.K_F6),
            0x76: ("f7", pygame.K_F7),
            0x77: ("f8", pygame.K_F8),
            0x78: ("f9", pygame.K_F9),
            0x79: ("f10", pygame.K_F10),
            0x7A: ("f11", pygame.K_F11),
            0x7B: ("f12", pygame.K_F12),
        }

        pressed = set()
        class KeyEvent:
            def __init__(self, k, u=""):
                self.key = k
                self.unicode = u

        while self.running:
            time.sleep(0.005)
            for vk, (char_repr, py_key) in VK_MAP.items():
                is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                if is_down and vk not in pressed:
                    pressed.add(vk)
                    self.handle_key_down(KeyEvent(py_key, char_repr if len(char_repr) == 1 else ""))
                elif not is_down and vk in pressed:
                    pressed.remove(vk)
                    self.handle_key_up(KeyEvent(py_key, char_repr if len(char_repr) == 1 else ""))

        self.shutdown()

    def run(self):
        """Main event polling loop running at low-latency 120 FPS."""
        if not PYGAME_AVAILABLE:
            if sys.platform == "win32":
                self.run_windows_console_fallback()
                return
            else:
                print(f"[AccessibleDAWApp] Error: Pygame library failed to load ({PYGAME_IMPORT_ERROR}).")
                return

        self.setup_display()
        self.announce_welcome()

        print("\nStudio ready. Playing notes via QWERTY keyboard. Press F1 for shortcuts manual.\n")

        while self.running:
            # Poll at 120 Hz for sub-10ms keyboard latency
            self.clock.tick(120)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break

                elif event.type == pygame.KEYDOWN:
                    self.handle_key_down(event)

                elif event.type == pygame.KEYUP:
                    self.handle_key_up(event)

            # Optional visual rendering for sighted teachers/collaborators
            if not self.is_headless and self.screen:
                self._render_accessible_screen()

        self.shutdown()

    # -----------------------------------------------------------------------
    # Accessible Key Down Dispatcher
    # -----------------------------------------------------------------------
    def handle_key_down(self, event):
        """Routes keyboard events between Step Sequencer, Musical Matrix, and Transport."""
        key = event.key
        mods = pygame.key.get_mods()
        shift = bool(mods & pygame.KMOD_SHIFT)
        ctrl = bool(mods & pygame.KMOD_CTRL)

        # -------------------------------------------------------------------
        # Global Hotkeys (F1 to F12, Escape)
        # -------------------------------------------------------------------
        if key == pygame.K_F1:
            if shift:
                # Read full manual
                speech.speak(speech.get_text("help_title") + " " + speech.get_text("help_body"), interrupt=True)
            else:
                self.help_mode = not self.help_mode
                lang = speech.get_language()
                if self.help_mode:
                    speech.play_earcon("boundary")
                    msg = "تم تفعيل نمط دليل المفاتيح التفاعلي. اضغط على أي زر لسماع وظيفته الموسيقية، واضغط إف واحد مجدداً للعودة للعزف." if lang == "ar" else "Interactive Help Mode active. Press any key to hear what it does. Press F1 again to exit."
                    speech.speak(msg, interrupt=True)
                else:
                    speech.play_earcon("boundary")
                    msg = "تم إنهاء نمط دليل المفاتيح. الاستوديو جاهز للعزف والتسجيل." if lang == "ar" else "Exited Help Mode. Studio is ready for live play."
                    speech.speak(msg, interrupt=True)
            return

        if self.help_mode:
            self.speak_key_help(key, ctrl, shift, event)
            return

        elif key == pygame.K_F2:
            # Read current active track info
            self.sequencer.announce_track_info()
            return

        elif key == pygame.K_F3:
            # Toggle audible Metronome click
            self.sequencer.toggle_metronome()
            return

        elif key == pygame.K_F4:
            # Read BPM tempo
            speech.speak(speech.get_text("tempo_changed", bpm=self.sequencer.bpm), interrupt=True)
            return

        elif key == pygame.K_F5:
            # Toggle 16-Step Drum Grid Mode
            self.step_sequencer.toggle_mode()
            return

        elif key == pygame.K_F6:
            # Quantize active track
            self.sequencer.quantize_track(self.sequencer.active_track_idx, grid_division=16)
            return

        elif key == pygame.K_F7:
            # Solo active track
            self.sequencer.toggle_track_solo()
            return

        elif key == pygame.K_F8:
            # Mute active track
            self.sequencer.toggle_track_mute()
            return

        elif key == pygame.K_F9:
            # Undo last pass on active track
            self.sequencer.undo_active_track()
            return

        elif key == pygame.K_F10:
            # Clear active track notes
            self.sequencer.clear_active_track()
            return

        elif key == pygame.K_F11:
            # Export project to MIDI and WAV
            self.exporter.export_project()
            return

        elif key == pygame.K_F12:
            # Switch Language (Arabic <-> English)
            speech.toggle_language()
            return

        elif key == pygame.K_ESCAPE:
            # Emergency MIDI Silence / Exit drum mode
            if self.step_sequencer.is_active:
                self.step_sequencer.toggle_mode()
            else:
                self.synth.panic()
                self.keyboard.release_all_keys()
                speech.speak(speech.get_text("panic"), interrupt=True)
            return

        # -------------------------------------------------------------------
        # 16-Step Drum Grid Mode Handlers
        # -------------------------------------------------------------------
        if self.step_sequencer.is_active:
            if key == pygame.K_LEFT:
                self.step_sequencer.move_step(-1)
                return
            elif key == pygame.K_RIGHT:
                self.step_sequencer.move_step(1)
                return
            elif key == pygame.K_UP:
                self.step_sequencer.move_drum(-1)
                return
            elif key == pygame.K_DOWN:
                self.step_sequencer.move_drum(1)
                return
            elif key == pygame.K_SPACE:
                self.step_sequencer.toggle_current_hit()
                return
            elif key == pygame.K_c and ctrl:
                self.step_sequencer.clear_grid()
                return
            # Preset rhythms in drum mode
            elif key == pygame.K_m and ctrl:
                self.step_sequencer.load_preset("maqsum")
                return
            elif key == pygame.K_d and ctrl:
                self.step_sequencer.load_preset("four_on_floor")
                return
            elif key == pygame.K_k and ctrl:
                self.step_sequencer.load_preset("rock")
                return
            elif key == pygame.K_RETURN:
                # Transfer drum grid into user track
                events = self.step_sequencer.render_to_track_events(self.sequencer.bpm, bars=4)
                target_track = self.sequencer.tracks[self.sequencer.active_track_idx]
                target_track.save_undo_state()
                target_track.events = events
                lang = speech.get_language()
                msg = f"تم نقل إيقاع الدرامز إلى المسار {self.sequencer.active_track_idx + 1}" if lang == "ar" else f"Copied drum pattern to Track {self.sequencer.active_track_idx + 1}"
                speech.speak(msg, interrupt=True)
                return

        # -------------------------------------------------------------------
        # Normal Studio Mode Handlers
        # -------------------------------------------------------------------
        # Track Selection (Keys 1 through 8)
        if pygame.K_1 <= key <= pygame.K_8:
            track_num = key - pygame.K_1
            self.sequencer.select_track(track_num)
            return

        # Transport: Spacebar (Play/Stop)
        if key == pygame.K_SPACE:
            self.sequencer.toggle_play_stop()
            return

        # Transport: R (Record with 4-beat count-in)
        if key == pygame.K_r:
            if self.sequencer.state != Sequencer.RECORDING and self.sequencer.state != Sequencer.COUNTING_IN:
                self.sequencer.start_recording()
            else:
                self.sequencer.stop()
            return

        # Transport: L (Toggle Loop Mode)
        if key == pygame.K_l:
            self.sequencer.toggle_loop()
            return

        # Instrument Program Switching (Tab / Shift+Tab)
        if key == pygame.K_TAB:
            delta = -1 if shift else 1
            self.sequencer.change_track_program(delta)
            return

        # Track Volume Adjust (Up / Down)
        if key == pygame.K_UP:
            self.sequencer.adjust_track_volume(5)
            return
        elif key == pygame.K_DOWN:
            self.sequencer.adjust_track_volume(-5)
            return

        # Track Stereo Panning (Left / Right) or Category Jump (Ctrl + Left / Right)
        if key == pygame.K_LEFT:
            if ctrl:
                self.sequencer.change_track_program(-8)
            else:
                self.sequencer.adjust_track_pan(-5)
            return
        elif key == pygame.K_RIGHT:
            if ctrl:
                self.sequencer.change_track_program(8)
            else:
                self.sequencer.adjust_track_pan(5)
            return

        # Octave Shift (PageUp / PageDown)
        if key == pygame.K_PAGEUP:
            octave, changed = self.keyboard.octave_up()
            if changed:
                speech.speak(speech.get_text("octave_changed", octave=octave), interrupt=True)
            else:
                speech.play_earcon("boundary")
            return
        elif key == pygame.K_PAGEDOWN:
            octave, changed = self.keyboard.octave_down()
            if changed:
                speech.speak(speech.get_text("octave_changed", octave=octave), interrupt=True)
            else:
                speech.play_earcon("boundary")
            return

        # Velocity Adjust (Home / End)
        if key == pygame.K_HOME:
            vel, changed = self.keyboard.velocity_up(10)
            if changed:
                speech.speak(speech.get_text("velocity_changed", velocity=vel), interrupt=True)
            else:
                speech.play_earcon("boundary")
            return
        elif key == pygame.K_END:
            vel, changed = self.keyboard.velocity_down(10)
            if changed:
                speech.speak(speech.get_text("velocity_changed", velocity=vel), interrupt=True)
            else:
                speech.play_earcon("boundary")
            return

        # Tempo BPM Adjust ([ and ])
        if key == pygame.K_LEFTBRACKET:
            delta = -1 if shift else -5
            self.sequencer.adjust_bpm(delta)
            return
        elif key == pygame.K_RIGHTBRACKET:
            delta = 1 if shift else 5
            self.sequencer.adjust_bpm(delta)
            return

        # Status readout (Enter)
        if key == pygame.K_RETURN:
            bar, beat = self.sequencer.get_bar_beat()
            track_idx = self.sequencer.active_track_idx
            track = self.sequencer.tracks[track_idx]
            inst = GM_INSTRUMENTS[track.program]
            inst_name = inst["ar"] if speech.get_language() == "ar" else inst["en"]
            metro_state = "مفعّل" if self.sequencer.metronome_enabled else "معطّل"
            msg = speech.get_text(
                "status_summary",
                track_num=track_idx + 1,
                inst_name=inst_name,
                bpm=self.sequencer.bpm,
                metronome_state=metro_state,
                bar=bar
            )
            speech.speak(msg, interrupt=True)
            return

        # -------------------------------------------------------------------
        # Musical QWERTY Key Press
        # -------------------------------------------------------------------
        key_char = event.unicode if event.unicode else pygame.key.name(key)
        note_result = self.keyboard.process_key_down(key, key_char)
        if note_result:
            midi_note, velocity = note_result
            self.sequencer.record_note_on(midi_note, velocity)

    # -----------------------------------------------------------------------
    # Accessible Key Up Dispatcher
    # -----------------------------------------------------------------------
    def handle_key_up(self, event):
        """Processes key release to stop musical notes."""
        if self.help_mode:
            return
        midi_note = self.keyboard.process_key_up(event.key)
        if midi_note is not None:
            self.sequencer.record_note_off(midi_note)

    def speak_key_help(self, key, ctrl, shift, event):
        """Speaks the musical studio function of any key pressed in Help Mode."""
        lang = speech.get_language()
        ar = (lang == "ar")

        if key == pygame.K_SPACE:
            speech.speak("مسطرة المسافة: تشغيل وإيقاف المقاطع الموسيقية، أو تفعيل نغمات الدرامز في شبكة الإيقاع" if ar else "Spacebar: Play or Stop playback, or toggle drum hit in grid", interrupt=True)
        elif key == pygame.K_r:
            speech.speak("حرف R: بدء التسجيل الحي على المسار النشط بعد عد تنازلي 4 نبضات" if ar else "R key: Record on active track with 4-beat count-in", interrupt=True)
        elif key == pygame.K_l:
            speech.speak("حرف L: تفعيل أو إيقاف التكرار التلقائي اللوب" if ar else "L key: Toggle loop playback mode", interrupt=True)
        elif key == pygame.K_F1:
            speech.speak("إف 1: الخروج من نمط استكشاف المفاتيح، أو شفت مع إف 1 لقراءة الدليل كاملاً" if ar else "F1: Exit help mode, or Shift+F1 for full manual", interrupt=True)
        elif key == pygame.K_F2:
            speech.speak("إف 2: نطق تفاصيل المسار النشط الآلة والصوت والتوزيع" if ar else "F2: Announce active track details", interrupt=True)
        elif key == pygame.K_F3:
            speech.speak("إف 3: تشغيل أو إيقاف صوت بندول الإيقاع الميترونوم" if ar else "F3: Toggle metronome click", interrupt=True)
        elif key == pygame.K_F4:
            speech.speak("إف 4: نطق سرعة الإيقاع الحالية" if ar else "F4: Announce tempo BPM", interrupt=True)
        elif key == pygame.K_F5:
            speech.speak("إف 5: فتح منظم إيقاع الطبول ذو الستة عشر خطوة" if ar else "F5: Open 16-step drum grid sequencer", interrupt=True)
        elif key == pygame.K_F6:
            speech.speak("إف 6: تصحيح التوقيت وضبط الإيقاع كوانتايز بدقة 1/16" if ar else "F6: Smart quantize track notes to 1/16th grid", interrupt=True)
        elif key == pygame.K_F7:
            speech.speak("إف 7: عزل المسار الحالي وسماعه منفرداً صولو" if ar else "F7: Solo active track", interrupt=True)
        elif key == pygame.K_F8:
            speech.speak("إف 8: كتم صوت المسار الحالي أو إلغاء الكتم" if ar else "F8: Mute/Unmute active track", interrupt=True)
        elif key == pygame.K_F9:
            speech.speak("إف 9: التراجع عن آخر تسجيل في المسار النشط" if ar else "F9: Undo last recording pass on active track", interrupt=True)
        elif key == pygame.K_F10:
            speech.speak("إف 10: مسح جميع النوتات المسجلة في المسار النشط" if ar else "F10: Clear notes on active track", interrupt=True)
        elif key == pygame.K_F11:
            speech.speak("إف 11: تصدير المشروع إلى ملف ميدي وملف صوتي واف" if ar else "F11: Export session to MIDI and WAV audio", interrupt=True)
        elif key == pygame.K_F12:
            speech.speak("إف 12: تبديل لغة النطق بين العربية والإنجليزية" if ar else "F12: Toggle speech language between Arabic and English", interrupt=True)
        elif pygame.K_1 <= key <= pygame.K_8:
            t_num = key - pygame.K_1 + 1
            speech.speak(f"رقم {t_num}: اختيار المسار الموسيقي {t_num}" if ar else f"Number {t_num}: Select track {t_num}", interrupt=True)
        elif key == pygame.K_TAB:
            speech.speak("زر تاب: الانتقال إلى الآلة الموسيقية التالية من بنك الآلات الـ 128، وشفت مع تاب للرجوع للآلة السابقة" if ar else "Tab: Next instrument, Shift+Tab: Previous instrument", interrupt=True)
        elif key == pygame.K_UP:
            speech.speak("سهم أعلى: زيادة مستوى صوت المسار الحالي بمقدار 5 بالمائة، أو اختيار آلة الدرامز السابقة" if ar else "Up Arrow: Increase track volume by 5%, or previous drum sound", interrupt=True)
        elif key == pygame.K_DOWN:
            speech.speak("سهم أسفل: خفض مستوى صوت المسار الحالي بمقدار 5 بالمائة، أو اختيار آلة الدرامز التالية" if ar else "Down Arrow: Decrease track volume by 5%, or next drum sound", interrupt=True)
        elif key == pygame.K_LEFT:
            if ctrl:
                speech.speak("كنترول مع سهم يسار: القفز إلى عائلة الآلات الموسيقية السابقة" if ar else "Ctrl+Left: Jump to previous instrument category", interrupt=True)
            else:
                speech.speak("سهم يسار: توجيه الصوت جهة السماعة اليسرى، أو التحرك للخطوة السابقة في شبكة الدرامز" if ar else "Left Arrow: Pan left, or move to previous step", interrupt=True)
        elif key == pygame.K_RIGHT:
            if ctrl:
                speech.speak("كنترول مع سهم يمين: القفز إلى عائلة الآلات الموسيقية التالية كالأوتار أو النحاسيات" if ar else "Ctrl+Right: Jump to next instrument category", interrupt=True)
            else:
                speech.speak("سهم يمين: توجيه الصوت جهة السماعة اليمنى، أو التحرك للخطوة التالية في شبكة الدرامز" if ar else "Right Arrow: Pan right, or move to next step", interrupt=True)
        elif key == pygame.K_PAGEUP:
            speech.speak("بيج أب: رفع أوكتاف لوحة المفاتيح الموسيقية أوكتاف كامل لأعلى" if ar else "Page Up: Shift musical keyboard up one octave", interrupt=True)
        elif key == pygame.K_PAGEDOWN:
            speech.speak("بيج داون: خفض أوكتاف لوحة المفاتيح الموسيقية أوكتاف كامل لأسفل" if ar else "Page Down: Shift musical keyboard down one octave", interrupt=True)
        elif key == pygame.K_HOME:
            speech.speak("زر هوم: زيادة قوة نقر المفاتيح فيلوستي بمقدار 10" if ar else "Home: Increase touch velocity by 10", interrupt=True)
        elif key == pygame.K_END:
            speech.speak("زر إند: تقليل قوة نقر المفاتيح فيلوستي بمقدار 10" if ar else "End: Decrease touch velocity by 10", interrupt=True)
        elif key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            speech.speak("الأقواس المربعة: تعديل سرعة الإيقاع بي بي إم بمقدار 5 نبضات" if ar else "Square brackets: Adjust tempo BPM by 5", interrupt=True)
        elif key == pygame.K_RETURN:
            speech.speak("زر إنتر: نطق تقرير موقع العزف بالمازورة والنبضة وحالة المسار" if ar else "Enter: Announce playhead bar, beat, and status", interrupt=True)
        elif key == pygame.K_ESCAPE:
            speech.speak("زر الهروب إسكيب: إخماد كافة الأصوات والنغمات فوراً" if ar else "Escape: MIDI panic silence all notes", interrupt=True)
        elif self.keyboard.is_musical_key(event.unicode if event.unicode else pygame.key.name(key)):
            speech.speak("مفتاح نغمة موسيقية لعزف الآلة المحددة حياً عبر أوكتافي الكيبورد" if ar else "Musical key: plays live note on current track", interrupt=True)
        else:
            speech.speak(f"زر: {pygame.key.name(key)}" if ar else f"Key: {pygame.key.name(key)}", interrupt=True)

    # -----------------------------------------------------------------------
    # High-Contrast Visual Screen (Accessible to Low-Vision & Collaborators)
    # -----------------------------------------------------------------------
    def _render_accessible_screen(self):
        """Renders clean, high-contrast visual display (White on Dark Blue)."""
        self.screen.fill((15, 20, 35))  # Deep high-contrast blue background

        # Simple high-contrast font
        font = pygame.font.SysFont("sans-serif", 24)
        small_font = pygame.font.SysFont("sans-serif", 18)

        track_idx = self.sequencer.active_track_idx
        track = self.sequencer.tracks[track_idx]
        inst = GM_INSTRUMENTS[track.program]
        bar, beat = self.sequencer.get_bar_beat()

        # Mode Banner
        if self.step_sequencer.is_active:
            mode_text = font.render("[16-Step Drum Grid Mode Active (F5 to Exit)]", True, (255, 220, 0))
            self.screen.blit(mode_text, (20, 20))
            
            step_str = f"Step: {self.step_sequencer.current_step + 1} / 16"
            drum_str = f"Drum: {self.step_sequencer.instruments[self.step_sequencer.current_drum]['en']}"
            t1 = font.render(step_str, True, (255, 255, 255))
            t2 = font.render(drum_str, True, (100, 230, 255))
            self.screen.blit(t1, (20, 60))
            self.screen.blit(t2, (20, 95))
            
            # Step indicators
            for s in range(16):
                x = 20 + s * 45
                color = (255, 200, 0) if s == self.step_sequencer.current_step else (60, 70, 90)
                is_hit = self.step_sequencer.grid[self.step_sequencer.current_drum][s]
                if is_hit:
                    color = (0, 255, 120)
                pygame.draw.rect(self.screen, color, (x, 140, 38, 38), border_radius=4)
        else:
            state_str = "RECORDING" if self.sequencer.state == Sequencer.RECORDING else ("PLAYING" if self.sequencer.state == Sequencer.PLAYING else "STOPPED")
            title = font.render(f"Accessible Mini-DAW - [{state_str}]", True, (255, 255, 255))
            self.screen.blit(title, (20, 20))

            info_str = f"Track {track_idx + 1}: {inst['en']} ({inst['ar']})"
            t1 = font.render(info_str, True, (100, 220, 255))
            self.screen.blit(t1, (20, 60))

            t2 = font.render(f"Tempo: {self.sequencer.bpm} BPM | Bar: {bar} | Beat: {beat} | Octave: {self.keyboard.base_octave}", True, (255, 255, 255))
            self.screen.blit(t2, (20, 95))

            vol_pct = int((track.volume / 127.0) * 100)
            t3 = font.render(f"Volume: {vol_pct}% | Pan: {track.pan} | Metronome: {'ON' if self.sequencer.metronome_enabled else 'OFF'}", True, (200, 200, 200))
            self.screen.blit(t3, (20, 130))

        # Bottom shortcut hints
        hint = small_font.render("F1: Shortcuts Manual | Space: Play/Stop | R: Record | F5: Drum Grid | F11: Export | F12: Switch Language", True, (170, 180, 200))
        self.screen.blit(hint, (20, 440))

        pygame.display.flip()

    def shutdown(self):
        """Clean shutdown of all audio, sequencer, and speech engines."""
        print("\nShutting down Accessible Mini-DAW Studio...")
        self.sequencer.close()
        self.synth.panic()
        self.synth.close()
        speech.shutdown()
        if PYGAME_AVAILABLE:
            pygame.quit()
        print("Studio closed cleanly. Goodbye!")


if __name__ == "__main__":
    import traceback
    import datetime

    # Ensure working directory is the application directory (critical for PyInstaller bundles)
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
        os.chdir(app_dir)
        sys.path.insert(0, app_dir)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    # Setup diagnostic file logger alongside console output
    log_path = os.path.join(app_dir, "studio_debug.log")
    try:
        log_file = open(log_path, "a", encoding="utf-8")
        class DualLogger:
            def __init__(self, stream, log):
                self.stream = stream
                self.log = log
            def write(self, msg):
                if self.stream:
                    try:
                        self.stream.write(msg)
                    except Exception:
                        pass
                try:
                    self.log.write(msg)
                    self.log.flush()
                except Exception:
                    pass
            def flush(self):
                if self.stream:
                    try:
                        self.stream.flush()
                    except Exception:
                        pass
                try:
                    self.log.flush()
                except Exception:
                    pass
        sys.stdout = DualLogger(sys.stdout, log_file)
        sys.stderr = DualLogger(sys.stderr, log_file)
    except Exception:
        pass

    print(f"\n{'=' * 60}")
    print(f"[{datetime.datetime.now()}] AccessibleStudio Launching...")
    print(f"Python Executable: {sys.executable}")
    print(f"Application Directory: {app_dir}")
    print(f"{'=' * 60}\n")

    app = None
    try:
        sf_arg = sys.argv[1] if len(sys.argv) > 1 else None
        app = AccessibleDAWApp(soundfont_path=sf_arg)
        app.run()
    except KeyboardInterrupt:
        if app:
            app.shutdown()
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[FATAL STARTUP ERROR]:\n{tb}")
        crash_file = os.path.join(app_dir, "crash.log")
        try:
            with open(crash_file, "w", encoding="utf-8") as f:
                f.write(tb)
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"AccessibleStudio encountered a startup error:\n\n{str(e)}\n\nPlease see 'crash.log' or 'studio_debug.log' for details.",
                    "AccessibleStudio - Error",
                    0x10
                )
            except Exception:
                pass
        sys.exit(1)
