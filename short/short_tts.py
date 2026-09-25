"""Narration for the Short: one ElevenLabs request for the whole script (no sentence joins, so no gulps), with
character timestamps used to time every caption chunk. Cached by text hash; loudness-normalised to -14 LUFS.

Run from short/:  python3 short_tts.py
Writes out/narration.wav and out/timing.json.
"""
import os, sys, json, base64, hashlib, subprocess, wave
import requests
from termcolor import cprint
from short_script import BEATS, spoken_text

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
CACHE = os.path.join(OUT, "cache")
NARRATION_WAV = os.path.join(OUT, "narration.wav")
TIMING_JSON = os.path.join(OUT, "timing.json")
ELEVENLABS_MODEL = "eleven_multilingual_v2"
ELEVENLABS_VOICE = "gUABw7pXQjhjt0kNFBTF"   # Andrew
ELEVENLABS_SEED = 1947
VOICE_SETTINGS = {"stability": 0.45, "similarity_boost": 0.8, "style": 0.35, "use_speaker_boost": True}
SR = 24000
LEAD_S = 0.15           # silence before the first word
TAIL_S = 0.8            # silence after the last word
LOUDNESS = "loudnorm=I=-14:TP=-1.5:LRA=11"


def synth(text):
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        sys.exit("ELEVENLABS_API_KEY is not set (export it from ~/.zshrc)")
    body = {"text": text, "model_id": ELEVENLABS_MODEL, "seed": ELEVENLABS_SEED, "voice_settings": VOICE_SETTINGS}
    h = hashlib.sha1(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]
    cached = os.path.join(CACHE, f"{h}.json")
    if os.path.exists(cached):
        cprint(f"[tts] using cached take {h}", "cyan")
        with open(cached, encoding="utf-8") as f:
            return json.load(f)
    cprint(f"[tts] requesting ElevenLabs ({ELEVENLABS_MODEL}, Andrew), {len(text)} characters", "cyan")
    try:
        r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE}/with-timestamps",
                          params={"output_format": "pcm_24000"}, json=body, timeout=300, headers={"xi-api-key": key})
    except requests.RequestException as e:
        sys.exit(f"ElevenLabs request failed: {e}")
    if r.status_code != 200:
        sys.exit(f"ElevenLabs error {r.status_code}: {r.text[:300]}")
    data = r.json()
    os.makedirs(CACHE, exist_ok=True)
    with open(cached, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def main():
    os.makedirs(OUT, exist_ok=True)
    text, spans = spoken_text()
    data = synth(text)
    al = data.get("alignment") or data.get("normalized_alignment")
    chars, starts, ends = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
    if "".join(chars) != text:
        cprint("[warn] alignment text differs from the script; mapping by position anyway", "yellow")
    pcm = base64.b64decode(data["audio_base64"])
    raw = os.path.join(OUT, "narration_raw.wav")
    lead = b"\x00\x00" * int(LEAD_S * SR); tail = b"\x00\x00" * int(TAIL_S * SR)
    with wave.open(raw, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(lead + pcm + tail)
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", LOUDNESS, "-ar", str(SR), NARRATION_WAV], check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"loudness normalisation failed: {e}")
    duration = (len(lead) + len(pcm) + len(tail)) / 2 / SR

    chunks = []
    for b, c, a, z in spans:
        z = min(z, len(starts)) - 1
        chunks.append(dict(beat=b, chunk=c, start=round(LEAD_S + starts[a], 3), end=round(LEAD_S + ends[z], 3),
                           display=BEATS[b]["chunks"][c][1]))
    beats = []
    for b in range(len(BEATS)):
        mine = [ch for ch in chunks if ch["beat"] == b]
        beats.append(dict(beat=b, visual=BEATS[b]["visual"], kicker=BEATS[b]["kicker"], start=mine[0]["start"]))
    for i, bt in enumerate(beats):
        bt["end"] = beats[i + 1]["start"] if i + 1 < len(beats) else duration
    beats[0]["start"] = 0.0
    with open(TIMING_JSON, "w", encoding="utf-8") as f:
        json.dump(dict(duration=round(duration, 3), beats=beats, chunks=chunks), f, indent=1)
    cprint(f"[ ok ] narration {duration:.1f} s -> {NARRATION_WAV}", "green")
    for bt in beats:
        cprint(f"      {bt['start']:5.1f}-{bt['end']:5.1f}  {bt['visual']}", "green")


if __name__ == "__main__":
    main()
