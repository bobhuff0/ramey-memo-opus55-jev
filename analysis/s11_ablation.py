"""Step 11: the paired scoring-and-geometry ablation proposed by the Codex (GPT-6 Astra) review.

Question: does the step-6/7 method leave image information unused? Known phrases are planted on real blank film
(disjoint patches, below the text) at the measured letter strength and ranked against every one-letter variant
and random strings, exactly as in step 7, but under a 3 x 3 design:

  scoring   ncc        step-6 baseline: line high-passed, template not (the inconsistency Codex flagged)
            ncc_hp     the same high-pass applied to line AND template
            whitened   grain-whitened matched filter: line and template filtered by 1/sqrt(grain PSD), then NCC;
                       the PSD is estimated on film to the RIGHT of the test patches (never on test grain)
  geometry  oracle          font, pitch, cap, blur and position all known: score at the planted spot only
            known_geometry  geometry known, position searched along the line (+/-10 px in y)
            free_geometry   step-7 search: four fonts x three pitches, position free

Phrases are withheld (none used to fit anything in steps 6-7) and include an implausible string. Blank controls
rank the same candidates on grain with nothing planted. Reported per cell: exact-phrase wins, median rank,
top-1 character error, and whether the truth was localised within half a pitch of where it was planted.
"""
import numpy as np, cv2, os, random, time, json, tifffile
from multiprocessing import Pool
import s6_calibration as s6
import s7_synthetic as s7
from common import OUT, save_result, info, ok, warn, err

DS = s6.DS
TEST_PATCHES = [(5780, 1000), (6160, 1000), (6540, 1000)]   # (y, x) full res in hdr_R: disjoint rows below line 9
PATCH_H, PATCH_W = 400, 6256
PSD_REGION = (5780, 7400, 1540, 3500)                        # (y, x, h, w) full res: columns right of the test patches
PHRASES = ["MAJOR MARCEL", "BRAZEL RANCH", "EIGHTH AIR FORCE", "DISC", "KQXV ZWPJT"]   # withheld; last one implausible
FONT, PITCH, CAP = s7.FONT, s7.PITCH, s7.CAP
STRENGTHS = [("blur x1", s7.BLUR, 1.0), ("blur x2", s7.BLUR, 2.0), ("blur x4", s7.BLUR, 4.0), ("sharp x1", s7.SHARP_BLUR, 1.0)]
PLANT_X = 400
PAD_X, PAD_Y = 32, 8          # zero margin around filtered templates, so filter ringing is part of the template
TILE = 64                     # PSD tile (quarter-scale px)
PSD_FLOOR = 0.02              # fraction of the median PSD added before inversion (regularisation)
HP_SIGMA = 25
Y_SLACK = s6.Y_SLACK
N_RANDOM = s7.N_RANDOM
SEED = s7.SEED
N_WORKERS = 10
SCORINGS = ["ncc", "ncc_hp", "whitened"]
GEOMETRIES = ["oracle", "known_geometry", "free_geometry"]
REPORT_MD = os.path.join(OUT, "ablation.md")

_S = {}   # worker state


def small(a): return cv2.resize(a, (a.shape[1] // DS, a.shape[0] // DS), interpolation=cv2.INTER_AREA)


def grain_psd(region):
    """Mean power spectrum of Hann-windowed TILE x TILE tiles (50% overlap) of the quarter-scale region."""
    r = region - region.mean()
    w = np.hanning(TILE); win = np.outer(w, w).astype(np.float32)
    psd = np.zeros((TILE, TILE)); n = 0
    for y in range(0, r.shape[0] - TILE + 1, TILE // 2):
        for x in range(0, r.shape[1] - TILE + 1, TILE // 2):
            t = r[y:y + TILE, x:x + TILE]; t = (t - t.mean()) * win
            psd += np.abs(np.fft.fft2(t)) ** 2; n += 1
    return psd / max(n, 1), n


def whitening_kernel(psd):
    """Zero-phase spatial kernel for 1/sqrt(PSD) with DC removed; unit energy (scale is irrelevant for NCC)."""
    W = 1.0 / np.sqrt(psd + PSD_FLOOR * np.median(psd)); W[0, 0] = 0.0
    k = np.fft.fftshift(np.real(np.fft.ifft2(W)))
    return (k / np.sqrt((k ** 2).sum())).astype(np.float32)


def hp(a, border=cv2.BORDER_REFLECT_101): return (a - cv2.GaussianBlur(a, (0, 0), HP_SIGMA, borderType=border)).astype(np.float32)


def whiten(a, k, border=cv2.BORDER_REFLECT_101): return cv2.filter2D(a, -1, k, borderType=border)


def padded(tpl):
    c = np.zeros((tpl.shape[0] + 2 * PAD_Y, tpl.shape[1] + 2 * PAD_X), np.float32)
    c[PAD_Y:PAD_Y + tpl.shape[0], PAD_X:PAD_X + tpl.shape[1]] = tpl
    return c


def build_line(phrase, sigma, patch, snr, gstd):
    """Plant the phrase on the raw (mean-removed) quarter-scale patch at the measured strength, defined as in s7:
    the high-passed phrase's std over its own columns equals snr x grain std."""
    tpl = s6.render(phrase, FONT, PITCH, CAP, sigma)
    canvas = np.zeros_like(patch); y = patch.shape[0] // 2 - tpl.shape[0] // 2
    canvas[y:y + tpl.shape[0], PLANT_X:PLANT_X + tpl.shape[1]] = tpl
    h = hp(canvas); c = patch.shape[0] // 2; sig = h[c - 10:c + 10, PLANT_X:PLANT_X + tpl.shape[1]].std()
    canvas *= snr * gstd / (sig + 1e-9)
    return patch + canvas, y


def init_worker(state):
    global _S; _S = state


def _versions(text, fname, p, sigma):
    tpl = s6.render(text, fname, p, CAP, sigma); pc = padded(tpl)
    return {"ncc": (tpl, 0, 0), "ncc_hp": (hp(pc, cv2.BORDER_CONSTANT), PAD_X, PAD_Y),
            "whitened": (whiten(pc, _S["kernel"], cv2.BORDER_CONSTANT), PAD_X, PAD_Y)}


def _match(line, tpl, ox, oy, fixed):
    """NCC of tpl against line. fixed: at the planted spot only. Else: x free, y within +/-Y_SLACK. Returns (score, glyph x)."""
    y_glyph = _S["y_plant"]; ly = y_glyph - oy
    if fixed:
        lx = PLANT_X - ox
        if ly < 0 or lx < 0 or ly + tpl.shape[0] > line.shape[0] or lx + tpl.shape[1] > line.shape[1]:
            return -1.0, PLANT_X
        win = line[ly:ly + tpl.shape[0], lx:lx + tpl.shape[1]]
        return float(cv2.matchTemplate(win, tpl, cv2.TM_CCOEFF_NORMED)[0, 0]), PLANT_X
    y0 = max(0, ly - Y_SLACK); y1 = min(line.shape[0], ly + tpl.shape[0] + Y_SLACK)
    band = line[y0:y1]
    if band.shape[0] < tpl.shape[0] or band.shape[1] < tpl.shape[1]:
        return -1.0, -1
    res = cv2.matchTemplate(band, tpl, cv2.TM_CCOEFF_NORMED); _, m, _, loc = cv2.minMaxLoc(res)
    return float(m), int(loc[0] + ox)


def _cand(text):
    """All nine scores for one candidate string: {scoring: {geometry: (score, x)}}."""
    out = {s: {} for s in SCORINGS}
    sigma = _S["sigma"]
    true_v = _versions(text, FONT, PITCH, sigma)
    for s in SCORINGS:
        tpl, ox, oy = true_v[s]; line = _S["line"][s]
        out[s]["oracle"] = _match(line, tpl, ox, oy, True)
        out[s]["known_geometry"] = _match(line, tpl, ox, oy, False)
        best = out[s]["known_geometry"]
        for fname, p, _, _ in s7.grid_for(sigma):
            if (fname, p) == (FONT, PITCH):
                continue
            v = _versions(text, fname, p, sigma)[s]
            m = _match(line, v[0], v[1], v[2], False)
            if m[0] > best[0]:
                best = m
        out[s]["free_geometry"] = best
    return text, out


def letters(a, b):
    n = sum(1 for ch in a if ch.isalpha()); d = sum(1 for x, y in zip(a, b) if x.isalpha() and x != y)
    return d / max(n, 1)


def rank_line(line_raw, y_plant, sigma, kernel, truth, cands):
    state = dict(line={"ncc": hp(line_raw), "ncc_hp": hp(line_raw), "whitened": whiten(line_raw, kernel)},
                 kernel=kernel, sigma=sigma, y_plant=y_plant)
    with Pool(N_WORKERS, initializer=init_worker, initargs=(state,)) as pool:
        scores = dict(pool.map(_cand, [truth] + cands, chunksize=4))
    cells = {}
    for s in SCORINGS:
        for g in GEOMETRIES:
            t, tx = scores[truth][s][g]
            above = [c for c in cands if scores[c][s][g][0] > t]
            top = max([truth] + cands, key=lambda c: scores[c][s][g][0])
            cells[f"{s}/{g}"] = dict(rank=len(above) + 1, truth_score=t, top=top, top1_char_error=letters(truth, top),
                                     localised=(g == "oracle") or abs(tx - PLANT_X) <= PITCH // 2,
                                     randoms_above=sum(1 for c in above if c in _RND[truth]))
    return cells, len(cands) + 1


_RND = {}


def summarise(rows):
    out = {}
    for cond in dict.fromkeys(r["condition"] for r in rows):
        sub = [r for r in rows if r["condition"] == cond]; out[cond] = {}
        for key in sub[0]["cells"]:
            cs = [r["cells"][key] for r in sub]
            out[cond][key] = dict(trials=len(cs), wins=sum(c["rank"] == 1 for c in cs),
                                  median_rank=float(np.median([c["rank"] for c in cs])),
                                  top10=sum(c["rank"] <= 10 for c in cs),
                                  mean_top1_char_error=float(np.mean([c["top1_char_error"] for c in cs])),
                                  localised=sum(c["localised"] for c in cs))
    return out


def write_report(res):
    L = ["# Step 11: scoring x geometry ablation (proposed by the Codex review)", "",
         f"Planted strength {res['settings']['snr']:.3f} of the grain (step-7 definition), {len(TEST_PATCHES)} disjoint "
         f"blank patches x {len(PHRASES)} withheld phrases = {len(TEST_PATCHES) * len(PHRASES)} trials per cell; "
         f"{N_RANDOM} random strings + every one-letter variant per phrase. Grain PSD for whitening estimated on "
         f"{res['settings']['psd_tiles']} tiles to the right of the test patches.", ""]
    for cond, cells in res["summary"].items():
        L += [f"## {cond}", "", "| scoring / geometry | first | top ten | median rank | top-1 letter error | localised |", "|---|---|---|---|---|---|"]
        for key, c in cells.items():
            L.append(f"| {key} | {c['wins']}/{c['trials']} | {c['top10']}/{c['trials']} | {c['median_rank']:g} | "
                     f"{c['mean_top1_char_error']:.2f} | {c['localised']}/{c['trials']} |")
        L.append("")
    L += ["## Blank controls (nothing planted; known geometry)", "", "| phrase | " + " | ".join(SCORINGS) + " |", "|---|" + "---|" * len(SCORINGS)]
    for b in res["blank_controls"]:
        L.append(f"| {b['phrase']} | " + " | ".join(f"rank {b['ranks'][s]} of {b['n']}" for s in SCORINGS) + " |")
    L.append("")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


BLUR_SWEEP_SIGMAS = [0.6, 1.5, 2.5, 3.5, 5.0]      # quarter-scale sigma; x4 for full res. 5.0 = the memo's measured blur
BLUR_SWEEP_PHRASES = ["BRAZEL RANCH", "DISC"]


def prepare():
    R = tifffile.imread(os.path.join(OUT, "hdr_R.tif")).astype(np.float32)
    patches = []
    for y, x in TEST_PATCHES:
        p = small(R[y:y + PATCH_H, x:x + PATCH_W]); patches.append((p - p.mean()).astype(np.float32))
    y, x, h, w = PSD_REGION
    psd, n_tiles = grain_psd(small(R[y:y + h, x:x + w])); kernel = whitening_kernel(psd)
    gstd = float(np.mean([hp(p)[p.shape[0] // 2 - 10:p.shape[0] // 2 + 10].std() for p in patches]))
    snr = s7.measure_snr([hp(p) for p in patches])[0]
    return patches, kernel, n_tiles, gstd, snr


def blur_sweep():
    """Supplement: at the measured strength, how blurred can the letters be before whitened matching stops winning?"""
    rng = random.Random(SEED); t0 = time.time()
    try:
        patches, kernel, n_tiles, gstd, snr = prepare()
        rows = []
        for sigma in BLUR_SWEEP_SIGMAS:
            for phrase in BLUR_SWEEP_PHRASES:
                _RND[phrase] = set(s6.randoms(phrase, N_RANDOM, random.Random(SEED)))
                cands = s6.variants(phrase) + sorted(_RND[phrase])
                for j, patch in enumerate(patches):
                    line, y_plant = build_line(phrase, sigma, patch, snr, gstd)
                    cells, n = rank_line(line, y_plant, sigma, kernel, phrase, cands)
                    rows.append(dict(sigma_full_res=sigma * DS, phrase=phrase, patch=j, n=n,
                                     ranks={s: cells[f"{s}/known_geometry"]["rank"] for s in SCORINGS},
                                     top1_char_error={s: cells[f"{s}/known_geometry"]["top1_char_error"] for s in SCORINGS}))
            sub = [r for r in rows if r["sigma_full_res"] == sigma * DS]
            ok(f"blur sigma {sigma * DS:.0f} px: " + "; ".join(f"{s} first {sum(r['ranks'][s] == 1 for r in sub)}/{len(sub)}, median rank "
                                                            f"{np.median([r['ranks'][s] for r in sub]):g}" for s in SCORINGS) + f" [{time.time() - t0:.0f}s]")
        res = dict(snr=snr, phrases=BLUR_SWEEP_PHRASES, sigmas_full_res=[s * DS for s in BLUR_SWEEP_SIGMAS], rows=rows)
        res["summary"] = {str(s * DS): {sc: dict(first=sum(r["ranks"][sc] == 1 for r in rows if r["sigma_full_res"] == s * DS),
                                                 median_rank=float(np.median([r["ranks"][sc] for r in rows if r["sigma_full_res"] == s * DS])),
                                                 trials=sum(1 for r in rows if r["sigma_full_res"] == s * DS))
                                        for sc in SCORINGS} for s in BLUR_SWEEP_SIGMAS}
    except Exception as e:
        err(f"blur sweep failed: {e}"); raise
    from common import load_results
    full = load_results()["ablation"]; full["blur_sweep"] = res; save_result("ablation", full)
    with open(REPORT_MD, "a", encoding="utf-8") as f:
        f.write("\n## Blur sweep at the measured strength (known geometry)\n\n| letter blur sigma (full-res px) | " +
                " | ".join(f"{s} first / median rank" for s in SCORINGS) + " |\n|---|" + "---|" * len(SCORINGS) + "\n")
        for k, v in res["summary"].items():
            f.write(f"| {float(k):g} | " + " | ".join(f"{v[s]['first']}/{v[s]['trials']} / {v[s]['median_rank']:g}" for s in SCORINGS) + " |\n")
    ok(f"blur sweep appended to {REPORT_MD}")


def main():
    rng = random.Random(SEED); t0 = time.time()
    try:
        R = tifffile.imread(os.path.join(OUT, "hdr_R.tif")).astype(np.float32)
        patches = []
        for y, x in TEST_PATCHES:
            p = small(R[y:y + PATCH_H, x:x + PATCH_W]); patches.append((p - p.mean()).astype(np.float32))
        y, x, h, w = PSD_REGION
        psd, n_tiles = grain_psd(small(R[y:y + h, x:x + w])); kernel = whitening_kernel(psd)
        gstd = float(np.mean([hp(p)[p.shape[0] // 2 - 10:p.shape[0] // 2 + 10].std() for p in patches]))
        snr = s7.measure_snr([hp(p) for p in patches])[0]
        wstd = float(np.mean([whiten(p, kernel).std() for p in patches]))
        ok(f"{len(patches)} disjoint blank patches; grain std {gstd:.2f}; measured signal/grain {snr:.3f}; "
           f"PSD from {n_tiles} tiles; whitened grain std {wstd:.3f} [{time.time() - t0:.0f}s]")
    except Exception as e:
        err(f"could not prepare patches/PSD: {e}"); raise
    res = dict(settings=dict(test_patches_full_res=TEST_PATCHES, patch_h=PATCH_H, patch_w=PATCH_W, psd_region_full_res=PSD_REGION,
                             psd_tiles=n_tiles, psd_tile=TILE, psd_floor=PSD_FLOOR, phrases=PHRASES, font=FONT,
                             pitch_full_res=PITCH * DS, cap_ratio=CAP, strengths=[dict(label=l, sigma_full_res=s * DS, mult=m) for l, s, m in STRENGTHS],
                             snr=snr, grain_std=gstd, n_random=N_RANDOM, scorings=SCORINGS, geometries=GEOMETRIES,
                             search_grid="s7.grid_for: four fonts x pitches 200/216/232 px, template blur = planted blur"))
    rows = []
    try:
        for phrase in PHRASES:
            _RND[phrase] = set(s6.randoms(phrase, N_RANDOM, rng))
        for label, sigma, mult in STRENGTHS:
            for phrase in PHRASES:
                cands = s6.variants(phrase) + sorted(_RND[phrase])
                for j, patch in enumerate(patches):
                    line, y_plant = build_line(phrase, sigma, patch, snr * mult, gstd)
                    cells, n = rank_line(line, y_plant, sigma, kernel, phrase, cands)
                    rows.append(dict(condition=label, phrase=phrase, patch=j, n=n, cells=cells))
                    info(f"{label:9s} '{phrase}' patch {j}: " + "  ".join(f"{k.split('/')[0][:3]}/{k.split('/')[1][:5]} {v['rank']}" for k, v in cells.items()) + f" [{time.time() - t0:.0f}s]")
        res["rows"] = rows; res["summary"] = summarise(rows)
        for cond, cells in res["summary"].items():
            ok(f"{cond}: " + "; ".join(f"{k}: {c['wins']}/{c['trials']} first, median {c['median_rank']:g}, "
                                      f"err {c['mean_top1_char_error']:.2f}" for k, c in cells.items()))
        blanks = []
        for phrase in PHRASES:
            cands = s6.variants(phrase) + sorted(_RND[phrase])
            tpl_h = s6.render(phrase, FONT, PITCH, CAP, s7.BLUR).shape[0]
            cells, n = rank_line(patches[0], patches[0].shape[0] // 2 - tpl_h // 2, s7.BLUR, kernel, phrase, cands)
            blanks.append(dict(phrase=phrase, n=n, ranks={s: cells[f"{s}/known_geometry"]["rank"] for s in SCORINGS}))
            info(f"blank control '{phrase}': " + ", ".join(f"{s} rank {cells[f'{s}/known_geometry']['rank']}/{n}" for s in SCORINGS))
        res["blank_controls"] = blanks
    except Exception as e:
        err(f"ablation failed: {e}"); raise
    save_result("ablation", res); write_report(res)
    ok(f"report -> {REPORT_MD} [{time.time() - t0:.0f}s]")


if __name__ == "__main__":
    import sys
    blur_sweep() if "--blur-sweep" in sys.argv else main()
