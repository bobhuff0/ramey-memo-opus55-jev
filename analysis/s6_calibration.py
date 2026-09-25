"""Step 6: the known-word test. Can template matching find words nobody disputes?

Work at 1/4 scale. Each phrase is rendered in four monospace fonts (bright ink, as on the negative), placed on
a character pitch p with cap height r*p, blurred by sigma, and slid along the straightened line(s) where it
should be (normalised cross-correlation, free x, +/-10 px in y).

Geometry fit: each known phrase is scored over the full grid; its best (pitch, cap ratio, blur) is recorded.
Test (leave-one-out): each phrase's candidates are scored with the geometry fitted on the OTHER known phrases
(pitch +/-1 step, all four fonts). Candidates = the true phrase + every one-letter substitution + random
strings of the same shape (letters replaced at random, spaces and punctuation kept). Rank 1 = truth wins.
Disputed word: 7-letter candidates scored just left of the located OF THE WRECK on the same strip.
"""
import numpy as np, cv2, tifffile, os, json, random, string, time
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFont
from common import OUT, save_result, load_results, info, ok, warn, err

DS = 4
FONTS = {"Andale Mono": ("/System/Library/Fonts/Supplemental/Andale Mono.ttf", 0),
         "Menlo Bold": ("/System/Library/Fonts/Menlo.ttc", 1),
         "Courier New Bold": ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf", 0),
         "Liberation Mono Bold": (os.path.join(os.path.dirname(__file__), "..", "..", "build", "fonts", "LiberationMono-Bold.ttf"), 0)}
PITCHES = list(range(48, 81, 4))
CAP_RATIOS = [0.5, 0.6, 0.7]
BLURS = [1, 2, 3, 5, 8]
Y_SLACK = 10
N_RANDOM = 300
SEED = 1947
KNOWN = [("FORT WORTH, TEX.", ["L_3"]),
         ("WEATHER BALLOONS", ["L_7", "R_7"]),
         ("OF THE WRECK", ["L_2", "R_2"]),
         ("FORWARDED", ["L_2", "R_2"]),
         ("RAMEY", ["R_9"])]
DISPUTED = ["VICTIMS", "REMAINS", "FINDING", "VIEWING", "PACKING", "HOLDING", "SIGHTED"]

_STRIPS = {}
_FONT_CACHE = {}


def load_strips():
    out = {}
    for name in {s for _, ss in KNOWN for s in ss}:
        s = tifffile.imread(os.path.join(OUT, f"strip_{name}.tif")).astype(np.float32)
        s = cv2.resize(s, (s.shape[1] // DS, s.shape[0] // DS), interpolation=cv2.INTER_AREA)
        out[name] = (s - cv2.GaussianBlur(s, (0, 0), 25)).astype(np.float32)
    return out


def font(name, px):
    key = (name, px)
    if key not in _FONT_CACHE:
        path, idx = FONTS[name]
        _FONT_CACHE[key] = ImageFont.truetype(path, px, index=idx)
    return _FONT_CACHE[key]


def cap_scale(name):
    f = font(name, 200); b = f.getbbox("H"); return (b[3] - b[1]) / 200.0


def render(text, name, p, r, sigma):
    cap = r * p; size = max(6, int(round(cap / cap_scale(name)))); f = font(name, size)
    pad = int(3 * sigma) + 4; H = int(cap * 1.6) + 2 * pad; W = int(p * len(text)) + 2 * pad
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    top_h = f.getbbox("H")[1]; y = pad + int(cap * 0.3) - top_h
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        w = f.getlength(ch); d.text((pad + i * p + (p - w) / 2, y), ch, font=f, fill=255)
    a = np.asarray(im, np.float32) / 255.0
    return cv2.GaussianBlur(a, (0, 0), sigma) if sigma > 0 else a


def score(strip, tpl, x_window=None):
    c = strip.shape[0] // 2; th = tpl.shape[0]
    y0 = max(0, c - th // 2 - Y_SLACK); y1 = min(strip.shape[0], c + (th - th // 2) + Y_SLACK)
    band = strip[y0:y1]
    if x_window is not None:
        a, b = max(0, x_window[0]), min(strip.shape[1], x_window[1] + tpl.shape[1]); band = band[:, a:b]
    else:
        a = 0
    if band.shape[0] < th or band.shape[1] < tpl.shape[1]:
        return -1.0, (0, 0)
    res = cv2.matchTemplate(band, tpl, cv2.TM_CCOEFF_NORMED); _, m, _, loc = cv2.minMaxLoc(res)
    return float(m), (int(loc[0] + a), int(loc[1] + y0))


def best_over(text, strips, grid, x_window=None):
    best = (-1.0, None)
    for (fname, p, r, s) in grid:
        tpl = render(text, fname, p, r, s)
        for sname in strips:
            m, loc = score(_STRIPS[sname], tpl, x_window)
            if m > best[0]:
                best = (m, dict(font=fname, pitch=p, cap_ratio=r, blur=s, strip=sname, x=loc[0], y=loc[1]))
    return best


def _cand_job(args):
    text, strips, grid, x_window = args
    return text, best_over(text, strips, grid, x_window)[0]


def variants(text):
    out = set()
    for i, ch in enumerate(text):
        if ch in string.ascii_uppercase:
            for L in string.ascii_uppercase:
                if L != ch:
                    out.add(text[:i] + L + text[i + 1:])
    return sorted(out)


def randoms(text, n, rng):
    out = set()
    while len(out) < n:
        out.add("".join(rng.choice(string.ascii_uppercase) if ch in string.ascii_uppercase else ch for ch in text))
    out.discard(text); return sorted(out)


def full_grid(): return [(f, p, r, s) for f in FONTS for p in PITCHES for r in CAP_RATIOS for s in BLURS]


def loo_grid(fits, exclude):
    others = [v for k, v in fits.items() if k != exclude]
    p = int(np.median([o["pitch"] for o in others]))
    ratios = [o["cap_ratio"] for o in others]; cap = max(set(ratios), key=ratios.count)
    blur = float(np.median([o["blur"] for o in others]))
    i = PITCHES.index(min(PITCHES, key=lambda q: abs(q - p)))
    ps = PITCHES[max(0, i - 1):i + 2]
    return [(f, pp, cap, blur) for f in FONTS for pp in ps], dict(pitch=p, cap_ratio=cap, blur=blur, pitches=ps)


def init_worker(strips):
    global _STRIPS; _STRIPS = strips


def rank_candidates(pool, truth, cands, strips, grid, x_window=None):
    jobs = [(t, strips, grid, x_window) for t in [truth] + cands]
    scores = dict(pool.map(_cand_job, jobs, chunksize=4))
    t = scores[truth]; above = [c for c in cands if scores[c] > t]
    return t, above, scores


def main():
    global _STRIPS
    rng = random.Random(SEED); _STRIPS = load_strips(); t0 = time.time()
    res = dict(settings=dict(fonts=list(FONTS), pitches_full_res=[p * DS for p in PITCHES], cap_ratios=CAP_RATIOS,
                             blurs_sigma_full_res=[s * DS for s in BLURS], n_random=N_RANDOM, seed=SEED))
    try:
        with Pool(10, initializer=init_worker, initargs=(_STRIPS,)) as pool:
            fits = {}
            for text, strips in KNOWN:
                grid = full_grid(); chunks = [grid[i::10] for i in range(10)]
                outs = pool.starmap(best_over, [(text, strips, g) for g in chunks])
                m, g = max(outs, key=lambda o: o[0]); fits[text] = dict(ncc=m, **g)
                ok(f"fit '{text}': NCC {m:.3f}  font {g['font']}, pitch {g['pitch'] * DS} px, cap {g['cap_ratio']}, "
                   f"blur sigma {g['blur'] * DS} px, strip {g['strip']} at x={g['x'] * DS}")
            res["fits"] = fits
            tests = {}
            for text, strips in KNOWN:
                grid, geo = loo_grid(fits, text)
                var = variants(text); rnd = randoms(text, N_RANDOM, rng)
                t, above, scores = rank_candidates(pool, text, var + rnd, strips, grid)
                va = [c for c in above if c in var]; ra = [c for c in above if c in rnd]
                top = sorted(scores.items(), key=lambda kv: -kv[1])[:5]
                tests[text] = dict(geometry=geo, truth_ncc=t, rank=len(above) + 1, n_candidates=len(var) + len(rnd) + 1,
                                   variants_above=len(va), n_variants=len(var), randoms_above=len(ra), n_random=len(rnd),
                                   top5=top)
                ok(f"test '{text}': rank {len(above) + 1} of {len(var) + len(rnd) + 1}; one-letter variants above {len(va)}/{len(var)}; "
                   f"random above {len(ra)}/{len(rnd)}; top: {top[0][0]} ({top[0][1]:.3f}) [{time.time() - t0:.0f}s]")
            res["tests"] = tests
            # The located OF THE WRECK puts the 7-letter slot left of the traced strip start (under the thumb),
            # and the known-word test shows locations are unreliable anyway, so the word is searched along all of line 2.
            grid, geo = loo_grid(fits, None)
            rnd7 = randoms("XXXXXXX", N_RANDOM, rng)
            jobs = [(w, ["L_2", "R_2"], grid, None) for w in DISPUTED + rnd7]
            scores = dict(pool.map(_cand_job, jobs, chunksize=4))
            order = sorted(scores.items(), key=lambda kv: -kv[1])
            ranks = {w: 1 + sum(1 for _, v in order if v > scores[w]) for w in DISPUTED}
            res["disputed"] = dict(strips=["L_2", "R_2"], geometry=geo, ranks=ranks,
                                   scores={w: scores[w] for w in DISPUTED}, n_candidates=len(scores),
                                   random_above_victims=sum(1 for w in rnd7 if scores[w] > scores["VICTIMS"]),
                                   located_OF_THE_WRECK_full_res_x=fits["OF THE WRECK"]["x"] * DS,
                                   located_FORWARDED_full_res_x=fits["FORWARDED"]["x"] * DS,
                                   expected_char_gap=17, found_char_gap=round((fits["FORWARDED"]["x"] - fits["OF THE WRECK"]["x"]) / fits["OF THE WRECK"]["pitch"], 1))
            ok(f"disputed word: ranks {ranks} of {len(scores)}; random strings above VICTIMS {res['disputed']['random_above_victims']}/{len(rnd7)}")
    except Exception as e:
        err(f"calibration failed: {e}"); raise
    with open(os.path.join(OUT, "calibration.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    save_result("calibration", {k: v for k, v in res.items()})


if __name__ == "__main__":
    main()
