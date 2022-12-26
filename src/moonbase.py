import urllib.parse
import requests
import asyncio
import logging
import sys
import re
from dataclasses import dataclass
from pydub import AudioSegment

from resource_paths import tmp_fn


log = logging.getLogger("moonbase")
log.setLevel(logging.DEBUG)


def commit_moonbase(text, filename):
    params = {"text": text}
    q = urllib.parse.urlencode(params)
    url = "http://tts.cyzon.us/tts"
    try:
        r = requests.get(url, params, allow_redirects=True)
    except Exception as e:
        logging.error(e)
        return False, -1, str(e)
    if r.status_code != 200:
        logging.error(f"Failed with code {r.status_code}: {r.text}")
        return False, r.status_code, r.text
    open(filename, 'wb').write(r.content)
    logging.info(f"Wrote to {filename}.")
    return True, None, None


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
class TTSToken:
    phoneme: str = ""
    suffix: str = ""
    dur_ms: int = 0
    tone: int = 0


def token_to_str(t: TTSToken) -> str:
    return f"[{t.phoneme}<{t.dur_ms},{t.tone}>{t.suffix}]"


BPM_TOKEN_REGEX = r"(\d+)BPM$"
PITCH_TOKEN_REGEX = r"([A-G]\d?#?)$"
PHONEME_TOKEN_REGEX = r"([a-z\-]+)(:(\d+))?(\/(\d+))?$"

# "regolith" is what I'm calling strings which will be transpiled into
# moonbase alpha TTS syntax
def translate(regolith):

    error_return = "", 0

    def invalid_phoneme(p):
        print(f"Invalid phoneme: {p}")
        return error_return

    regolith = regolith.split(" ")
    if not regolith:
        return error_return

    bpm = 120
    beat_ms = 60000 // bpm

    out_tokens = []
    tone_id = 13
    for token in regolith:
        if not token:
            continue
        if token == ":|":
            out_tokens.extend(out_tokens)
            continue
        bpm_match = re.match(BPM_TOKEN_REGEX, token)
        pitch_match = re.match(PITCH_TOKEN_REGEX, token)
        phoneme_match = re.match(PHONEME_TOKEN_REGEX, token)
        if bpm_match:
            bpm = int(bpm_match.group(1))
            if bpm < 30:
                print(f"Bad BPM less than 30: {bpm}")
                return error_return
            beat_ms = 60000 // bpm
        elif pitch_match:
            tone_str = pitch_match.group(1)
            if tone_str not in NOTE_TO_TONE:
                print(f"Bad pitch: {token}")
                return error_return
            tone_id = NOTE_TO_TONE[tone_str]
        elif phoneme_match:
            prefix = phoneme_match.group(1)
            if prefix == "-":
                prefix = "_"
            presuf = prefix.split("-")
            prefix = presuf[0]
            if prefix != "_":
                if len(prefix) < 2:
                    return invalid_phoneme(prefix)
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
                print(f"Bad multiplier: {token}")
            dur_ms = int(beat_ms * beat_numer / beat_denom)
            t = TTSToken(prefix, suffix, dur_ms, tone_id)
            out_tokens.append(t)
        else:
            print(f"Bad token \"{token}\"")
            return error_return
    total_ms = 0
    for t in out_tokens:
        total_ms += t.dur_ms
    return " ".join(map(token_to_str, out_tokens)), total_ms


def compile_chorus(filename, *voices):
    translated = []
    durations = []
    filenames = []

    for i, voice in enumerate(voices):
        tts, dur = translate(voice)
        if not tts:
            print(f"Failed to translate part {i+1}")
            return False
        translated.append(tts)
        durations.append(dur)
        if len(voices) > 1:
            fn = tmp_fn(f"part-{i}", "wav")
            filenames.append(fn)
        else:
            filenames.append(filename)

    if len(set(durations)) > 1:
        print(f"Inconsistent nominal durations: {durations} milliseconds")
        return False

    master_track = None
    for i, (tr, dur, fn) in enumerate(zip(translated, durations, filenames)):
        success, retcode, error = commit_moonbase(tr, fn)
        if not success:
            print(f"Failed to export track {i+1}: {retcode}, {error}")
            return False
        audio = AudioSegment.from_file(fn)
        if len(translated) > 1:
            audio = audio.speedup(len(audio) / dur)
        if master_track is None:
            master_track = audio
        else:
            master_track = master_track.overlay(audio)

    master_track.export(filename, format='mp3')


def sing_song_file(infile, outfile):

    file = open(infile)
    if not file:
        return False

    tracks = []
    track = ""
    for line in file.read().splitlines():
        if not line:
            if track:
                tracks.append(track)
            track = ""
            continue
        if line.startswith("#"):
            continue
        track += line + " "
    if track:
        tracks.append(track)

    if not tracks:
        print(f"No tracks found in {infile}.")
        return False

    return compile_chorus(outfile, *tracks)


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
        format="[%(levelname)s] [%(name)s] %(message)s")

    filename = "song.mp3"
    songname = sys.argv[1]

    sing_song_file(songname, filename)


if __name__ == "__main__":
    main()
