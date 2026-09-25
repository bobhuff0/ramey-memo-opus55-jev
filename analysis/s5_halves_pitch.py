"""Step 5: (a) where the two halves overlap, found by matching their grain; (b) character pitch along
the straightened lines; (c) a denoiser comparison on one straightened line.

(a) Unsmoothed high-passed 384-px patches from the right edge of the left half are searched in the left third
    of the right half by normalised cross-correlation. A consistent offset with a high peak, far above the
    second-best location and a control patch, means the two files show the same negative.
(b) The column profile of each strip's text band is autocorrelated; the first strong peak between 150 and 320 px
    is the typewriter pitch.
"""
import numpy as np, cv2, tifffile, os, glob
from skimage.restoration import denoise_tv_chambolle, denoise_nl_means
from common import OUT, FIG, save_result, load_results, info, ok, warn, err

PATCH = 384
SEARCH_X = (0, 4200)
HP_SIGMA = 12
PITCH_RANGE = (150, 320)
DENOISE_LINE = ("L", 3)


def hp(a): return (a - cv2.GaussianBlur(a, (0, 0), HP_SIGMA)).astype(np.float32)


def overlap():
    L = tifffile.imread(os.path.join(OUT, "hdr_L.tif")); R = tifffile.imread(os.path.join(OUT, "hdr_R.tif"))
    Lh, Rh = hp(L), hp(R); Rs = Rh[:, SEARCH_X[0]:SEARCH_X[1]]
    rows = []
    for (y, x) in [(3200, 9400), (3800, 9800), (4400, 9300), (5000, 9700), (5600, 9500), (4200, 10100)]:
        tpl = Lh[y:y + PATCH, x:x + PATCH]
        res = cv2.matchTemplate(Rs, tpl, cv2.TM_CCOEFF_NORMED)
        _, best, _, loc = cv2.minMaxLoc(res)
        r2 = res.copy(); cy, cx = loc[1], loc[0]; r2[max(0, cy - 60):cy + 60, max(0, cx - 60):cx + 60] = -1
        second = float(r2.max())
        rows.append(dict(L_xy=[x, y], R_xy=[int(cx + SEARCH_X[0]), int(cy)], ncc=float(best), second=second,
                         dx=int(x - (cx + SEARCH_X[0])), dy=int(y - cy)))
        info(f"L patch at ({x},{y}) -> R ({cx + SEARCH_X[0]},{cy}): NCC {best:.3f}, next best {second:.3f}")
    ctrl_tpl = Lh[1500:1500 + PATCH, 6000:6000 + PATCH]
    ctrl = float(cv2.matchTemplate(Rs, ctrl_tpl, cv2.TM_CCOEFF_NORMED).max())
    good = [r for r in rows if r["ncc"] > 0.5]
    dx = np.array([r["dx"] for r in good]); dy = np.array([r["dy"] for r in good])
    out = dict(patches=rows, control_best_ncc=ctrl, n_matched=len(good),
               offset_dx_median=float(np.median(dx)) if len(good) else None,
               offset_dy_median=float(np.median(dy)) if len(good) else None,
               offset_dx_range=[int(dx.min()), int(dx.max())] if len(good) else None,
               ncc_range=[float(min(r["ncc"] for r in good)), float(max(r["ncc"] for r in good))] if good else None,
               second_best_max=float(max(r["second"] for r in rows)))
    if good:
        ok(f"halves: {len(good)}/{len(rows)} patches match at R col 0 = L col {np.median(dx):.0f} (dy {np.median(dy):.0f}); "
           f"NCC {out['ncc_range'][0]:.2f}-{out['ncc_range'][1]:.2f}; next best <= {out['second_best_max']:.2f}; control {ctrl:.2f}")
    else:
        warn("halves: no patch matched")
    return out


def pitch():
    """Mean power spectrum of the text-band column profile over all strips (1500-px windows, half overlap).
    Also computed for a band 200 px off the text (control)."""
    N = 1500; freqs = np.fft.rfftfreq(N); acc = {"text": np.zeros(len(freqs)), "control": np.zeros(len(freqs))}; nwin = 0
    for f in sorted(glob.glob(os.path.join(OUT, "strip_*.tif"))):
        s = cv2.GaussianBlur(tifffile.imread(f).astype(np.float32), (0, 0), 3); c = s.shape[0] // 2
        for key, rows in [("text", slice(c - 50, c + 50)), ("control", slice(0, 60))]:
            band = s[rows].mean(axis=0)
            for x0 in range(0, len(band) - N, N // 2):
                w = band[x0:x0 + N]; w = (w - w.mean()) * np.hanning(N)
                acc[key] += np.abs(np.fft.rfft(w)) ** 2
                if key == "text":
                    nwin += 1
    sel = (freqs > 1 / PITCH_RANGE[1]) & (freqs < 1 / PITCH_RANGE[0])
    spec = acc["text"] / acc["control"]
    k = int(np.argmax(spec[sel])); fpk = freqs[sel][k]
    # parabolic refinement on the ratio spectrum
    i = np.where(sel)[0][k]; y0, y1, y2 = spec[i - 1], spec[i], spec[i + 1]
    fref = fpk + (0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)) * (freqs[1] - freqs[0])
    prominence = float(spec[sel][k] / np.median(spec[sel]))
    ok(f"pitch: mean spectrum over {nwin} windows peaks at {1 / fref:.0f} px per character (text/control power ratio "
       f"{prominence:.1f}x the band median)")
    return dict(pitch_px=float(1 / fref), prominence=prominence, windows=nwin,
                ratio_spectrum=[[float(1 / f), float(v)] for f, v in zip(freqs[sel], spec[sel])])


def denoise():
    half, n = DENOISE_LINE
    s = tifffile.imread(os.path.join(OUT, f"strip_{half}_{n}.tif")).astype(np.float32)
    seg = s[:, 1200:4200]; lo, hi = np.percentile(seg, 1), np.percentile(seg, 99.5); z = np.clip((seg - lo) / (hi - lo), 0, 1)
    small = cv2.resize(z, (z.shape[1] // 3, z.shape[0] // 3), interpolation=cv2.INTER_AREA)
    methods = [("raw", small),
               ("Gaussian, sigma 5 px", cv2.GaussianBlur(small, (0, 0), 5 / 3)),
               ("median 15 px + Gaussian", cv2.GaussianBlur(cv2.medianBlur((small * 255).astype(np.uint8), 5).astype(np.float32) / 255, (0, 0), 1)),
               ("total variation", denoise_tv_chambolle(small, weight=0.15)),
               ("non-local means", denoise_nl_means(small, h=0.08, patch_size=5, patch_distance=6, fast_mode=True))]
    rows = []
    for name, im in methods:
        im = (im - im.min()) / (im.max() - im.min() + 1e-6); rows.append((np.clip(im, 0, 1) * 255).astype(np.uint8))
    sheet = np.vstack([np.pad(r, ((0, 6), (0, 0)), constant_values=0) for r in rows])
    cv2.imwrite(os.path.join(FIG, "denoise_compare.png"), sheet)
    ok(f"denoise figure: {[m[0] for m in methods]} on strip {half}{n}")
    return dict(line=f"{half}{n}", methods=[m[0] for m in methods])


def main():
    try:
        save_result("halves", overlap())
        save_result("pitch", pitch())
        save_result("denoise", denoise())
    except Exception as e:
        err(f"step 5 failed: {e}"); raise


if __name__ == "__main__":
    main()
