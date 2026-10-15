import os
import time
import wave
import numpy as np
import mido
import config


class StudioExporter:
    @staticmethod
    def export_all(sequencer, synth_engine, speech):
        os.makedirs(config.EXPORT_DIR, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        mid_path = os.path.join(config.EXPORT_DIR, f"project_{timestamp}.mid")
        wav_path = os.path.join(config.EXPORT_DIR, f"project_{timestamp}.wav")

        speech.speak("جاري تصدير المشروع إلى ملف ميدي وملف صوتي ماستر ويف")
        StudioExporter.export_midi(sequencer, synth_engine, mid_path)
        StudioExporter.export_wav(sequencer, synth_engine, wav_path)
        speech.speak(f"تم التصدير بنجاح في مجلد إكسبورتس باسم بروجكت {timestamp}")
        return mid_path, wav_path

    @staticmethod
    def export_midi(sequencer, synth_engine, filepath: str):
        mid = mido.MidiFile(type=1, ticks_per_beat=480)
        tempo = mido.bpm2tempo(sequencer.bpm)

        for tr in sequencer.tracks:
            if not tr.events:
                continue
            midi_track = mido.MidiTrack()
            mid.tracks.append(midi_track)

            inst_name = config.GM_INSTRUMENTS.get(tr.program, {}).get("en", f"Track {tr.track_id + 1}")
            midi_track.append(mido.MetaMessage("track_name", name=inst_name, time=0))
            if tr.track_id == 0:
                midi_track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

            if tr.channel != 9:
                midi_track.append(mido.Message("program_change", channel=tr.channel, program=tr.program, time=0))
            midi_track.append(mido.Message("control_change", channel=tr.channel, control=7, value=tr.volume, time=0))
            midi_track.append(mido.Message("control_change", channel=tr.channel, control=10, value=tr.pan, time=0))
            midi_track.append(mido.Message("control_change", channel=tr.channel, control=91, value=tr.reverb, time=0))

            sorted_events = sorted(tr.events, key=lambda e: e["time"])
            last_tick = 0
            for ev in sorted_events:
                curr_tick = int(round((ev["time"] / sequencer.beat_duration) * 480))
                delta_tick = max(0, curr_tick - last_tick)
                last_tick = curr_tick
                if ev["type"] == "note_on" and tr.channel != 9:
                    cent = synth_engine.get_cent_offset(ev["note"], tr.channel)
                    pb = int(round((cent / 200.0) * 8192.0))
                    midi_track.append(mido.Message("pitchwheel", channel=tr.channel, pitch=max(-8192, min(8191, pb)), time=delta_tick))
                    delta_tick = 0
                msg_type = "note_on" if ev["type"] == "note_on" else "note_off"
                midi_track.append(
                    mido.Message(msg_type, channel=tr.channel, note=ev["note"], velocity=ev["vel"], time=delta_tick)
                )

        mid.save(filepath)

    @staticmethod
    def export_wav(sequencer, synth_engine, filepath: str):
        sr = config.SAMPLE_RATE
        total_duration = sequencer.loop_duration + 1.2
        total_samples = int(sr * total_duration)
        mix_left = np.zeros(total_samples, dtype=np.float32)
        mix_right = np.zeros(total_samples, dtype=np.float32)

        for tr in sequencer.tracks:
            if not sequencer.is_track_audible(tr) or not tr.events:
                continue

            open_notes = {}
            note_spans = []
            for ev in sorted(tr.events, key=lambda e: e["time"]):
                if ev["type"] == "note_on":
                    open_notes[ev["note"]] = (ev["time"], ev["vel"])
                elif ev["type"] == "note_off" and ev["note"] in open_notes:
                    t_start, vel = open_notes.pop(ev["note"])
                    dur = max(0.08, ev["time"] - t_start)
                    note_spans.append((ev["note"], vel, t_start, dur))

            for note, (t_start, vel) in open_notes.items():
                note_spans.append((note, vel, t_start, 0.28))

            vol_gain = tr.volume / 127.0
            pan_norm = tr.pan / 127.0
            rev_amt = tr.reverb / 127.0
            l_pan = vol_gain * (1.0 - max(0.0, pan_norm - 0.5) * 1.6)
            r_pan = vol_gain * (1.0 - max(0.0, 0.5 - pan_norm) * 1.6)

            for note, vel, t_start, dur in note_spans:
                render_dur = dur + 0.22 if tr.channel != 9 else 0.42
                cent = synth_engine.get_cent_offset(note, tr.channel)
                wave_mono = synth_engine.synthesize_wave(
                    tr.channel,
                    tr.program,
                    note,
                    duration=render_dur,
                    sample_rate=sr,
                    cent_offset=cent,
                    reverb_amount=rev_amt,
                )
                amp = vel / 127.0
                start_idx = int(t_start * sr)
                end_idx = min(total_samples, start_idx + len(wave_mono))
                seg_len = end_idx - start_idx
                if seg_len > 0:
                    mix_left[start_idx:end_idx] += wave_mono[:seg_len] * amp * l_pan
                    mix_right[start_idx:end_idx] += wave_mono[:seg_len] * amp * r_pan

        peak = max(np.max(np.abs(mix_left)), np.max(np.abs(mix_right)), 1e-5)
        if peak > 0.92:
            mix_left = np.tanh((mix_left / peak) * 1.15) * 0.92
            mix_right = np.tanh((mix_right / peak) * 1.15) * 0.92

        stereo_pcm = np.empty((total_samples * 2,), dtype=np.int16)
        stereo_pcm[0::2] = (mix_left * 32767.0).astype(np.int16)
        stereo_pcm[1::2] = (mix_right * 32767.0).astype(np.int16)

        with wave.open(filepath, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(stereo_pcm.tobytes())
