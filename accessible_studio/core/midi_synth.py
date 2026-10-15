"""
AccessibleStudio Core - Low-Latency MIDI Synthesis Engine
=========================================================
Engineered for zero-latency polyphonic live playback on Windows via
the native Microsoft GS Wavetable Synthesizer (winmm.dll).
Supports 16 independent MIDI channels, volume (CC#7), pan (CC#10),
pitch bend, GM percussion on Channel 9, and cross-platform fallbacks.
"""

import os
import sys
import time
import math
import wave
import struct
import threading
from typing import Optional, List, Dict, Tuple

from accessible_studio.config import (
    SAMPLE_RATE,
    BUFFER_SIZE,
    POLYPHONY,
    METRONOME_CHANNEL,
    EARCON_CHANNEL,
    SOUNDFONT_SEARCH_PATHS
)


class WinMMMidiSynth:
    """
    Direct Windows MultiMedia (winmm.dll) MIDI Synthesizer.
    Zero external dependencies, zero DLL downloads, zero SoundFont files required.
    Uses Microsoft GS Wavetable Synth built into every Windows installation (XP to 11).
    Provides sub-5ms low-latency polyphonic instrument playback across all 16 MIDI channels.
    """

    def __init__(self):
        self.handle = None
        self._winmm = None
        self.channel_volumes = [100] * 16
        self.channel_pans = [64] * 16
        self.channel_programs = [0] * 16
        self._open()

    def _open(self):
        try:
            import ctypes
            self._winmm = ctypes.windll.winmm
            hmo = ctypes.c_void_p()
            # MIDI_MAPPER = -1 (0xFFFFFFFF)
            res = self._winmm.midiOutOpen(ctypes.byref(hmo), -1, 0, 0, 0)
            if res == 0:
                self.handle = hmo
                print("[MidiSynth] Windows Native GS Wavetable Synth initialized successfully.")
                for ch in range(16):
                    self.set_volume(ch, self.channel_volumes[ch])
                    self.set_pan(ch, self.channel_pans[ch])
            else:
                print(f"[MidiSynth] midiOutOpen returned error code: {res}")
        except Exception as e:
            print(f"[MidiSynth] Native winmm MIDI unavailable: {e}")
            self.handle = None

    def _send_short_msg(self, status: int, data1: int = 0, data2: int = 0):
        if not self.handle or not self._winmm:
            return
        import ctypes
        msg = (status & 0xFF) | ((data1 & 0x7F) << 8) | ((data2 & 0x7F) << 16)
        try:
            self._winmm.midiOutShortMsg(self.handle, ctypes.c_ulong(msg))
        except Exception:
            pass

    def note_on(self, channel: int, note: int, velocity: int):
        ch = max(0, min(15, channel))
        n = max(0, min(127, note))
        v = max(0, min(127, velocity))
        self._send_short_msg(0x90 | ch, n, v)

    def note_off(self, channel: int, note: int):
        ch = max(0, min(15, channel))
        n = max(0, min(127, note))
        self._send_short_msg(0x80 | ch, n, 0)

    def program_change(self, channel: int, program: int):
        ch = max(0, min(15, channel))
        p = max(0, min(127, program))
        self.channel_programs[ch] = p
        # Channel 9 (10 in 1-based indexing) is standard GM Percussion in MIDI
        if ch != 9:
            self._send_short_msg(0xC0 | ch, p, 0)

    def set_volume(self, channel: int, volume: int):
        ch = max(0, min(15, channel))
        v = max(0, min(127, volume))
        self.channel_volumes[ch] = v
        self._send_short_msg(0xB0 | ch, 7, v)

    def set_pan(self, channel: int, pan: int):
        ch = max(0, min(15, channel))
        p = max(0, min(127, pan))
        self.channel_pans[ch] = p
        self._send_short_msg(0xB0 | ch, 10, p)

    def pitch_bend(self, channel: int, value: int):
        ch = max(0, min(15, channel))
        val = max(0, min(16383, value + 8192))
        lsb = val & 0x7F
        msb = (val >> 7) & 0x7F
        self._send_short_msg(0xE0 | ch, lsb, msb)

    def all_notes_off(self, channel: Optional[int] = None):
        channels = [channel] if channel is not None else list(range(16))
        for ch in channels:
            self._send_short_msg(0xB0 | ch, 123, 0)
            self._send_short_msg(0xB0 | ch, 120, 0)

    def panic(self):
        self.all_notes_off()
        for ch in range(16):
            for n in range(128):
                self._send_short_msg(0x80 | ch, n, 0)

    def close(self):
        if self.handle and self._winmm:
            self.panic()
            try:
                self._winmm.midiOutClose(self.handle)
            except Exception:
                pass
            self.handle = None


class SoftwareSynthFallback:
    """Pure Python tracking synthesizer for zero-dependency execution in test/CI environments."""

    def __init__(self):
        self.volumes = [100] * 16
        self.pans = [64] * 16
        self.programs = [0] * 16
        self._active_voices: Dict[Tuple[int, int], float] = {}

    def note_on(self, channel: int, note: int, velocity: int):
        self._active_voices[(channel, note)] = time.time()

    def note_off(self, channel: int, note: int):
        self._active_voices.pop((channel, note), None)

    def program_change(self, channel: int, program: int):
        self.programs[channel] = program

    def set_volume(self, channel: int, volume: int):
        self.volumes[channel] = volume

    def set_pan(self, channel: int, pan: int):
        self.pans[channel] = pan

    def all_notes_off(self, channel: int):
        keys = [k for k in self._active_voices.keys() if k[0] == channel]
        for k in keys:
            self._active_voices.pop(k, None)

    def close(self):
        self._active_voices.clear()


class MidiSynthEngine:
    """
    Unified Multi-Channel Audio Synthesis & Mixing Engine.
    Seamlessly manages WinMM on Windows, FluidSynth on Linux/Mac, or Software Fallback.
    """

    def __init__(self, soundfont_path: Optional[str] = None):
        self.fs = None
        self.sfid = -1
        self.soundfont_path = None
        self.is_winmm = False
        self._winmm_synth = None
        self.is_fallback = False
        self._fallback_synth = None
        self._lock = threading.Lock()

        # Track channel states (volume, pan, program)
        self.channel_volumes: List[int] = [100] * 16
        self.channel_pans: List[int] = [64] * 16       # 64 = Center
        self.channel_programs: List[int] = [0] * 16
        self.channel_programs[METRONOME_CHANNEL] = 0  # Standard Drum Bank on Ch 9

        self._init_synth(soundfont_path)

    def _init_synth(self, custom_sf_path: Optional[str] = None):
        # 1. On Windows, WinMMMidiSynth is primary (zero latency, zero external soundfont files needed)
        if sys.platform == "win32":
            try:
                winmm = WinMMMidiSynth()
                if winmm.handle:
                    self.is_winmm = True
                    self._winmm_synth = winmm
                    print("[MidiSynthEngine] Active Engine: Windows Native GS Wavetable Synthesizer.")
                    return
            except Exception as e:
                print(f"[MidiSynthEngine] WinMM init note: {e}")

        # 2. Try FluidSynth if available (Linux / macOS)
        try:
            import fluidsynth
            self.fs = fluidsynth.Synth(samplerate=float(SAMPLE_RATE), gain=0.8, polyphony=POLYPHONY)
            driver = "wasapi" if sys.platform == "win32" else ("coreaudio" if sys.platform == "darwin" else "pulseaudio")
            try:
                self.fs.start(driver=driver)
            except Exception:
                self.fs.start()

            sf_file = custom_sf_path
            if not sf_file:
                for p in SOUNDFONT_SEARCH_PATHS:
                    if os.path.exists(p):
                        sf_file = p
                        break
            if sf_file and os.path.exists(sf_file):
                self.sfid = self.fs.sfload(sf_file)
                self.soundfont_path = sf_file

            for ch in range(16):
                self.fs.cc(ch, 7, self.channel_volumes[ch])
                self.fs.cc(ch, 10, self.channel_pans[ch])
                if ch != METRONOME_CHANNEL:
                    self.fs.program_change(ch, self.channel_programs[ch])
                else:
                    self.fs.bank_select(METRONOME_CHANNEL, 128)

            self.fs.program_change(EARCON_CHANNEL, 13)  # Xylophone for earcons
            return

        except Exception as err:
            self._init_software_fallback()

    def _init_software_fallback(self):
        self.is_fallback = True
        self._fallback_synth = SoftwareSynthFallback()
        print("[MidiSynthEngine] Software Synth Fallback active.")

    def note_on(self, channel: int, note: int, velocity: int):
        channel = max(0, min(15, channel))
        note = max(0, min(127, note))
        velocity = max(0, min(127, velocity))

        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.note_on(channel, note, velocity)
                return
            if not self.is_fallback and self.fs:
                try:
                    self.fs.noteon(channel, note, velocity)
                    return
                except Exception:
                    pass
            if self._fallback_synth:
                self._fallback_synth.note_on(channel, note, velocity)

    def note_off(self, channel: int, note: int):
        channel = max(0, min(15, channel))
        note = max(0, min(127, note))

        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.note_off(channel, note)
                return
            if not self.is_fallback and self.fs:
                try:
                    self.fs.noteoff(channel, note)
                    return
                except Exception:
                    pass
            if self._fallback_synth:
                self._fallback_synth.note_off(channel, note)

    def program_change(self, channel: int, program: int):
        channel = max(0, min(15, channel))
        program = max(0, min(127, program))
        self.channel_programs[channel] = program

        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.program_change(channel, program)
                return
            if not self.is_fallback and self.fs:
                try:
                    if channel != METRONOME_CHANNEL:
                        self.fs.program_change(channel, program)
                    return
                except Exception:
                    pass
            if self._fallback_synth:
                self._fallback_synth.program_change(channel, program)

    def set_volume(self, channel: int, volume: int):
        channel = max(0, min(15, channel))
        volume = max(0, min(127, volume))
        self.channel_volumes[channel] = volume

        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.set_volume(channel, volume)
                return
            if not self.is_fallback and self.fs:
                try:
                    self.fs.cc(channel, 7, volume)
                    return
                except Exception:
                    pass
            if self._fallback_synth:
                self._fallback_synth.set_volume(channel, volume)

    def set_pan(self, channel: int, pan: int):
        channel = max(0, min(15, channel))
        pan = max(0, min(127, pan))
        self.channel_pans[channel] = pan

        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.set_pan(channel, pan)
                return
            if not self.is_fallback and self.fs:
                try:
                    self.fs.cc(channel, 10, pan)
                    return
                except Exception:
                    pass
            if self._fallback_synth:
                self._fallback_synth.set_pan(channel, pan)

    def pitch_bend(self, channel: int, value: int):
        channel = max(0, min(15, channel))
        midi_val = max(0, min(16383, value + 8192))
        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.pitch_bend(channel, value)
                return
            if not self.is_fallback and self.fs:
                try:
                    self.fs.pitch_bend(channel, midi_val)
                except Exception:
                    pass

    def all_notes_off(self, channel: Optional[int] = None):
        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.all_notes_off(channel)
                return
            channels = [channel] if channel is not None else list(range(16))
            for ch in channels:
                if not self.is_fallback and self.fs:
                    try:
                        self.fs.cc(ch, 120, 0)
                        self.fs.cc(ch, 123, 0)
                    except Exception:
                        pass
                if self._fallback_synth:
                    self._fallback_synth.all_notes_off(ch)

    def panic(self):
        self.all_notes_off()
        with self._lock:
            if self.is_winmm and self._winmm_synth:
                self._winmm_synth.panic()
                return
            if not self.is_fallback and self.fs:
                for ch in range(16):
                    for n in range(128):
                        try:
                            self.fs.noteoff(ch, n)
                        except Exception:
                            pass

    def render_wav_offline(self, midi_path: str, output_wav_path: str) -> bool:
        """High-precision software additive renderer for exporting WAV without C-libraries."""
        if not os.path.exists(midi_path):
            return False

        try:
            import mido
            mid = mido.MidiFile(midi_path)
            total_time = mid.length + 1.0
            total_samples = int(total_time * SAMPLE_RATE)

            left_buf = [0.0] * total_samples
            right_buf = [0.0] * total_samples
            current_time = 0.0
            active_notes: Dict[Tuple[int, int], List[float]] = {}

            for msg in mid:
                current_time += msg.time
                if msg.type == "note_on" and msg.velocity > 0:
                    freq = 440.0 * (2.0 ** ((msg.note - 69) / 12.0))
                    active_notes[(msg.channel, msg.note)] = [current_time, msg.velocity / 127.0, freq]
                elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                    key = (msg.channel, msg.note)
                    if key in active_notes:
                        start_t, vel, freq = active_notes.pop(key)
                        end_t = current_time
                        start_s = int(start_t * SAMPLE_RATE)
                        end_s = min(total_samples, int(end_t * SAMPLE_RATE))
                        duration_s = max(1, end_s - start_s)
                        pan = self.channel_pans[min(15, msg.channel)] / 127.0
                        vol = (self.channel_volumes[min(15, msg.channel)] / 127.0) * vel * 0.35

                        for i in range(duration_s):
                            idx = start_s + i
                            if idx >= total_samples:
                                break
                            t_sec = i / SAMPLE_RATE
                            env = 1.0
                            if i < 441:
                                env = i / 441.0
                            elif i > duration_s - 882:
                                env = max(0.0, (duration_s - i) / 882.0)

                            sample = (
                                math.sin(2.0 * math.pi * freq * t_sec) * 0.6 +
                                math.sin(4.0 * math.pi * freq * t_sec) * 0.25 +
                                math.sin(6.0 * math.pi * freq * t_sec) * 0.15
                            ) * vol * env

                            left_buf[idx] += sample * (1.0 - pan)
                            right_buf[idx] += sample * pan

            with wave.open(output_wav_path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                frames = bytearray()
                for s in range(total_samples):
                    l_val = max(-1.0, min(1.0, left_buf[s]))
                    r_val = max(-1.0, min(1.0, right_buf[s]))
                    l_int = int(l_val * 32767.0)
                    r_int = int(r_val * 32767.0)
                    frames.extend(struct.pack("<hh", l_int, r_int))
                wf.writeframes(frames)

            return True
        except Exception as e:
            print(f"[MidiSynthEngine] WAV render error: {e}")
            return False

    def close(self):
        with self._lock:
            if self.is_winmm and self._winmm_synth:
                try:
                    self._winmm_synth.close()
                except Exception:
                    pass
            if not self.is_fallback and self.fs:
                try:
                    self.fs.delete()
                except Exception:
                    pass
            if self._fallback_synth:
                self._fallback_synth.close()
