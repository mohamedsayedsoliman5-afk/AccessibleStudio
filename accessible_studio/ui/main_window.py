"""
AccessibleStudio UI - High-Contrast Accessible Desktop Window
=============================================================
Native Windows Desktop GUI engineered from first principles for blind
and visually impaired musicians and audio producers.
Features:
- Native Win32 HWND registered with NVDA/JAWS accessibility tree.
- Standard Accessible Menu Bar (File, Tracks, Transport, Drums, Help).
- High-contrast visual layout for sighted collaborators and low-vision.
- Live active track, transport parameters, 8-track grid, and note readout.
- Full keyboard piano matrix (Z-M, Q-I) with zero-latency response.
- Dedicated accessible dialogs (Instrument Picker, Shortcuts Manual).
"""

import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from accessible_studio.config import (
    GM_INSTRUMENTS,
    STEP_DRUM_INSTRUMENTS,
    get_note_name,
    DEFAULT_BPM
)
from accessible_studio.accessibility.speech import speech
from accessible_studio.core.sequencer import Sequencer


class AccessibleStudioWindow:
    """Main Application Window & Screen-Reader-First User Interface."""

    def __init__(self, sequencer, synth_engine, drum_grid, keyboard_mapper, exporter):
        self.sequencer = sequencer
        self.synth = synth_engine
        self.drum_grid = drum_grid
        self.keyboard = keyboard_mapper
        self.exporter = exporter

        self.root = None
        self._running = True
        self.help_mode = False

        # Visual string variables
        self._track_title_var = None
        self._transport_var = None
        self._mixer_var = None
        self._state_var = None
        self._live_note_var = None
        self.track_frames = []

    def run(self):
        """Initializes and runs the native desktop GUI."""
        self.root = tk.Tk()
        self.root.title("AccessibleStudio DAW - استوديو الألحان الميسر للمكفوفين")
        self.root.geometry("920x680")
        self.root.minsize(800, 560)
        self.root.configure(bg="#0B132B")

        # 1. Build Menu Bar
        self._build_menu_bar()

        # 2. Build High-Contrast Visual Cards
        self._build_header_card()
        self._build_status_card()
        self._build_live_note_card()
        self._build_tracks_grid()
        self._build_footer_bar()

        # 3. Connect Keyboard Events
        self.root.bind("<KeyPress>", self._on_key_press)
        self.root.bind("<KeyRelease>", self._on_key_release)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 4. Announce Welcome via NVDA/JAWS
        self._announce_welcome()

        # 5. Start GUI Refresh Timer (40ms = 25 FPS)
        self.root.after(40, self._refresh_gui_loop)

        # 6. Run Tkinter Mainloop
        self.root.mainloop()

    def _build_menu_bar(self):
        """Builds standard accessible Windows menu bar."""
        menubar = tk.Menu(self.root)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="مشروع جديد (New Project)", accelerator="Ctrl+N", command=self._cmd_new_project)
        file_menu.add_command(label="تصدير ملف ميدي (Export MIDI)", accelerator="Ctrl+Shift+E", command=self._cmd_export)
        file_menu.add_command(label="تصدير ملف صوتي WAV (Export WAV)", accelerator="Ctrl+E", command=self._cmd_export)
        file_menu.add_separator()
        file_menu.add_command(label="مسح كل مسارات المشروع (Clear All)", command=self._cmd_clear_all)
        file_menu.add_separator()
        file_menu.add_command(label="خروج (Exit)", accelerator="Alt+F4", command=self._on_close)
        menubar.add_cascade(label="ملف (File)", menu=file_menu)

        # Tracks Menu
        tracks_menu = tk.Menu(menubar, tearoff=0)
        tracks_menu.add_command(label="المسار التالي (Next Track)", accelerator="Down", command=self.sequencer.select_next_track)
        tracks_menu.add_command(label="المسار السابق (Previous Track)", accelerator="Up", command=self.sequencer.select_prev_track)
        tracks_menu.add_separator()
        tracks_menu.add_command(label="اختيار الآلة الموسيقية من القائمة (Select Instrument)", accelerator="Ctrl+I", command=self._open_instrument_picker)
        tracks_menu.add_command(label="الآلة التالية (Next Instrument)", accelerator="Tab", command=lambda: self.sequencer.change_track_program(1))
        tracks_menu.add_command(label="الآلة السابقة (Previous Instrument)", accelerator="Shift+Tab", command=lambda: self.sequencer.change_track_program(-1))
        tracks_menu.add_separator()
        tracks_menu.add_command(label="كتم المسار (Mute Track)", accelerator="M", command=self.sequencer.toggle_track_mute)
        tracks_menu.add_command(label="عزل المسار (Solo Track)", accelerator="S", command=self.sequencer.toggle_track_solo)
        tracks_menu.add_command(label="التراجع عن آخر تسجيل (Undo)", accelerator="Ctrl+Z", command=self.sequencer.undo_active_track)
        tracks_menu.add_command(label="مسح نوتات المسار الحالي (Clear Track)", accelerator="Ctrl+Delete", command=self.sequencer.clear_active_track)
        tracks_menu.add_command(label="ضبط إيقاعي 1/16 (Quantize)", accelerator="Ctrl+Q", command=lambda: self.sequencer.quantize_track(self.sequencer.active_track_idx, 16))
        menubar.add_cascade(label="مسارات (Tracks)", menu=tracks_menu)

        # Transport Menu
        transport_menu = tk.Menu(menubar, tearoff=0)
        transport_menu.add_command(label="تشغيل / إيقاف (Play/Stop)", accelerator="Space", command=self.sequencer.toggle_play_stop)
        transport_menu.add_command(label="تسجيل مع عد تنازلي (Record 4-Beat)", accelerator="R", command=self.sequencer.start_recording)
        transport_menu.add_command(label="العودة للبداية (Rewind to Start)", accelerator="Home", command=self.sequencer.rewind_to_start)
        transport_menu.add_separator()
        transport_menu.add_command(label="تفعيل / تعطيل المترونوم (Toggle Metronome)", accelerator="F3", command=self.sequencer.toggle_metronome)
        transport_menu.add_command(label="زيادة السرعة BPM (Tempo Up)", accelerator="+", command=lambda: self.sequencer.adjust_bpm(5))
        transport_menu.add_command(label="تقليل السرعة BPM (Tempo Down)", accelerator="-", command=lambda: self.sequencer.adjust_bpm(-5))
        transport_menu.add_separator()
        transport_menu.add_command(label="رفع الأوكتاف (Octave Up)", accelerator="]", command=self._cmd_octave_up)
        transport_menu.add_command(label="خفض الأوكتاف (Octave Down)", accelerator="[", command=self._cmd_octave_down)
        menubar.add_cascade(label="عزف وتحكم (Transport)", menu=transport_menu)

        # Drums Menu
        drums_menu = tk.Menu(menubar, tearoff=0)
        drums_menu.add_command(label="فتح / إغلاق شبكة الدرامز (Drum Grid Mode)", accelerator="F5", command=self.drum_grid.toggle_mode)
        drums_menu.add_separator()
        drums_menu.add_command(label="إيقاع مقسوم شرقي (Arabic Maqsum)", accelerator="Ctrl+M", command=lambda: self.drum_grid.load_preset("maqsum"))
        drums_menu.add_command(label="إيقاع صعيدي شرقي (Arabic Saidi)", command=lambda: self.drum_grid.load_preset("saidi"))
        drums_menu.add_command(label="إيقاع ملفوف شرقي (Arabic Malfuf)", command=lambda: self.drum_grid.load_preset("malfuf"))
        drums_menu.add_command(label="إيقاع بوب ودانس (Four on the Floor)", accelerator="Ctrl+D", command=lambda: self.drum_grid.load_preset("four_on_floor"))
        drums_menu.add_command(label="إيقاع روك كلاسيكي (Rock Beat)", accelerator="Ctrl+K", command=lambda: self.drum_grid.load_preset("rock"))
        drums_menu.add_separator()
        drums_menu.add_command(label="نسخ الإيقاع إلى مسار المشروع (Copy to Track)", accelerator="Enter (in drum mode)", command=self._cmd_copy_drums_to_track)
        menubar.add_cascade(label="إيقاعات ودرامز (Drums)", menu=drums_menu)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="دليل الاختصارات الشامل (Shortcuts Manual)", accelerator="F1", command=self._open_shortcuts_dialog)
        help_menu.add_command(label="نمط دليل المفاتيح التفاعلي (Interactive Help)", accelerator="Shift+F1", command=self._toggle_interactive_help)
        help_menu.add_command(label="تبديل لغة النطق (Toggle Language Ar/En)", accelerator="F12", command=speech.toggle_language)
        help_menu.add_separator()
        help_menu.add_command(label="نبذة عن البرنامج (About)", command=self._show_about)
        menubar.add_cascade(label="مساعدة (Help)", menu=help_menu)

        self.root.config(menu=menubar)

    def _build_header_card(self):
        header = tk.Frame(self.root, bg="#1C2541", pady=10, padx=16)
        header.pack(fill=tk.X, padx=12, pady=(10, 6))

        t = tk.Label(
            header,
            text="AccessibleStudio DAW | استوديو الألحان الميسر للمكفوفين",
            font=("Segoe UI", 16, "bold"),
            fg="#F0B90B",
            bg="#1C2541"
        )
        t.pack(anchor="w")

        sub = tk.Label(
            header,
            text="نظام عزف وتسجيل متكامل | مدعوم لقارئات الشاشة (NVDA / JAWS) والمؤشرات السمعية",
            font=("Segoe UI", 10),
            fg="#58A6FF",
            bg="#1C2541"
        )
        sub.pack(anchor="w")

    def _build_status_card(self):
        card = tk.Frame(self.root, bg="#161B22", relief=tk.RIDGE, bd=2, padx=16, pady=12)
        card.pack(fill=tk.X, padx=12, pady=6)

        self._track_title_var = tk.StringVar(value="المسار 1: بيانو صوتي كبير | Track 1: Acoustic Grand Piano")
        t_lbl = tk.Label(card, textvariable=self._track_title_var, font=("Segoe UI", 14, "bold"), fg="#FFFFFF", bg="#161B22")
        t_lbl.pack(anchor="w", pady=(0, 4))

        self._transport_var = tk.StringVar(value="السرعة: 120 نبضة/د | المازورة: 1 | النبضة: 1 | الأوكتاف: 4 | الشدة: 100")
        pos_lbl = tk.Label(card, textvariable=self._transport_var, font=("Segoe UI", 11), fg="#58A6FF", bg="#161B22")
        pos_lbl.pack(anchor="w", pady=(0, 4))

        self._mixer_var = tk.StringVar(value="مستوى الصوت: 100% | التوزيع: في المنتصف | بندول الإيقاع: مفعّل")
        m_lbl = tk.Label(card, textvariable=self._mixer_var, font=("Segoe UI", 11), fg="#8B949E", bg="#161B22")
        m_lbl.pack(anchor="w", pady=(0, 4))

        self._state_var = tk.StringVar(value="الحالة: جاهز للعزف | اضغط Space للتشغيل أو R للتسجيل")
        st_lbl = tk.Label(card, textvariable=self._state_var, font=("Segoe UI", 11, "bold"), fg="#F0B90B", bg="#161B22")
        st_lbl.pack(anchor="w")

    def _build_live_note_card(self):
        frame = tk.Frame(self.root, bg="#0D1117", relief=tk.SOLID, bd=1, padx=14, pady=8)
        frame.pack(fill=tk.X, padx=12, pady=6)

        self._live_note_var = tk.StringVar(value="العزف المباشر: جاهز | مفاتيح البيانو: Z S X D C V G B H N J M و Q 2 W 3 E R 5 T 6 Y 7 U I")
        lbl = tk.Label(frame, textvariable=self._live_note_var, font=("Segoe UI", 12, "bold"), fg="#00FF7F", bg="#0D1117")
        lbl.pack(anchor="w")

    def _build_tracks_grid(self):
        container = tk.Frame(self.root, bg="#0B132B")
        container.pack(fill=tk.X, padx=12, pady=6)

        self.track_frames = []
        for i in range(self.sequencer.num_tracks):
            tf = tk.Frame(container, bg="#1C2541", relief=tk.RAISED, bd=2, padx=4, pady=8)
            tf.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=3)

            n_lbl = tk.Label(tf, text=f"Track {i+1}", font=("Segoe UI", 11, "bold"), fg="#FFFFFF", bg="#1C2541")
            n_lbl.pack()

            inst_lbl = tk.Label(tf, text="Piano", font=("Segoe UI", 8), fg="#8B949E", bg="#1C2541")
            inst_lbl.pack()

            cnt_lbl = tk.Label(tf, text="0 notes", font=("Segoe UI", 8), fg="#58A6FF", bg="#1C2541")
            cnt_lbl.pack()

            # Clickable for sighted mouse users
            def _make_handler(idx=i):
                return lambda e: self.sequencer.select_track(idx)
            tf.bind("<Button-1>", _make_handler(i))
            n_lbl.bind("<Button-1>", _make_handler(i))

            self.track_frames.append((tf, n_lbl, inst_lbl, cnt_lbl))

    def _build_footer_bar(self):
        footer = tk.Frame(self.root, bg="#161B22", padx=12, pady=8)
        footer.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=8)

        text = (
            "F1: دليل الاختصارات الشامل | Space: تشغيل/إيقاف | R: تسجيل مع العد التنازلي | Ctrl+I: اختيار الآلة الموسيقية\n"
            "Up / Down: التنقل بين المسارات | Tab: تغيير الآلة | F5: شبكة الدرامز | F11: تصدير WAV/MIDI | F12: تبديل اللغة"
        )
        lbl = tk.Label(footer, text=text, font=("Segoe UI", 9), fg="#C9D1D9", bg="#161B22", justify=tk.LEFT)
        lbl.pack(anchor="w")

    def _announce_welcome(self):
        welcome_text = speech.get_text("welcome")
        speech.speak(welcome_text, interrupt=True)

    # -----------------------------------------------------------------------
    # Keyboard Event Routing
    # -----------------------------------------------------------------------
    def _on_key_press(self, event):
        keysym = event.keysym
        char = event.char
        is_shift = bool(event.state & 0x0001)
        is_ctrl = bool(event.state & 0x0004)

        # 1. Global Functional Hotkeys (F1 to F12, Escape)
        if keysym == "F1":
            if is_shift:
                self._open_shortcuts_dialog()
            else:
                self._toggle_interactive_help()
            return

        if self.help_mode:
            self._speak_key_description(keysym, char, is_ctrl, is_shift)
            return

        if keysym == "F2":
            self.sequencer.announce_track_info()
            return
        elif keysym == "F3":
            self.sequencer.toggle_metronome()
            return
        elif keysym == "F4":
            speech.speak(speech.get_text("tempo_changed", bpm=self.sequencer.bpm), interrupt=True)
            return
        elif keysym == "F5":
            self.drum_grid.toggle_mode()
            return
        elif keysym == "F6":
            self.sequencer.quantize_track(self.sequencer.active_track_idx, 16)
            return
        elif keysym == "F7":
            self.sequencer.toggle_track_solo()
            return
        elif keysym == "F8":
            self.sequencer.toggle_track_mute()
            return
        elif keysym == "F9":
            self.sequencer.undo_active_track()
            return
        elif keysym == "F10":
            self.sequencer.clear_active_track()
            return
        elif keysym == "F11":
            self._cmd_export()
            return
        elif keysym == "F12":
            speech.toggle_language()
            return
        elif keysym == "Escape":
            if self.drum_grid.is_active:
                self.drum_grid.toggle_mode()
            else:
                self.synth.panic()
                self.keyboard.release_all_keys()
                speech.speak(speech.get_text("panic"), interrupt=True)
            return

        # 2. Drum Grid Mode Handlers
        if self.drum_grid.is_active:
            if keysym == "Left":
                self.drum_grid.move_step(-1)
                return
            elif keysym == "Right":
                self.drum_grid.move_step(1)
                return
            elif keysym == "Up":
                self.drum_grid.move_drum(-1)
                return
            elif keysym == "Down":
                self.drum_grid.move_drum(1)
                return
            elif keysym == "space":
                self.drum_grid.toggle_current_hit()
                return
            elif keysym in ["Return", "KP_Enter"]:
                self._cmd_copy_drums_to_track()
                return

        # 3. Normal Studio Mode Controls
        # Track Navigation (Up / Down)
        if keysym == "Up":
            if is_ctrl:
                self.sequencer.adjust_track_volume(5)
            else:
                self.sequencer.select_prev_track()
            return
        elif keysym == "Down":
            if is_ctrl:
                self.sequencer.adjust_track_volume(-5)
            else:
                self.sequencer.select_next_track()
            return

        # Pan / Rewind (Left / Right)
        if keysym == "Left":
            self.sequencer.adjust_track_pan(-5)
            return
        elif keysym == "Right":
            self.sequencer.adjust_track_pan(5)
            return

        # Space (Play / Stop)
        if keysym == "space":
            self.sequencer.toggle_play_stop()
            return

        # Transport & Editing Shortcuts
        if char == "r" or keysym == "r":
            if is_ctrl:
                self.sequencer.start_recording()
            elif not self.drum_grid.is_active and not self.keyboard.is_musical_key(char):
                self.sequencer.start_recording()
            else:
                # 'r' is a musical note (F5) in the upper octave!
                pass

        if is_ctrl and (char == "z" or keysym == "z"):
            self.sequencer.undo_active_track()
            return

        if is_ctrl and (char == "i" or keysym == "i"):
            self._open_instrument_picker()
            return

        if is_ctrl and (char == "q" or keysym == "q"):
            self.sequencer.quantize_track(self.sequencer.active_track_idx, 16)
            return

        if is_ctrl and (char == "e" or keysym == "e"):
            self._cmd_export()
            return

        if is_ctrl and (char == "m" or keysym == "m"):
            self.drum_grid.load_preset("maqsum")
            return

        if is_ctrl and (char == "d" or keysym == "d"):
            self.drum_grid.load_preset("four_on_floor")
            return

        if is_ctrl and (char == "k" or keysym == "k"):
            self.drum_grid.load_preset("rock")
            return

        if keysym in ["Home"]:
            self.sequencer.rewind_to_start()
            return

        # Tab / Shift+Tab for instrument cycling
        if keysym in ["Tab", "ISO_Left_Tab"]:
            delta = -1 if is_shift else 1
            self.sequencer.change_track_program(delta)
            return

        # Octave shifting ([ and ])
        if keysym == "bracketleft":
            self._cmd_octave_down()
            return
        elif keysym == "bracketright":
            self._cmd_octave_up()
            return

        # Tempo BPM adjust (- and +)
        if char == "-":
            self.sequencer.adjust_bpm(-5)
            return
        elif char in ["+", "="]:
            self.sequencer.adjust_bpm(5)
            return

        # Direct Track Selection (Keys 1 through 8)
        if keysym in [str(i) for i in range(1, 9)] and not is_shift:
            # Note: Digits 2, 3, 5, 6, 7 are also black keys in the upper octave if played in musical mode
            # If not already musical key:
            if not self.keyboard.is_musical_key(char):
                idx = int(keysym) - 1
                self.sequencer.select_track(idx)
                return

        # 4. Musical QWERTY Key Press
        note_res = self.keyboard.process_key_down(keysym, char)
        if note_res:
            midi_note, vel = note_res
            self.sequencer.record_note_on(midi_note, vel)

    def _on_key_release(self, event):
        keysym = event.keysym
        char = event.char
        rel_note = self.keyboard.process_key_up(keysym, char)
        if rel_note is not None:
            self.sequencer.record_note_off(rel_note)

    # -----------------------------------------------------------------------
    # Periodic GUI Refresh Loop (25 FPS)
    # -----------------------------------------------------------------------
    def _refresh_gui_loop(self):
        if not self._running or not self.root:
            return

        try:
            active_idx = self.sequencer.active_track_idx
            track = self.sequencer.tracks[active_idx]
            inst = GM_INSTRUMENTS[track.program]
            bar, beat = self.sequencer.get_bar_beat()
            lang = speech.language

            # 1. Update Active Track Banner
            inst_name = inst["ar"] if lang == "ar" else inst["en"]
            self._track_title_var.set(f"المسار {active_idx + 1}: {inst_name} ({inst['en']})")

            # 2. Update Transport readout
            self._transport_var.set(
                f"السرعة: {self.sequencer.bpm} BPM | المازورة: {bar} | النبضة: {beat} | الأوكتاف: {self.keyboard.base_octave} | الشدة: {self.keyboard.velocity}"
            )

            # 3. Update Mixer readout
            metro_str = "مفعّل (ON)" if self.sequencer.metronome_enabled else "معطّل (OFF)"
            vol_pct = int((track.volume / 127.0) * 100)
            mute_str = "مكتوم" if track.muted else "نشط"
            self._mixer_var.set(f"مستوى الصوت: {vol_pct}% | التوزيع: {track.pan} | بندول الإيقاع: {metro_str} | الحالة: {mute_str}")

            # 4. Update DAW State
            if self.drum_grid.is_active:
                step_display = self.drum_grid.current_step + 1
                drum_name = self.drum_grid.instruments[self.drum_grid.current_drum]["ar" if lang == "ar" else "en"]
                self._state_var.set(f"[نمط شبكة الدرامز 16 خطوة] الخطوة: {step_display}/16 | الآلة: {drum_name} (اضغط F5 للخروج)")
            else:
                if self.sequencer.state == Sequencer.RECORDING:
                    s_str = "تسجيل جارٍ..."
                elif self.sequencer.state == Sequencer.PLAYING:
                    s_str = "تشغيل..."
                elif self.sequencer.state == Sequencer.COUNTING_IN:
                    s_str = "عد تنازلي..."
                else:
                    s_str = "جاهز للعزف"
                self._state_var.set(f"الحالة: {s_str} | المسار المحدد: {active_idx + 1}")

            # 5. Update Live Note Display
            active_keys = self.keyboard._active_keys
            if active_keys:
                names = [get_note_name(n, lang) for n in active_keys.values()]
                self._live_note_var.set(f"العزف المباشر: {', '.join(names)}")
            else:
                self._live_note_var.set("العزف المباشر: جاهز | مفاتيح البيانو: Z S X D C V G B H N J M و Q 2 W 3 E R 5 T 6 Y 7 U I")

            # 6. Update 8 Track Grid Boxes
            for i, (tf, n_lbl, inst_lbl, cnt_lbl) in enumerate(self.track_frames):
                t = self.sequencer.tracks[i]
                t_inst = GM_INSTRUMENTS[t.program]["en"][:12]
                n_count = len(t.events) // 2
                inst_lbl.config(text=t_inst)
                cnt_lbl.config(text=f"{n_count} notes" if not t.muted else "[Muted]")

                if i == active_idx:
                    tf.config(bg="#F0B90B")
                    n_lbl.config(bg="#F0B90B", fg="#0B132B")
                    inst_lbl.config(bg="#F0B90B", fg="#0B132B")
                    cnt_lbl.config(bg="#F0B90B", fg="#0B132B")
                else:
                    tf.config(bg="#1C2541")
                    n_lbl.config(bg="#1C2541", fg="#FFFFFF")
                    inst_lbl.config(bg="#1C2541", fg="#8B949E")
                    cnt_lbl.config(bg="#1C2541", fg="#58A6FF")

            self.root.after(40, self._refresh_gui_loop)

        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Accessible Dialogs & Commands
    # -----------------------------------------------------------------------
    def _open_instrument_picker(self):
        """Opens fully accessible modal dialog with all 128 GM instruments."""
        top = tk.Toplevel(self.root)
        top.title("اختيار الآلة الموسيقية | Select GM Instrument")
        top.geometry("520x440")
        top.configure(bg="#161B22")
        top.grab_set()

        lbl = tk.Label(top, text="اختر آلة موسيقية بالأسهم ثم اضغط Enter:", font=("Segoe UI", 12, "bold"), fg="#F0B90B", bg="#161B22")
        lbl.pack(pady=(12, 6), padx=12, anchor="w")

        frame = tk.Frame(top, bg="#161B22")
        frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=6)

        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        lb = tk.Listbox(frame, font=("Segoe UI", 11), bg="#0D1117", fg="#FFFFFF", selectbackground="#F0B90B", selectforeground="#0B132B", yscrollcommand=scrollbar.set)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=lb.yview)

        for p_num, inst in enumerate(GM_INSTRUMENTS):
            lb.insert(tk.END, f"{p_num + 1:03d}: {inst['ar']} - {inst['en']}")

        # Select currently active program
        current_p = self.sequencer.tracks[self.sequencer.active_track_idx].program
        lb.selection_set(current_p)
        lb.see(current_p)
        lb.focus_set()

        def _choose(e=None):
            sel = lb.curselection()
            if sel:
                self.sequencer.set_track_program(sel[0])
            top.destroy()

        def _on_arrow(e=None):
            sel = lb.curselection()
            if sel:
                p_num = sel[0]
                inst = GM_INSTRUMENTS[p_num]
                name = inst["ar"] if speech.language == "ar" else inst["en"]
                speech.speak(f"{p_num + 1}: {name}", interrupt=True)

        lb.bind("<Return>", _choose)
        lb.bind("<Double-Button-1>", _choose)
        lb.bind("<KeyRelease-Up>", _on_arrow)
        lb.bind("<KeyRelease-Down>", _on_arrow)

        btn_box = tk.Frame(top, bg="#161B22")
        btn_box.pack(fill=tk.X, padx=12, pady=10)
        ok_btn = tk.Button(btn_box, text="اختيار (Select)", font=("Segoe UI", 10, "bold"), bg="#F0B90B", fg="#0B132B", command=_choose)
        ok_btn.pack(side=tk.RIGHT, padx=6)
        cancel_btn = tk.Button(btn_box, text="إلغاء (Cancel)", font=("Segoe UI", 10), bg="#30363D", fg="#FFFFFF", command=top.destroy)
        cancel_btn.pack(side=tk.RIGHT)

        speech.speak("قائمة الآلات الموسيقية الـ 128. تنقل بالأسهم واضغط إنتر للاختيار.", interrupt=True)

    def _open_shortcuts_dialog(self):
        """Displays full shortcuts manual."""
        top = tk.Toplevel(self.root)
        top.title("دليل الاختصارات الشامل | Shortcuts Manual")
        top.geometry("640x520")
        top.configure(bg="#161B22")
        top.grab_set()

        t_lbl = tk.Label(top, text="دليل اختصارات استوديو الألحان الميسر:", font=("Segoe UI", 13, "bold"), fg="#F0B90B", bg="#161B22")
        t_lbl.pack(anchor="w", padx=14, pady=(12, 6))

        text_widget = tk.Text(top, font=("Segoe UI", 10), bg="#0D1117", fg="#FFFFFF", wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=14, pady=6)

        manual_text = (
            "1. العزف بالكمبيوتر (Virtual Piano):\n"
            "   - الأوكتاف الأول: Z (دو), S (دو دييز), X (ري), D (ري دييز), C (مي), V (فا), G (فا دييز), B (صول), H (صول دييز), N (لا), J (لا دييز), M (سي)\n"
            "   - الأوكتاف الثاني: Q (دو مرتفع), 2, W, 3, E, R, 5, T, 6, Y, 7, U, I (دو أعلى)\n"
            "   - خفض / رفع الأوكتاف: مفتاح [ ومفتاح ]\n"
            "\n"
            "2. التحكم والتسجيل (Transport):\n"
            "   - تشغيل / إيقاف: Space\n"
            "   - تسجيل فوري مع عد تنازلي 4 نبضات: مفتاح R\n"
            "   - العودة للمازورة الأولى: مفتاح Home\n"
            "   - تفعيل / تعطيل المترونوم: مفتاح F3\n"
            "   - زيادة / تقليل سرعة الإيقاع: مفتاح + ومفتاح -\n"
            "\n"
            "3. إدارة المسارات والآلات (Tracks & Instruments):\n"
            "   - التنقل بين المسارات: السهم لأعلى والسهم لأسفل\n"
            "   - اختيار الآلة من القائمة الكاملة: Ctrl + I\n"
            "   - تبديل الآلة السريع: Tab و Shift + Tab\n"
            "   - تعديل مستوى الصوت: Ctrl + السهم لأعلى / لأسفل\n"
            "   - تعديل التوزيع الستريو: السهم يميناً ويساراً\n"
            "   - كتم / عزل المسار: مفتاح M ومفتاح S\n"
            "   - ضبط إيقاعي (Quantize 1/16): Ctrl + Q\n"
            "   - تراجع عن آخر تسجيل: Ctrl + Z\n"
            "   - مسح نوتات المسار: Ctrl + Delete\n"
            "\n"
            "4. شبكة إيقاعات الدرامز (Drum Machine):\n"
            "   - فتح / إغلاق شبكة الدرامز: مفتاح F5\n"
            "   - التنقل بين خطوات الإيقاع (1-16): السهم يميناً ويساراً\n"
            "   - التنقل بين آلات الدرامز: السهم لأعلى ولأسفل\n"
            "   - تفعيل ضربة الإيقاع: المسافة Space\n"
            "   - تحميل إيقاع مقسوم شرقي: Ctrl + M\n"
            "   - تحميل إيقاع صعيدي: من قائمة إيقاعات\n"
            "   - تحميل إيقاع بوب ودانس: Ctrl + D\n"
            "   - نسخ الإيقاع إلى مسار المشروع: مفتاح Enter\n"
            "\n"
            "5. التصدير واللغة:\n"
            "   - تصدير ملفات WAV و MIDI: مفتاح F11 أو Ctrl + E\n"
            "   - تبديل لغة النطق (عربي / إنجليزي): مفتاح F12\n"
            "   - إيقاف الطوارئ والصمت التام: مفتاح Escape\n"
        )
        text_widget.insert(tk.END, manual_text)
        text_widget.config(state=tk.DISABLED)

        close_btn = tk.Button(top, text="إغلاق (Close)", font=("Segoe UI", 10, "bold"), bg="#F0B90B", fg="#0B132B", command=top.destroy)
        close_btn.pack(pady=8)
        close_btn.focus_set()

        speech.speak("تم فتح دليل الاختصارات. تنقل بالأسهم لقراءته، أو اضغط مسافة للإغلاق.", interrupt=True)

    def _toggle_interactive_help(self):
        self.help_mode = not self.help_mode
        if self.help_mode:
            speech.play_earcon("boundary")
            speech.speak("تم تفعيل نمط دليل المفاتيح التفاعلي. اضغط على أي زر في لوحة المفاتيح لسماع وظيفته. اضغط إف واحد للخروج.", interrupt=True)
        else:
            speech.play_earcon("boundary")
            speech.speak("تم إنهاء نمط دليل المفاتيح. الاستوديو جاهز للعزف والتسجيل.", interrupt=True)

    def _speak_key_description(self, keysym: str, char: str, is_ctrl: bool, is_shift: bool):
        c = (char or keysym).lower()
        if c == "space":
            speech.speak("مسافة: تشغيل وإيقاف المشروع الموسيقي", interrupt=True)
        elif c == "r":
            speech.speak("حرف R: بدء التسجيل الموسيقي بعد عد تنازلي 4 نبضات", interrupt=True)
        elif c == "m":
            speech.speak("حرف M: كتم أو تشغيل صوت المسار الحالي", interrupt=True)
        elif c == "s":
            speech.speak("حرف S: عزل المسار الحالي لسماعه منفرداً", interrupt=True)
        elif keysym in ["Up", "Down"]:
            speech.speak("السهم لأعلى ولأسفل: التنقل بين مسارات الاستوديو الثمانية", interrupt=True)
        elif keysym in ["Left", "Right"]:
            speech.speak("السهم يميناً ويساراً: توزيع الصوت في السماعة اليمنى أو اليسرى", interrupt=True)
        elif keysym == "Tab":
            speech.speak("زر Tab: الانتقال للآلة الموسيقية التالية من بين 128 آلة", interrupt=True)
        elif keysym in ["bracketleft", "bracketright"]:
            speech.speak("مفتاح القوس: خفض أو رفع طبقة الأوكتاف الموسيقية للبيانو", interrupt=True)
        elif keysym == "Home":
            speech.speak("مفتاح Home: العودة لبداية المازورة الأولى من المقطوعة", interrupt=True)
        elif keysym == "F3":
            speech.speak("إف 3: تفعيل أو تعطيل صوت بندول الإيقاع المترونوم", interrupt=True)
        elif keysym == "F5":
            speech.speak("إف 5: فتح أو إغلاق شبكة صانع إيقاعات الدرامز 16 خطوة", interrupt=True)
        elif keysym == "F11":
            speech.speak("إف 11: تصدير المشروع إلى ملف ميدي وملف صوتي عالي الجودة WAV", interrupt=True)
        elif self.keyboard.is_musical_key(c):
            note = self.keyboard.get_base_midi_root()
            name = get_note_name(note, speech.language)
            speech.speak(f"مفتاح بيانو: يعزف نوتة موسيقية حقيقية", interrupt=True)
        else:
            speech.speak(f"مفتاح {keysym}", interrupt=True)

    def _cmd_new_project(self):
        for t in self.sequencer.tracks:
            t.clear()
        self.sequencer.rewind_to_start()
        speech.speak("تم إنشاء مشروع جديد وفارغ بنجاح", interrupt=True)

    def _cmd_clear_all(self):
        self._cmd_new_project()

    def _cmd_octave_up(self):
        octave, changed = self.keyboard.octave_up()
        if changed:
            speech.speak(speech.get_text("octave_changed", octave=octave), interrupt=True)
        else:
            speech.play_earcon("boundary")

    def _cmd_octave_down(self):
        octave, changed = self.keyboard.octave_down()
        if changed:
            speech.speak(speech.get_text("octave_changed", octave=octave), interrupt=True)
        else:
            speech.play_earcon("boundary")

    def _cmd_copy_drums_to_track(self):
        events = self.drum_grid.render_to_track_events(self.sequencer.bpm, bars=4)
        active_t = self.sequencer.tracks[self.sequencer.active_track_idx]
        active_t.save_undo_state()
        active_t.events = events
        msg = f"تم نسخ إيقاع الدرامز إلى المسار {self.sequencer.active_track_idx + 1}" if speech.language == "ar" else f"Copied drum pattern to Track {self.sequencer.active_track_idx + 1}"
        speech.speak(msg, interrupt=True)

    def _cmd_export(self):
        self.exporter.export_project()

    def _show_about(self):
        msg = (
            "استوديو الألحان الميسر للمكفوفين (AccessibleStudio DAW)\n"
            "الإصدار: 2.0.0\n\n"
            "تطبيق متكامل لإنتاج الموسيقى والعزف الحي مصمم خصيصاً للموسيقيين المكفوفين.\n"
            "يعتمد بنسبة 100% على واجهات ويندوز الأصيلة، وتولك Tolk لقارئات الشاشة (NVDA / JAWS)،\n"
            "ومحرك صوت ويندوز الأصيل منخفض التأخير (Microsoft GS Wavetable Synth).\n\n"
            "تطوير مشترك: محمد سيد & Antigravity Deepmind AI."
        )
        messagebox.showinfo("حول الاستوديو | About", msg)

    def _on_close(self):
        self._running = False
        self.sequencer.close()
        self.synth.panic()
        self.synth.close()
        speech.shutdown()
        if self.root:
            self.root.destroy()
