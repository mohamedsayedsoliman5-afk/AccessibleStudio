import pygame
import config
from keyboard_mapper import OFFSET_TO_KEY_LABEL


class StudioUIRenderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_title = pygame.font.SysFont("segoeui", 20, bold=True)
        self.font_md = pygame.font.SysFont("consolas", 15, bold=True)
        self.font_sm = pygame.font.SysFont("consolas", 13)
        self.font_xs = pygame.font.SysFont("consolas", 11)

        self.transport_buttons = {}
        self.track_rects = {}
        self.mute_rects = {}
        self.solo_rects = {}
        self.vol_slider_rects = {}
        self.step_cell_rects = {}
        self.white_key_rects = []
        self.black_key_rects = []

    def render(self, app):
        self.screen.fill((14, 17, 24))
        self._draw_top_transport_bar(app)
        if app.step_seq.active:
            self._draw_step_sequencer_view(app)
        else:
            self._draw_tracks_mixer_and_arrangement(app)
        self._draw_bottom_piano_and_status(app)
        pygame.display.flip()

    def _draw_top_transport_bar(self, app):
        bar_rect = pygame.Rect(0, 0, config.WINDOW_WIDTH, 76)
        pygame.draw.rect(self.screen, (22, 26, 36), bar_rect)
        pygame.draw.line(self.screen, (45, 55, 75), (0, 75), (config.WINDOW_WIDTH, 75), 2)

        title_surf = self.font_title.render(config.APP_NAME, True, (245, 205, 75))
        self.screen.blit(title_surf, (16, 10))
        sub_mode = "FluidSynth SF2 Engine" if app.synth.using_fluidsynth else "Physical & Oriental Synth"
        sub_surf = self.font_xs.render(sub_mode, True, (140, 165, 195))
        self.screen.blit(sub_surf, (16, 38))

        seq = app.sequencer
        btn_specs = [
            ("play", "PLAY / STOP [Space]", seq.state == "PLAYING", (38, 166, 91), 225, 95),
            ("rec", "REC [F2]", seq.state in ("RECORDING", "COUNT_IN"), (215, 48, 65), 326, 78),
            ("loop", f"LOOP {seq.bars}B [F4]", seq.loop_enabled, (52, 130, 210), 410, 92),
            ("metro", "METRO [F3]", seq.metronome_enabled, (155, 95, 210), 508, 84),
            ("quant", "QUANT [F6]", False, (65, 80, 105), 598, 84),
            ("drums", "16-STEP [F5]", app.step_seq.active, (220, 135, 35), 688, 92),
            ("rhythm", "BEAT [F9]", False, (65, 80, 105), 786, 80),
            ("help", "HELP [F1]", app.help_mode, (40, 165, 175), 872, 78),
            ("export", "EXPORT [Ctrl+E]", False, (85, 110, 75), 956, 108),
        ]

        self.transport_buttons.clear()
        for btn_id, label, is_active, active_col, x, w in btn_specs:
            rect = pygame.Rect(x, 12, w, 34)
            self.transport_buttons[btn_id] = rect
            bg = active_col if is_active else (36, 43, 58)
            border = (255, 235, 120) if is_active else (75, 88, 115)
            pygame.draw.rect(self.screen, bg, rect, border_radius=6)
            pygame.draw.rect(self.screen, border, rect, width=1, border_radius=6)
            lbl_surf = self.font_xs.render(label, True, (245, 248, 255))
            self.screen.blit(
                lbl_surf,
                (rect.x + (rect.w - lbl_surf.get_width()) // 2, rect.y + (rect.h - lbl_surf.get_height()) // 2),
            )

        bar_num, beat_num = seq.get_bar_beat_display()
        maqam_en = config.MAQAMAT[app.synth.maqam_idx]["name_en"]
        root_en = config.NOTE_NAMES_EN[app.synth.maqam_root]
        chord_en = config.CHORD_MODES[app.mapper.chord_mode_idx]["name_en"]
        info_line = (
            f"BPM: {seq.bpm} [-/+]  |  BAR: {bar_num:02d} BEAT: {beat_num}  |  "
            f"SCALE: {maqam_en} ({root_en}) [Ctrl+B/N]  |  MODE: {chord_en} [Ctrl+K]  |  "
            f"OCTAVE: {app.mapper.base_octave} (TR:{app.mapper.transpose:+d})"
        )
        info_surf = self.font_xs.render(info_line, True, (205, 220, 240))
        self.screen.blit(info_surf, (225, 53))

        vu_x = 1076
        pygame.draw.rect(self.screen, (14, 18, 26), (vu_x, 14, 108, 24), border_radius=4)
        l_w = int(min(1.0, app.synth.master_peak_l) * 102)
        r_w = int(min(1.0, app.synth.master_peak_r) * 102)
        pygame.draw.rect(self.screen, (60, 215, 120), (vu_x + 3, 17, l_w, 7), border_radius=2)
        pygame.draw.rect(self.screen, (55, 185, 245), (vu_x + 3, 27, r_w, 7), border_radius=2)
        vu_lbl = self.font_xs.render("MASTER L/R", True, (150, 170, 195))
        self.screen.blit(vu_lbl, (vu_x + 18, 42))

    def _draw_tracks_mixer_and_arrangement(self, app):
        seq = app.sequencer
        self.track_rects.clear()
        self.mute_rects.clear()
        self.solo_rects.clear()
        self.vol_slider_rects.clear()

        start_y = 84
        row_h = 54
        left_panel_w = 430
        timeline_x = left_panel_w + 14
        timeline_w = config.WINDOW_WIDTH - timeline_x - 16

        for idx, tr in enumerate(seq.tracks):
            y = start_y + idx * (row_h + 4)
            row_rect = pygame.Rect(12, y, config.WINDOW_WIDTH - 24, row_h)
            self.track_rects[idx] = row_rect

            is_sel = idx == seq.active_track_idx
            audible = seq.is_track_audible(tr)
            bg_col = (32, 42, 62) if is_sel else (22, 27, 38)
            border_col = (250, 205, 70) if is_sel else (45, 54, 72)
            pygame.draw.rect(self.screen, bg_col, row_rect, border_radius=6)
            pygame.draw.rect(self.screen, border_col, row_rect, width=2 if is_sel else 1, border_radius=6)

            inst_name = "Oriental & GM Drum Kit" if tr.channel == 9 else config.GM_INSTRUMENTS[tr.program]["en"]
            tr_title = f"{idx + 1}. {inst_name[:24]}"
            t_col = (255, 240, 150) if is_sel else ((220, 230, 245) if audible else (120, 130, 145))
            self.screen.blit(self.font_md.render(tr_title, True, t_col), (22, y + 7))

            pan_str = "L" if tr.pan < 45 else ("R" if tr.pan > 83 else "C")
            rev_pct = int(tr.reverb * 100 / 127)
            sub_txt = f"Ch:{tr.channel + 1:02d} | Pan:{pan_str} | Rev:{rev_pct}% | Notes:{len(tr.events) // 2}"
            self.screen.blit(self.font_xs.render(sub_txt, True, (150, 170, 195)), (22, y + 30))

            m_rect = pygame.Rect(268, y + 12, 28, 28)
            s_rect = pygame.Rect(302, y + 12, 28, 28)
            self.mute_rects[idx] = m_rect
            self.solo_rects[idx] = s_rect

            pygame.draw.rect(self.screen, (210, 60, 60) if tr.muted else (42, 50, 66), m_rect, border_radius=4)
            pygame.draw.rect(self.screen, (230, 175, 40) if tr.solo else (42, 50, 66), s_rect, border_radius=4)
            self.screen.blit(self.font_xs.render("M", True, (255, 255, 255)), (m_rect.x + 9, m_rect.y + 7))
            self.screen.blit(self.font_xs.render("S", True, (255, 255, 255)), (s_rect.x + 9, s_rect.y + 7))

            vol_rect = pygame.Rect(340, y + 14, 82, 12)
            self.vol_slider_rects[idx] = vol_rect
            pygame.draw.rect(self.screen, (14, 18, 25), vol_rect, border_radius=4)
            fill_w = int((tr.volume / 127.0) * vol_rect.w)
            pygame.draw.rect(self.screen, (65, 190, 240), (vol_rect.x, vol_rect.y, fill_w, vol_rect.h), border_radius=4)

            peak_w = int(min(1.0, app.synth.channel_peaks.get(tr.channel, 0.0)) * 82)
            pygame.draw.rect(self.screen, (14, 18, 25), (340, y + 31, 82, 8), border_radius=3)
            pygame.draw.rect(self.screen, (75, 225, 130), (340, y + 31, peak_w, 8), border_radius=3)

            tl_rect = pygame.Rect(timeline_x, y + 6, timeline_w, row_h - 12)
            pygame.draw.rect(self.screen, (14, 18, 26), tl_rect, border_radius=4)

            total_bars = max(1, seq.bars)
            for b in range(1, total_bars):
                bx = tl_rect.x + int((b / total_bars) * tl_rect.w)
                pygame.draw.line(self.screen, (32, 40, 56), (bx, tl_rect.y), (bx, tl_rect.bottom), 1)

            loop_dur = max(0.001, seq.loop_duration)
            open_map = {}
            spans = []
            for ev in tr.events:
                if ev["type"] == "note_on":
                    open_map[ev["note"]] = ev["time"]
                elif ev["type"] == "note_off" and ev["note"] in open_map:
                    st_t = open_map.pop(ev["note"])
                    spans.append((ev["note"], st_t, max(st_t + 0.05, ev["time"])))
            for n_val, st_t in open_map.items():
                spans.append((n_val, st_t, min(loop_dur, st_t + 0.12)))

            note_color = (245, 155, 55) if tr.channel == 9 else ((90, 215, 250) if is_sel else (70, 155, 195))
            for n_val, st_t, end_t in spans:
                nx = tl_rect.x + int((st_t / loop_dur) * tl_rect.w)
                nw = max(4, int(((end_t - st_t) / loop_dur) * tl_rect.w))
                norm_pitch = max(0.0, min(1.0, (n_val - 36) / 48.0))
                ny = tl_rect.bottom - 6 - int(norm_pitch * (tl_rect.h - 10))
                pygame.draw.rect(self.screen, note_color, (nx, ny, min(nw, tl_rect.right - nx), 5), border_radius=2)

            if seq.state in ("PLAYING", "RECORDING"):
                ph_x = tl_rect.x + int(seq.get_playhead_progress() * tl_rect.w)
                ph_col = (255, 70, 80) if seq.state == "RECORDING" else (255, 235, 90)
                pygame.draw.line(self.screen, ph_col, (ph_x, tl_rect.y), (ph_x, tl_rect.bottom), 2)

    def _draw_step_sequencer_view(self, app):
        self.step_cell_rects.clear()
        panel_rect = pygame.Rect(16, 86, config.WINDOW_WIDTH - 32, 456)
        pygame.draw.rect(self.screen, (20, 25, 36), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, (235, 165, 50), panel_rect, width=2, border_radius=8)

        preset_name = (
            config.RHYTHM_PRESETS[app.step_seq.preset_idx]["name_en"]
            if app.step_seq.preset_idx >= 0
            else "Custom Pattern"
        )
        hdr = f"16-STEP ORIENTAL & STUDIO DRUM SEQUENCER (Preset: {preset_name} | Press F5 to return to Tracks | Space/Click to toggle hits)"
        self.screen.blit(self.font_md.render(hdr, True, (250, 215, 95)), (30, 96))

        grid_x = 235
        grid_y = 132
        cell_w = 56
        cell_h = 38
        playing_step = int(app.sequencer.get_playhead_progress() * 16) % 16 if app.sequencer.state != "IDLE" else -1

        for s_idx in range(16):
            sx = grid_x + s_idx * (cell_w + 3)
            col = (255, 225, 90) if s_idx == app.step_seq.current_step else (155, 175, 200)
            self.screen.blit(self.font_xs.render(f"{s_idx + 1:02d}", True, col), (sx + 18, grid_y - 18))

        for d_idx, piece in enumerate(config.DRUM_PIECES):
            ry = grid_y + d_idx * (cell_h + 5)
            is_cur_row = d_idx == app.step_seq.current_drum_idx
            lbl_col = (255, 225, 95) if is_cur_row else (200, 215, 235)
            self.screen.blit(self.font_sm.render(piece["en"], True, lbl_col), (32, ry + 9))

            note = piece["note"]
            for s_idx in range(16):
                cx = grid_x + s_idx * (cell_w + 3)
                c_rect = pygame.Rect(cx, ry, cell_w, cell_h)
                self.step_cell_rects[(d_idx, s_idx)] = c_rect

                vel = app.step_seq.grid[note][s_idx]
                if vel >= 120:
                    fill = (235, 75, 65)
                elif vel >= 90:
                    fill = (55, 195, 110)
                elif vel > 0:
                    fill = (65, 145, 225)
                else:
                    fill = (32, 39, 54) if (s_idx // 4) % 2 == 0 else (26, 32, 45)

                pygame.draw.rect(self.screen, fill, c_rect, border_radius=5)

                is_cursor = is_cur_row and (s_idx == app.step_seq.current_step)
                if is_cursor:
                    pygame.draw.rect(self.screen, (255, 240, 110), c_rect, width=3, border_radius=5)
                elif s_idx == playing_step:
                    pygame.draw.rect(self.screen, (110, 235, 255), c_rect, width=2, border_radius=5)
                else:
                    pygame.draw.rect(self.screen, (55, 65, 85), c_rect, width=1, border_radius=5)

    def _draw_bottom_piano_and_status(self, app):
        piano_top = 550
        piano_h = 148
        pygame.draw.rect(self.screen, (18, 22, 32), (0, piano_top, config.WINDOW_WIDTH, piano_h))
        pygame.draw.line(self.screen, (50, 62, 85), (0, piano_top), (config.WINDOW_WIDTH, piano_top), 2)

        self.white_key_rects.clear()
        self.black_key_rects.clear()

        base_midi = app.mapper.get_base_midi_note()
        active_ch = app.sequencer.active_track.channel
        active_set = app.synth.active_notes.get(active_ch, set())

        white_offsets = [i for i in range(32) if (i % 12) in (0, 2, 4, 5, 7, 9, 11)]
        num_white = len(white_offsets)
        wk_w = (config.WINDOW_WIDTH - 32) / float(num_white)
        wk_h = 132

        offset_to_white_x = {}
        for w_idx, semitone_off in enumerate(white_offsets):
            wx = int(16 + w_idx * wk_w)
            w_rect = pygame.Rect(wx, piano_top + 8, int(wk_w) - 2, wk_h)
            midi_note = max(0, min(127, base_midi + semitone_off))
            self.white_key_rects.append((w_rect, midi_note))
            offset_to_white_x[semitone_off] = wx

            is_pressed = midi_note in active_set
            col = (85, 215, 250) if is_pressed else (238, 242, 248)
            pygame.draw.rect(self.screen, col, w_rect, border_radius=4)
            pygame.draw.rect(self.screen, (40, 48, 62), w_rect, width=1, border_radius=4)

            key_lbl = OFFSET_TO_KEY_LABEL.get(semitone_off, "")
            if key_lbl:
                lbl_s = self.font_sm.render(key_lbl, True, (25, 35, 50))
                self.screen.blit(lbl_s, (w_rect.x + (w_rect.w - lbl_s.get_width()) // 2, w_rect.bottom - 40))

            if midi_note % 12 == 0:
                n_str = f"C{(midi_note // 12) - 1}"
                n_s = self.font_xs.render(n_str, True, (90, 105, 130))
                self.screen.blit(n_s, (w_rect.x + (w_rect.w - n_s.get_width()) // 2, w_rect.bottom - 20))

        bk_w = int(wk_w * 0.62)
        bk_h = int(wk_h * 0.60)
        for semitone_off in range(32):
            if (semitone_off % 12) in (1, 3, 6, 8, 10):
                prev_white = semitone_off - 1
                if prev_white in offset_to_white_x:
                    bx = offset_to_white_x[prev_white] + int(wk_w * 0.68)
                    b_rect = pygame.Rect(bx, piano_top + 8, bk_w, bk_h)
                    midi_note = max(0, min(127, base_midi + semitone_off))
                    self.black_key_rects.append((b_rect, midi_note))

                    is_pressed = midi_note in active_set
                    b_col = (245, 190, 55) if is_pressed else (24, 28, 38)
                    pygame.draw.rect(self.screen, b_col, b_rect, border_radius=4)
                    pygame.draw.rect(self.screen, (70, 82, 105), b_rect, width=1, border_radius=4)

                    key_lbl = OFFSET_TO_KEY_LABEL.get(semitone_off, "")
                    if key_lbl:
                        lbl_s = self.font_xs.render(key_lbl, True, (15, 20, 30) if is_pressed else (210, 220, 235))
                        self.screen.blit(lbl_s, (b_rect.x + (b_rect.w - lbl_s.get_width()) // 2, b_rect.bottom - 22))

        status_rect = pygame.Rect(0, config.WINDOW_HEIGHT - 38, config.WINDOW_WIDTH, 38)
        pygame.draw.rect(self.screen, (10, 13, 19), status_rect)
        speech_txt = f"Screen Reader Output: {app.speech.last_spoken}"
        self.screen.blit(self.font_sm.render(speech_txt[:115], True, (125, 230, 175)), (16, config.WINDOW_HEIGHT - 28))

    def handle_mouse_down(self, pos, app):
        for btn_id, rect in self.transport_buttons.items():
            if rect.collidepoint(pos):
                if btn_id == "play":
                    app.sequencer.toggle_play()
                elif btn_id == "rec":
                    app.sequencer.toggle_record()
                elif btn_id == "loop":
                    app.sequencer.loop_enabled = not app.sequencer.loop_enabled
                    app.speech.speak("التكرار اللوب مفعل" if app.sequencer.loop_enabled else "اللوب متوقف")
                elif btn_id == "metro":
                    app.sequencer.metronome_enabled = not app.sequencer.metronome_enabled
                    app.speech.speak("الميترونوم مفعل" if app.sequencer.metronome_enabled else "الميترونوم متوقف")
                elif btn_id == "quant":
                    app.sequencer.quantize_active_track()
                elif btn_id == "drums":
                    app.step_seq.toggle_mode()
                elif btn_id == "rhythm":
                    app.step_seq.load_next_preset()
                elif btn_id == "help":
                    app.help_mode = not app.help_mode
                    app.speech.speak("تم تفعيل دليل المفاتيح" if app.help_mode else "تم إغلاق دليل المفاتيح")
                elif btn_id == "export":
                    from exporter import StudioExporter
                    StudioExporter.export_all(app.sequencer, app.synth, app.speech)
                return

        if app.step_seq.active:
            for (d_idx, s_idx), c_rect in self.step_cell_rects.items():
                if c_rect.collidepoint(pos):
                    app.step_seq.toggle_step_at(d_idx, s_idx)
                    return
        else:
            for idx, m_rect in self.mute_rects.items():
                if m_rect.collidepoint(pos):
                    tr = app.sequencer.tracks[idx]
                    tr.muted = not tr.muted
                    app.speech.speak(f"تراك {idx + 1} {'مكتوم' if tr.muted else 'مسموع'}")
                    return
            for idx, s_rect in self.solo_rects.items():
                if s_rect.collidepoint(pos):
                    tr = app.sequencer.tracks[idx]
                    tr.solo = not tr.solo
                    app.speech.speak(f"صولو تراك {idx + 1} {'مفعل' if tr.solo else 'ملغى'}")
                    return
            for idx, v_rect in self.vol_slider_rects.items():
                if v_rect.collidepoint(pos):
                    tr = app.sequencer.tracks[idx]
                    rel = max(0.0, min(1.0, (pos[0] - v_rect.x) / float(v_rect.w)))
                    tr.volume = int(round(rel * 127))
                    app.synth.set_volume(tr.channel, tr.volume)
                    app.speech.speak(f"صوت تراك {idx + 1}: {int(rel * 100)} بالمئة")
                    return
            for idx, r_rect in self.track_rects.items():
                if r_rect.collidepoint(pos):
                    app.mapper.release_all_pressed(app.synth)
                    app.sequencer.active_track_idx = idx
                    app.announce_track_status(app.sequencer.active_track)
                    return

        tr = app.sequencer.active_track
        for b_rect, midi_note in self.black_key_rects:
            if b_rect.collidepoint(pos):
                app.mapper.mouse_active_note = (tr.channel, midi_note)
                app.synth.note_on(tr.channel, midi_note, app.mapper.velocity)
                app.sequencer.record_note_on(midi_note, app.mapper.velocity)
                return

        for w_rect, midi_note in self.white_key_rects:
            if w_rect.collidepoint(pos):
                app.mapper.mouse_active_note = (tr.channel, midi_note)
                app.synth.note_on(tr.channel, midi_note, app.mapper.velocity)
                app.sequencer.record_note_on(midi_note, app.mapper.velocity)
                return

    def handle_mouse_up(self, app):
        if app.mapper.mouse_active_note is not None:
            ch, note = app.mapper.mouse_active_note
            app.synth.note_off(ch, note)
            app.sequencer.record_note_off(note)
            app.mapper.mouse_active_note = None
