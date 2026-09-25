"""Step 9: reader agreement on Rudiak's ten-reader table, counted by word with Jev.

For every word position, Jev judges whether each pair of readings names the same word (spelling variants such as
DISC/DISK count as one). Code groups readings at SAME_WORD_THRESHOLD and marks a position "agreed" when at least
AGREE_THRESHOLD readers give the same word, otherwise "does not match". These are judgments about the published
transcriptions, not about the scan.

Jev answers are cached in out/jev_same_word.json; change the thresholds and re-run without new requests.
"""
import os, json
from common import HERE, OUT, save_result, info, ok, warn, err
from jev_same_word import same_word_probabilities, pair_key
from agreement import slot_readings, classify_slot

MATRIX = os.path.join(HERE, "sources", "rudiak_slot_matrix_latest.json")
CACHE = os.path.join(OUT, "jev_same_word.json")
REPORT_MD = os.path.join(OUT, "reader_agreement.md")
N_READERS = 10
SAME_WORD_THRESHOLD = 0.5
AGREE_THRESHOLD = 6
REVIEW_BAND = (0.3, 0.7)
AGREE_LEVELS = [3, 5, 6, 8, 10]
SENSITIVITY_SAME_THRESHOLDS = [0.3, 0.5, 0.7, 0.9]


def load_matrix():
    try:
        with open(MATRIX, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        err(f"could not read {MATRIX}: {e}"); raise


def load_cache():
    if not os.path.exists(CACHE):
        return {}
    with open(CACHE, encoding="utf-8") as f:
        return json.load(f)


def jev_probs(matrix):
    cache = load_cache(); need = {}
    for line, slots in matrix.items():
        for s in slots:
            sid = f"L{line}S{s['slot']}"; rd = sorted(slot_readings(s["latest"]))
            have = cache.get(sid, {})
            if any(pair_key(a, b) not in have for i, a in enumerate(rd) for b in rd[i + 1:]):
                need[sid] = rd
    if need:
        info(f"asking Jev about {len(need)} word positions")
        cache.update(same_word_probabilities(need))
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=1)
        ok(f"cached Jev answers -> {CACHE}")
    else:
        ok("all Jev answers cached; no requests made")
    return cache


def summarize(rows):
    total = len(rows)
    return {k: dict(jev=sum(r["n_readers"] >= k for r in rows), exact=sum(r["exact_n"] >= k for r in rows), of=total)
            for k in AGREE_LEVELS}


def write_markdown(rows, summary):
    L = ["# Reader agreement on the Ramey memo (Rudiak's ten-reader table)", "",
         f"Readings grouped as the same word by Jev at P >= {SAME_WORD_THRESHOLD}; a position is **agreed** when "
         f"at least {AGREE_THRESHOLD} of {N_READERS} readers give the same word. These are judgments about the "
         "published transcriptions, not about the scan.", "",
         "| readers agreeing | positions (Jev, by word) | positions (exact spelling) |", "|---|---|---|"]
    L += [f"| {k}+ of {N_READERS} | {v['jev']} of {v['of']} | {v['exact']} of {v['of']} |" for k, v in summary.items()]
    for line in sorted({r["line"] for r in rows}, key=int):
        L += ["", f"## Line {line}", "", "| pos | word | readers | status | does not match |", "|---|---|---|---|---|"]
        for r in (x for x in rows if x["line"] == line):
            word = " / ".join(r["variants"]) or "—"
            nm = "; ".join(f"{m['reading']} ({', '.join(m['readers'])})" for m in r["non_matching"]) or "—"
            L.append(f"| {r['slot']} | {word} | {r['n_readers']} | {r['status']} | {nm} |")
    unc = [(f"line {r['line']} pos {r['slot']}", u) for r in rows for u in r["uncertain_pairs"]]
    if unc:
        L += ["", f"## Pairs for human review (Jev P between {REVIEW_BAND[0]} and {REVIEW_BAND[1]})", ""]
        L += [f"- {where}: {u['pair']} (P = {u['p']})" for where, u in unc]
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    ok(f"report -> {REPORT_MD}")


def classify_all(matrix, probs, same_threshold):
    rows = []
    for line, slots in matrix.items():
        for s in slots:
            sid = f"L{line}S{s['slot']}"
            r = classify_slot(slot_readings(s["latest"]), probs.get(sid, {}), same_threshold, AGREE_THRESHOLD, REVIEW_BAND)
            rows.append(dict(line=line, slot=s["slot"], **r))
    return rows


def main():
    matrix = load_matrix(); probs = jev_probs(matrix)
    rows = classify_all(matrix, probs, SAME_WORD_THRESHOLD)
    n_pairs = sum(len(v) for v in probs.values())
    sensitivity = {str(t): summarize(classify_all(matrix, probs, t)) for t in SENSITIVITY_SAME_THRESHOLDS}
    for t, sm in sensitivity.items():
        info(f"same-word threshold {t}: " + ", ".join(f"{k}+ -> {v['jev']}" for k, v in sm.items()))
    summary = summarize(rows)
    for k, v in summary.items():
        info(f"{k}+ of {N_READERS} readers: {v['jev']} of {v['of']} positions by word (exact spelling: {v['exact']})")
    merged = [r for r in rows if len(r["variants"]) > 1]
    for r in merged:
        warn(f"line {r['line']} pos {r['slot']}: Jev merged {' / '.join(r['variants'])} -> {r['n_readers']} readers")
    write_markdown(rows, summary)
    save_result("reader_agreement", dict(settings=dict(same_word_threshold=SAME_WORD_THRESHOLD, agree_threshold=AGREE_THRESHOLD,
                                                       review_band=REVIEW_BAND, n_readers=N_READERS),
                                         n_positions=len(rows), n_pairs_judged=n_pairs,
                                         n_positions_with_pairs=len(probs), summary=summary,
                                         sensitivity_same_threshold=sensitivity, positions=rows))


if __name__ == "__main__":
    main()
