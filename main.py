import pygame
import config
from speech_engine import SpeechEngine
from synth_engine import SynthEngine
from keyboard_mapper import KeyboardMapper
from sequencer import Sequencer
from step_sequencer import StepSequencer
from exporter import StudioExporter
from ui_renderer import StudioUIRenderer


class AccessibleStudioApp:
    def __init__(self):
        pygame.mixer.pre_init(config.SAMPLE_RATE, -16, 2, config.AUDIO_BUFFER)
        pygame.init()
        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        pygame.display.set_caption(f"{config.APP_NAME} - استوديو الموسيقى الناطق للمكفوفين")
        self.clock = pygame.time.Clock()

        self.speech = SpeechEngine(lang="ar")
        self.synth = SynthEngine(config.DEFAULT_SF2_PATH)
        self.mapper = KeyboardMapper()
        self.sequencer = Sequencer(self.synth, self.speech)
        self.step_seq = StepSequencer(self.sequencer, self.synth, self.speech)
        self.ui = StudioUIRenderer(self.screen)

        self.help_mode = False
        self.running = True

        engine_mode = "FluidSynth SF2" if self.synth.using_fluidsynth else "محرك التوليف الفيزيائي والشرقي المدمج"
        self.speech.speak(
            f"مرحباً بك في {config.APP_NAME}. يعمل الآن عبر {engine_mode}. "
            "اضغط F1 لدليل المفاتيح التفاعلي، أو ابدأ العزف مباشرة بالحروف."
        )

    def announce_track_status(self, tr):
        if tr.channel == 9:
            inst_name = "طقم درامز وطبلة شرقية"
        else:
            inst_name = config.GM_INSTRUMENTS[tr.program][self.speech.lang]
        state_parts = []
        if tr.solo:
            state_parts.append("صولو")
        if tr.muted:
            state_parts.append("صامت")
        state_parts.append(f"{len(tr.events) // 2} نوتة" if tr.events else "فارغ")
        status_text = " - ".join(state_parts)
        self.speech.speak(f"تراك {tr.track_id + 1}: {inst_name} ({status_text})")

    def announce_full_project_status(self):
        tr = self.sequencer.active_track
        inst_name = "درامز وطبلة" if tr.channel == 9 else config.GM_INSTRUMENTS[tr.program]["ar"]
        maqam_name = config.MAQAMAT[self.synth.maqam_idx]["name_ar"]
        root_name = config.NOTE_NAMES_AR[self.synth.maqam_root]
        chord_name = config.CHORD_MODES[self.mapper.chord_mode_idx]["name_ar"]
        note_count = len(tr.events) // 2
        self.speech.speak(
            f"تراك {tr.track_id + 1}: {inst_name}، {maqam_name} من درجة {root_name}، "
            f"نمط العزف {chord_name}، السرعة {self.sequencer.bpm} نبضة، "
            f"اللوب {self.sequencer.bars} بار، النوتات {note_count}، الصوت {int(tr.volume * 100 / 127)} بالمئة"
        )

    def handle_keydown(self, event):
        key = event.key
        mods = pygame.key.get_mods()
        ctrl = bool(mods & pygame.KMOD_CTRL)
        alt = bool(mods & pygame.KMOD_ALT)
        shift = bool(mods & pygame.KMOD_SHIFT)
        key_name = pygame.key.name(key).lower()

        if key == pygame.K_F1:
            self.help_mode = not self.help_mode
            if self.help_mode:
                self.speech.speak("تم تفعيل دليل المفاتيح التفاعلي. اضغط أي زر لسماع وظيفته، واضغط F1 للعودة للعزف")
            else:
                self.speech.speak("تم الخروج من دليل المفاتيح، يمكنك العزف الآن")
            return

        if self.help_mode:
            if key_name in config.KEY_HELP_AR:
                self.speech.speak(config.KEY_HELP_AR[key_name])
            else:
                notes = self.mapper.get_midi_notes(key, self.sequencer.active_track.channel == 9)
                if notes:
                    n_name = config.NOTE_NAMES_AR[notes[0] % 12]
                    octv = (notes[0] // 12) - 1
                    self.speech.speak(f"مفتاح عزف نغمة {n_name} أوكتاف {octv}")
                else:
                    self.speech.speak(f"زر {key_name}")
            return

        if key == pygame.K_F5:
            self.step_seq.toggle_mode()
            return

        if key == pygame.K_F9:
            self.step_seq.load_next_preset()
            return

        if self.step_seq.active:
            if key == pygame.K_LEFT:
                self.step_seq.move_step(-1)
                return
            elif key == pygame.K_RIGHT:
                self.step_seq.move_step(1)
                return
            elif key == pygame.K_UP:
                self.step_seq.move_drum_piece(-1)
                return
            elif key == pygame.K_DOWN:
                self.step_seq.move_drum_piece(1)
                return
            elif key == pygame.K_SPACE:
                self.step_seq.toggle_current_step_hit()
                return

        if ctrl and key == pygame.K_z:
            self.sequencer.undo()
            return
        if ctrl and key == pygame.K_y:
            self.sequencer.redo()
            return
        if ctrl and key == pygame.K_s:
            self.sequencer.save_session()
            return
        if ctrl and key == pygame.K_o:
            self.sequencer.load_session()
            return
        if ctrl and key == pygame.K_e:
            StudioExporter.export_all(self.sequencer, self.synth, self.speech)
            return

        if ctrl and key == pygame.K_b:
            next_maqam = (self.synth.maqam_idx + 1) % len(config.MAQAMAT)
            self.synth.set_maqam(next_maqam)
            m_info = config.MAQAMAT[self.synth.maqam_idx]
            root_ar = config.NOTE_NAMES_AR[self.synth.maqam_root]
            self.speech.speak(f"تم اختيار {m_info['name_ar']} على درجة {root_ar}")
            return

        if ctrl and key == pygame.K_n:
            next_root = (self.synth.maqam_root + 1) % 12
            self.synth.set_maqam(self.synth.maqam_idx, next_root)
            m_info = config.MAQAMAT[self.synth.maqam_idx]
            root_ar = config.NOTE_NAMES_AR[self.synth.maqam_root]
            self.speech.speak(f"درجة ركوز المقام: {root_ar} ({m_info['name_ar']})")
            return

        if ctrl and key == pygame.K_k:
            mode_info = self.mapper.cycle_chord_mode(self.synth)
            self.speech.speak(f"نمط العزف: {mode_info['name_ar']}")
            return

        if key == pygame.K_INSERT:
            self.synth.set_sustain_pedal(not self.synth.sustain_pedal)
            st = "مفعلة" if self.synth.sustain_pedal else "متوقفة"
            self.speech.speak(f"دواسة الرنين المتصل سستين {st}")
            return

        if key == pygame.K_F2 or (ctrl and key == pygame.K_r):
            self.sequencer.toggle_record()
            return

        if key == pygame.K_F3 or (ctrl and key == pygame.K_t):
            self.sequencer.metronome_enabled = not self.sequencer.metronome_enabled
            st = "مفعل" if self.sequencer.metronome_enabled else "متوقف"
            self.speech.speak(f"بندول الإيقاع الميترونوم {st}")
            return

        if key == pygame.K_F4 or (ctrl and key == pygame.K_l):
            self.sequencer.loop_enabled = not self.sequencer.loop_enabled
            st = "مفعل" if self.sequencer.loop_enabled else "متوقف"
            self.speech.speak(f"التكرار التلقائي اللوب {st}")
            return

        if key == pygame.K_F6 or (ctrl and key == pygame.K_q):
            if ctrl and key == pygame.K_F6:
                self.sequencer.cycle_quantize_division()
            else:
                self.sequencer.quantize_active_track()
            return

        if key == pygame.K_F10 or (ctrl and key == pygame.K_d):
            tr = self.sequencer.active_track
            tr.solo = not tr.solo
            st = "مفعل" if tr.solo else "ملغى"
            self.speech.speak(f"وضع العزل صولو لتراك {tr.track_id + 1} {st}")
            return

        if key == pygame.K_F11 or (ctrl and key == pygame.K_m):
            tr = self.sequencer.active_track
            tr.muted = not tr.muted
            st = "مكتوم" if tr.muted else "مسموع"
            self.speech.speak(f"تراك {tr.track_id + 1} {st}")
            return

        if key == pygame.K_F12:
            self.speech.lang = "en" if self.speech.lang == "ar" else "ar"
            msg = "English voice active" if self.speech.lang == "en" else "تم تفعيل اللغة العربية"
            self.speech.speak(msg)
            return

        if key == pygame.K_SPACE:
            self.sequencer.toggle_play()
            return

        if key == pygame.K_TAB:
            self.announce_full_project_status()
            return

        if key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self.sequencer.clear_active_track()
            return

        if key in (pygame.K_F7, pygame.K_MINUS, pygame.K_KP_MINUS):
            self.sequencer.bpm = max(config.MIN_BPM, self.sequencer.bpm - 5)
            self.speech.speak(f"السرعة {self.sequencer.bpm} نبضة في الدقيقة")
            return
        if key in (pygame.K_F8, pygame.K_PLUS, pygame.K_KP_PLUS):
            self.sequencer.bpm = min(config.MAX_BPM, self.sequencer.bpm + 5)
            self.speech.speak(f"السرعة {self.sequencer.bpm} نبضة في الدقيقة")
            return

        if alt and key in (pygame.K_UP, pygame.K_DOWN):
            tr = self.sequencer.active_track
            delta = 13 if key == pygame.K_UP else -13
            tr.volume = max(0, min(127, tr.volume + delta))
            self.synth.set_volume(tr.channel, tr.volume)
            pct = int(round((tr.volume / 127.0) * 100))
            self.speech.speak(f"مستوى صوت تراك {tr.track_id + 1}: {pct} بالمئة")
            return

        if alt and key in (pygame.K_LEFT, pygame.K_RIGHT):
            tr = self.sequencer.active_track
            if key == pygame.K_LEFT:
                tr.pan = 0 if tr.pan <= 64 else 64
            else:
                tr.pan = 127 if tr.pan >= 64 else 64
            self.synth.set_pan(tr.channel, tr.pan)
            pos_ar = "يسار" if tr.pan < 40 else ("يمين" if tr.pan > 88 else "منتصف")
            self.speech.speak(f"توجيه صوت تراك {tr.track_id + 1}: {pos_ar}")
            return

        if alt and key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            tr = self.sequencer.active_track
            delta = 20 if key == pygame.K_PAGEUP else -20
            tr.reverb = max(0, min(127, tr.reverb + delta))
            self.synth.set_reverb(tr.channel, tr.reverb)
            pct = int(round((tr.reverb / 127.0) * 100))
            self.speech.speak(f"صدى الصوت ريفيرب لتراك {tr.track_id + 1}: {pct} بالمئة")
            return

        if key == pygame.K_HOME or (shift and key == pygame.K_UP):
            vel = self.mapper.adjust_velocity(10)
            self.speech.speak(f"قوة لمس المفاتيح {vel}")
            return
        if key == pygame.K_END or (shift and key == pygame.K_DOWN):
            vel = self.mapper.adjust_velocity(-10)
            self.speech.speak(f"قوة لمس المفاتيح {vel}")
            return

        if shift and key in (pygame.K_LEFT, pygame.K_RIGHT):
            delta = 1 if key == pygame.K_RIGHT else -1
            tr_semi = self.mapper.shift_transpose(delta, self.synth)
            self.speech.speak(f"ترانسبوز {tr_semi:+d} نصف تون")
            return

        if key == pygame.K_UP:
            self.mapper.release_all_pressed(self.synth)
            self.sequencer.active_track_idx = (self.sequencer.active_track_idx - 1) % len(self.sequencer.tracks)
            self.announce_track_status(self.sequencer.active_track)
            return
        if key == pygame.K_DOWN:
            self.mapper.release_all_pressed(self.synth)
            self.sequencer.active_track_idx = (self.sequencer.active_track_idx + 1) % len(self.sequencer.tracks)
            self.announce_track_status(self.sequencer.active_track)
            return

        if key in (pygame.K_LEFT, pygame.K_RIGHT):
            tr = self.sequencer.active_track
            if tr.channel == 9:
                self.speech.speak("تراك 8 مخصص للطبول والإيقاعات، اضغط F9 لتغيير الإيقاع الشرقي أو الغربي أو F5 لفتح منظم الخطوات")
                return
            step = 8 if ctrl else 1
            direction = 1 if key == pygame.K_RIGHT else -1
            tr.program = (tr.program + (step * direction)) % 128
            self.synth.preview_instrument(tr.channel, tr.program)
            inst_info = config.GM_INSTRUMENTS[tr.program]
            if ctrl:
                self.speech.speak(f"عائلة {inst_info['family_ar']}: {inst_info[self.speech.lang]}")
            else:
                self.speech.speak(f"آلة {inst_info[self.speech.lang]}")
            return

        if key == pygame.K_PAGEUP:
            if ctrl:
                options = [1, 2, 4, 8, 16, 32]
                idx = min(len(options) - 1, options.index(self.sequencer.bars) + 1) if self.sequencer.bars in options else 2
                self.sequencer.bars = options[idx]
                self.speech.speak(f"طول اللوب {self.sequencer.bars} بار")
            else:
                octv = self.mapper.shift_octave(1, self.synth)
                self.speech.speak(f"الأوكتاف {octv}")
            return

        if key == pygame.K_PAGEDOWN:
            if ctrl:
                options = [1, 2, 4, 8, 16, 32]
                idx = max(0, options.index(self.sequencer.bars) - 1) if self.sequencer.bars in options else 2
                self.sequencer.bars = options[idx]
                self.speech.speak(f"طول اللوب {self.sequencer.bars} بار")
            else:
                octv = self.mapper.shift_octave(-1, self.synth)
                self.speech.speak(f"الأوكتاف {octv}")
            return

        if not ctrl and not alt:
            tr = self.sequencer.active_track
            notes = self.mapper.get_midi_notes(key, is_drum_track=(tr.channel == 9))
            if notes and key not in self.mapper.pressed_keys:
                vel = self.mapper.velocity
                self.mapper.pressed_keys[key] = (tr.channel, notes)
                for n in notes:
                    self.synth.note_on(tr.channel, n, vel)
                    self.sequencer.record_note_on(n, vel)

    def handle_keyup(self, event):
        key = event.key
        if key in self.mapper.pressed_keys:
            ch, notes = self.mapper.pressed_keys.pop(key)
            for n in notes:
                self.synth.note_off(ch, n)
                self.sequencer.record_note_off(n)

    def run(self):
        frame_counter = 0
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.step_seq.active:
                            self.step_seq.toggle_mode()
                        elif self.help_mode:
                            self.help_mode = False
                            self.speech.speak("تم الخروج من دليل المفاتيح")
                        else:
                            self.running = False
                    else:
                        self.handle_keydown(event)
                elif event.type == pygame.KEYUP:
                    self.handle_keyup(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.ui.handle_mouse_down(event.pos, self)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.ui.handle_mouse_up(self)

            self.sequencer.update()
            self.synth.update()

            frame_counter += 1
            if frame_counter >= 6:
                frame_counter = 0
                self.ui.render(self)

            self.clock.tick(config.FPS)

        self.sequencer.stop()
        self.synth.shutdown()
        self.speech.shutdown()
        pygame.quit()


if __name__ == "__main__":
    app = AccessibleStudioApp()
    app.run()
