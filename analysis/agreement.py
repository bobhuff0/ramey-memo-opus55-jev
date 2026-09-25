"""Code-owned policy: group readings into words at a probability threshold, then classify each word position
by how many readers agree. No model calls here, so thresholds can change without re-querying Jev."""
from jev_same_word import pair_key


def clean(w): return " ".join(w.split()).upper()


def slot_readings(latest):
    """{reader: raw reading} -> {reading: [readers]} for non-empty readings."""
    out = {}
    for reader, w in latest.items():
        w = clean(w)
        if w:
            out.setdefault(w, []).append(reader)
    return out


def group(readings, probs, same_threshold):
    """Complete-linkage grouping: a reading joins a group only if it matches every member at >= same_threshold,
    so one loose pair cannot chain two different words together."""
    order = sorted(readings, key=lambda w: -len(readings[w]))
    groups = []
    for w in order:
        for g in groups:
            if all(probs.get(pair_key(w, m), 0.0) >= same_threshold for m in g):
                g.append(w); break
        else:
            groups.append([w])
    return groups


def classify_slot(readings, probs, same_threshold, agree_threshold, review_band):
    groups = group(readings, probs, same_threshold)
    counted = sorted(([sorted(sum((readings[w] for w in g), [])), g] for g in groups), key=lambda x: -len(x[0]))
    top_readers, top_group = counted[0] if counted else ([], [])
    lo, hi = review_band
    return dict(
        word=top_group[0] if top_group else "", variants=top_group, n_readers=len(top_readers), readers=top_readers,
        status="agreed" if len(top_readers) >= agree_threshold else "does not match",
        exact_n=max((len(v) for v in readings.values()), default=0),
        non_matching=[dict(reading=" / ".join(g), readers=r) for r, g in counted[1:]],
        uncertain_pairs=[dict(pair=k, p=round(p, 3)) for k, p in probs.items() if lo <= p <= hi])
