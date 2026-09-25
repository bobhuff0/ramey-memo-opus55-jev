"""Step 2: grain size on blank paper, and the software-enlargement signature of each file.

Grain: radially averaged autocorrelation of high-passed blank-paper tiles; report the lag where it falls to 0.5.
Sampling: (a) the spatial frequency below which 99% of the high-passed power lies;
          (b) the period of the interpolation pattern, from the spectrum of the column-wise mean |d/dx| signal.
"""
import numpy as np, cv2
from common import HALVES, REF_EXPOSURE, WHOLE_FILE, SCANS, load_half, load, save_result, info, ok, err
from s1_register import paper_mask
import os

TILE = 512
N_BLANK_TILES = 12
TEXT_SIGMA = 40


def blank_tiles(img):
    """Paper tiles with the least text-scale structure."""
    mask = paper_mask(img)
    band = cv2.GaussianBlur(img, (0, 0), 6) - cv2.GaussianBlur(img, (0, 0), TEXT_SIGMA)
    cands = []
    H, W = img.shape
    for y in range(0, H - TILE, TILE // 2):
        for x in range(0, W - TILE, TILE // 2):
            if mask[y:y + TILE, x:x + TILE].mean() < 0.98:
                continue
            cands.append((float(band[y:y + TILE, x:x + TILE].std()), y, x))
    cands.sort()
    return [(y, x) for _, y, x in cands[:N_BLANK_TILES]]


def radial_acf(tile):
    t = tile - cv2.GaussianBlur(tile, (0, 0), TEXT_SIGMA); t = t - t.mean()
    F = np.fft.fft2(t); ac = np.fft.fftshift(np.real(np.fft.ifft2(F * np.conj(F)))); ac /= ac.max()
    c = TILE // 2; yy, xx = np.indices(ac.shape); r = np.hypot(yy - c, xx - c).astype(int)
    prof = np.bincount(r.ravel(), ac.ravel()) / np.bincount(r.ravel())
    return prof[:60]


def half_width(prof):
    i = int(np.argmax(prof < 0.5)); return float(i - 1 + (prof[i - 1] - 0.5) / (prof[i - 1] - prof[i]))


def sampling(img):
    h = img - cv2.GaussianBlur(img, (0, 0), 3)
    out = {}
    for axis, name in [(1, "x"), (0, "y")]:
        d = np.abs(np.diff(h, axis=axis)).mean(axis=1 - axis)
        d = d - np.convolve(d, np.ones(51) / 51, mode="same"); d = d[100:-100]
        spec = np.abs(np.fft.rfft(d * np.hanning(len(d)))); freqs = np.fft.rfftfreq(len(d))
        sel = freqs > 0.05; k = np.argmax(spec[sel]); f = freqs[sel][k]
        ac = np.correlate(d, d, "full")[len(d) - 1:]; ac /= ac[0]
        rep = int(np.argmax(ac[5:30])) + 5
        out[name] = dict(period_px=float(1 / f), peak_to_median=float(spec[sel][k] / np.median(spec[sel])),
                         pattern_repeat_px=rep, repeat_acf=float(ac[rep]))
    tile = img[img.shape[0] // 2 - 1024:img.shape[0] // 2 + 1024, img.shape[1] // 2 - 1024:img.shape[1] // 2 + 1024]
    t = tile - cv2.GaussianBlur(tile, (0, 0), 60)
    P = np.abs(np.fft.fftshift(np.fft.fft2(t * np.outer(np.hanning(2048), np.hanning(2048))))) ** 2
    yy, xx = np.indices(P.shape); r = np.hypot(yy - 1024, xx - 1024) / 2048
    order = np.argsort(r.ravel()); cum = np.cumsum(P.ravel()[order]); cum /= cum[-1]
    out["f99_cycles_per_px"] = float(r.ravel()[order][np.searchsorted(cum, 0.99)])
    bins = np.arange(0, 0.5, 0.005); idx = np.digitize(r.ravel(), bins)
    prof = np.array([P.ravel()[idx == i].mean() for i in range(1, len(bins))])
    db = 10 * np.log10(prof / prof[2:8].max())
    sel = (bins[:-1] > 0.2) & (bins[:-1] < 0.35)
    f_notch = float(bins[:-1][sel][np.argmin(db[sel])] + 0.0025)
    out["spectrum_notch_cycles_per_px"] = f_notch
    out["source_sample_spacing_px"] = float(1 / f_notch)
    out["radial_power_db"] = [[float(f), float(v)] for f, v in zip(bins[:-1], db)]
    return out


def main():
    res = {}
    try:
        files = {f"{h}_{REF_EXPOSURE}": (lambda h=h: load_half(h, REF_EXPOSURE)) for h in HALVES}
        files["All_1000dpi"] = lambda: load(os.path.join(SCANS, WHOLE_FILE))
        for name, loader in files.items():
            img = loader()
            profs = [radial_acf(img[y:y + TILE, x:x + TILE]) for y, x in blank_tiles(img)]
            prof = np.mean(profs, axis=0); hw = half_width(prof)
            s = sampling(img)
            res[name] = dict(grain_acf_half_lag_px=hw, grain_fwhm_px=2 * hw, grain_acf=prof[:30].tolist(), sampling=s,
                             enlargement_estimate=float(0.5 / s["f99_cycles_per_px"]))
            ok(f"{name}: grain ACF half-lag {hw:.2f} px (FWHM {2 * hw:.1f}); interpolation period x {s['x']['period_px']:.3f} "
               f"y {s['y']['period_px']:.3f} px, repeat {s['x']['pattern_repeat_px']} px; 99% power below "
                   f"{s['f99_cycles_per_px']:.3f} cyc/px; spectral notch at {s['spectrum_notch_cycles_per_px']:.4f} "
                   f"-> source sample every {s['source_sample_spacing_px']:.2f} px")
    except Exception as e:
        err(f"grain/sampling failed: {e}"); raise
    save_result("grain_sampling", res)


if __name__ == "__main__":
    main()
