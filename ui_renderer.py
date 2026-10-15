import pygame
import config
from keyboard_mapper import OFFSET_TO_KEY_LABEL


class StudioUIRenderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_title = pygame.font.SysFont("segoeui", 20, bold=True)
        self.font_md = pygame.font.SysFont("consolas", 14, bold=True)
        self.font_sm = pygame.font.SysFont("consolas", 12)
        self.font_xs = pygame.font.SysFont("consolas", 11)

        self.transport_buttons = {}
        self.pattern_buttons = {}
        self.track_rects = {}
        self.mute_rects = {}
        self.solo_rects = {}
        self.vol_slider_rects = {}
        self.timeline_rects = {}
        self.fx_slider_rects = {}
        self.step_cell_rects = {}
        self.white_key_rects = []
        self.black_key_rects = []

    def render(self, app):
        w, h = self.screen.get_size()
        self.screen.fill((12, 15, 22))
        self._draw_top_transport_bar(app, w)
        if app.step_seq.active:
            self._draw_step_sequencer_view(app, w, h)
        else:
            self._draw_tracks_and_inspector(app, w, h)
        self._draw_bottom_piano_and_status(app, w, h)
        pygame.display.flip()

    def _draw_top_transport_bar(self, app, w: int):
        bar_rect = pygame.Rect(0, 0, w, 82)
        pygame.draw.rect(self.screen, (19, 24, 34), bar_rect)
        pygame.draw.line(self.screen, (45, 58, 82), (0, 81), (w, 81), 2)

        title_surf = self.font_title.render(config.APP_NAME, True, (248, 208, 78))
        self.screen.blit(title_surf, (14, 8))
        sub_surf = self.font_xs.render(app.synth.loaded_sf2_name[:32], True, (130, 175, 215))
        self.screen.blit(sub_surf, (14, 34))

        voice_short = app.speech.preferred_voice_name[:26]
        v_surf = self.font_xs.render(f"TTS [Ctrl+V]: {voice_short}", True, (115, 225, 165))
        self.screen.blit(v_surf, (14, 52))

        seq = app.sequencer
        btn_specs = [
            ("play", "PLAY [Space]", seq.state == "PLAYING", (36, 168, 92), 235, 86),
            ("rec", "REC [F2]", seq.state in ("RECORDING", "COUNT_IN"), (218, 48, 65), 325, 72),
            ("loop", f"LOOP {seq.bars}B [F4]", seq.loop_enabled, (48, 128, 210), 401, 86),
            ("metro", "METRO [F3/T]", seq.metronome_enabled, (148, 92, 210), 491, 86),
            ("quant", "QUANT [F6]", False, (60, 76, 102), 581, 78),
            ("edit", "NOTES [F3]", app.note_editor.active, (215, 115, 45), 663, 78),
            ("drums", "DRUMS [F5]", app.step_seq.active, (220, 140, 35), 745, 82),
            ("rhythm", "BEAT [F9]", False, (60, 76, 102), 831, 74),
            ("voice", "VOICE [Ctrl+V]", False, (45, 125, 115), 909, 92),
            ("sf2", "LOAD SF2", app.synth.using_fluidsynth, (75, 105, 155), 1005, 74),
            ("export", "EXPORT [Ctrl+E]", False, (82, 118, 72), 1083, 98),
        ]

        self.transport_buttons.clear()
        for btn_id, label, is_active, active_col, x, bw in btn_specs:
            rect = pygame.Rect(x, 10, bw, 32)
            self.transport_buttons[btn_id] = rect
            bg = active_col if is_active else (32, 39, 54)
            border = (255, 235, 120) if is_active else (70, 84, 112)
            pygame.draw.rect(self.screen, bg, rect, border_radius=5)
            pygame.draw.rect(self.screen, border, rect, width=1, border_radius=5)
            lbl_surf = self.font_xs.render(label, True, (245, 248, 255))
            self.screen.blit(
                lbl_surf,
                (rect.x + (rect.w - lbl_surf.get_width()) // 2, rect.y + (rect.h - lbl_surf.get_height()) // 2),
            )

        self.pattern_buttons.clear()
        pat_x = 235
        for p_idx, p_lbl in enumerate(["PAT A", "PAT B", "PAT C", "PAT D"]):
            p_rect = pygame.Rect(pat_x + p_idx * 58, 48, 54, 24)
            self.pattern_buttons[p_idx] = p_rect
            is_cur = seq.current_pattern_idx == p_idx
            has_data = any(len(t.patterns[p_idx]) > 0 for t in seq.tracks)
            bg = (230, 175, 45) if is_cur else ((45, 78, 110) if has_data else (28, 34, 48))
            pygame.draw.rect(self.screen, bg, p_rect, border_radius=4)
            pygame.draw.rect(self.screen, (95, 115, 145), p_rect, width=1, border_radius=4)
            txt_c = (15, 20, 30) if is_cur else (230, 238, 250)
            ps = self.font_xs.render(p_lbl, True, txt_c)
            self.screen.blit(ps, (p_rect.x + (p_rect.w - ps.get_width()) // 2, p_rect.y + 5))

        chain_rect = pygame.Rect(pat_x + 236, 48, 86, 24)
        self.transport_buttons["chain"] = chain_rect
        pygame.draw.rect(self.screen, (45, 155, 120) if seq.song_chain_mode else (32, 39, 54), chain_rect, border_radius=4)
        self.screen.blit(self.font_xs.render("SONG CHAIN", True, (245, 250, 255)), (chain_rect.x + 8, chain_rect.y + 5))

        bar_num, beat_num = seq.get_bar_beat_display()
        maqam_en = config.MAQAMAT[app.synth.maqam_idx]["name_en"]
        root_en = config.NOTE_NAMES_EN[app.synth.maqam_root]
        arp_en = config.ARP_MODES[app.mapper.arp_mode_idx]["name_en"]
        lock_str = "LOCK" if app.mapper.scale_lock else "FREE"
        info_line = (
            f"BPM:{seq.bpm} | BAR:{bar_num:02d}.{beat_num} | "
            f"{maqam_en}({root_en}) [{lock_str}] | ARP:{arp_en} | "
            f"TREM:{'ON' if app.synth.tremolo_enabled else 'OFF'}"
        )
        self.screen.blit(self.font_xs.render(info_line, True, (205, 222, 242)), (570, 53))

        osc_rect = pygame.Rect(w - 168, 10, 154, 62)
        pygame.draw.rect(self.screen, (10, 14, 20), osc_rect, border_radius=5)
        pygame.draw.rect(self.screen, (55, 72, 98), osc_rect, width=1, border_radius=5)
        buf = app.synth.oscilloscope_buffer
        pts = []
        mid_y = osc_rect.centery
        for i in range(0, len(buf), 2):
            px = osc_rect.x + 4 + int((i / float(len(buf))) * (osc_rect.w - 8))
            py = int(mid_y - float(buf[i]) * (osc_rect.h * 0.42))
            pts.append((px, max(osc_rect.top + 2, min(osc_rect.bottom - 2, py))))
        if len(pts) > 2:
            pygame.draw.lines(self.screen, (75, 235, 165), False, pts, 2)

    def _draw_tracks_and_inspector(self, app, w: int, h: int):
        seq = app.sequencer
        self.track_rects.clear()
        self.mute_rects.clear()
        self.solo_rects.clear()
        self.vol_slider_rects.clear()
        self.timeline_rects.clear()
        self.fx_slider_rects.clear()

        inspector_w = 265
        main_area_w = w - inspector_w - 24
        start_y = 90
        avail_h = h - 255
        row_h = max(46, (avail_h // 8) - 4)
        left_panel_w = 365
        timeline_x = left_panel_w + 12
        timeline_w = main_area_w - timeline_x

        for idx, tr in enumerate(seq.tracks):
            y = start_y + idx * (row_h + 4)
            row_rect = pygame.Rect(12, y, main_area_w, row_h)
            self.track_rects[idx] = row_rect

            is_sel = idx == seq.active_track_idx
            audible = seq.is_track_audible(tr)
            bg_col = (30, 41, 62) if is_sel else (20, 25, 36)
            border_col = (248, 205, 72) if is_sel else (42, 52, 70)
            pygame.draw.rect(self.screen, bg_col, row_rect, border_radius=6)
            pygame.draw.rect(self.screen, border_col, row_rect, width=2 if is_sel else 1, border_radius=6)

            inst_name = "Oriental & Studio Drum Kit" if tr.channel == 9 else config.GM_INSTRUMENTS[tr.program]["en"]
            tr_title = f"{idx + 1}. {inst_name[:22]}"
            t_col = (255, 240, 145) if is_sel else ((220, 230, 245) if audible else (115, 125, 140))
            self.screen.blit(self.font_md.render(tr_title, True, t_col), (20, y + 6))

            pan_str = "L" if tr.pan < 45 else ("R" if tr.pan > 83 else "C")
            sub_txt = f"Pan:{pan_str} Rev:{int(tr.reverb*100/127)}% Del:{int(tr.delay*100/127)}% [{len(tr.events)//2}n]"
            self.screen.blit(self.font_xs.render(sub_txt, True, (145, 168, 195)), (20, y + 27))

            m_rect = pygame.Rect(228, y + 10, 26, 26)
            s_rect = pygame.Rect(258, y + 10, 26, 26)
            self.mute_rects[idx] = m_rect
            self.solo_rects[idx] = s_rect

            pygame.draw.rect(self.screen, (215, 58, 58) if tr.muted else (40, 48, 64), m_rect, border_radius=4)
            pygame.draw.rect(self.screen, (232, 178, 42) if tr.solo else (40, 48, 64), s_rect, border_radius=4)
            self.screen.blit(self.font_xs.render("M", True, (255, 255, 255)), (m_rect.x + 8, m_rect.y + 6))
            self.screen.blit(self.font_xs.render("S", True, (255, 255, 255)), (s_rect.x + 8, s_rect.y + 6))

            vol_rect = pygame.Rect(292, y + 12, 72, 11)
            self.vol_slider_rects[idx] = vol_rect
            pygame.draw.rect(self.screen, (12, 16, 24), vol_rect, border_radius=4)
            fill_w = int((tr.volume / 127.0) * vol_rect.w)
            pygame.draw.rect(self.screen, (62, 188, 242), (vol_rect.x, vol_rect.y, fill_w, vol_rect.h), border_radius=4)

            peak_w = int(min(1.0, app.synth.channel_peaks.get(tr.channel, 0.0)) * 72)
            pygame.draw.rect(self.screen, (12, 16, 24), (292, y + 28, 72, 7), border_radius=3)
            pygame.draw.rect(self.screen, (72, 225, 130), (292, y + 28, peak_w, 7), border_radius=3)

            tl_rect = pygame.Rect(timeline_x, y + 5, timeline_w, row_h - 10)
            self.timeline_rects[idx] = tl_rect
            pygame.draw.rect(self.screen, (13, 17, 25), tl_rect, border_radius=4)

            total_bars = max(1, seq.bars)
            for b in range(1, total_bars * 4):
                bx = tl_rect.x + int((b / float(total_bars * 4)) * tl_rect.w)
                col = (38, 48, 68) if b % 4 == 0 else (22, 28, 40)
                pygame.draw.line(self.screen, col, (bx, tl_rect.y), (bx, tl_rect.bottom), 1)

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

            note_color = (245, 155, 55) if tr.channel == 9 else ((92, 218, 252) if is_sel else (68, 152, 192))
            for s_i, (n_val, st_t, end_t) in enumerate(spans):
                nx = tl_rect.x + int((st_t / loop_dur) * tl_rect.w)
                nw = max(5, int(((end_t - st_t) / loop_dur) * tl_rect.w))
                norm_pitch = max(0.0, min(1.0, (n_val - 36) / 48.0))
                ny = tl_rect.bottom - 6 - int(norm_pitch * (tl_rect.h - 10))
                c = (255, 85, 120) if (is_sel and app.note_editor.active and s_i == app.note_editor.selected_idx) else note_color
                pygame.draw.rect(self.screen, c, (nx, ny, min(nw, tl_rect.right - nx), 5), border_radius=2)

            if seq.state in ("PLAYING", "RECORDING"):
                ph_x = tl_rect.x + int(seq.get_playhead_progress() * tl_rect.w)
                ph_col = (255, 68, 78) if seq.state == "RECORDING" else (255, 235, 90)
                pygame.draw.line(self.screen, ph_col, (ph_x, tl_rect.y), (ph_x, tl_rect.bottom), 2)

        insp_rect = pygame.Rect(w - inspector_w - 12, start_y, inspector_w, 8 * (row_h + 4) - 4)
        pygame.draw.rect(self.screen, (20, 26, 38), insp_rect, border_radius=7)
        pygame.draw.rect(self.screen, (58, 74, 102), insp_rect, width=1, border_radius=7)

        atr = seq.active_track
        self.screen.blit(self.font_md.render(f"TRACK {atr.track_id + 1} DSP & FX RACK", True, (248, 208, 82)), (insp_rect.x + 14, insp_rect.y + 12))
        fam_en = "Percussion" if atr.channel == 9 else config.GM_INSTRUMENTS[atr.program]["family_en"]
        self.screen.blit(self.font_xs.render(f"Family: {fam_en}", True, (155, 180, 210)), (insp_rect.x + 14, insp_rect.y + 34))

        fx_specs = [
            ("volume", "Track Volume [Alt+Up/Dn]", atr.volume, (65, 195, 245)),
            ("pan", "Stereo Pan [Alt+L/R]", atr.pan, (240, 185, 65)),
            ("reverb", "Hall Reverb [Alt+PgUp/Dn]", atr.reverb, (165, 115, 245)),
            ("delay", "Echo Delay [Alt+Home/End]", atr.delay, (75, 220, 165)),
            ("cutoff", "Filter Cutoff [Ctrl+Up/Dn]", atr.cutoff, (245, 125, 95)),
            ("drive", "Warm Overdrive", atr.drive, (235, 80, 95)),
        ]

        fy = insp_rect.y + 64
        for fx_id, lbl, val, col in fx_specs:
            self.screen.blit(self.font_xs.render(f"{lbl}: {int(val * 100 / 127)}%", True, (215, 228, 245)), (insp_rect.x + 14, fy))
            s_rect = pygame.Rect(insp_rect.x + 14, fy + 18, insp_rect.w - 28, 13)
            self.fx_slider_rects[fx_id] = s_rect
            pygame.draw.rect(self.screen, (12, 15, 22), s_rect, border_radius=4)
            fw = int((val / 127.0) * s_rect.w)
            pygame.draw.rect(self.screen, col, (s_rect.x, s_rect.y, fw, s_rect.h), border_radius=4)
            fy += 46

        shortcuts_box = [
            "Ctrl+1..4 : Switch Pattern A-D",
            "Ctrl+C/V  : Copy/Paste Pattern",
            "Ctrl+B/N  : Maqam & Root Key",
            "Ctrl+A    : Arpeggiator Mode",
            "F3        : Step Note Editor",
            "Slash (/) : Oud/Qanun Tremolo",
        ]
        fy += 6
        for sc_line in shortcuts_box:
            if fy + 16 < insp_rect.bottom:
                self.screen.blit(self.font_xs.render(sc_line, True, (145, 170, 200)), (insp_rect.x + 14, fy))
                fy += 18

    def _draw_step_sequencer_view(self, app, w: int, h: int):
        self.step_cell_rects.clear()
        panel_rect = pygame.Rect(14, 88, w - 28, h - 252)
        pygame.draw.rect(self.screen, (20, 25, 36), panel_rect, border_radius=8)
        pygame.draw.rect(self.screen, (235, 165, 50), panel_rect, width=2, border_radius=8)

        preset_name = (
            config.RHYTHM_PRESETS[app.step_seq.preset_idx]["name_en"]
            if app.step_seq.preset_idx >= 0
            else "Custom Oriental Pattern"
        )
        hdr = f"16-STEP ORIENTAL & STUDIO DRUM SEQUENCER (Preset: {preset_name} | Press F5 to return | Space/Click to toggle hits)"
        self.screen.blit(self.font_md.render(hdr, True, (250, 215, 95)), (28, 98))

        grid_x = 230
        grid_y = 132
        avail_w = w - grid_x - 36
        cell_w = max(36, (avail_w // 16) - 4)
        avail_h = panel_rect.h - 60
        cell_h = max(24, (avail_h // len(config.DRUM_PIECES)) - 4)
        playing_step = int(app.sequencer.get_playhead_progress() * 16) % 16 if app.sequencer.state != "IDLE" else -1

        for s_idx in range(16):
            sx = grid_x + s_idx * (cell_w + 4)
            col = (255, 225, 90) if s_idx == app.step_seq.current_step else (155, 175, 200)
            self.screen.blit(self.font_xs.render(f"{s_idx + 1:02d}", True, col), (sx + cell_w // 3, grid_y - 16))

        for d_idx, piece in enumerate(config.DRUM_PIECES):
            ry = grid_y + d_idx * (cell_h + 4)
            is_cur_row = d_idx == app.step_seq.current_drum_idx
            lbl_col = (255, 225, 95) if is_cur_row else (200, 215, 235)
            self.screen.blit(self.font_sm.render(piece["en"], True, lbl_col), (28, ry + (cell_h - 14) // 2))

            note = piece["note"]
            for s_idx in range(16):
                cx = grid_x + s_idx * (cell_w + 4)
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

                pygame.draw.rect(self.screen, fill, c_rect, border_radius=4)

                is_cursor = is_cur_row and (s_idx == app.step_seq.current_step)
                if is_cursor:
                    pygame.draw.rect(self.screen, (255, 240, 110), c_rect, width=3, border_radius=4)
                elif s_idx == playing_step:
                    pygame.draw.rect(self.screen, (110, 235, 255), c_rect, width=2, border_radius=4)
                else:
                    pygame.draw.rect(self.screen, (55, 65, 85), c_rect, width=1, border_radius=4)

    def _draw_bottom_piano_and_status(self, app, w: int, h: int):
        piano_top = h - 158
        piano_h = 122
        pygame.draw.rect(self.screen, (18, 22, 32), (0, piano_top, w, piano_h))
        pygame.draw.line(self.screen, (50, 62, 85), (0, piano_top), (w, piano_top), 2)

        self.white_key_rects.clear()
        self.black_key_rects.clear()

        base_midi = app.mapper.get_base_midi_note()
        active_ch = app.sequencer.active_track.channel
        active_set = app.synth.active_notes.get(active_ch, set())

        white_offsets = [i for i in range(32) if (i % 12) in (0, 2, 4, 5, 7, 9, 11)]
        num_white = len(white_offsets)
        wk_w = (w - 28) / float(num_white)
        wk_h = 108

        offset_to_white_x = {}
        for w_idx, semitone_off in enumerate(white_offsets):
            wx = int(14 + w_idx * wk_w)
            w_rect = pygame.Rect(wx, piano_top + 7, int(wk_w) - 2, wk_h)
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
                self.screen.blit(lbl_s, (w_rect.x + (w_rect.w - lbl_s.get_width()) // 2, w_rect.bottom - 36))

            if midi_note % 12 == 0:
                n_str = f"C{(midi_note // 12) - 1}"
                n_s = self.font_xs.render(n_str, True, (90, 105, 130))
                self.screen.blit(n_s, (w_rect.x + (w_rect.w - n_s.get_width()) // 2, w_rect.bottom - 18))

        bk_w = int(wk_w * 0.62)
        bk_h = int(wk_h * 0.60)
        for semitone_off in range(32):
            if (semitone_off % 12) in (1, 3, 6, 8, 10):
                prev_white = semitone_off - 1
                if prev_white in offset_to_white_x:
                    bx = offset_to_white_x[prev_white] + int(wk_w * 0.68)
                    b_rect = pygame.Rect(bx, piano_top + 7, bk_w, bk_h)
                    midi_note = max(0, min(127, base_midi + semitone_off))
                    self.black_key_rects.append((b_rect, midi_note))

                    is_pressed = midi_note in active_set
                    b_col = (245, 190, 55) if is_pressed else (24, 28, 38)
                    pygame.draw.rect(self.screen, b_col, b_rect, border_radius=4)
                    pygame.draw.rect(self.screen, (70, 82, 105), b_rect, width=1, border_radius=4)

                    key_lbl = OFFSET_TO_KEY_LABEL.get(semitone_off, "")
                    if key_lbl:
                        lbl_s = self.font_xs.render(key_lbl, True, (15, 20, 30) if is_pressed else (210, 220, 235))
                        self.screen.blit(lbl_s, (b_rect.x + (b_rect.w - lbl_s.get_width()) // 2, b_rect.bottom - 20))

        status_rect = pygame.Rect(0, h - 36, w, 36)
        pygame.draw.rect(self.screen, (9, 12, 18), status_rect)
        speech_txt = f"Voice [{app.speech.preferred_voice_name[:22]}]: {app.speech.last_spoken}"
        self.screen.blit(self.font_sm.render(speech_txt[:135], True, (120, 232, 175)), (14, h - 26))

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
                elif btn_id == "edit":
                    app.note_editor.toggle_mode()
                elif btn_id == "drums":
                    app.step_seq.toggle_mode()
                elif btn_id == "rhythm":
                    app.step_seq.load_next_preset()
                elif btn_id == "voice":
                    app.speech.cycle_voice(1)
                elif btn_id == "sf2":
                    app.prompt_load_sf2_file()
                elif btn_id == "chain":
                    app.sequencer.song_chain_mode = not app.sequencer.song_chain_mode
                    app.speech.speak("وضع تسلسل الأغنية الكاملة مفعل" if app.sequencer.song_chain_mode else "وضع المقطع المنفرد")
                elif btn_id == "export":
                    from exporter import StudioExporter
                    StudioExporter.export_all(app.sequencer, app.synth, app.speech)
                return

        for p_idx, p_rect in self.pattern_buttons.items():
            if p_rect.collidepoint(pos):
                app.sequencer.select_pattern(p_idx)
                return

        if app.step_seq.active:
            for (d_idx, s_idx), c_rect in self.step_cell_rects.items():
                if c_rect.collidepoint(pos):
                    app.step_seq.toggle_step_at(d_idx, s_idx)
                    return
        else:
            for fx_id, s_rect in self.fx_slider_rects.items():
                if s_rect.collidepoint(pos):
                    tr = app.sequencer.active_track
                    rel = max(0.0, min(1.0, (pos[0] - s_rect.x) / float(s_rect.w)))
                    val = int(round(rel * 127))
                    if fx_id == "volume":
                        tr.volume = val
                        app.synth.set_volume(tr.channel, val)
                    elif fx_id == "pan":
                        tr.pan = val
                        app.synth.set_pan(tr.channel, val)
                    elif fx_id == "reverb":
                        tr.reverb = val
                        app.synth.set_reverb(tr.channel, val)
                    elif fx_id == "delay":
                        tr.delay = val
                        app.synth.set_delay(tr.channel, val)
                    elif fx_id == "cutoff":
                        tr.cutoff = max(15, val)
                        app.synth.set_cutoff(tr.channel, tr.cutoff)
                    elif fx_id == "drive":
                        tr.drive = val
                        app.synth.set_drive(tr.channel, val)
                    app.speech.speak(f"{fx_id} {int(rel * 100)} بالمئة")
                    return

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
            for idx, tl_rect in self.timeline_rects.items():
                if tl_rect.collidepoint(pos):
                    app.sequencer.active_track_idx = idx
                    norm_t = max(0.0, min(0.99, (pos[0] - tl_rect.x) / float(tl_rect.w)))
                    norm_p = 1.0 - max(0.0, min(1.0, (pos[1] - tl_rect.y) / float(tl_rect.h)))
                    midi_n = 36 + int(round(norm_p * 36))
                    app.sequencer.toggle_piano_roll_note_at(idx, norm_t, midi_n)
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
