"""
Accessible Mini-DAW Configuration Module
========================================
Designed specifically for blind and visually impaired musicians.
Provides bilingual localization (Arabic primary, English secondary),
General MIDI 128 instrument definitions, GM Drum map, keybindings,
and audio engine parameters.
"""

import os
from typing import Dict, List, Tuple, Any

# Current Project Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOUNDFONTS_DIR = os.path.join(BASE_DIR, "soundfonts")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")

os.makedirs(SOUNDFONTS_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)
os.makedirs(RECORDINGS_DIR, exist_ok=True)

# Candidate SoundFont paths to probe automatically across OS environments
SOUNDFONT_SEARCH_PATHS = [
    os.path.join(SOUNDFONTS_DIR, "default.sf2"),
    os.path.join(SOUNDFONTS_DIR, "GeneralUser_GS.sf2"),
    os.path.join(SOUNDFONTS_DIR, "FluidR3_GM.sf2"),
    "/usr/share/sounds/sf2/FluidR3_GM.sf2",
    "/usr/share/sounds/sf2/default-GM.sf2",
    "/usr/share/soundfonts/default.sf2",
    "/usr/share/sounds/sf2/TimGM6mb.sf2",
    "/usr/share/soundfonts/FluidR3_GM.sf2",
    "/usr/share/soundfonts/GeneralUser_GS.sf2",
    "/data/data/com.termux/files/home/soundfonts/default.sf2",
    "C:\\soundfonts\\default.sf2",
    "C:\\soundfonts\\GeneralUser_GS.sf2",
    "C:\\ProgramData\\soundfonts\\default.sf2",
]

# Audio Engine Buffer and Performance Settings
SAMPLE_RATE = 44100
BUFFER_SIZE = 512       # 512 samples (~11.6 ms latency) for real-time responsiveness
AUDIO_CHANNELS = 2      # Stereo
POLYPHONY = 64
MAX_TRACKS = 8
METRONOME_CHANNEL = 9   # 0-indexed MIDI channel 9 = GM Channel 10
EARCON_CHANNEL = 8      # Channel dedicated to UI sound cues
DEFAULT_BPM = 120
MIN_BPM = 40
MAX_BPM = 280
DEFAULT_VELOCITY = 100
DEFAULT_OCTAVE = 4      # Middle C = C4 = MIDI 60
PPQ = 480               # Pulses (ticks) per quarter note for standard MIDI timing

# GM Percussion Note Numbers for Metronome
METRONOME_HIGH_NOTE = 76  # High Woodblock (Downbeat / Beat 1)
METRONOME_LOW_NOTE = 77   # Low Woodblock (Beats 2, 3, 4)
METRONOME_VELOCITY_HIGH = 115
METRONOME_VELOCITY_LOW = 90

# ---------------------------------------------------------------------------
# General MIDI 128 Instruments: (Program Number 0-127, English, Arabic, Category)
# ---------------------------------------------------------------------------
GM_INSTRUMENTS: List[Dict[str, Any]] = [
    # 0-7: Piano
    {"id": 0, "en": "Acoustic Grand Piano", "ar": "بيانو صوتي كبير", "cat_en": "Piano", "cat_ar": "بيانو"},
    {"id": 1, "en": "Bright Acoustic Piano", "ar": "بيانو ساطع", "cat_en": "Piano", "cat_ar": "بيانو"},
    {"id": 2, "en": "Electric Grand Piano", "ar": "جراند بيانو كهربائي", "cat_en": "Piano", "cat_ar": "بيانو"},
    {"id": 3, "en": "Honky-tonk Piano", "ar": "بيانو هانكي تونك", "cat_en": "Piano", "cat_ar": "بيانو"},
    {"id": 4, "en": "Electric Piano 1 (Rhodes)", "ar": "بيانو كهربائي رودز", "cat_en": "Piano", "cat_ar": "بيانو"},
    {"id": 5, "en": "Electric Piano 2 (Chorused)", "ar": "بيانو كهربائي كوروس", "cat_en": "Piano", "cat_ar": "بيانو"},
    {"id": 6, "en": "Harpsichord", "ar": "هاربسيكورد", "cat_en": "Piano", "cat_ar": "بيانو"},
    {"id": 7, "en": "Clavinet", "ar": "كلافينيت", "cat_en": "Piano", "cat_ar": "بيانو"},

    # 8-15: Chromatic Percussion
    {"id": 8, "en": "Celesta", "ar": "سيليستا", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},
    {"id": 9, "en": "Glockenspiel", "ar": "جلوكنسبيل", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},
    {"id": 10, "en": "Music Box", "ar": "صندوق موسيقي", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},
    {"id": 11, "en": "Vibraphone", "ar": "فايبرفون", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},
    {"id": 12, "en": "Marimba", "ar": "ماريمبا", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},
    {"id": 13, "en": "Xylophone", "ar": "زايلوفون", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},
    {"id": 14, "en": "Tubular Bells", "ar": "أجراس أنبوبية", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},
    {"id": 15, "en": "Dulcimer", "ar": "دلسيمر / سنطور", "cat_en": "Chromatic Percussion", "cat_ar": "إيقاع لحني"},

    # 16-23: Organ
    {"id": 16, "en": "Drawbar Organ (Hammond)", "ar": "أورج هاموند دروبار", "cat_en": "Organ", "cat_ar": "أورغ"},
    {"id": 17, "en": "Percussive Organ", "ar": "أورج إيقاعي", "cat_en": "Organ", "cat_ar": "أورغ"},
    {"id": 18, "en": "Rock Organ", "ar": "أورج روك", "cat_en": "Organ", "cat_ar": "أورغ"},
    {"id": 19, "en": "Church Organ", "ar": "أورج كنسي", "cat_en": "Organ", "cat_ar": "أورغ"},
    {"id": 20, "en": "Reed Organ", "ar": "أورج ريشي / هارمونيوم", "cat_en": "Organ", "cat_ar": "أورغ"},
    {"id": 21, "en": "Accordion", "ar": "أكورديون", "cat_en": "Organ", "cat_ar": "أورغ"},
    {"id": 22, "en": "Harmonica", "ar": "هارمونيكا", "cat_en": "Organ", "cat_ar": "أورغ"},
    {"id": 23, "en": "Tango Accordion", "ar": "باندونيون تانجو", "cat_en": "Organ", "cat_ar": "أورغ"},

    # 24-31: Guitar
    {"id": 24, "en": "Acoustic Guitar (Nylon)", "ar": "جيتار كلاسيكي نايلون", "cat_en": "Guitar", "cat_ar": "جيتار"},
    {"id": 25, "en": "Acoustic Guitar (Steel)", "ar": "جيتار صوتي أوتار معدنية", "cat_en": "Guitar", "cat_ar": "جيتار"},
    {"id": 26, "en": "Electric Guitar (Jazz)", "ar": "جيتار جاز كهربائي", "cat_en": "Guitar", "cat_ar": "جيتار"},
    {"id": 27, "en": "Electric Guitar (Clean)", "ar": "جيتار كهربائي نقي", "cat_en": "Guitar", "cat_ar": "جيتار"},
    {"id": 28, "en": "Electric Guitar (Muted)", "ar": "جيتار كهربائي مكتوم", "cat_en": "Guitar", "cat_ar": "جيتار"},
    {"id": 29, "en": "Overdriven Guitar", "ar": "جيتار كهربائي أوفر درايف", "cat_en": "Guitar", "cat_ar": "جيتار"},
    {"id": 30, "en": "Distortion Guitar", "ar": "جيتار ديستورشن", "cat_en": "Guitar", "cat_ar": "جيتار"},
    {"id": 31, "en": "Guitar Harmonics", "ar": "هارمونيكس جيتار", "cat_en": "Guitar", "cat_ar": "جيتار"},

    # 32-39: Bass
    {"id": 32, "en": "Acoustic Bass", "ar": "كونتراباص صوتي", "cat_en": "Bass", "cat_ar": "باص"},
    {"id": 33, "en": "Electric Bass (Finger)", "ar": "بيس جيتار بالأصابع", "cat_en": "Bass", "cat_ar": "باص"},
    {"id": 34, "en": "Electric Bass (Pick)", "ar": "بيس جيتار بالريشة", "cat_en": "Bass", "cat_ar": "باص"},
    {"id": 35, "en": "Fretless Bass", "ar": "بيس جيتار بدون دساتين", "cat_en": "Bass", "cat_ar": "باص"},
    {"id": 36, "en": "Slap Bass 1", "ar": "سلاب باص 1", "cat_en": "Bass", "cat_ar": "باص"},
    {"id": 37, "en": "Slap Bass 2", "ar": "سلاب باص 2", "cat_en": "Bass", "cat_ar": "باص"},
    {"id": 38, "en": "Synth Bass 1", "ar": "سينث باص 1", "cat_en": "Bass", "cat_ar": "باص"},
    {"id": 39, "en": "Synth Bass 2", "ar": "سينث باص 2", "cat_en": "Bass", "cat_ar": "باص"},

    # 40-47: Strings
    {"id": 40, "en": "Violin", "ar": "كمان سولو", "cat_en": "Strings", "cat_ar": "وتريات"},
    {"id": 41, "en": "Viola", "ar": "فيولا", "cat_en": "Strings", "cat_ar": "وتريات"},
    {"id": 42, "en": "Cello", "ar": "تشيلو سولو", "cat_en": "Strings", "cat_ar": "وتريات"},
    {"id": 43, "en": "Contrabass", "ar": "كونتراباص سولو", "cat_en": "Strings", "cat_ar": "وتريات"},
    {"id": 44, "en": "Tremolo Strings", "ar": "وتريات تريمولّو", "cat_en": "Strings", "cat_ar": "وتريات"},
    {"id": 45, "en": "Pizzicato Strings", "ar": "وتريات بيتزيكاتو (نقر)", "cat_en": "Strings", "cat_ar": "وتريات"},
    {"id": 46, "en": "Orchestral Harp", "ar": "هارب أوركسترالي", "cat_en": "Strings", "cat_ar": "وتريات"},
    {"id": 47, "en": "Timpani", "ar": "تيمباني أوركسترالي", "cat_en": "Strings", "cat_ar": "وتريات"},

    # 48-55: Ensemble
    {"id": 48, "en": "String Ensemble 1", "ar": "أوركسترا وتريات 1", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},
    {"id": 49, "en": "String Ensemble 2", "ar": "أوركسترا وتريات هادئة", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},
    {"id": 50, "en": "SynthStrings 1", "ar": "سينث وتريات 1", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},
    {"id": 51, "en": "SynthStrings 2", "ar": "سينث وتريات 2", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},
    {"id": 52, "en": "Choir Aahs", "ar": "كورال بشري آهات", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},
    {"id": 53, "en": "Voice Oohs", "ar": "أصوات بشرية أوه", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},
    {"id": 54, "en": "Synth Voice", "ar": "سينث بشري إلكتروني", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},
    {"id": 55, "en": "Orchestra Hit", "ar": "ضربة أوركسترا", "cat_en": "Ensemble", "cat_ar": "فرق وتريات وكورال"},

    # 56-63: Brass
    {"id": 56, "en": "Trumpet", "ar": "بوق / ترومبيت", "cat_en": "Brass", "cat_ar": "نحاسيات"},
    {"id": 57, "en": "Trombone", "ar": "ترومبون", "cat_en": "Brass", "cat_ar": "نحاسيات"},
    {"id": 58, "en": "Tuba", "ar": "توبا", "cat_en": "Brass", "cat_ar": "نحاسيات"},
    {"id": 59, "en": "Muted Trumpet", "ar": "ترومبيت مكتوم سوردينة", "cat_en": "Brass", "cat_ar": "نحاسيات"},
    {"id": 60, "en": "French Horn", "ar": "هورن فرنسي", "cat_en": "Brass", "cat_ar": "نحاسيات"},
    {"id": 61, "en": "Brass Section", "ar": "فرقة نحاسيات", "cat_en": "Brass", "cat_ar": "نحاسيات"},
    {"id": 62, "en": "Synth Brass 1", "ar": "سينث نحاسيات 1", "cat_en": "Brass", "cat_ar": "نحاسيات"},
    {"id": 63, "en": "Synth Brass 2", "ar": "سينث نحاسيات 2", "cat_en": "Brass", "cat_ar": "نحاسيات"},

    # 64-71: Reed
    {"id": 64, "en": "Soprano Sax", "ar": "ساكسفون سوبرانو", "cat_en": "Reed", "cat_ar": "آلات قصبية"},
    {"id": 65, "en": "Alto Sax", "ar": "ساكسفون ألتو", "cat_en": "Reed", "cat_ar": "آلات قصبية"},
    {"id": 66, "en": "Tenor Sax", "ar": "ساكسفون تينور", "cat_en": "Reed", "cat_ar": "آلات قصبية"},
    {"id": 67, "en": "Baritone Sax", "ar": "ساكسفون باريتون", "cat_en": "Reed", "cat_ar": "آلات قصبية"},
    {"id": 68, "en": "Oboe", "ar": "أوبوا", "cat_en": "Reed", "cat_ar": "آلات قصبية"},
    {"id": 69, "en": "English Horn", "ar": "هورن إنجليزي", "cat_en": "Reed", "cat_ar": "آلات قصبية"},
    {"id": 70, "en": "Bassoon", "ar": "باصون", "cat_en": "Reed", "cat_ar": "آلات قصبية"},
    {"id": 71, "en": "Clarinet", "ar": "كلارينيت", "cat_en": "Reed", "cat_ar": "آلات قصبية"},

    # 72-79: Pipe
    {"id": 72, "en": "Piccolo", "ar": "بيكولو", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},
    {"id": 73, "en": "Flute", "ar": "فلوت أوركسترالي", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},
    {"id": 74, "en": "Recorder", "ar": "ريكوردر", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},
    {"id": 75, "en": "Pan Flute", "ar": "بان فلوت / ناي", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},
    {"id": 76, "en": "Blown Bottle", "ar": "نفخ زجاجة", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},
    {"id": 77, "en": "Shakuhachi", "ar": "شاكوهاتشي ياباني", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},
    {"id": 78, "en": "Whistle", "ar": "صفارة لحنية", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},
    {"id": 79, "en": "Ocarina", "ar": "أوكارينا", "cat_en": "Pipe", "cat_ar": "مزامير وفلوت"},

    # 80-87: Synth Lead
    {"id": 80, "en": "Lead 1 (Square)", "ar": "سينث ليد موجة مربعة", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},
    {"id": 81, "en": "Lead 2 (Sawtooth)", "ar": "سينث ليد سن المنشار", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},
    {"id": 82, "en": "Lead 3 (Calliope)", "ar": "سينث كاليوبي", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},
    {"id": 83, "en": "Lead 4 (Chiff)", "ar": "سينث تشيف", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},
    {"id": 84, "en": "Lead 5 (Charang)", "ar": "سينث تشارانج", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},
    {"id": 85, "en": "Lead 6 (Voice)", "ar": "سينث ليد صوتي", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},
    {"id": 86, "en": "Lead 7 (Fifths)", "ar": "سينث ليد خماسيات", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},
    {"id": 87, "en": "Lead 8 (Bass + Lead)", "ar": "سينث ليد مع باص", "cat_en": "Synth Lead", "cat_ar": "سينث ليد"},

    # 88-95: Synth Pad
    {"id": 88, "en": "Pad 1 (New Age)", "ar": "سينث باد نيو إيدج", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},
    {"id": 89, "en": "Pad 2 (Warm)", "ar": "سينث باد دافئ", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},
    {"id": 90, "en": "Pad 3 (Polysynth)", "ar": "سينث باد بولي سينث", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},
    {"id": 91, "en": "Pad 4 (Choir)", "ar": "سينث باد كورال فضاء", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},
    {"id": 92, "en": "Pad 5 (Bowed)", "ar": "سينث باد قوسي", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},
    {"id": 93, "en": "Pad 6 (Metallic)", "ar": "سينث باد رنين معدني", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},
    {"id": 94, "en": "Pad 7 (Halo)", "ar": "سينث باد هالة نورانية", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},
    {"id": 95, "en": "Pad 8 (Sweep)", "ar": "سينث باد سويب فلتر", "cat_en": "Synth Pad", "cat_ar": "سينث باد"},

    # 96-103: Synth Effects
    {"id": 96, "en": "FX 1 (Rain)", "ar": "مؤثرات مطر", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},
    {"id": 97, "en": "FX 2 (Soundtrack)", "ar": "مؤثرات تصويرية", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},
    {"id": 98, "en": "FX 3 (Crystal)", "ar": "مؤثرات بلورات", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},
    {"id": 99, "en": "FX 4 (Atmosphere)", "ar": "مؤثرات غلاف جوي", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},
    {"id": 100, "en": "FX 5 (Brightness)", "ar": "مؤثرات إشراق", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},
    {"id": 101, "en": "FX 6 (Goblins)", "ar": "مؤثرات خيالية", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},
    {"id": 102, "en": "FX 7 (Echoes)", "ar": "مؤثرات صدى متساقط", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},
    {"id": 103, "en": "FX 8 (Sci-Fi)", "ar": "مؤثرات خيال علمي", "cat_en": "Synth Effects", "cat_ar": "مؤثرات صوتية سينث"},

    # 104-111: Ethnic
    {"id": 104, "en": "Sitar", "ar": "سيتار هندي / عود", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},
    {"id": 105, "en": "Banjo", "ar": "بانجو", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},
    {"id": 106, "en": "Shamisen", "ar": "شاميسين ياباني", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},
    {"id": 107, "en": "Koto", "ar": "كوتو ياباني / قانون", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},
    {"id": 108, "en": "Kalimba", "ar": "كاليمبا إفريقية", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},
    {"id": 109, "en": "Bagpipe", "ar": "مزمار القربة الاسكتلندي", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},
    {"id": 110, "en": "Fiddle", "ar": "ربابة / فيدل شعبي", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},
    {"id": 111, "en": "Shanai", "ar": "شحناي هندي / مزمار بلدي", "cat_en": "Ethnic", "cat_ar": "آلات شرقية وتراثية"},

    # 112-119: Percussive
    {"id": 112, "en": "Tinkle Bell", "ar": "جرس رنان خفيف", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},
    {"id": 113, "en": "Agogo", "ar": "أجوجو برازيلي", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},
    {"id": 114, "en": "Steel Drums", "ar": "براميل حديدية كاريبية", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},
    {"id": 115, "en": "Woodblock", "ar": "قوالب خشبية وود بلوك", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},
    {"id": 116, "en": "Taiko Drum", "ar": "طبول تايكو يابانية", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},
    {"id": 117, "en": "Melodic Tom", "ar": "تومات لحنية", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},
    {"id": 118, "en": "Synth Drum", "ar": "درام إلكتروني سينث", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},
    {"id": 119, "en": "Reverse Cymbal", "ar": "صنج معكوس", "cat_en": "Percussive", "cat_ar": "إيقاعات لحنية"},

    # 120-127: Sound Effects
    {"id": 120, "en": "Guitar Fret Noise", "ar": "صوت دساتين الجيتار", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
    {"id": 121, "en": "Breath Noise", "ar": "صوت أنفاس", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
    {"id": 122, "en": "Seashore", "ar": "أمواج البحر", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
    {"id": 123, "en": "Bird Tweet", "ar": "تغريد العصافير", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
    {"id": 124, "en": "Telephone Ring", "ar": "رنين هاتف", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
    {"id": 125, "en": "Helicopter", "ar": "مروحية هليكوبتر", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
    {"id": 126, "en": "Applause", "ar": "تصفيق جمهور", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
    {"id": 127, "en": "Gunshot", "ar": "طلقة نارية", "cat_en": "Sound Effects", "cat_ar": "مؤثرات طبيعية"},
]

# ---------------------------------------------------------------------------
# GM Percussion / Drum Mapping (Channel 9)
# ---------------------------------------------------------------------------
GM_DRUMS: Dict[int, Dict[str, str]] = {
    35: {"en": "Acoustic Bass Drum", "ar": "دم بيس صوتي"},
    36: {"en": "Bass Drum 1 (Kick)", "ar": "كيك درام"},
    37: {"en": "Side Stick (Rimshot)", "ar": "ريم شوت خشبي"},
    38: {"en": "Acoustic Snare", "ar": "سنير درام صوتي"},
    39: {"en": "Hand Clap", "ar": "تصفيق يدوي"},
    40: {"en": "Electric Snare", "ar": "سنير درام كهربائي"},
    41: {"en": "Low Floor Tom", "ar": "توم أرضي منخفض"},
    42: {"en": "Closed Hi-Hat", "ar": "هاي هات مغلق"},
    43: {"en": "High Floor Tom", "ar": "توم أرضي عالي"},
    44: {"en": "Pedal Hi-Hat", "ar": "هاي هات بدواسة"},
    45: {"en": "Low Tom", "ar": "توم منخفض"},
    46: {"en": "Open Hi-Hat", "ar": "هاي هات مفتوح"},
    47: {"en": "Low-Mid Tom", "ar": "توم متوسط منخفض"},
    48: {"en": "Hi-Mid Tom", "ar": "توم متوسط عالي"},
    49: {"en": "Crash Cymbal 1", "ar": "صنج كراش 1"},
    50: {"en": "High Tom", "ar": "توم عالي"},
    51: {"en": "Ride Cymbal 1", "ar": "صنج رايد 1"},
    52: {"en": "Chinese Cymbal", "ar": "صنج صيني"},
    53: {"en": "Ride Bell", "ar": "جرس صنج الرايد"},
    54: {"en": "Tambourine", "ar": "دف / طار"},
    55: {"en": "Splash Cymbal", "ar": "صنج سبلاش"},
    56: {"en": "Cowbell", "ar": "جرس البقر"},
    57: {"en": "Crash Cymbal 2", "ar": "صنج كراش 2"},
    58: {"en": "Vibraslap", "ar": "فايبرسلاب"},
    59: {"en": "Ride Cymbal 2", "ar": "صنج رايد 2"},
    60: {"en": "Hi Bongo", "ar": "بونقز عالي"},
    61: {"en": "Low Bongo", "ar": "بونقز منخفض"},
    62: {"en": "Mute Hi Conga", "ar": "كونجا مكتومة عالية"},
    63: {"en": "Open Hi Conga (Darbuka Tek)", "ar": "كونجا مفتوحة / تك دربوكة"},
    64: {"en": "Low Conga (Darbuka Dum)", "ar": "كونجا منخفضة / دم دربوكة"},
    65: {"en": "High Timbale", "ar": "تيمبال عالي"},
    66: {"en": "Low Timbale", "ar": "تيمبال منخفض"},
    67: {"en": "High Agogo", "ar": "أجوجو عالي"},
    68: {"en": "Low Agogo", "ar": "أجوجو منخفض"},
    69: {"en": "Cabasa", "ar": "كاباسا"},
    70: {"en": "Maracas", "ar": "ماراكاس شخشيخة"},
    75: {"en": "Claves", "ar": "عصي إيقاعية كلافز"},
    76: {"en": "Hi Wood Block", "ar": "وود بلوك عالي"},
    77: {"en": "Low Wood Block", "ar": "وود بلوك منخفض"},
    80: {"en": "Mute Triangle", "ar": "مثلث مكتوم"},
    81: {"en": "Open Triangle", "ar": "مثلث رنان مفتوح"},
}

# ---------------------------------------------------------------------------
# Dedicated Step Sequencer Instruments (16-Step Drum Grid Mode)
# ---------------------------------------------------------------------------
STEP_DRUM_INSTRUMENTS: List[Dict[str, Any]] = [
    {"note": 36, "en": "Kick Drum", "ar": "كيك بيس", "shortcut": "1"},
    {"note": 38, "en": "Snare Drum", "ar": "سنير درام", "shortcut": "2"},
    {"note": 42, "en": "Closed Hi-Hat", "ar": "هاي هات مغلق", "shortcut": "3"},
    {"note": 46, "en": "Open Hi-Hat", "ar": "هاي هات مفتوح", "shortcut": "4"},
    {"note": 39, "en": "Hand Clap", "ar": "تصفيق يدوي", "shortcut": "5"},
    {"note": 37, "en": "Rimshot", "ar": "ريم شوت", "shortcut": "6"},
    {"note": 64, "en": "Darbuka Dum (Low Conga)", "ar": "دم دربوكة", "shortcut": "7"},
    {"note": 63, "en": "Darbuka Tek (Open Conga)", "ar": "تك دربوكة", "shortcut": "8"},
    {"note": 49, "en": "Crash Cymbal", "ar": "صنج كراش", "shortcut": "9"},
    {"note": 54, "en": "Tambourine", "ar": "رق / دف", "shortcut": "0"},
]

# ---------------------------------------------------------------------------
# Western & Oriental Arabic Musical Notes Spelling
# ---------------------------------------------------------------------------
NOTE_NAMES: Dict[str, List[str]] = {
    "en": ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"],
    "ar": ["دو", "دو دييز", "ري", "ري دييز", "مي", "فا", "فا دييز", "صول", "صول دييز", "لا", "لا دييز", "سي"],
}

def get_note_name(midi_number: int, lang: str = "ar") -> str:
    """Returns friendly note name with octave (e.g. 'C4' or 'دو 4')."""
    if midi_number < 0 or midi_number > 127:
        return str(midi_number)
    octave = (midi_number // 12) - 1
    note_idx = midi_number % 12
    name_list = NOTE_NAMES.get(lang, NOTE_NAMES["ar"])
    return f"{name_list[note_idx]} {octave}"

# ---------------------------------------------------------------------------
# Localization Strings for Accessible Screen Reader Announcements
# ---------------------------------------------------------------------------
STRINGS: Dict[str, Dict[str, str]] = {
    "ar": {
        "welcome": "أهلاً بك في استوديو الألحان الميسر للمكفوفين. تم تحديد المسار الأول: بيانو صوتي كبير. السرعة 120 نبضة في الدقيقة. اضغط إف واحد لسماع دليل الاختصارات.",
        "help_title": "دليل الاختصارات الكامل:",
        "help_body": (
            "لوحة المفاتيح الموسيقية: الصف الأسفل زد إكس سي في بي إن إم أوكتاف أول. الصف الأعلى كيو دبليو إي آر تي واي يو أوكتاف ثان. المفاتيح السوداء: إس دي، جي إتش جيه، 2 3، 5 6 7.\n"
            "التحكم: المسافة لتشغيل وإيقاف التسجيل أو العزف. حرف آر لبدء التسجيل مع عد تنازلي 4 نبضات. حرف إل لتفعيل وضع التكرار الحلقي.\n"
            "الأرقام من 1 إلى 8: لاختيار المسار الصوتي النشط.\n"
            "تاب وشفت تاب: التبديل بين الآلات الموسيقية الـ 128.\n"
            "إف 2: نطق تفاصيل المسار الحالي (الآلة، الصوت، التوزيع).\n"
            "إف 3: تشغيل أو إيقاف المترونوم الصوتي.\n"
            "إف 4: إعلان السرعة الحالية أو ضبطها.\n"
            "إف 5: فتح أو إغلاق شبكة الطبول والدرامز 16 خطوة.\n"
            "إف 6: تصحيح التوقيت كوانتايز بدقة جزء من 16.\n"
            "إف 7: تفعيل أو إلغاء العزف المنفرد سولو للمسار.\n"
            "إف 8: كتم صوت المسار الحالي أو إلغاء الكتم.\n"
            "إف 9: التراجع عن آخر تسجيل في المسار.\n"
            "إف 10: مسح جميع النوتات المسجلة في المسار.\n"
            "إف 11: تصدير المشروع إلى ملف ميدي وملف صوتي واف.\n"
            "إف 12: تبديل لغة النطق بين العربية والإنجليزية.\n"
            "السهم لأعلى ولأسفل: رفع وخفض مستوى صوت المسار.\n"
            "السهم لليمين ولليسار: توجيه الصوت يمين أو يسار أو وسط.\n"
            "بيج أب وبيج داون: رفع وخفض الأوكتاف.\n"
            "هوم وإند: رفع وخفض قوة اللمس فيلوستي.\n"
            "القوس الأيمن والأيسر: تسريع وإبطاء الإيقاع 5 درجات.\n"
            "زر الهروب إسكيب: إيقاف جميع الأصوات فوراً وحالات الطوارئ."
        ),
        "track_selected": "المسار {track_num}: {inst_name}",
        "track_info": "المسار {track_num}: الآلة {inst_name}. مستوى الصوت {volume} بالمئة. التوزيع {pan}. {status}",
        "solo_on": "سولو مفعّل للمسار {track_num}",
        "solo_off": "تم إلغاء السولو للمسار {track_num}",
        "mute_on": "تم كتم المسار {track_num}",
        "mute_off": "تم إلغاء كتم المسار {track_num}",
        "program_changed": "الآلة: {inst_name}",
        "octave_changed": "الأوكتاف {octave}",
        "velocity_changed": "قوة اللمس {velocity}",
        "tempo_changed": "السرعة {bpm} نبضة في الدقيقة",
        "volume_changed": "مستوى الصوت {volume}",
        "pan_left": "التوزيع يسار {val}",
        "pan_right": "التوزيع يمين {val}",
        "pan_center": "التوزيع في المنتصف",
        "metronome_on": "تم تشغيل المترونوم",
        "metronome_off": "تم إيقاف المترونوم",
        "loop_on": "وضع التكرار الحلقي مفعّل",
        "loop_off": "وضع التكرار الحلقي معطّل",
        "count_in": "استعد للتسجيل: {beat}",
        "rec_started": "بدأ التسجيل الآن على المسار {track_num}",
        "rec_stopped": "تم إيقاف التسجيل. تم حفظ {count} حدث موسيقي.",
        "playback_started": "بدء التشغيل",
        "playback_stopped": "توقف التشغيل عند المازورة {bar}، النبضة {beat}",
        "quantized": "تم تصحيح التوقيت للمسار {track_num} بدقة جزء من {grid}",
        "undo_done": "تم التراجع عن التسجيل الأخير للمسار {track_num}",
        "undo_empty": "لا يوجد تسجيلات سابقة للتراجع عنها في هذا المسار",
        "track_cleared": "تم تفريغ نوتات المسار {track_num}",
        "exporting": "جاري تصدير المشروع إلى ملف ميدي وملف صوتي عالي الجودة...",
        "export_success": "تم التصدير بنجاح! تم حفظ ملف الميدي في: {midi_path} وملف الصوت في: {wav_path}",
        "export_error": "حدث خطأ أثناء التصدير: {err}",
        "panic": "تم إخماد جميع النوتات الموسيقية والأصوات",
        "step_mode_enter": "تم الدخول إلى شبكة الطبول 16 خطوة. استخدم السهمين يمين ويسار للتنقل بين الخطوات، والسهمين أعلى وأسفل لاختيار الآلة الإيقاعية، ومسطرة المسافة للتفعيل أو الإلغاء. اضغط إف 5 للخروج.",
        "step_mode_exit": "تم الخروج من شبكة الطبول والعودة إلى لوحة العزف والمسارات.",
        "step_info": "الخطوة {step}: {hits}",
        "step_empty": "فارغة",
        "drum_selected": "{drum_name}: {state}",
        "drum_toggled_on": "{drum_name}: مفعّل على الخطوة {step}",
        "drum_toggled_off": "{drum_name}: معطّل على الخطوة {step}",
        "language_switched": "تم تحويل اللغة إلى العربية",
        "boundary_reached": "وصلت إلى الحد الأقصى أو الأدنى",
        "status_summary": "المسار {track_num} نشط. الآلة: {inst_name}. السرعة {bpm}. المترونوم {metronome_state}. المازورة {bar}.",
    },
    "en": {
        "welcome": "Welcome to Accessible Mini-DAW Studio for blind musicians. Track 1 selected: Acoustic Grand Piano. Tempo 120 BPM. Press F1 for the keyboard shortcuts manual.",
        "help_title": "Full Keyboard Shortcuts Manual:",
        "help_body": (
            "Musical Keyboard: Lower Octave: Z X C V B N M (white keys), S D G H J (black keys). Upper Octave: Q W E R T Y U (white keys), 2 3 5 6 7 (black keys).\n"
            "Transport: Spacebar to Play/Stop. R to Record with 4-beat audible count-in. L to toggle Loop mode.\n"
            "Numbers 1 to 8: Select active track.\n"
            "Tab / Shift+Tab: Next and Previous Instrument (128 General MIDI presets).\n"
            "F2: Read current track status (Instrument, Volume, Panning, Mute/Solo).\n"
            "F3: Toggle audible Metronome click on/off.\n"
            "F4: Announce current BPM tempo.\n"
            "F5: Toggle 16-Step Drum Grid Mode.\n"
            "F6: Smart Quantize active track to nearest 1/16th note.\n"
            "F7: Solo active track.\n"
            "F8: Mute/Unmute active track.\n"
            "F9: Undo last recording pass on active track.\n"
            "F10: Clear all recorded notes on active track.\n"
            "F11: Export multi-track project to Standard MIDI (.mid) and Audio (.wav).\n"
            "F12: Switch TTS speech language (Arabic / English).\n"
            "Up / Down Arrows: Adjust track volume CC#7.\n"
            "Left / Right Arrows: Adjust track stereo panning CC#10.\n"
            "PageUp / PageDown: Octave Shift up/down.\n"
            "Home / End: Note Velocity adjust (+10 / -10).\n"
            "[ and ]: Decrease and Increase BPM by 5.\n"
            "Escape: MIDI Panic / Silence all ringing notes."
        ),
        "track_selected": "Track {track_num}: {inst_name}",
        "track_info": "Track {track_num}: Instrument {inst_name}. Volume {volume} percent. Pan {pan}. {status}",
        "solo_on": "Track {track_num} Soloed",
        "solo_off": "Track {track_num} Solo Off",
        "mute_on": "Track {track_num} Muted",
        "mute_off": "Track {track_num} Unmuted",
        "program_changed": "Instrument: {inst_name}",
        "octave_changed": "Octave {octave}",
        "velocity_changed": "Velocity {velocity}",
        "tempo_changed": "Tempo {bpm} BPM",
        "volume_changed": "Volume {volume}",
        "pan_left": "Pan Left {val}",
        "pan_right": "Pan Right {val}",
        "pan_center": "Pan Center",
        "metronome_on": "Metronome On",
        "metronome_off": "Metronome Off",
        "loop_on": "Loop Mode On",
        "loop_off": "Loop Mode Off",
        "count_in": "Count-in: {beat}",
        "rec_started": "Recording started on Track {track_num}",
        "rec_stopped": "Recording stopped. Saved {count} musical events.",
        "playback_started": "Playback started",
        "playback_stopped": "Playback stopped at Bar {bar}, Beat {beat}",
        "quantized": "Track {track_num} quantized to 1/{grid} division",
        "undo_done": "Undid last recording pass on Track {track_num}",
        "undo_empty": "Nothing to undo on this track",
        "track_cleared": "Track {track_num} notes cleared",
        "exporting": "Exporting project to MIDI and high-resolution WAV...",
        "export_success": "Export successful! MIDI: {midi_path}, Audio: {wav_path}",
        "export_error": "Export failed: {err}",
        "panic": "All notes silenced (MIDI Panic)",
        "step_mode_enter": "16-Step Drum Grid Mode active. Use Left and Right arrows to navigate steps, Up and Down arrows to choose drum sound, Spacebar to toggle drum hit. Press F5 to exit.",
        "step_mode_exit": "Exited Drum Grid Mode. Returned to live keyboard tracks.",
        "step_info": "Step {step}: {hits}",
        "step_empty": "Empty",
        "drum_selected": "{drum_name}: {state}",
        "drum_toggled_on": "{drum_name}: On at Step {step}",
        "drum_toggled_off": "{drum_name}: Off at Step {step}",
        "language_switched": "Language switched to English",
        "boundary_reached": "Limit reached",
        "status_summary": "Track {track_num} active. Instrument: {inst_name}. Tempo {bpm} BPM. Metronome {metronome_state}. Bar {bar}.",
    }
}
