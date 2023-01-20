import urllib.parse
import requests
import asyncio
import logging
import sys
import re
import os
from dataclasses import dataclass
from pydub import AudioSegment
from typing import List, Tuple
from fractions import Fraction

from resource_paths import hashed_fn


log = logging.getLogger("moonbase")
log.setLevel(logging.DEBUG)


def commit_moonbase(text):
    filename = hashed_fn("moonbase", text.encode(), "wav")
    if os.path.exists(filename):
        print(f"Using cached file {filename}")
        return filename, None, None

    if not text:
        return "", 0, "Empty text!"

    if len(text) > 1024:
        print(f"Too long: {len(text)} > 1024")
        return "", 0, "Input too long: " + str(len(text))

    params = {"text": text}
    q = urllib.parse.urlencode(params)
    url = "http://tts.cyzon.us/tts"
    try:
        r = requests.get(url, params, allow_redirects=True)
    except Exception as e:
        logging.error(e)
        return "", -1, str(e)
    if r.status_code != 200:
        logging.error(f"Failed with code {r.status_code}: {r.text}")
        return "", r.status_code, r.text
    open(filename, 'wb').write(r.content)
    logging.info(f"Wrote to {filename}.")
    return filename, None, None


NOTE_TO_TONE = {
    # standard scale
    "C"  : 13,
    "C#" : 14,
    "D"  : 15,
    "D#" : 16,
    "E"  : 17,
    "F"  : 18,
    "F#" : 19,
    "G"  : 20,
    "G#" : 21,
    "A"  : 22,
    "A#" : 23,
    "B"  : 24,

    # unambiguous full scale
    "C1"  : 1,
    "C1#" : 2,
    "D1"  : 3,
    "D1#" : 4,
    "E1"  : 5,
    "F1"  : 6,
    "F1#" : 7,
    "G1"  : 8,
    "G1#" : 9,
    "A1"  : 10,
    "A1#" : 11,
    "B1"  : 12,

    "C2"  : 13,
    "C2#" : 14,
    "D2"  : 15,
    "D2#" : 16,
    "E2"  : 17,
    "F2"  : 18,
    "F2#" : 19,
    "G2"  : 20,
    "G2#" : 21,
    "A2"  : 22,
    "A2#" : 23,
    "B2"  : 24,

    "C3"  : 25,
    "C3#" : 26,
    "D3"  : 27,
    "D3#" : 28,
    "E3"  : 29,
    "F3"  : 30,
    "F3#" : 31,
    "G3"  : 32,
    "G3#" : 33,
    "A3"  : 34,
    "A3#" : 35,
    "B3"  : 36,

    "C4"  : 37
}


@dataclass()
class Literal:
    serialno: int = 0
    literal: str = ""
    filename: str = ""
    lineno: int = -1
    colno: int = -1


@dataclass()
class RegoNote:
    prefix: str = ""
    suffix: str = ""
    beats: Tuple[int, int] = None
    literal: Literal = None


@dataclass()
class TempoDirective:
    bpm: int = 0
    literal: Literal = None


@dataclass()
class PitchDirective:
    tone_id: int = 0
    literal: Literal = None


@dataclass()
class RepeatDirective:
    is_open: bool = False
    literal: Literal = None


@dataclass()
class TrackDirective:
    track_id: int = 0
    literal: Literal = None


@dataclass()
class BeatAssertion:
    beats: int = 0
    literal: Literal = None


@dataclass()
class MoonbaseNote:
    prefix: str = ""
    suffix: str = ""
    dur_ms: int = 0
    tone_id: int = 0


@dataclass()
class ExportedTrack:
    track_id: int = 0
    notes: List[MoonbaseNote] = None
    beats: float = 0


def to_moonbase_str(n: MoonbaseNote) -> str:
    ms = n.dur_ms
    bias = 67
    # the TTS engine adds about 4 seconds worth of audio for every 60
    # notes, regardless of BPM; 4000 ms / 60 notes ~= 67 ms per note.
    # however this doesn't apply to rests.
    if n.prefix != "_" and n.dur_ms > bias:
        ms -= bias
    return f"[{n.prefix}<{round(ms)},{n.tone_id}>{n.suffix}]"


def tokenize_string(string):

    out_tokens = []

    if not string:
        return out_tokens

    for i, match in enumerate(re.finditer(r"(\S+)", string)):
        rt = Literal()
        rt.serialno = i
        rt.colno = match.span()[0]
        rt.literal = match.group(0)
        out_tokens.append(rt)

    return out_tokens


def tokenize_file(filename) -> List[Literal]:

    out_tokens = []
    f = open(filename)
    if not f:
        return out_tokens

    serialno = 0
    for i, line in enumerate(f.read().splitlines()):
        if not line:
            continue
        if line.startswith("#"):
            continue
        for match in re.finditer(r"(\S+)", line):
            rt = Literal()
            rt.serialno = serialno
            serialno += 1
            rt.lineno = i + 1
            rt.colno = match.span()[0] + 1
            rt.literal = match.group(0)
            rt.filename = filename
            out_tokens.append(rt)

    return out_tokens


BPM_TOKEN_REGEX = r"(\d+)BPM$"
BEAT_ASSERT_TOKEN_REGEX = r"\@(\d+)"
TRACK_TOKEN_REGEX = r"TRACK(\d+)$"
PITCH_TOKEN_REGEX = r"([A-G]\d?#?)$"
PHONEME_TOKEN_REGEX = r"([a-z\-]+)(:(\d+))?(\/(\d+))?$"


# tokens are just the parsed string/file; symbols actually have
# semantic meaning. a single- or multi-track song is defined by an
# ordered sequence of symbols. symbols can be notes, pitch changes,
# tempo changes, (maybe track changes?) etc.
def cast_literal_to_symbol(literal: Literal):

    if literal.literal == ":|":
        symbol = RepeatDirective()
        symbol.is_open = False
        symbol.literal = literal
        return symbol

    if literal.literal == "|:":
        symbol = RepeatDirective()
        symbol.is_open = True
        symbol.literal = literal
        return symbol

    bpm_match = re.match(BPM_TOKEN_REGEX, literal.literal)
    if bpm_match:
        bpm = int(bpm_match.group(1))
        if bpm < 30:
            return None
        symbol = TempoDirective()
        symbol.bpm = bpm
        symbol.literal = literal
        return symbol

    beat_assert_match = re.match(BEAT_ASSERT_TOKEN_REGEX, literal.literal)
    if beat_assert_match:
        beats = int(beat_assert_match.group(1))
        symbol = BeatAssertion()
        symbol.beats = beats
        symbol.literal = literal
        return symbol

    track_match = re.match(TRACK_TOKEN_REGEX, literal.literal)
    if track_match:
        track_id = int(track_match.group(1))
        symbol = TrackDirective()
        symbol.track_id = track_id
        symbol.literal = literal
        return symbol

    pitch_match = re.match(PITCH_TOKEN_REGEX, literal.literal)
    if pitch_match:
        tone_str = pitch_match.group(1)
        if tone_str not in NOTE_TO_TONE:
            return None
        symbol = PitchDirective()
        symbol.tone_id = NOTE_TO_TONE[tone_str]
        symbol.literal = literal
        return symbol

    phoneme_match = re.match(PHONEME_TOKEN_REGEX, literal.literal)
    if phoneme_match:
        prefix = phoneme_match.group(1)
        if prefix == "-":
            prefix = "_"
        if prefix == "the": # maybe will add more common words
            prefix = "thuh"
        presuf = prefix.split("-")
        prefix = presuf[0]
        if prefix != "_":
            if len(prefix) < 2:
                return None
        suffix = ""
        if len(presuf) > 1:
            suffix = presuf[1]
        beat_numer = 1
        beat_denom = 1
        if phoneme_match.group(3):
            beat_numer = int(phoneme_match.group(3))
        if phoneme_match.group(5):
            beat_denom = int(phoneme_match.group(5))
        if beat_numer < 1 or beat_denom < 1:
            return None
        symbol = RegoNote()
        symbol.prefix = prefix
        symbol.suffix = suffix
        symbol.beats = Fraction(beat_numer, beat_denom)
        symbol.literal = literal
        return symbol

    return None


# "regolith" is what I'm calling strings which will be transpiled into
# moonbase alpha TTS syntax
def translate(tokens):

    if not tokens:
        return []

    symbols = []
    for token in tokens:
        s = cast_literal_to_symbol(token)
        if not s:
            return [], f"Bad symbol cast: {token}"
        symbols.append(s)
    return symbols, None


def export_notes_to_moonbase(notes) -> List[ExportedTrack]:
    total_ms = 0
    tracks = {}
    tone_id = 13
    bpm = 120
    track_id = 1
    for n in notes:
        if track_id not in tracks:
            tracks[track_id] = ExportedTrack()
            tracks[track_id].track_id = track_id
            tracks[track_id].notes = []
            tracks[track_id].beats = Fraction(0, 1)
        if isinstance(n, RegoNote):
            dur_ms = (n.beats.numerator / n.beats.denominator) * 60000 // bpm
            mb = MoonbaseNote()
            mb.prefix = n.prefix
            mb.suffix = n.suffix
            mb.dur_ms = dur_ms
            mb.tone_id = tone_id
            tracks[track_id].notes.append(mb)
            tracks[track_id].beats += n.beats
        elif isinstance(n, PitchDirective):
            tone_id = n.tone_id
        elif isinstance(n, TempoDirective):
            bpm = n.bpm
        elif isinstance(n, RepeatDirective):
            # not implemented: open/closed distinction, i.e., |: ... :|
            tracks[track_id].notes.extend(tracks[track_id].notes)
            tracks[track_id].beats *= 2
        elif isinstance(n, TrackDirective):
            track_id = n.track_id
        elif isinstance(n, BeatAssertion):
            if n.beats == tracks[track_id].beats:
                pass
            else:
                print(f"Failed assertion; expected beats={n.beats}, got {tracks[track_id].beats}")
                print(n)
        else:
            print(f"Unsupported symbol type: {str(type(n))}")
    return list(t for t in tracks.values() if t.notes)


def to_moonbase_sequences(track: ExportedTrack):
    ret = []
    current = ""
    for note in track.notes:
        mbstr = to_moonbase_str(note)
        if len(current) + len(mbstr) > 1024:
            ret.append(current)
            current = ""
        current += mbstr
    if current:
        ret.append(current)
    return ret


def commit_moonbase_multi(sequences):

    master_fn = hashed_fn("moonbase-multi", " ".join(sequences).encode(), "wav")
    if os.path.exists(master_fn):
        print(f"Using cached file {master_fn}")
        return master_fn, 0, ""

    master_audio = AudioSegment.empty()
    for seq in sequences:
        fn, retcode, error = commit_moonbase(seq)
        if not fn:
            return "", retcode, error
        audio = AudioSegment.from_file(fn)
        master_audio += audio

    master_audio.export(master_fn, format='wav')

    return master_fn, 0, ""



def compile_tracks(filename, *tracks):

    master_track = None

    for track in tracks:
        sequences = to_moonbase_sequences(track)
        fn, retcode, error = commit_moonbase_multi(sequences)
        if not fn:
            return False
        audio = AudioSegment.from_file(fn)
        if master_track is None:
            master_track = audio
        else:
            master_track = master_track.overlay(audio)

    master_track.export(filename, format='mp3')


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
        format="[%(levelname)s] [%(name)s] %(message)s")

    lyrics_file = sys.argv[1]
    if len(sys.argv) < 3:
        audio_file = lyrics_file.replace(".txt", ".mp3")
    else:
        audio_file = sys.argv[2]

    tokens = tokenize_file(lyrics_file)
    notes, error = translate(tokens)
    if error:
        print(error)
        return
    tracks = export_notes_to_moonbase(notes)
    for track in tracks:
        print(track.beats)
    compile_tracks(audio_file, *tracks)


if __name__ == "__main__":
    main()
