import os
import time
import numpy as np
import pygame
import config

if hasattr(os, "add_dll_directory"):
    _orig_add_dll_dir = os.add_dll_directory
    def _safe_add_dll_dir(path):
        if os.path.isdir(path):
            return _orig_add_dll_dir(path)
        class _DummyDir:
            def close(self): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
        return _DummyDir()
    os.add_dll_directory = _safe_add_dll_dir
    try:
        _safe_add_dll_dir(os.path.abspath("."))
    except Exception:
        pass


class SynthEngine:
    def __init__(self, sf2_path: str = config.DEFAULT_SF2_PATH):
        self.using_fluidsynth = False
        self.fs = None
        self.sfid = -1

        self.channel_programs = {ch: 0 for ch in range(16)}
        self.channel_volumes = {ch: 105 for ch in range(16)}
        self.channel_pans = {ch: 64 for ch in range(16)}
        self.channel_reverbs = {ch: 40 for ch in range(16)}
        self.active_notes = {ch: set() for ch in range(16)}
        self.sustained_notes = {ch: set() for ch in range(16)}
        self.channel_peaks = {ch: 0.0 for ch in range(16)}
        self.master_peak_l = 0.0
        self.master_peak_r = 0.0
        self.sustain_pedal = False

        self.maqam_idx = 0
        self.maqam_root = 0

        self._sound_cache = {}
        self._playing_channels = {}
        self._scheduled_events = []

        self._try_init_fluidsynth(sf2_path)

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=config.SAMPLE_RATE, size=-16, channels=2, buffer=config.AUDIO_BUFFER)
        pygame.mixer.set_num_channels(64)

    def _try_init_fluidsynth(self, sf2_path: str):
        candidate_paths = [
            sf2_path,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), sf2_path),
            "/usr/share/sounds/sf2/FluidR3_GM.sf2",
            "/usr/share/soundfonts/default.sf2",
        ]
        found_sf2 = next((p for p in candidate_paths if os.path.isfile(p)), None)
        if not found_sf2:
            return

        try:
            import fluidsynth
            fs = fluidsynth.Synth(samplerate=float(config.SAMPLE_RATE))
            for drv in ("wasapi", "dsound", "alsa", "pulseaudio", "coreaudio", "sdl2"):
                try:
                    fs.start(driver=drv)
                    break
                except Exception:
                    continue
            else:
                fs.start()

            sfid = fs.sfload(found_sf2)
            if sfid >= 0:
                self.fs = fs
                self.sfid = sfid
                self.using_fluidsynth = True
                for ch in range(16):
                    bank = 128 if ch == 9 else 0
                    self.fs.program_select(ch, self.sfid, bank, 0)
                    self.fs.cc(ch, 91, self.channel_reverbs[ch])
        except Exception:
            self.using_fluidsynth = False
            self.fs = None

    def get_cent_offset(self, note: int, channel: int = 0) -> float:
        if channel == 9:
            return 0.0
        maqam = config.MAQAMAT[self.maqam_idx]
        degree = (note - self.maqam_root) % 12
        return float(maqam["cents"].get(degree, 0.0))

    def set_maqam(self, maqam_idx: int, root_key: int = None):
        self.all_notes_off()
        self.maqam_idx = maqam_idx % len(config.MAQAMAT)
        if root_key is not None:
            self.maqam_root = root_key % 12

    def set_instrument(self, channel: int, program: int, bank: int = 0):
        program = max(0, min(127, program))
        self.all_notes_off(channel)
        self.channel_programs[channel] = program
        if self.using_fluidsynth and self.fs is not None:
            actual_bank = 128 if channel == 9 else bank
            try:
                self.fs.program_select(channel, self.sfid, actual_bank, program)
            except Exception:
                pass

    def set_volume(self, channel: int, volume: int):
        volume = max(0, min(127, volume))
        self.channel_volumes[channel] = volume
        if self.using_fluidsynth and self.fs is not None:
            try:
                self.fs.cc(channel, 7, volume)
            except Exception:
                pass

    def set_pan(self, channel: int, pan: int):
        pan = max(0, min(127, pan))
        self.channel_pans[channel] = pan
        if self.using_fluidsynth and self.fs is not None:
            try:
                self.fs.cc(channel, 10, pan)
            except Exception:
                pass

    def set_reverb(self, channel: int, reverb_level: int):
        reverb_level = max(0, min(127, reverb_level))
        self.channel_reverbs[channel] = reverb_level
        if self.using_fluidsynth and self.fs is not None:
            try:
                self.fs.cc(channel, 91, reverb_level)
            except Exception:
                pass

    def set_sustain_pedal(self, enabled: bool):
        self.sustain_pedal = enabled
        if self.using_fluidsynth and self.fs is not None:
            val = 127 if enabled else 0
            for ch in range(16):
                if ch != 9:
                    try:
                        self.fs.cc(ch, 64, val)
                    except Exception:
                        pass
        if not enabled:
            for ch in range(16):
                for note in list(self.sustained_notes[ch]):
                    if note not in self.active_notes[ch]:
                        self._builtin_note_off(ch, note)
                self.sustained_notes[ch].clear()

    def note_on(self, channel: int, note: int, velocity: int = 100):
        note = max(0, min(127, note))
        velocity = max(1, min(127, velocity))
        self.active_notes[channel].add(note)
        cent_offset = self.get_cent_offset(note, channel)

        vol_norm = (self.channel_volumes.get(channel, 105) / 127.0) * (velocity / 127.0)
        pan_norm = self.channel_pans.get(channel, 64) / 127.0
        self.channel_peaks[channel] = min(1.0, max(self.channel_peaks[channel], vol_norm))
        self.master_peak_l = min(1.0, max(self.master_peak_l, vol_norm * (1.0 - max(0.0, pan_norm - 0.5))))
        self.master_peak_r = min(1.0, max(self.master_peak_r, vol_norm * (1.0 - max(0.0, 0.5 - pan_norm))))

        if self.using_fluidsynth and self.fs is not None:
            try:
                if channel != 9:
                    pb_val = int(round((cent_offset / 200.0) * 8192.0))
                    self.fs.pitch_bend(channel, max(-8192, min(8191, pb_val)))
                self.fs.noteon(channel, note, velocity)
                return
            except Exception:
                pass

        self._builtin_note_on(channel, note, velocity, cent_offset)

    def note_off(self, channel: int, note: int):
        self.active_notes[channel].discard(note)
        if self.sustain_pedal and channel != 9:
            self.sustained_notes[channel].add(note)
            return

        if self.using_fluidsynth and self.fs is not None:
            try:
                self.fs.noteoff(channel, note)
                return
            except Exception:
                pass

        self._builtin_note_off(channel, note)

    def all_notes_off(self, channel: int = None):
        channels = [channel] if channel is not None else list(range(16))
        for ch in channels:
            for note in list(self.active_notes[ch] | self.sustained_notes[ch]):
                if self.using_fluidsynth and self.fs is not None:
                    try:
                        self.fs.noteoff(ch, note)
                    except Exception:
                        pass
                self._builtin_note_off(ch, note)
            self.active_notes[ch].clear()
            self.sustained_notes[ch].clear()

    def preview_instrument(self, channel: int, program: int):
        self.set_instrument(channel, program)
        if channel == 9:
            self.schedule_preview_notes(9, [(61, 115, 0.0, 0.14), (60, 110, 0.15, 0.28)])
        else:
            root = 60 + self.maqam_root
            self.schedule_preview_notes(
                channel,
                [(root, 95, 0.0, 0.22), (root + 4, 92, 0.05, 0.25), (root + 7, 92, 0.10, 0.30)]
            )

    def schedule_preview_notes(self, channel: int, notes_spec):
        now = time.perf_counter()
        for note, vel, start_offset, end_offset in notes_spec:
            self._scheduled_events.append((now + start_offset, "on", channel, note, vel))
            self._scheduled_events.append((now + end_offset, "off", channel, note, 0))

    def update(self):
        self.master_peak_l *= 0.965
        self.master_peak_r *= 0.965
        for ch in range(16):
            self.channel_peaks[ch] *= 0.96

        if not self._scheduled_events:
            return
        now = time.perf_counter()
        remaining = []
        for ev in self._scheduled_events:
            trig_time, action, ch, note, vel = ev
            if now >= trig_time:
                if action == "on":
                    self.note_on(ch, note, vel)
                else:
                    self.note_off(ch, note)
            else:
                remaining.append(ev)
        self._scheduled_events = remaining

    @staticmethod
    def _karplus_strong_pluck(freq: float, num_samples: int, sample_rate: int, damping: float = 0.994, brightness: float = 0.5) -> np.ndarray:
        period = max(2, int(round(sample_rate / max(20.0, freq))))
        rng = np.random.default_rng(int(freq * 100))
        burst = rng.uniform(-1.0, 1.0, period).astype(np.float32)
        burst = np.convolve(burst, np.array([0.25, 0.5, 0.25], dtype=np.float32), mode="same")
        n_blocks = (num_samples // period) + 2
        blocks = []
        curr = burst.copy()
        kernel = np.array([1.0 - brightness, brightness], dtype=np.float32)
        for _ in range(n_blocks):
            blocks.append(curr)
            shifted = np.roll(curr, 1)
            curr = ((curr * kernel[0]) + (shifted * kernel[1])) * damping
        wave = np.concatenate(blocks)[:num_samples]
        return wave

    @classmethod
    def synthesize_wave(
        cls,
        channel: int,
        program: int,
        note: int,
        duration: float = 1.4,
        sample_rate: int = config.SAMPLE_RATE,
        cent_offset: float = 0.0,
        reverb_amount: float = 0.3,
    ) -> np.ndarray:
        num_samples = max(1, int(sample_rate * duration))
        t = np.linspace(0.0, duration, num_samples, endpoint=False, dtype=np.float32)
        rng = np.random.default_rng(note + program * 131 + channel * 17)

        if channel == 9:
            if note == 36:
                f_env = 42.0 + 115.0 * np.exp(-t * 28.0)
                phase = 2.0 * np.pi * np.cumsum(f_env) / sample_rate
                click = rng.uniform(-0.6, 0.6, num_samples).astype(np.float32) * np.exp(-t * 95.0)
                wave = np.sin(phase) * np.exp(-t * 11.5) + click
            elif note == 38:
                noise = rng.uniform(-1.0, 1.0, num_samples).astype(np.float32)
                body = (np.sin(2.0 * np.pi * 185.0 * t) + 0.5 * np.sin(2.0 * np.pi * 330.0 * t)) * np.exp(-t * 19.0)
                wave = (noise * 0.68 * np.exp(-t * 14.5)) + (body * 0.42)
            elif note in (42, 46):
                decay = 38.0 if note == 42 else 8.5
                metallic = (
                    np.sign(np.sin(2.0 * np.pi * 3120.0 * t))
                    + np.sign(np.sin(2.0 * np.pi * 4580.0 * t))
                    + rng.uniform(-1.0, 1.0, num_samples).astype(np.float32)
                ) / 3.0
                wave = metallic * np.exp(-t * decay) * 0.65
            elif note == 39:
                noise = rng.uniform(-1.0, 1.0, num_samples).astype(np.float32)
                flutter = np.maximum(0.0, np.sin(2.0 * np.pi * 110.0 * t)) * np.exp(-t * 32.0) + np.exp(-t * 14.0) * 0.5
                wave = noise * flutter * 0.65
            elif note == 61:
                f_env = 94.0 + 95.0 * np.exp(-t * 22.0)
                phase = 2.0 * np.pi * np.cumsum(f_env) / sample_rate
                skin = np.sin(2.0 * np.pi * 240.0 * t) * np.exp(-t * 35.0) * 0.35
                wave = (np.sin(phase) * np.exp(-t * 9.5)) + skin
            elif note in (60, 62):
                base_f = 460.0 if note == 60 else 590.0
                ring = (
                    np.sin(2.0 * np.pi * base_f * t)
                    + 0.65 * np.sin(2.0 * np.pi * (base_f * 2.14) * t)
                    + 0.35 * np.sin(2.0 * np.pi * (base_f * 3.41) * t)
                )
                slap = rng.uniform(-0.8, 0.8, num_samples).astype(np.float32) * np.exp(-t * 65.0)
                wave = (ring * np.exp(-t * 28.0) * 0.75) + slap
            elif note == 54:
                jingle = (
                    np.sin(2.0 * np.pi * 5200.0 * t)
                    + np.sin(2.0 * np.pi * 7100.0 * t)
                    + rng.uniform(-1.0, 1.0, num_samples).astype(np.float32)
                ) * 0.33
                wave = jingle * np.exp(-t * 22.0)
            elif note in (76, 77, 75):
                f = 1200.0 if note == 76 else (840.0 if note == 77 else 620.0)
                wave = (np.sin(2.0 * np.pi * f * t) + 0.3 * np.sin(2.0 * np.pi * (f * 2.4) * t)) * np.exp(-t * 45.0)
            else:
                wave = np.sin(2.0 * np.pi * 200.0 * t) * np.exp(-t * 15.0)
            return np.clip(wave, -1.0, 1.0).astype(np.float32)

        freq = 440.0 * (2.0 ** (((note + (cent_offset / 100.0)) - 69.0) / 12.0))
        family = program // 8

        if program in (24, 25, 45, 46, 104, 105, 106, 107) or family == 3:
            damping = 0.996 if program in (105, 107) else 0.993
            bright = 0.35 if program == 105 else 0.55
            pluck1 = cls._karplus_strong_pluck(freq, num_samples, sample_rate, damping=damping, brightness=bright)
            pluck2 = cls._karplus_strong_pluck(freq * 1.0018, num_samples, sample_rate, damping=damping, brightness=bright)
            body_res = np.sin(2.0 * np.pi * freq * t) * np.exp(-t * 3.5) * 0.25
            wave = (pluck1 * 0.5) + (pluck2 * 0.5) + body_res
        elif family in (0, 1):
            inharm = 1.0004
            wave = (
                1.00 * np.sin(2.0 * np.pi * freq * t) * np.exp(-t * 1.8)
                + 0.48 * np.sin(2.0 * np.pi * (freq * 2.0 * inharm) * t) * np.exp(-t * 3.2)
                + 0.24 * np.sin(2.0 * np.pi * (freq * 3.0 * inharm) * t) * np.exp(-t * 4.8)
                + 0.12 * np.sin(2.0 * np.pi * (freq * 4.0 * inharm) * t) * np.exp(-t * 6.5)
                + 0.06 * np.sin(2.0 * np.pi * (freq * 5.0 * inharm) * t) * np.exp(-t * 8.5)
            )
            attack = np.minimum(1.0, t / 0.004)
            wave = wave * attack
        elif family == 2:
            vib = 1.0 + 0.0025 * np.sin(2.0 * np.pi * 6.2 * t)
            ph = 2.0 * np.pi * freq * vib * t
            wave = (
                0.8 * np.sin(ph)
                + 0.6 * np.sin(ph * 2.0)
                + 0.45 * np.sin(ph * 3.0)
                + 0.3 * np.sin(ph * 4.0)
                + 0.2 * np.sin(ph * 6.0)
            )
            env = np.minimum(1.0, t / 0.015) * np.exp(-t * 0.45)
            wave = wave * env
        elif family == 4:
            ph = 2.0 * np.pi * freq * t
            sub = np.sin(ph)
            growl = np.tanh(2.4 * np.sin(ph) + 1.2 * np.sin(2.0 * ph)) * np.exp(-t * 4.5)
            env = np.minimum(1.0, t / 0.006) * np.exp(-t * 2.4)
            wave = (sub * 0.65 + growl * 0.35) * env
        elif family in (5, 6) or program == 110:
            vib_delay = np.minimum(1.0, t / 0.25)
            vib = 1.0 + (0.0042 * vib_delay * np.sin(2.0 * np.pi * 5.6 * t))
            ph = 2.0 * np.pi * freq * vib * t
            ph2 = 2.0 * np.pi * (freq * 1.003) * vib * t
            saw1 = np.zeros_like(t)
            saw2 = np.zeros_like(t)
            for k in range(1, 8):
                saw1 += (np.sin(k * ph) / k) * np.exp(-k * 0.18)
                saw2 += (np.sin(k * ph2) / k) * np.exp(-k * 0.18)
            attack_time = 0.055 if family == 5 else 0.11
            env = np.minimum(1.0, t / attack_time) * np.exp(-t * 0.55)
            wave = (saw1 + saw2) * 0.5 * env
        elif family in (7, 8) or program == 111:
            vib = 1.0 + 0.003 * np.sin(2.0 * np.pi * 5.2 * t)
            ph = 2.0 * np.pi * freq * vib * t
            mod_index = 2.8 * np.minimum(1.0, t / 0.03) * np.exp(-t * 1.8)
            wave = np.sin(ph + mod_index * np.sin(ph)) + 0.4 * np.sin(2.0 * ph)
            env = np.minimum(1.0, t / 0.025) * np.exp(-t * 0.9)
            wave = wave * env
        elif family == 9:
            vib_delay = np.minimum(1.0, t / 0.18)
            vib = 1.0 + (0.0055 * vib_delay * np.sin(2.0 * np.pi * 5.4 * t))
            ph = 2.0 * np.pi * freq * vib * t
            breath_raw = rng.uniform(-1.0, 1.0, num_samples).astype(np.float32)
            breath_filtered = np.convolve(breath_raw, np.ones(7, dtype=np.float32) / 7.0, mode="same")
            breath_env = (0.18 * np.exp(-t * 8.0)) + 0.07
            tone = np.sin(ph) + 0.38 * np.sin(2.0 * ph) + 0.14 * np.sin(3.0 * ph)
            env = np.minimum(1.0, t / 0.045) * np.exp(-t * 0.7)
            wave = (tone + breath_filtered * breath_env * np.sin(ph)) * env
        else:
            vib = 1.0 + 0.003 * np.sin(2.0 * np.pi * 5.0 * t)
            ph = 2.0 * np.pi * freq * vib * t
            wave = 0.6 * np.tanh(1.8 * np.sin(ph)) + 0.4 * np.sin(2.0 * ph)
            env = np.minimum(1.0, t / 0.015) * np.exp(-t * 1.2)
            wave = wave * env

        if reverb_amount > 0.02:
            d1 = int(0.029 * sample_rate)
            d2 = int(0.053 * sample_rate)
            rev = np.zeros_like(wave)
            if d1 < num_samples:
                rev[d1:] += wave[:-d1] * 0.35 * reverb_amount
            if d2 < num_samples:
                rev[d2:] += wave[:-d2] * 0.22 * reverb_amount
            wave = wave + rev

        peak = np.max(np.abs(wave))
        if peak > 1e-6:
            wave = wave / peak
        return (wave * 0.58).astype(np.float32)

    def _builtin_note_on(self, channel: int, note: int, velocity: int, cent_offset: float):
        if not pygame.mixer.get_init():
            return
        program = self.channel_programs.get(channel, 0)
        rev_amt = self.channel_reverbs.get(channel, 40) / 127.0
        cache_key = (channel == 9, program if channel != 9 else 0, note, int(round(cent_offset)), int(round(rev_amt * 4)))

        if cache_key not in self._sound_cache:
            if len(self._sound_cache) > 512:
                self._sound_cache.clear()
            dur = 0.42 if channel == 9 else 1.8
            mono = self.synthesize_wave(
                channel, program, note, duration=dur, cent_offset=cent_offset, reverb_amount=rev_amt
            )
            stereo = np.column_stack((mono, mono))
            pcm16 = np.ascontiguousarray((stereo * 32767.0), dtype=np.int16)
            self._sound_cache[cache_key] = pygame.sndarray.make_sound(pcm16)

        snd = self._sound_cache[cache_key]
        ch_vol = (self.channel_volumes.get(channel, 105) / 127.0) * (velocity / 127.0)
        pan = self.channel_pans.get(channel, 64) / 127.0
        left_vol = ch_vol * (1.0 - max(0.0, pan - 0.5) * 1.6)
        right_vol = ch_vol * (1.0 - max(0.0, 0.5 - pan) * 1.6)

        mixer_ch = pygame.mixer.find_channel(True)
        if mixer_ch is not None:
            mixer_ch.set_volume(max(0.0, min(1.0, left_vol)), max(0.0, min(1.0, right_vol)))
            mixer_ch.play(snd)
            self._playing_channels[(channel, note)] = mixer_ch

    def _builtin_note_off(self, channel: int, note: int):
        if channel == 9:
            return
        mixer_ch = self._playing_channels.pop((channel, note), None)
        if mixer_ch is not None:
            mixer_ch.fadeout(110)

    def shutdown(self):
        self.all_notes_off()
        if self.using_fluidsynth and self.fs is not None:
            try:
                self.fs.delete()
            except Exception:
                pass
