"""Step 1: how well do the four brightness captures of each half line up, and is their grain shared?

Global and 512-px-tile phase correlation on high-passed images against the 60B capture,
then high-pass NCC after the measured shift. Tiles are taken on the memo paper only.
"""
import numpy as np, cv2
from common import EXPOSURES, REF_EXPOSURE, HALVES, load_half, save_result, info, ok, warn, err, ncc

HIGHPASS_SIGMA = 12
TILE = 512
TILE_STEP = 768
MIN_TILE_RESPONSE = 0.05


def highpass(a): return a - cv2.GaussianBlur(a, (0, 0), HIGHPASS_SIGMA)


def paper_mask(ref):
    """Memo paper is the darker (in stored values) mid-grey band; background film is bright."""
    small = cv2.resize(ref, (ref.shape[1] // 16, ref.shape[0] // 16), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), 6)
    thr = np.percentile(small, 45)
    m = (small < thr).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    return cv2.resize(m, (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_NEAREST).astype(bool)


def tile_shifts(ref_hp, mov_hp, mask):
    H, W = ref_hp.shape; win = cv2.createHanningWindow((TILE, TILE), cv2.CV_32F); rows = []
    for y in range(TILE, H - 2 * TILE, TILE_STEP):
        for x in range(TILE, W - 2 * TILE, TILE_STEP):
            if mask[y:y + TILE, x:x + TILE].mean() < 0.9:
                continue
            (dx, dy), resp = cv2.phaseCorrelate(ref_hp[y:y + TILE, x:x + TILE], mov_hp[y:y + TILE, x:x + TILE], win)
            if resp < MIN_TILE_RESPONSE:
                continue
            M = np.float32([[1, 0, -dx], [0, 1, -dy]])
            moved = cv2.warpAffine(mov_hp[y - 64:y + TILE + 64, x - 64:x + TILE + 64], M, (TILE + 128, TILE + 128))[64:-64, 64:-64]
            rows.append(dict(x=x, y=y, dx=float(dx), dy=float(dy), resp=float(resp),
                             ncc_aligned=ncc(ref_hp[y:y + TILE, x:x + TILE], moved),
                             ncc_unaligned=ncc(ref_hp[y:y + TILE, x:x + TILE], mov_hp[y:y + TILE, x:x + TILE])))
    return rows


def main():
    out = {}
    for half in HALVES:
        try:
            ref = load_half(half, REF_EXPOSURE); mask = paper_mask(ref); ref_hp = highpass(ref)
            info(f"{half}: paper mask covers {mask.mean():.1%} of the frame")
            out[half] = {}
            for exp in EXPOSURES:
                if exp == REF_EXPOSURE:
                    continue
                mov_hp = highpass(load_half(half, exp))
                rows = tile_shifts(ref_hp, mov_hp, mask)
                if not rows:
                    warn(f"{half} {exp}: no usable tiles"); continue
                mag = np.array([np.hypot(r["dx"], r["dy"]) for r in rows])
                na = np.array([r["ncc_aligned"] for r in rows]); nu = np.array([r["ncc_unaligned"] for r in rows])
                out[half][exp] = dict(n_tiles=len(rows), shift_median=float(np.median(mag)), shift_max=float(mag.max()),
                                      shift_p10=float(np.percentile(mag, 10)), shift_p90=float(np.percentile(mag, 90)),
                                      ncc_aligned_median=float(np.median(na)), ncc_aligned_min=float(na.min()),
                                      ncc_unaligned_median=float(np.median(nu)), tiles=rows)
                ok(f"{half} {exp} vs {REF_EXPOSURE}: {len(rows)} tiles, shift median {np.median(mag):.2f} px "
                   f"(max {mag.max():.2f}), grain NCC aligned {np.median(na):.3f} / unaligned {np.median(nu):.3f}")
        except Exception as e:
            err(f"registration failed for {half}: {e}"); raise
    save_result("register", out)


if __name__ == "__main__":
    main()
