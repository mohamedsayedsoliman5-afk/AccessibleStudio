# Accessible Mini-DAW & Live Musical Instrument Studio
## استوديو الألحان الميسر للمكفوفين وضعاف البصر

A production-ready, screen-reader-first Desktop Digital Audio Workstation (DAW) and Live Instrument Studio engineered specifically for blind and visually impaired musicians.

Built with Python 3.10+, Pygame, FluidSynth (16 MIDI Channels), CyTolk (NVDA/JAWS/SAPI direct bridge), and Mido.

---

## 1. Key Features & Accessibility Innovations

1. **Instant Interruptible Speech Output:**
   - Prioritizes **CyTolk** (direct C-bindings to Tolk) for sub-millisecond, interruptible speech via **NVDA**, **JAWS**, or Windows SAPI.
   - Non-blocking daemon worker fallbacks (**pyttsx3**, **SAPI COM**, **speech-dispatcher**, or **termux-tts**) guarantee audio synthesis and sequencer timing are **never blocked** by speech.
   - Bilingual support: **Arabic** as the primary language (switchable to **English** at any time via `F12`).

2. **Auditory Earcon System (Non-Verbal Audio Cues):**
   - Blind musicians do not have to wait for speech synthesis to finish before making musical decisions.
   - Specialized earcons for:
     - `Record Start`: Ascending high double-beep ($C_6 \to G_6$).
     - `Record Stop`: Descending double-beep ($G_6 \to C_6$).
     - `Play / Stop`: Bright chime ($E_5$) and low click ($C_4$).
     - `Boundary Reached`: Low warning buzzer ($C_3$).
     - `Smart Quantization`: Ascending 4-note arpeggio ($C_5 \to E_5 \to G_5 \to C_6$).
     - `Step On / Off`: Distinct woodblock clicks.

3. **2-Octave Ergonomic QWERTY Keyboard:**
   - **Lower Octave:** `Z`, `S`, `X`, `D`, `C`, `V`, `G`, `B`, `H`, `N`, `J`, `M`
   - **Upper Octave:** `Q`, `2`, `W`, `3`, `E`, `R`, `5`, `T`, `6`, `Y`, `7`, `U`, `I`
   - Real-time octave shifting (`PageUp` / `PageDown`) and velocity control (`Home` / `End`).
   - Hardware debounce and anti-repeat tracking prevents OS key-repeat stutter while holding musical chords.

4. **Multi-Track Sequencer & Looper (8 User Tracks + Percussion):**
   - High-precision clock based on `time.perf_counter()`.
   - **4-Beat Audible Count-in** before recording begins (Beat 1 high woodblock, Beats 2-4 low woodblocks).
   - Real-time **Overdubbing** and synchronized multi-track playback.
   - **Smart Quantization (`F6`)**: Snaps notes to the nearest 1/16th or 1/8th grid mathematically while preserving musical phrasing.
   - Multi-level **Undo (`F9`)** for each individual track.

5. **16-Step Drum Grid Mode (`F5`):**
   - Non-visual rhythmic pattern sequencing.
   - Navigate 16 steps using `Left` and `Right` arrows (reads step number + active drum hits).
   - Select drum piece using `Up` and `Down` arrows (instant audio preview of Kick, Snare, Hi-Hats, Darbuka Dum/Tek, Claps, etc.).
   - `Spacebar` toggles drum hits on/off with earcon and speech feedback.
   - Built-in rhythmic presets: Oriental Maqsum (`Ctrl+M`), Four-on-the-Floor (`Ctrl+D`), Classic Rock (`Ctrl+K`).
   - `Enter` transfers the finished 16-step rhythm into any user track.

6. **Studio Export Utilities (`F11`):**
   - Exports the multi-track arrangement into **Standard MIDI File Type 1 (.mid)** with separate tracks, instrument bank programs, CC#7 volume, and CC#10 panning.
   - Renders a CD-quality **16-bit 44.1kHz Stereo WAV file (.wav)** using FluidSynth offline rendering or the internal additive synthesis engine.

---

## 2. Complete Keyboard Shortcuts Reference

| Key / Shortcut | Function | Description (Arabic / English) |
| :--- | :--- | :--- |
| `Spacebar` | Play / Stop | تشغيل وإيقاف العزف أو التسجيل / Toggle Transport Playback & Stop |
| `R` | Record | بدء التسجيل مع عد تنازلي 4 نبضات / Record with 4-beat audible count-in |
| `L` | Toggle Loop | تفعيل أو إيقاف التكرار الحلقي / Toggle continuous loop mode |
| `1` to `8` | Track 1–8 | اختيار المسار الموسيقي النشط / Select active track |
| `Tab` | Next Instrument | الآلة التالية من بنك الـ 128 آلة / Next General MIDI instrument |
| `Shift + Tab` | Prev Instrument | الآلة السابقة / Previous General MIDI instrument |
| `F1` | Help Manual | قراءة دليل الاختصارات بالصوت / Read keyboard shortcuts manual |
| `F2` | Track Info | نطق تفاصيل المسار النشط / Announce track instrument, volume, pan |
| `F3` | Metronome | تشغيل/إيقاف صوت المترونوم / Toggle metronome click |
| `F4` | Tempo / BPM | إعلان سرعة الإيقاع الحالية / Announce current BPM tempo |
| `F5` | Drum Grid | فتح وإغلاق شبكة الطبول 16 خطوة / Toggle 16-step drum grid mode |
| `F6` | Quantize | تصحيح التوقيت بدقة 1/16 / Smart quantize track to 1/16th note |
| `F7` | Solo Track | تفعيل/إلغاء العزف المنفرد للمسار / Solo active track |
| `F8` | Mute Track | كتم/إلغاء كتم المسار النشط / Mute/Unmute active track |
| `F9` | Undo | التراجع عن آخر تسجيل في المسار / Undo last recording pass |
| `F10` | Clear Track | مسح نوتات المسار الحالي / Clear active track notes |
| `F11` | Export | تصدير إلى ملف ميدي و ملف صوتي واف / Export to .mid and .wav |
| `F12` | Language | تبديل لغة النطق (عربي / إنجليزي) / Toggle speech language (AR / EN) |
| `Up / Down` | Volume / Drum | تعديل صوت المسار أو اختيار آلة الدرامز / Volume CC#7 (+-5) or Drum piece |
| `Left / Right` | Pan / Step | توزيع الصوت يمين/يسار أو التنقل بين الخطوات / Pan CC#10 or Step navigate |
| `PageUp / Down`| Octave Shift | رفع أو خفض الأوكتاف / Octave Shift Up / Down |
| `Home / End` | Velocity | تعديل قوة اللمس / Note Velocity (+-10) |
| `[` and `]` | BPM Adjust | خفض أو رفع السرعة بمقدار 5 نبضات / Tempo down/up by 5 BPM |
| `Enter` | Status Summary | نطق موقع المازورة والنبضة والسرعة / Announce Bar, Beat, and status |
| `Escape` | MIDI Panic | إخماد جميع الأصوات فوراً بحالات الطوارئ / Silence all ringing notes |

---

## 3. Project File Structure

```text
blind_daw/
├── config.py            # Keybindings, 128 GM instruments, GM drum bank, localization
├── speech_engine.py     # CyTolk screen-reader bridge, daemon fallbacks, earcons
├── synth_engine.py      # FluidSynth 16-channel mixer & software synth fallback
├── keyboard_mapper.py   # 2-octave QWERTY matrix, octave shifts, debounce logic
├── sequencer.py         # 8-track MIDI recorder, 4-beat count-in, smart quantizer
├── step_sequencer.py    # 16-step accessible drum grid with oriental & modern presets
├── exporter.py          # Type-1 Standard MIDI compiler & 16-bit 44.1kHz WAV renderer
├── main.py              # Pygame low-latency event loop & hotkey dispatcher
├── requirements.txt     # Python package dependencies
├── README.md            # Comprehensive documentation & manual
├── soundfonts/          # Directory for .sf2 SoundFont files
├── exports/             # Exported .mid and .wav files
└── recordings/          # Session recordings
```

---

## 4. Installation & Setup

### Prerequisites
- Python 3.10 or higher.
- FluidSynth audio library installed on your system:
  - **Windows:** Download FluidSynth binaries or install via `vcpkg install fluidsynth` or `winget install fluidsynth`.
  - **Linux (Ubuntu/Debian):** `sudo apt install fluidsynth fluid-soundfont-gm`
  - **macOS:** `brew install fluidsynth`
  - **Android Termux:** `pkg install fluidsynth python-numpy`

### Python Environment Setup
```bash
cd blind_daw
pip install -r requirements.txt
```

### Launching the Studio
```bash
# Launch with default SoundFont detection:
python main.py

# Launch specifying a custom SoundFont path:
python main.py /path/to/my_soundfont.sf2
```

---

## 5. Screen Reader Compatibility

Tested and optimized for:
- **NVDA (NonVisual Desktop Access)**: Full instant speech and earcon support via CyTolk / Tolk.
- **JAWS for Windows**: Native detection through Tolk.
- **Windows SAPI 5**: High-speed fallback with interruptibility.
- **Linux Speech Dispatcher (`spd-say`)**: Native Orca/Linux terminal accessibility.
- **Android Termux (`termux-tts-speak`)**: Speech support in mobile development environments.
