"""Step 4: trace every typed line through each merged half and resample it flat.

At 1/4 scale, an anisotropic blur (wide along x, narrow along y) turns each typed line into a bright ridge.
A structure-tensor orientation field gives the local slope of the lines everywhere, including word gaps.
Each line is traced as a streamline of that field from a seed on the ridge, with a weak pull toward the
ridge crest. Duplicates (streamlines that converge) and weak paths are dropped. Straight strips are then
sampled at full resolution from the merged image along each traced centre line.
"""
import numpy as np, cv2, tifffile, os
from scipy.signal import find_peaks
from scipy.ndimage import gaussian_filter1d, map_coordinates
from common import HALVES, OUT, FIG, save_result, info, ok, warn, err

DS = 4
ALONG_SIGMA, ACROSS_SIGMA, BG_SIGMA = 25, 4, 30
TENSOR_SIGMA = 35
STEP = 2
RIDGE_PULL = 0.15
# Analyst-chosen seeds, in 1/4-scale pixels: memo line number -> (column, row). Chosen by inspecting the
# ridge-profile peaks at the most periodic column of each half (see README). Line 3 is short and does not
# reach the right half; line 9 (signature) is only on the right half, so it has its own seed column.
SEEDS = {
    "L": {1: (1816, 550), 2: (1816, 671), 3: (1816, 780), 4: (1816, 928), 5: (1816, 1038),
          6: (1816, 1179), 7: (1816, 1289), 8: (1816, 1427)},
    "R": {1: (536, 548), 2: (536, 658), 4: (536, 867), 5: (536, 983), 6: (536, 1089),
          7: (536, 1192), 8: (536, 1285), 9: (1006, 1426)},
}
# Analyst-chosen text extents in full-resolution columns (from the full-width strip sheets).
EXTENTS = {"L": {n: (4400, 10819) for n in range(1, 9)},
           "R": {**{n: (0, 8400) for n in range(1, 9)}, 9: (3300, 5000)}}
STRIP_HALF_HEIGHT = 170
EXTENT_FRAC = 0.30
PROF_W, PROF_STEP = 24, 8
MAX_SHIFT = 6
WIN_HALF = 190
LINE_PERIOD_RANGE = (95, 145)
RECENTRE_ITERS, RECENTRE_WIN, RECENTRE_RANGE = 2, 600, 90
MIN_LINE_GAP_PX, GAP_MARGIN = 280, 200


def ridge_image(hdr):
    s = cv2.resize(hdr, (hdr.shape[1] // DS, hdr.shape[0] // DS), interpolation=cv2.INTER_AREA)
    return cv2.GaussianBlur(s, (0, 0), sigmaX=ALONG_SIGMA, sigmaY=ACROSS_SIGMA) - cv2.GaussianBlur(s, (0, 0), BG_SIGMA)


def slope_field(A):
    gx = cv2.Sobel(A, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(A, cv2.CV_32F, 0, 1, ksize=5)
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), TENSOR_SIGMA); jyy = cv2.GaussianBlur(gy * gy, (0, 0), TENSOR_SIGMA)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), TENSOR_SIGMA)
    grad_angle = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
    line_angle = grad_angle + np.pi / 2
    m = np.tan(line_angle); return np.clip(np.nan_to_num(m), -0.6, 0.6).astype(np.float32)


def sample(img, y, x): return float(map_coordinates(img, [[y], [x]], order=1, mode="nearest")[0])


def streamline(A, M, x0, y0):
    H, W = A.shape; pts = {int(x0): y0}
    for d in (STEP, -STEP):
        x, y = float(x0), float(y0)
        while 1 <= x + d < W - 1:
            y += sample(M, y, x) * d; x += d
            if not (3 <= y < H - 3):
                break
            up, mid, dn = sample(A, y - 2, x), sample(A, y, x), sample(A, y + 2, x)
            denom = up - 2 * mid + dn
            if denom < 0:
                y += RIDGE_PULL * float(np.clip(-(dn - up) / (2 * denom) * 2, -2, 2))
            pts[int(round(x))] = y
    xs = np.array(sorted(pts)); return xs, np.array([pts[k] for k in xs])


def column_profiles(A):
    xs = np.arange(PROF_W, A.shape[1] - PROF_W, PROF_STEP)
    P = np.stack([A[:, x - PROF_W // 2:x + PROF_W // 2].mean(axis=1) for x in xs], axis=1)
    return xs, P


def best_shift(p, q):
    """Sub-pixel shift s such that q(y + s) best matches p(y), |s| <= MAX_SHIFT."""
    p = (p - p.mean()) / (p.std() + 1e-6); q = (q - q.mean()) / (q.std() + 1e-6)
    cc = [np.dot(p[MAX_SHIFT:-MAX_SHIFT], q[MAX_SHIFT + s:len(q) - MAX_SHIFT + s]) for s in range(-MAX_SHIFT, MAX_SHIFT + 1)]
    k = int(np.argmax(cc))
    if 0 < k < len(cc) - 1:
        d = cc[k - 1] - 2 * cc[k] + cc[k + 1]
        return k - MAX_SHIFT + (0.5 * (cc[k - 1] - cc[k + 1]) / d if d < 0 else 0.0)
    return float(k - MAX_SHIFT)


def track_pattern(P, ci, y0):
    """Follow y0 from column index ci across all columns by correlating a multi-line window of neighbouring profiles."""
    n, H = P.shape[1], P.shape[0]; ys = np.full(n, np.nan); ys[ci] = y0
    for d in (1, -1):
        y = float(y0); c = ci
        while 0 <= c + d < n:
            lo = int(round(y)) - WIN_HALF; hi = int(round(y)) + WIN_HALF
            if lo - MAX_SHIFT < 0 or hi + MAX_SHIFT >= H:
                break
            p = P[lo:hi, c]; q = P[lo - MAX_SHIFT:hi + MAX_SHIFT, c + d]
            s = best_shift(np.pad(p, MAX_SHIFT, mode="edge"), q)
            y += s; c += d; ys[c] = y
    return ys


def sample_strip(hdr, xq, yc):
    dy = np.arange(-STRIP_HALF_HEIGHT, STRIP_HALF_HEIGHT, dtype=np.float32)
    mx = np.ascontiguousarray(np.broadcast_to(xq[None, :], (len(dy), len(xq))), dtype=np.float32)
    my = np.ascontiguousarray(yc[None, :] + dy[:, None], dtype=np.float32)
    return cv2.remap(hdr, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def recentre(hdr, xq, yc):
    """Move the centre line onto the text band: per window, the offset of the brightest smoothed row near the centre."""
    for _ in range(RECENTRE_ITERS):
        s = sample_strip(hdr, xq, yc); s = cv2.GaussianBlur(s, (0, 0), sigmaX=40, sigmaY=10)
        s = s - cv2.GaussianBlur(s, (0, 0), 80)
        c = STRIP_HALF_HEIGHT; offs, xs_w = [], []
        for x0 in range(0, len(xq) - RECENTRE_WIN, RECENTRE_WIN // 3):
            prof = s[c - RECENTRE_RANGE:c + RECENTRE_RANGE, x0:x0 + RECENTRE_WIN].mean(axis=1)
            offs.append(int(np.argmax(prof)) - RECENTRE_RANGE); xs_w.append(x0 + RECENTRE_WIN // 2)
        if len(offs) < 2:
            break
        off = gaussian_filter1d(np.interp(np.arange(len(xq)), xs_w, gaussian_filter1d(np.array(offs, float), 1.5)), 100)
        yc = (yc + off).astype(np.float32)
    return yc


def extent(A, xs, ys):
    s = gaussian_filter1d(np.array([sample(A, y, x) for x, y in zip(xs, ys)]), 25)
    thr = EXTENT_FRAC * np.percentile(s, 95); on = np.where(s > thr)[0]
    return (on[0], on[-1], float(np.mean(s[on[0]:on[-1] + 1]))) if len(on) > 20 else (0, 0, 0.0)


def main():
    res = {}
    for half in HALVES:
        try:
            hdr = tifffile.imread(os.path.join(OUT, f"hdr_{half}.tif")).astype(np.float32)
            A = ridge_image(hdr); H, W = A.shape
            pxs, P = column_profiles(A)
            lines = []
            for line_no, (col, y_seed) in SEEDS[half].items():
                ci = int(np.argmin(np.abs(pxs - col)))
                prof = P[:, ci]; lo = max(0, y_seed - 20); y_seed = lo + int(np.argmax(prof[lo:y_seed + 21]))
                ys_all = track_pattern(P, ci, float(y_seed)); good = ~np.isnan(ys_all)
                xs = pxs[good]; ys = ys_all[good]; _, _, strength = extent(A, xs, ys)
                x_lo, x_hi = EXTENTS.get(half, {}).get(line_no, (0, W * DS))
                keep = (xs * DS >= x_lo) & (xs * DS <= x_hi)
                xx = xs[keep] * DS; yy = gaussian_filter1d(ys, 6)[keep] * DS
                xq = np.arange(xx[0], xx[-1], dtype=np.float32)
                yc0 = np.interp(xq, xx, yy).astype(np.float32); yc = recentre(hdr, xq, yc0)
                info(f"{half} line {line_no}: re-centred by {np.abs(yc - yc0).mean():.0f} px on average (max {np.abs(yc - yc0).max():.0f})")
                xx = xq[::16]; yy = yc[::16]
                lines.append(dict(line=line_no, seed_col=int(col * DS), seed_y=int(y_seed * DS), x0=int(xx[0]), x1=int(xx[-1]),
                                  knots_x=xx.tolist(), knots_y=yy.tolist(),
                                  travel_px=float(yy.max() - yy.min()), strength=strength))
            for a, b in zip(lines[:-1], lines[1:]):
                x = np.arange(max(a["x0"], b["x0"]), min(a["x1"], b["x1"]), 25)
                if not len(x):
                    continue
                gap = np.interp(x, b["knots_x"], b["knots_y"]) - np.interp(x, a["knots_x"], a["knots_y"])
                bad = x[gap < MIN_LINE_GAP_PX]
                if len(bad):
                    mid = 0.5 * (x[0] + x[-1])
                    for l in (a, b):
                        if bad.min() > mid:
                            l["x1"] = int(min(l["x1"], bad.min() - GAP_MARGIN))
                        else:
                            l["x0"] = int(max(l["x0"], bad.max() + GAP_MARGIN))
                    warn(f"{half} lines {a['line']}/{b['line']} come within {gap.min():.0f} px; both cut at "
                         f"{'x1=' + str(a['x1']) if bad.min() > mid else 'x0=' + str(a['x0'])}")
            for l in lines:
                keep = [(kx, ky) for kx, ky in zip(l["knots_x"], l["knots_y"]) if l["x0"] <= kx <= l["x1"]]
                l["knots_x"] = [k[0] for k in keep]; l["knots_y"] = [k[1] for k in keep]
                l["travel_px"] = float(max(l["knots_y"]) - min(l["knots_y"]))
            mid_x = np.median([0.5 * (l["x0"] + l["x1"]) for l in lines])
            centers = [float(np.interp(mid_x, l["knots_x"], l["knots_y"])) for l in lines]
            spacing = np.diff(centers)
            res[half] = dict(n_lines=len(lines), lines=lines, spacing_px=spacing.tolist(),
                             spacing_median=float(np.median(spacing)) if len(spacing) else None)
            ok(f"{half}: {len(lines)} lines; spacing {np.round(spacing).astype(int).tolist()} px; "
               f"travel {[int(l['travel_px']) for l in lines]} px")
            vis = cv2.cvtColor(np.clip((hdr[::DS, ::DS] - 40) * 1.4, 0, 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)
            for i, l in enumerate(lines):
                pts = np.c_[np.array(l["knots_x"]) / DS, np.array(l["knots_y"]) / DS].astype(np.int32)
                cv2.polylines(vis, [pts], False, (60, 180, 255), 3)
                cv2.putText(vis, str(l["line"]), (int(pts[0][0]) - 45, int(pts[0][1]) + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (60, 180, 255), 3)
            cv2.imwrite(os.path.join(FIG, f"lines_overlay_{half}.png"), vis)
            strips = []
            for i, l in enumerate(lines):
                xq = np.arange(l["x0"], l["x1"], dtype=np.float32)
                yc = np.interp(xq, l["knots_x"], l["knots_y"]).astype(np.float32)
                strip = sample_strip(hdr, xq, yc)
                tifffile.imwrite(os.path.join(OUT, f"strip_{half}_{l['line']}.tif"), strip.astype(np.float32)); strips.append(strip)
            Wd = max(s.shape[1] for s in strips); fill = float(np.median(hdr))
            sheet = np.vstack([np.pad(s, ((0, 12), (0, Wd - s.shape[1])), constant_values=fill) for s in strips])
            sheet = cv2.GaussianBlur(sheet, (0, 0), 4)
            lo, hi = np.percentile(sheet, 1), np.percentile(sheet, 99.5)
            sheet = np.clip((sheet - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
            cv2.imwrite(os.path.join(FIG, f"strips_{half}.png"), cv2.resize(sheet, (Wd // 4, sheet.shape[0] // 4), interpolation=cv2.INTER_AREA))
        except Exception as e:
            err(f"line tracing failed for {half}: {e}"); raise
    save_result("lines", res)


if __name__ == "__main__":
    main()
