"""Step 10: Jev checks every narration sentence of ../build/script.py against the evidence (results.json, sources).
Code decides what happens to each answer: a sentence Jev finds checkable (P >= 0.5) and not 'supports' at confidence
>= 0.8 goes to human review. Answers are cached per scene (sentences + evidence + prompts), so unchanged scenes are
not re-asked. Reviewer notes (REVIEW_NOTES, checked by Claude Opus 5.5 against results.json and factcheck.md) are
printed in the report next to Jev's answer; a flagged sentence without a note is PENDING."""
import os, json, hashlib, importlib.util
from common import HERE, OUT, info, ok, warn, err, save_result, load_results
from evidence import scene_evidence, SCENE_TOPICS
from jev_claims import check_scenes, JEV_MODEL, PROMPT_VERSION

SCRIPT = os.path.join(HERE, "..", "build", "script.py")
CACHE = os.path.join(OUT, "jev_script_check.json")
REPORT_MD = os.path.join(OUT, "script_check.md")
CHECKABLE_THRESHOLD = 0.5
AUTO_ACCEPT = 0.8
REVIEWER = "Claude Opus 5.5, against results.json and factcheck.md"
REVIEW_NOTES = {
    "For almost forty years": "Confirmed: factcheck.md 2, Brad Sparks made out words in the mid-1980s; about forty years by 2026.",
    "The film is a negative, so the typed letters": "Confirmed: letters are lighter than the background in every file; "
                                                    "steps s1-s5 measured the files before any reading.",
    "One of its flags sent Opus 5.5 back": "Confirmed: Jev answered 'contradicts' on the sharp-letter sentence; the review found "
                                           "blurred templates in the sharp condition; the re-run changed 0 of 20 to 4 of 20.",
    "Claude Opus 5.5 wrote and ran every step": "Confirmed: steps s1-s8 were written and run in this session by Claude Opus 5.5.",
    "On the right half, the four brightness files": "Confirmed: max shift 0.153 px (under 1/6 px = 0.167); grain NCC 0.80-0.92.",
    "Opus 5.5 mapped that shift point by point": "Confirmed: after dense re-alignment, left 65B 0.89 and 70B 0.87 ('almost point nine'); "
                                                 "55B, 21% clipped, 0.74; right half 0.80-0.92.",
    "The paper is curled and tilted.": "Confirmed: right line 5 drifts 339 px; right median spacing 547 px (ratio 0.62).",
    "This is the cleanest view of the memo": "Judgment, worded as Opus 5.5's result; nine lines confirmed (left 1-8, right 1,2,4-9).",
    "The short line: AT FORT WORTH, TEX.": "Confirmed: line 3 is traced only on the left half; agreed words AT FORT WORTH TEX.",
    "WEATHER BALLOONS on line seven": "Confirmed: line 7 WEATHER 9 and BALLOONS 9 readers; line 9 one position, 1,648 px traced.",
    "Fourteen reach eight of ten readers.": "Confirmed: 8+ readers at 14 of 74 positions; 6+ at 22 of 74 = 29.7%.",
    "Only five word positions are unanimous": "Confirmed: 10/10 at line 2 OF, THE and line 3 AT, FORT, WORTH; factcheck.md also counts 5.",
    "Jev merged the C and K spellings of DISC": "Confirmed: line 4 DISK = DISC, 7 readers; factcheck.md 8b 'THE + quoted disc 7/10'; RAMEY 5, TEMPLE 3.",
    "Moving Jev's same-word threshold": "Confirmed: 6+ gives 22/22/21/21 and 10/10 gives 6/5/5/5 at 0.3/0.5/0.7/0.9; others unchanged.",
    "What survives is a skeleton": "Interpretation of the agreed words: WRECK, FORWARDED, AT FORT WORTH TEX, WEATHER BALLOONS; "
                                   "the first paragraph's content words fall below 6 readers.",
    "VICTIMS, say six of the ten readers": "Confirmed: VICTIMS readers include David Rudiak (R); factcheck.md 3: memo work since "
                                           "about 1999-2000, so more than twenty-five years.",
    "REMAINS, say two others.": "Confirmed: REMAINS (Fishbine, McNeff), FINDING (Sparks); VIEWING suggested (factcheck.md 4d).",
    "By Jev's count, VICTIMS just clears": "Confirmed: 6 readers equals the 6-reader threshold; second sentence is a caution, not a claim.",
    "Opus 5.5 rendered five undisputed phrases": "Confirmed: 4 fonts; 9 pitches, 3 letter heights, 5 blurs; slid along each straightened line.",
    "Some random strings beat every true phrase": "Confirmed: random strings above the truth range from 8/300 (WEATHER BALLOONS) to "
                                                  "219/300 (RAMEY); 65-144 one-letter misspellings beat each phrase.",
    "Five phrases on four patches of film": "Confirmed: A and B each 5 phrases x 4 patches = 20 trials; Courier New Bold at 216 px in the search.",
    "FINDING came first out of three hundred and seven": "Confirmed: FINDING 1, REMAINS 4, VICTIMS 31 of 307; 26 random strings above VICTIMS.",
    "No. Not even the latest AI": "Conclusion from the calibration (true phrases 149th-285th) and synthetic (blurred: 0 of 20) results.",
}


def load_scenes():
    try:
        spec = importlib.util.spec_from_file_location("script", SCRIPT); mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod); return mod.SCENES
    except Exception as e:
        err(f"cannot load {SCRIPT}: {e}"); raise


def load_cache():
    if not os.path.exists(CACHE): return {}
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        warn(f"cache unreadable, asking Jev again: {e}"); return {}


def scene_key(sentences, evidence):
    blob = json.dumps([JEV_MODEL, PROMPT_VERSION, sentences, evidence], sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def classify(a):
    if a["p_checkable"] < CHECKABLE_THRESHOLD: return "not a claim"
    if a["relation"] == "supports" and a["confidence"] >= AUTO_ACCEPT: return "verified"
    return "review"


def review_note(sentence):
    return next((note for prefix, note in REVIEW_NOTES.items() if sentence.startswith(prefix)), "")


def write_markdown(rows, model, counts):
    lines = ["# Jev script check", "",
             f"Model: `{model}`. Each narration sentence was judged against the evidence for its scene "
             f"(topics per scene in `evidence.py`). Checkable at P >= {CHECKABLE_THRESHOLD}; auto-accepted when Jev "
             f"answers 'supports' at confidence >= {AUTO_ACCEPT}; everything else goes to review.", "",
             f"Sentences: {counts['sentences']} · checkable: {counts['checkable']} · verified by Jev: {counts['verified']} "
             f"· sent to review: {counts['review']}", "",
             "The evidence is the project's own record (measured results, the source fact-check, and a description of "
             "the process), so this checks that the narration matches the record; it does not re-measure anything.", "",
             f"## Sent to review (reviewer: {REVIEWER})", ""]
    for r in rows:
        if r["action"] == "review":
            p = r["probabilities"]
            lines.append(f"- **{r['scene']}** — {r['sentence']}  \n  Jev: {r['relation']} ({r['confidence']:.2f}); "
                         f"supports {p.get('supports', 0):.2f}, contradicts {p.get('contradicts', 0):.2f}, "
                         f"says nothing {p.get('says_nothing', 0):.2f}  \n  Review: {r['review_note'] or 'PENDING'}")
    lines += ["", "## Every sentence", "", "| scene | P(checkable) | Jev | conf | action | sentence |", "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['scene']} | {r['p_checkable']:.2f} | {r['relation']} | {r['confidence']:.2f} | {r['action']} | "
                     f"{r['sentence'].replace('|', '/')} |")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    R = load_results(); scenes = load_scenes(); cache = load_cache(); jobs = {}; keys = {}
    for sc in scenes:
        if sc["id"] not in SCENE_TOPICS:
            err(f"no evidence topics for scene {sc['id']}"); raise SystemExit(1)
        ev = scene_evidence(sc["id"], R); k = scene_key(sc["narration"], ev); keys[sc["id"]] = k
        if k not in cache: jobs[sc["id"]] = (ev, sc["narration"])
    info(f"asking Jev about {len(jobs)} of {len(scenes)} scenes ({sum(len(j[1]) for j in jobs.values())} sentences)")
    for sid, res in check_scenes(jobs).items():
        cache[keys[sid]] = res
    with open(CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=1, ensure_ascii=False)
    ok(f"cached Jev answers -> {CACHE}")
    rows, models = [], set()
    for sc in scenes:
        res = cache[keys[sc["id"]]]; models.add(res["model"])
        for a in res["sentences"]:
            rows.append(dict(scene=sc["id"], **a, action=classify(a), review_note=review_note(a["sentence"])))
    counts = dict(sentences=len(rows), checkable=sum(r["action"] != "not a claim" for r in rows),
                  verified=sum(r["action"] == "verified" for r in rows), review=sum(r["action"] == "review" for r in rows))
    model = ", ".join(sorted(models))
    info(f"{counts['sentences']} sentences: {counts['checkable']} checkable, {counts['verified']} verified by Jev, "
         f"{counts['review']} for review")
    for r in rows:
        if r["action"] == "review":
            if r["review_note"]:
                info(f"{r['scene']}: Jev {r['relation']} ({r['confidence']:.2f}) :: {r['sentence'][:80]} | reviewed")
            else:
                warn(f"{r['scene']}: Jev {r['relation']} ({r['confidence']:.2f}) :: {r['sentence'][:110]} | PENDING")
    pending = sum(r["action"] == "review" and not r["review_note"] for r in rows)
    (warn if pending else ok)(f"review notes cover {counts['review'] - pending} of {counts['review']} flagged sentences")
    write_markdown(rows, model, counts); ok(f"report -> {REPORT_MD}")
    save_result("script_check", dict(model=model, checkable_threshold=CHECKABLE_THRESHOLD, auto_accept=AUTO_ACCEPT,
                                     reviewer=REVIEWER, **counts, pending=pending, checked=rows))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        err(f"script check failed: {e}"); raise
