"""Scan every cached ElevenLabs sentence clip for narration artifacts: short isolated bursts (breaths, gulps,
lip smacks) before the first word or after the last word, and long pauses inside a sentence.

Run from build/:  python3 qc/audio_artifacts.py
Writes qc/audio_artifacts.json.
"""
import os, sys, json, wave, hashlib
import numpy as np
from termcolor import cprint

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from script import SCENES

CACHE = os.path.join(HERE, "cache")
OUT_JSON = os.path.join(HERE, "qc", "audio_artifacts.json")
PROVIDER, MODEL, VOICE = "elevenlabs", "eleven_multilingual_v2", "gUABw7pXQjhjt0kNFBTF"
FRAME_S = 0.02
SPEECH_DB = -45.0          # frame counts as sound above this
MAX_BURST_S = 0.35         # an edge segment this short, cut off from the words, is an artifact
MIN_ISOLATION_S = 0.25     # silence separating it from the words
LONG_PAUSE_S = 0.9         # internal pause worth reporting


def cache_path(text, prev, nxt):
    ctx = f"|{prev}|{nxt}"
    key = hashlib.sha1(f"{PROVIDER}|{MODEL}|{VOICE}||{text}{ctx}".encode()).hexdigest()
    return os.path.join(CACHE, key + ".wav")


def segments(path):
    with wave.open(path) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), np.int16) / 32768.0
    f = int(FRAME_S * sr); n = len(x) // f
    db = 20 * np.log10(np.sqrt((x[: n * f].reshape(n, f) ** 2).mean(1)) + 1e-9)
    on = db > SPEECH_DB
    segs, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]: j += 1
            segs.append((i * FRAME_S, j * FRAME_S, float(db[i:j].max()))); i = j
        else:
            i += 1
    # merge segments separated by < 60 ms (consonant gaps)
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 0.06:
            merged[-1] = (merged[-1][0], s[1], max(merged[-1][2], s[2]))
        else:
            merged.append(s)
    return merged, n * FRAME_S


def main():
    report, t_missing = [], 0
    for sc in SCENES:
        nar = sc["narration"]
        for i, sent in enumerate(nar):
            p = cache_path(sent, nar[i - 1] if i else None, nar[i + 1] if i + 1 < len(nar) else None)
            if not os.path.exists(p):
                t_missing += 1; cprint(f"missing clip: {sc['id']} #{i}", "red"); continue
            try:
                segs, dur = segments(p)
            except Exception as e:
                cprint(f"could not read {p}: {e}", "red"); continue
            issues = []
            if len(segs) > 1:
                a, b = segs[0], segs[1]
                if a[1] - a[0] <= MAX_BURST_S and b[0] - a[1] >= MIN_ISOLATION_S:
                    issues.append(dict(kind="leading burst", at=round(a[0], 2), length=round(a[1] - a[0], 2), gap=round(b[0] - a[1], 2), peak_db=round(a[2], 1)))
                a, b = segs[-1], segs[-2]
                if a[1] - a[0] <= MAX_BURST_S and a[0] - b[1] >= MIN_ISOLATION_S:
                    issues.append(dict(kind="trailing burst", at=round(a[0], 2), length=round(a[1] - a[0], 2), gap=round(a[0] - b[1], 2), peak_db=round(a[2], 1)))
                for s0, s1 in zip(segs, segs[1:]):
                    if s1[0] - s0[1] >= LONG_PAUSE_S and not (s1 is segs[-1] and issues and issues[-1]["kind"] == "trailing burst"):
                        issues.append(dict(kind="long pause", at=round(s0[1], 2), length=round(s1[0] - s0[1], 2)))
            report.append(dict(scene=sc["id"], index=i, text=sent, clip=os.path.basename(p), duration=round(dur, 2), issues=issues))
            if issues:
                cprint(f"{sc['id']} #{i}: {sent[:60]}", "yellow")
                for q in issues: cprint(f"    {q}", "yellow")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
    bad = sum(1 for r in report if r["issues"])
    cprint(f"{len(report)} clips scanned, {bad} with artifacts, {t_missing} missing -> {OUT_JSON}", "cyan")


if __name__ == "__main__":
    main()
