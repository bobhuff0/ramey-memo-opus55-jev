"""Step 7: known-answer test. Does the step-6 method work when the answer is planted?

A synthetic line is built by rendering a known phrase (Courier New Bold, fitted geometry from step 6) and adding
it to a real blank-paper patch from hdr_R (below the text block), at the signal-to-grain ratio measured on the
real line strips. Three conditions:
  A  sharp letters + real grain
  B  measured blur (sigma 20 px full res) + real grain
  C  measured blur, no grain
Each synthetic line is ranked exactly as in step 6 (true phrase vs every one-letter variant + random strings).
The sweep repeats A and B at multiples of the measured ratio, because that ratio is itself an estimate.
"""
import numpy as np, cv2, os, random, time
from multiprocessing import Pool
import s6_calibration as s6
from common import OUT, save_result, load_results, info, ok, err
import tifffile

DS = s6.DS
BLANK_PATCHES = [(6000, 1000), (6450, 1000), (6000, 3500), (6450, 3500)]  # (y, x) full res in hdr_R
STRIP_H, STRIP_W = 340, 6256
PHRASES = ["OF THE WRECK", "WEATHER BALLOONS", "FORT WORTH, TEX.", "FORWARDED", "RAMEY"]
FONT = "Courier New Bold"
PITCH, CAP, BLUR = 54, 0.5, 5.0
SHARP_BLUR = 0.6
PLANT_X = 400
N_RANDOM = 200
SEED = 1947
REAL_STRIPS = ["L_2", "L_3", "L_7", "R_7"]
SWEEP_PHRASE = "OF THE WRECK"
SWEEP_MULTS = [1, 1.5, 2, 3, 4, 6, 8]
N_WORKERS = 10


def highpass(a): return (a - cv2.GaussianBlur(a, (0, 0), 25)).astype(np.float32)


def small(a): return cv2.resize(a, (a.shape[1] // DS, a.shape[0] // DS), interpolation=cv2.INTER_AREA)


def measure_snr(grain_patches):
    """Signal std = sqrt(text-band variance - grain variance), both on the high-passed quarter-scale images."""
    t = []
    for n in REAL_STRIPS:
        s = highpass(small(tifffile.imread(os.path.join(OUT, f"strip_{n}.tif")).astype(np.float32)))
        c = s.shape[0] // 2; t.append(s[c - 10:c + 10].std())
    g = float(np.mean([p[p.shape[0] // 2 - 10:p.shape[0] // 2 + 10].std() for p in grain_patches]))
    T = float(np.median(t)); S = float(np.sqrt(max(T * T - g * g, 1e-6)))
    return S / g, T, g


def snr_from_calibration():
    """Independent estimate: for data = a*template + noise, NCC = r/sqrt(1+r^2), so r = NCC/sqrt(1-NCC^2).
    Uses the true phrases' step-6 scores; a template of the wrong shape scores lower, so this is a lower bound."""
    tests = load_results()["calibration"]["tests"]
    r = [v["truth_ncc"] / np.sqrt(1 - v["truth_ncc"] ** 2) for v in tests.values()]
    return float(np.median(r)), [float(min(r)), float(max(r))]


def build_line(phrase, sigma, grain, snr, gstd):
    tpl = s6.render(phrase, FONT, PITCH, CAP, sigma)
    line = np.zeros((STRIP_H // DS, STRIP_W // DS), np.float32)
    y = line.shape[0] // 2 - tpl.shape[0] // 2
    line[y:y + tpl.shape[0], PLANT_X:PLANT_X + tpl.shape[1]] = tpl
    line = highpass(line)
    c = line.shape[0] // 2; sig = line[c - 10:c + 10].std()
    line *= snr * gstd / (sig + 1e-9)
    return line + grain if grain is not None else line


def rank_one(phrase, line, grid, rng):
    var = s6.variants(phrase); rnd = s6.randoms(phrase, N_RANDOM, rng)
    with Pool(N_WORKERS, initializer=s6.init_worker, initargs=({"SYN": line},)) as pool:
        t, above, _ = s6.rank_candidates(pool, phrase, var + rnd, ["SYN"], grid)
    return dict(rank=len(above) + 1, n=len(var) + len(rnd) + 1, truth_ncc=t, randoms_above=sum(1 for c in above if c in rnd))


def grid_for(sigma):
    """All four fonts at the planted pitch and its neighbours; template blur equals the planted blur."""
    return [(f, p, CAP, sigma) for f in s6.FONTS for p in (PITCH - 4, PITCH, PITCH + 4)]


def conditions(grains, snr, g, rng, t0):
    conds = {"A_sharp_grain": (SHARP_BLUR, True), "B_blur_grain": (BLUR, True), "C_blur_nograin": (BLUR, False)}
    out = {}
    for cname, (sigma, use_grain) in conds.items():
        rows = []; grid = grid_for(sigma)
        for phrase in PHRASES:
            for j, grain in enumerate(grains if use_grain else [None]):
                r = rank_one(phrase, build_line(phrase, sigma, grain, snr, g), grid, rng)
                rows.append(dict(phrase=phrase, patch=j, **r))
                info(f"{cname} '{phrase}' patch {j}: rank {r['rank']}/{r['n']}, NCC {r['truth_ncc']:.3f} [{time.time() - t0:.0f}s]")
        wins = sum(r["rank"] == 1 for r in rows)
        out[cname] = dict(rows=rows, wins=wins, trials=len(rows), median_rank=float(np.median([r["rank"] for r in rows])))
        ok(f"{cname}: truth ranked #1 in {wins}/{len(rows)} trials, median rank {out[cname]['median_rank']:.0f}")
    return out


def sweep(grains, snr, g, rng, sigma, label, t0):
    rows = []; grid = grid_for(sigma)
    for mult in SWEEP_MULTS:
        rs = [rank_one(SWEEP_PHRASE, build_line(SWEEP_PHRASE, sigma, grain, snr * mult, g), grid, rng) for grain in grains]
        ranks = [r["rank"] for r in rs]
        rows.append(dict(mult=mult, snr=snr * mult, ranks=ranks, wins=sum(r == 1 for r in ranks)))
        ok(f"sweep ({label}) x{mult}: signal/grain {snr * mult:.2f} -> ranks {ranks} [{time.time() - t0:.0f}s]")
    return dict(phrase=SWEEP_PHRASE, n=rs[0]["n"], sigma_full_res=sigma * DS, rows=rows)


def main():
    rng = random.Random(SEED); t0 = time.time()
    try:
        R = tifffile.imread(os.path.join(OUT, "hdr_R.tif")).astype(np.float32)
        grains = [highpass(small(R[y:y + STRIP_H, x:x + STRIP_W])) for y, x in BLANK_PATCHES]
        snr, T, g = measure_snr(grains)
        snr_cal, snr_cal_range = snr_from_calibration()
        ok(f"measured signal/grain ratio on real lines: {snr:.2f} (text band std {T:.2f}, grain std {g:.2f}); "
           f"implied by the true phrases' calibration scores: {snr_cal:.2f} (range {snr_cal_range[0]:.2f}-{snr_cal_range[1]:.2f})")
    except Exception as e:
        err(f"could not prepare grain/SNR: {e}"); raise
    res = dict(settings=dict(snr=snr, snr_from_calibration=snr_cal, snr_from_calibration_range=snr_cal_range,
                             text_band_std=T, grain_std=g, blank_patches_full_res=BLANK_PATCHES, phrases=PHRASES,
                             font=FONT, pitch_full_res=PITCH * DS, cap_ratio=CAP, blur_sigma_full_res=BLUR * DS,
                             sharp_sigma_full_res=SHARP_BLUR * DS, n_random=N_RANDOM,
                             search_fonts=list(s6.FONTS), search_pitches_full_res=[(PITCH + d) * DS for d in (-4, 0, 4)],
                             template_blur="same as the planted letters in each condition"))
    try:
        res["results"] = conditions(grains, snr, g, rng, t0)
        res["sweep"] = sweep(grains, snr, g, rng, BLUR, "blurred", t0)
        res["sweep_sharp"] = sweep(grains, snr, g, rng, SHARP_BLUR, "sharp", t0)
    except Exception as e:
        err(f"synthetic test failed: {e}"); raise
    save_result("synthetic", res)


if __name__ == "__main__":
    main()
