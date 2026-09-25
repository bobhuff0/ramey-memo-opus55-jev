#!/usr/bin/env python3
"""Re-voice the Ramey memo video with a better TTS engine, then rebuild it.

Providers
  openai  POST https://api.openai.com/v1/audio/speech  (needs OPENAI_API_KEY)
          default model gpt-4o-mini-tts, default voice onyx; --instructions steers delivery
  gemini  generateContent on gemini-3.1-flash-tts-preview (needs GEMINI_API_KEY)
          default voice Charon; returns 24 kHz PCM
  piper   offline fallback (needs --piper-bin / --piper-model) — the voice you already heard
  elevenlabs  POST https://api.elevenlabs.io/v1/text-to-speech/<voice_id>  (needs ELEVENLABS_API_KEY)
          default model eleven_multilingual_v2, default voice Andrew (gUABw7pXQjhjt0kNFBTF);
          with --per-sentence the neighbouring sentences are sent as previous_text/next_text for continuity

By default each SCENE is synthesised as one request so the prosody flows across
sentences; caption cue times inside a scene are then allocated by character count.
Pass --per-sentence for exact per-sentence timing at the cost of some flow.

Every synthesised chunk is cached in cache/<sha1>.wav, so re-running with the same
provider/voice/text costs nothing.

Run from the build/ directory:
    python3 revoice.py --provider openai --voice onyx
Outputs: audio/<scene>.wav, manifest.json, captions.srt, scenes/*.mp4, ../Ramey-Memo-Opus55-Jev.mp4
"""
import os, sys, re, json, time, wave, base64, hashlib, argparse, subprocess, shutil
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(HERE, "audio"); CACHE = os.path.join(HERE, "cache")
os.makedirs(AUDIO, exist_ok=True); os.makedirs(CACHE, exist_ok=True)
SR = 24000
FINAL_MP4 = "Ramey-Memo-Opus55-Jev.mp4"
GAP, LEAD, TAIL = 0.45, 0.4, 0.6   # lead/tail are added to silence-trimmed clips (see trim_silence)

p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
p.add_argument("--provider", choices=["openai", "gemini", "piper", "elevenlabs"], required=True)
p.add_argument("--voice", default=None, help="openai: onyx/ash/echo/alloy/…  gemini: Charon/Kore/Puck/…")
p.add_argument("--model", default=None, help="openai: gpt-4o-mini-tts | tts-1-hd   gemini: gemini-3.1-flash-tts-preview")
p.add_argument("--instructions", default=(
    "Seasoned documentary narrator, in the register of a BBC history series. Warm, low, unhurried, but alive: "
    "vary pace and pitch with meaning rather than reading in one line. Slow down slightly and lean on numbers and "
    "on contrasts (Fort versus Tort, real grain versus half the grain, VICTIMS versus FINDING). Take a real beat after short "
    "declaratives such as 'It isn't.' and 'No.' Land sentence endings downward; no upspeak, no sing-song. Crisp "
    "consonants. Read words written in capitals as ordinary words. Read hyphenated capital letters (W-H-E-T-H-E-R) "
    "as individually spelled letters. Read single capital letters such as E and F as letter names."))
p.add_argument("--per-sentence", action="store_true", help="one request per sentence (exact caption timing)")
p.add_argument("--only", default=None, help="comma-separated scene ids to (re)build, for testing")
p.add_argument("--no-video", action="store_true", help="stop after audio + captions")
p.add_argument("--no-tidy", action="store_true", help="skip tidy_clip (edge-burst removal, pause cap, fades)")
p.add_argument("--piper-bin", default=os.environ.get("PIPER_BIN", "/tmp/piper/piper"))
p.add_argument("--piper-model", default=os.environ.get("PIPER_MODEL", "/tmp/en-us-ryan-high.onnx"))
A = p.parse_args()
ELEVENLABS_VOICES = {"gUABw7pXQjhjt0kNFBTF": "Andrew"}
ELEVENLABS_SEED = 1947
MODEL = A.model or {"openai": "gpt-4o-mini-tts", "gemini": "gemini-3.1-flash-tts-preview", "piper": "piper",
                    "elevenlabs": "eleven_multilingual_v2"}[A.provider]
VOICE = A.voice or {"openai": "onyx", "gemini": "Charon", "piper": "ryan", "elevenlabs": "gUABw7pXQjhjt0kNFBTF"}[A.provider]
VOICE_LABEL = ELEVENLABS_VOICES.get(VOICE, VOICE) if A.provider == "elevenlabs" else VOICE
if A.provider == "piper":
    # Piper's voice IS the model file; --voice does not select anything on that path
    if A.voice:
        print(f"note: --voice {A.voice!r} is ignored for piper; the voice is --piper-model", file=sys.stderr)
    VOICE = os.path.splitext(os.path.basename(A.piper_model))[0]      # e.g. en-us-ryan-high
CACHE_ID = MODEL if A.provider != "piper" else "piper:" + os.path.abspath(A.piper_model)   # cache key: one per model file
if A.no_video:
    # an audio-only preview is written to audio/preview/ so encode.py (which reads audio/<scene>.wav together
    # with manifest.json) can never mix preview audio with production timings
    AUDIO = os.path.join(AUDIO, "preview"); os.makedirs(AUDIO, exist_ok=True)
VOICE_TAG = f"{A.provider}/{MODEL}/{VOICE_LABEL}"   # provenance stored per scene in manifest.json (no slashes inside fields)


def clean(text):
    """Pronunciation nudges that hold for all three engines."""
    t = text.replace("TEX.", "Tex.").replace("NMEX", "New Mex").replace("UTA", "U-T-A").replace(" AI ", " A.I. ")
    t = t.replace("Opus 5.5", "Opus five point five").replace("AT FORT WORTH", "At Fort Worth").replace(" 2x.", " two-x.")
    for w in ["OF THE WRECK", "FORT WORTH", "TORT WORTH", "PORT WORTH", "WEATHER BALLOONS", "WHETHER BALLOONS", "FORWARDED",
              "BOMBARDED", "VICTIMS", "VIEWING", "REMAINS", "FINDING", "PACKING", "HOLDING", "SIGHTED", "RAMEY", "TEMPLE", "STORY", "LAND",
              "CREWS", "DISC", "DISK", "TIFF"]:
        t = t.replace(w, w.title() if " " in w else w.capitalize())
    t = re.sub(r"\b[A-Z]{3,}\b", lambda m: m.group(0) if m.group(0) in ACRONYMS else m.group(0).capitalize(), t)
    return t


ACRONYMS = {"U-T-A", "TIFF", "NMEX"}


def to_wav(src_bytes, path, src_is_pcm=False):
    """Normalise any returned audio to 24 kHz mono 16-bit WAV."""
    if src_is_pcm:
        with wave.open(path, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(src_bytes)
        return
    tmp = path + ".in"; open(tmp, "wb").write(src_bytes)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", tmp, "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", path], check=True)
    os.remove(tmp)


def synth_openai(text, path):
    import requests
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY is not set")
    body = {"model": MODEL, "voice": VOICE, "input": text, "response_format": "wav"}
    if MODEL.startswith("gpt-4o"):
        body["instructions"] = A.instructions
    r = requests.post("https://api.openai.com/v1/audio/speech", json=body, timeout=120,
                      headers={"Authorization": f"Bearer {key}"})
    if r.status_code != 200:
        sys.exit(f"OpenAI TTS error {r.status_code}: {r.text[:300]}")
    to_wav(r.content, path)


def synth_gemini(text, path):
    import requests
    key = os.environ.get("GEMINI_API_KEY") or sys.exit("GEMINI_API_KEY is not set")
    prompt = f"Read the following aloud in a calm, measured documentary-narrator voice at a moderate pace:\n\n{text}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
                      json=body, timeout=180, headers={"x-goog-api-key": key})
    if r.status_code != 200:
        sys.exit(f"Gemini TTS error {r.status_code}: {r.text[:300]}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    data = next(pt["inlineData"] for pt in parts if "inlineData" in pt)
    pcm = base64.b64decode(data["data"])
    to_wav(pcm, path, src_is_pcm=True)  # Gemini returns 16-bit PCM at 24 kHz


def synth_piper(text, path):
    tmp = path + ".piper.wav"
    subprocess.run([A.piper_bin, "--model", A.piper_model, "--output_file", tmp, "--sentence_silence", "0.1"],
                   input=text.encode(), capture_output=True, check=True)
    to_wav(open(tmp, "rb").read(), path); os.remove(tmp)


def synth_elevenlabs(text, path, prev=None, nxt=None):
    import requests
    key = os.getenv("ELEVENLABS_API_KEY") or sys.exit("ELEVENLABS_API_KEY is not set (export it from ~/.zshrc)")
    body = {"text": text, "model_id": MODEL, "seed": ELEVENLABS_SEED}
    if prev: body["previous_text"] = prev
    if nxt: body["next_text"] = nxt
    for attempt in range(5):
        try:
            r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}", params={"output_format": "pcm_24000"},
                              json=body, timeout=180, headers={"xi-api-key": key})
        except requests.RequestException as e:
            print(f"ElevenLabs request failed ({e}); retrying", file=sys.stderr); time.sleep(2 ** attempt); continue
        if r.status_code == 200:
            return to_wav(r.content, path, src_is_pcm=True)      # pcm_24000 = 16-bit mono PCM at 24 kHz
        if r.status_code in (429, 500, 502, 503, 504):
            print(f"ElevenLabs {r.status_code}; retrying", file=sys.stderr); time.sleep(2 ** attempt); continue
        sys.exit(f"ElevenLabs TTS error {r.status_code}: {r.text[:300]}")
    sys.exit("ElevenLabs TTS failed after 5 attempts")


SYNTH = {"openai": synth_openai, "gemini": synth_gemini, "piper": synth_piper, "elevenlabs": synth_elevenlabs}[A.provider]


def trim_silence(raw, margin_after=0.10, thresh=0.01):
    """Cut leading/trailing silence (below -40 dBFS) from a cached 24 kHz mono 16-bit clip.
    Keeps from the first loud sample to the last loud sample + margin_after. Writes <raw>.trim.wav next to the
    untouched raw file (regenerated when missing). Returns (trimmed_path, duration_seconds)."""
    import numpy as np
    out = raw[:-4] + ".trim.wav"
    if not os.path.exists(out):
        with wave.open(raw) as w:
            sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        if ch != 1 or sw != 2:
            sys.exit(f"unexpected WAV format in {raw} (want mono 16-bit)")
        loud = np.flatnonzero(np.abs(data.astype(np.int32)) > int(thresh * 32767))
        a = int(loud[0]) if len(loud) else 0
        b = min(len(data), int(loud[-1]) + int(margin_after * sr) + 1) if len(loud) else len(data)
        with wave.open(out, "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(data[a:b].tobytes())
    with wave.open(out) as w:
        return out, w.getnframes() / w.getframerate()


TIDY_FRAME_S = 0.01
TIDY_SOUND_DB = -45.0        # frame RMS above this counts as sound
TIDY_MAX_TRAIL_BURST_S = 0.15   # shorter than any real final word
TIDY_MAX_LEAD_BURST_S = 0.12    # shorter than a one-word sentence such as "No."
TIDY_MIN_ISOLATION_S = 0.25
TIDY_MAX_PAUSE_S = 0.70
TIDY_FADE_IN_S, TIDY_FADE_OUT_S = 0.010, 0.030


def tidy_clip(trimmed, margin_after=0.10):
    """Remove the artifacts ElevenLabs leaves at clip edges when given previous_text/next_text: an isolated
    breath or the clipped first syllable of the next sentence after the last word ('gulps'), or a stray burst
    before the first word. Also caps long pauses inside a sentence and fades both ends so no join clicks.
    Writes <clip>.tidy.wav once; returns (path, duration_seconds, report)."""
    import numpy as np
    out = trimmed[:-9] + ".tidy.wav"
    rep_path = out[:-4] + ".json"
    if not os.path.exists(out) or not os.path.exists(rep_path):
        with wave.open(trimmed) as w:
            sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32)
        f = int(TIDY_FRAME_S * sr); n = len(x) // f
        if n < 3:
            shutil.copy(trimmed, out); json.dump({}, open(rep_path, "w", encoding="utf-8"))
        else:
            db = 20 * np.log10(np.sqrt(((x[: n * f] / 32768.0).reshape(n, f) ** 2).mean(1)) + 1e-9)
            segs, i = [], 0
            while i < n:
                if db[i] > TIDY_SOUND_DB:
                    j = i
                    while j < n and db[j] > TIDY_SOUND_DB: j += 1
                    if segs and (i - segs[-1][1]) * TIDY_FRAME_S < 0.06:
                        segs[-1][1] = j
                    else:
                        segs.append([i, j])
                    i = j
                else:
                    i += 1
            rep = dict(dropped_trailing=[], dropped_leading=[], pauses_capped=[])
            while len(segs) > 1 and (segs[-1][1] - segs[-1][0]) * TIDY_FRAME_S <= TIDY_MAX_TRAIL_BURST_S \
                    and (segs[-1][0] - segs[-2][1]) * TIDY_FRAME_S >= TIDY_MIN_ISOLATION_S:
                rep["dropped_trailing"].append(round(segs[-1][0] * TIDY_FRAME_S, 2)); segs.pop()
            while len(segs) > 1 and (segs[0][1] - segs[0][0]) * TIDY_FRAME_S <= TIDY_MAX_LEAD_BURST_S \
                    and (segs[1][0] - segs[0][1]) * TIDY_FRAME_S >= TIDY_MIN_ISOLATION_S:
                rep["dropped_leading"].append(round(segs[0][0] * TIDY_FRAME_S, 2)); segs.pop(0)
            if segs:
                a = max(0, segs[0][0] * f - int(0.02 * sr)); b = min(len(x), segs[-1][1] * f + int(margin_after * sr))
                keep, cur = [], a
                for s0, s1 in zip(segs, segs[1:]):
                    g0, g1 = s0[1] * f, s1[0] * f
                    if (g1 - g0) / sr > TIDY_MAX_PAUSE_S:
                        half = int(TIDY_MAX_PAUSE_S * sr / 2)
                        keep.append(x[cur:g0 + half]); cur = g1 - half
                        rep["pauses_capped"].append([round(g0 / sr, 2), round((g1 - g0) / sr, 2)])
                keep.append(x[cur:b]); y = np.concatenate(keep)
            else:
                y = x.copy()
            fi, fo = int(TIDY_FADE_IN_S * sr), int(TIDY_FADE_OUT_S * sr)
            y[:fi] *= np.linspace(0, 1, fi); y[-fo:] *= np.linspace(1, 0, fo)
            with wave.open(out, "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(np.clip(y, -32768, 32767).astype(np.int16).tobytes())
            json.dump(rep, open(rep_path, "w", encoding="utf-8"))
    with wave.open(out) as w:
        d = w.getnframes() / w.getframerate()
    return out, d, json.load(open(rep_path, encoding="utf-8"))


def synth_cached(text, prev=None, nxt=None):
    ctx = f"|{prev}|{nxt}" if A.provider == "elevenlabs" else ""
    key = hashlib.sha1(f"{A.provider}|{CACHE_ID}|{VOICE}|{A.instructions if A.provider=='openai' else ''}|{text}{ctx}".encode()).hexdigest()
    path = os.path.join(CACHE, key + ".wav")
    if not os.path.exists(path):
        if A.provider == "elevenlabs":
            SYNTH(clean(text), path, clean(prev) if prev else None, clean(nxt) if nxt else None)
        else:
            SYNTH(clean(text), path)
    trimmed, d = trim_silence(path)
    if A.no_tidy:
        return trimmed, d
    tidy, d, rep = tidy_clip(trimmed)
    if any(rep.values()):
        print(f"  tidied {text[:48]!r}: {rep}", flush=True)
    return tidy, d


def word_times(path):
    """start times (s) of the spoken words in a trimmed clip, via whisper-1 word timestamps; cached as .words.json.
    Used only to time caption chunks inside a sentence (QC v2 m4). Returns None when unavailable."""
    j = path[:-4] + ".words.json"
    if os.path.exists(j):
        return json.load(open(j))
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    import requests
    with open(path, "rb") as f:
        r = requests.post("https://api.openai.com/v1/audio/transcriptions", headers={"Authorization": f"Bearer {key}"},
                          files={"file": (os.path.basename(path), f, "audio/wav")},
                          data={"model": "whisper-1", "response_format": "verbose_json", "timestamp_granularities[]": "word"}, timeout=300)
    if r.status_code != 200:
        return None
    w = [float(x["start"]) for x in r.json().get("words", [])]
    json.dump(w, open(j, "w"))
    return w


def silence(sec, path):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"anullsrc=r={SR}:cl=mono", "-t", f"{sec:.3f}",
                    "-c:a", "pcm_s16le", path], check=True)


def concat_wavs(parts, out):
    lst = out + ".txt"; open(lst, "w").write("".join(f"file '{q}'\n" for q in parts))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    os.remove(lst)


def loudnorm(path):
    tmp = path + ".ln.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", str(SR), tmp], check=True)
    shutil.move(tmp, path)


# ---------------------------------------------------------------- synthesis
only = set(A.only.split(",")) if A.only else None
old = {m["id"]: m for m in json.load(open(os.path.join(HERE, "manifest.json")))} if os.path.exists(os.path.join(HERE, "manifest.json")) else {}
manifest = []; t_global = 0.0
for sc in SCENES:
    if only and sc["id"] not in only and sc["id"] in old:
        m = dict(old[sc["id"]]); m["start"] = t_global; manifest.append(m); t_global += m["duration"]; continue
    parts = []; cues = []; t = LEAD
    lead = os.path.join(AUDIO, f"{sc['id']}_lead.wav"); silence(LEAD, lead); parts.append(lead)
    if A.per_sentence:
        for i, sent in enumerate(sc["narration"]):
            nar = sc["narration"]
            path, d = synth_cached(sent, nar[i - 1] if i else None, nar[i + 1] if i + 1 < len(nar) else None); parts.append(path)
            cues.append(dict(text=sent, start=t, end=t + d, words=word_times(path))); t += d
            if i < len(sc["narration"]) - 1:
                g = os.path.join(AUDIO, f"{sc['id']}_gap{i:02d}.wav"); silence(GAP, g); parts.append(g); t += GAP
    else:
        text = " ".join(sc["narration"])
        path, d = synth_cached(text); parts.append(path)
        total_chars = sum(len(s) for s in sc["narration"]); cur = t
        for sent in sc["narration"]:
            dd = d * len(sent) / total_chars; cues.append(dict(text=sent, start=cur, end=cur + dd)); cur += dd
        t += d
    tail = os.path.join(AUDIO, f"{sc['id']}_tail.wav"); silence(TAIL, tail); parts.append(tail); t += TAIL
    out = os.path.join(AUDIO, f"{sc['id']}.wav"); concat_wavs(parts, out); loudnorm(out)
    with wave.open(out) as w:
        dur = w.getnframes() / w.getframerate()
    manifest.append(dict(id=sc["id"], chapter=sc["chapter"], layout=sc["layout"], start=t_global, duration=dur, cues=cues, voice=VOICE_TAG))
    print(f"{sc['id']:14s} {dur:6.1f}s  starts {t_global:6.1f}s  [{A.provider}/{VOICE_LABEL}]", flush=True)
    t_global += dur
print(f"total {t_global:.1f} s")
# manifest.json describes the scenes that get ENCODED. An audio-only preview (--no-video) writes
# manifest.preview.json instead, so a later --only rebuild still carries over the encoded scenes' entries.
manifest_path = os.path.join(HERE, "manifest.preview.json" if A.no_video else "manifest.json")
json.dump(manifest, open(manifest_path, "w"), indent=1)


def ts(sec):
    h = int(sec // 3600); m = int(sec % 3600 // 60); s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def split_cue(text, start, end, words=None, limit=84):
    """split a sentence into balanced caption chunks of <= limit chars (no one-word orphans). Chunk start times
    come from the clip's word timestamps (index mapped proportionally), else from character counts."""
    import math
    w = text.split()
    if len(text) <= limit:
        return [(text, start, end)]
    n = math.ceil(len(text) / limit)
    while True:
        target = len(text) / n; chunks, cur = [], []
        for i, x in enumerate(w):
            if cur and (len(" ".join(cur + [x])) > limit or (len(" ".join(cur)) >= target and len(chunks) < n - 1)):
                chunks.append(cur); cur = []
            cur.append(x)
        chunks.append(cur)
        if all(len(" ".join(c)) <= limit for c in chunks):
            break
        n += 1
    idx = [0]
    for c in chunks[:-1]: idx.append(idx[-1] + len(c))
    if words:
        starts = [start + words[min(len(words) - 1, round(i * len(words) / len(w)))] if i else start for i in idx]
    else:
        tot = sum(len(" ".join(c)) for c in chunks); starts, t = [], start
        for c in chunks: starts.append(t); t += (end - start) * len(" ".join(c)) / tot
    ends = starts[1:] + [end]
    return [(" ".join(c), a, b) for c, a, b in zip(chunks, starts, ends)]


import re
srt = []; n = 1; prev_end = 0.0
for sc in manifest:
    for c in sc["cues"]:
        for text, a0, a1 in split_cue(c["text"], c["start"], c["end"], c.get("words")):
            t0 = max(sc["start"] + a0, prev_end); t1 = max(sc["start"] + a1, t0 + 0.2)    # no overlaps at scene joins
            srt.append(f"{n}\n{ts(t0)} --> {ts(t1)}\n{text}\n"); n += 1; prev_end = t1
open(os.path.join(HERE, "captions.srt"), "w", encoding="utf-8").write("\n".join(srt))
import math
def chap_t(t): t = math.ceil(t - 1e-6); return f"{t // 60:02d}:{t % 60:02d}"
chap = "\n".join(f"{chap_t(m['start'])} {m['chapter']}" for m in manifest if m["chapter"])
open(os.path.join(HERE, "chapters.txt"), "w", encoding="utf-8").write(chap + "\n")
print("captions.srt and chapters.txt written\n" + chap)
if A.no_video:
    print("audio-only preview: wrote audio/preview/<scene>.wav and manifest.preview.json; audio/<scene>.wav, manifest.json, the MP4 and the package texts are unchanged")
    sys.exit(0)

# ---------------------------------------------------------------- video
if not os.path.exists(os.path.join(HERE, "stills", "01_title.png")):
    subprocess.run([sys.executable, os.path.join(HERE, "render.py")], check=True)
ids = [m["id"] for m in manifest if (not only or m["id"] in only)]
subprocess.run([sys.executable, os.path.join(HERE, "encode.py")] + ids, check=True)
open(os.path.join(HERE, "concat.txt"), "w").write("".join(f"file 'scenes/{m['id']}.mp4'\n" for m in manifest))
final = os.path.join(HERE, "..", FINAL_MP4)
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(HERE, "concat.txt"),
                "-c", "copy", "-movflags", "+faststart", final], check=True, cwd=HERE)
shutil.copy(os.path.join(HERE, "captions.srt"), os.path.join(HERE, "..", "captions.srt"))
print("wrote", os.path.abspath(final))

def credit_line(manifest):
    """Narration credit derived from per-scene provenance. Every form ends with ', voice <token>'."""
    def fmt(tag, sep=", "):
        if tag == "unknown":
            return f"unknown engine{sep}voice unknown"
        prov, model, voice = tag.split("/", 2)
        name = {"openai": f"OpenAI {model}", "gemini": f"Google {model}", "piper": "Piper TTS",
                "elevenlabs": f"ElevenLabs {model}"}.get(prov, f"{prov} {model}")
        return f"{name}{sep}voice {voice}"
    tags = []
    for m in manifest:
        t = m.get("voice", "unknown")     # absent field = unknown, never inferred
        if t not in tags: tags.append(t)
    if len(tags) == 1:
        return fmt(tags[0])
    return "mixed (" + "; ".join(fmt(t, " ") for t in tags) + "), voice varies"


import re
credit = credit_line(manifest)
runtime = f"{int(t_global//60)}:{int(t_global%60):02d}"

# patch ../description.txt: CHAPTERS block, runtime and narration credit
dpath = os.path.join(HERE, "..", "description.txt")
if os.path.exists(dpath):
    d = open(dpath, encoding="utf-8").read()
    d = re.sub(r"CHAPTERS\n(?:\d\d:\d\d [^\n]*\n)+", "CHAPTERS\n" + chap + "\n", d)
    d = re.sub(r"AI-generated narration: .*?, voice [^\s.]+\.", f"AI-generated narration: {credit}.", d, count=1)
    d = re.sub(r"This (\d+:\d\d) investigation", f"This {runtime} investigation", d)
    open(dpath, "w", encoding="utf-8").write(d)
    print("updated ../description.txt (chapters, runtime, narration credit)")

# regenerate ../script.md from the rendered timings
title = "Roswell\u2019s Ramey Memo: Can the Latest AI Read It?"
tpath = os.path.join(HERE, "..", "title.txt")
if os.path.exists(tpath):
    title = open(tpath, encoding="utf-8").read().strip() or title
def mmss(t): return f"{int(t//60):02d}:{int(t%60):02d}"
lines = [f"# Narration script \u2014 {title}", "", f"Runtime {mmss(t_global)}. Scene starts are from the rendered file.", ""]
for m in manifest:
    lines += [f"## {mmss(m['start'])}  {m['id']}" + (f" \u2014 {m['chapter']}" if m.get("chapter") else ""), f"*Visual: {m['layout']}*", ""]
    lines += [f"- [{mmss(m['start'] + c['start'])}] {c['text']}" for c in m["cues"]]
    lines.append("")
open(os.path.join(HERE, "..", "script.md"), "w", encoding="utf-8").write("\n".join(lines))
print("regenerated ../script.md")

# patch ../README.md by stable field: runtime in the MP4 table row, and the narration sentence
rpath = os.path.join(HERE, "..", "README.md")
if os.path.exists(rpath):
    r = open(rpath, encoding="utf-8").read()
    r = re.sub(r"^\|\s*`" + re.escape(FINAL_MP4) + r"`\s*\|[^\n]*$",
               lambda mo: re.sub(r"\d+:\d\d", runtime, mo.group(0), count=1), r, count=1, flags=re.M)
    r = re.sub(r"The narration in the shipped MP4 is (?:.*?, voice [^\s.]+|[^\n]*?placeholder)\.",
               f"The narration in the shipped MP4 is {credit}.", r, count=1)
    open(rpath, "w", encoding="utf-8").write(r)
    print("updated ../README.md (runtime, narration credit)")
