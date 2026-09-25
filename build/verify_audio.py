#!/usr/bin/env python3
"""Check that every scene's narration audio says the whole script (QC finding B1: the TTS engine can
silently drop the end of a long request), numbers included (QC v2 m6).

Transcribes audio/<scene>.wav with OpenAI speech-to-text and aligns the words with build/script.py.
Digits in the transcript (and in the script) are spelled out first, so numbers are compared too.
Fails (exit 1) when any run of 3+ script words is missing, when any missing run contains a number word,
or when a scene's word match is below 0.9.
Writes verify_audio.json. Run from build/ after revoice.py:  python3 verify_audio.py [--model gpt-4o-transcribe]
"""
import os, re, sys, json, difflib, argparse, requests
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth", "twelve": "twelfth"}
NUMWORDS = set(ONES + TENS[2:] + ["hundred", "thousand", "point"]) | {ORD.get(w, w + "th") for w in ONES + TENS[2:]} | {
    "twentieth", "thirtieth", "fortieth", "fiftieth", "sixtieth", "seventieth", "eightieth", "ninetieth", "hundredth"}


def spell(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if 1100 <= n < 2100 and n % 100 != 0: return spell(n // 100) + " " + spell(n % 100)       # years: nineteen forty seven
    if n < 1000: return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + spell(n % 100))
    return spell(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + spell(n % 1000))


def ordinal(words):
    *head, last = words.split()
    last = last[:-1] + "ieth" if last.endswith("y") else ORD.get(last, last + "th")
    return " ".join(head + [last])


def spell_numbers(t):
    t = re.sub(r"(\d+)\s*%", r"\1 percent", t)
    t = re.sub(r"(\d*)\.(\d+)", lambda m: (spell(int(m.group(1))) + " " if m.group(1) else "") + "point " + " ".join(ONES[int(c)] for c in m.group(2)), t)
    t = re.sub(r"(\d+)(st|nd|rd|th)\b", lambda m: ordinal(spell(int(m.group(1)))), t)
    t = re.sub(r"\d[\d,]*", lambda m: spell(int(m.group(0).replace(",", ""))), t)
    return t


def words(t):
    t = t.lower().replace("’", "'")
    t = re.sub(r"(?<=\d)dpi\b", " dpi", t)
    t = re.sub(r"\bdpi\b", "dots per inch", t).replace("filenames", "file names").replace("telltale", "tell tale")
    t = re.sub(r"\b(\d+)x\b", r"\1 x", t)
    t = spell_numbers(t).replace("-", " ")
    w = [x.strip("'") for x in re.findall(r"[a-z']+", t)]
    return [x for x in w if x and x not in ("a", "and")]      # 'a hundred and seventy' vs 'one hundred seventy'


def transcribe(path, model):
    key = os.environ.get("OPENAI_API_KEY") or sys.exit("OPENAI_API_KEY is not set")
    with open(path, "rb") as f:
        r = requests.post("https://api.openai.com/v1/audio/transcriptions", headers={"Authorization": f"Bearer {key}"},
                          files={"file": (os.path.basename(path), f, "audio/wav")}, data={"model": model}, timeout=300)
    if r.status_code != 200:
        sys.exit(f"transcription error {r.status_code}: {r.text[:300]}")
    return r.json()["text"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--model", default="gpt-4o-transcribe"); A = ap.parse_args()
    report, bad = {}, False
    for sc in SCENES:
        ref = words(" ".join(sc["narration"]))
        hyp_text = transcribe(os.path.join(HERE, "audio", f"{sc['id']}.wav"), A.model)
        hyp = words(hyp_text)
        sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
        missing = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in ("delete", "replace"):
                run = ref[i1:i2]
                gone = [x for x in run if x not in hyp[j1:j2]]
                if len(run) >= 3 or any(x in NUMWORDS for x in gone):
                    missing.append(" ".join(run) + (f"  (heard: {' '.join(hyp[j1:j2])})" if j2 > j1 else ""))
        ratio = sm.ratio()
        ok = ratio >= 0.9 and not missing
        bad |= not ok
        report[sc["id"]] = dict(ok=ok, match=round(ratio, 3), missing=missing, transcript=hyp_text)
        print(f"{sc['id']:14s} {'OK  ' if ok else 'FAIL'} match {ratio:.3f}" + (f"  missing: {missing}" if missing else ""), flush=True)
    json.dump(report, open(os.path.join(HERE, "verify_audio.json"), "w"), indent=1)
    print("ALL SCENES OK" if not bad else "SOME SCENES FAILED")
    sys.exit(1 if bad else 0)
