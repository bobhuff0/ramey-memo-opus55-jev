"""Step 3: merge the four brightness captures of each half into one image.

Each capture is aligned to 60B with a smooth shift field (from the step-1 tile shifts; ~0 on the right half),
mapped to 60B's scale by a linear fit on unclipped pixels, then averaged with clipped pixels excluded.
Noise reduction is measured on blank paper as the high-pass std relative to 60B alone.
"""
import numpy as np, cv2, tifffile, os
from scipy.interpolate import RBFInterpolator
from common import EXPOSURES, REF_EXPOSURE, HALVES, OUT, load_half, load_results, save_result, info, ok, warn, err, ncc
from s2_grain_sampling import blank_tiles, TILE

CLIP_LO, CLIP_HI = 3, 252
FIT_SAMPLES = 400_000
FLOW_SMOOTH = 8


def shift_field(tiles, shape):
    pts = np.array([[t["y"] + 256, t["x"] + 256] for t in tiles], float)
    vals = np.array([[t["dy"], t["dx"]] for t in tiles], float)
    step = 64; gy, gx = np.mgrid[0:shape[0]:step, 0:shape[1]:step]
    f = RBFInterpolator(pts, vals, kernel="thin_plate_spline", smoothing=5.0)(np.c_[gy.ravel(), gx.ravel()])
    dy = cv2.resize(f[:, 0].reshape(gy.shape).astype(np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    dx = cv2.resize(f[:, 1].reshape(gy.shape).astype(np.float32), (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return dy, dx


def warp(img, dy, dx):
    yy, xx = np.indices(img.shape, dtype=np.float32)
    return cv2.remap(img, xx + dx, yy + dy, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def to_u8_highpass(a):
    h = cv2.GaussianBlur(a - cv2.GaussianBlur(a, (0, 0), 12), (0, 0), 1.5)
    return np.clip(128 + h * 3, 0, 255).astype(np.uint8)


def refine_dense(ref, img):
    """Per-pixel residual alignment by DIS optical flow on the high-passed grain."""
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM); dis.setPatchSize(16); dis.setPatchStride(4)
    fl = cv2.GaussianBlur(dis.calc(to_u8_highpass(ref), to_u8_highpass(img), None), (0, 0), FLOW_SMOOTH)
    yy, xx = np.indices(img.shape, dtype=np.float32)
    return cv2.remap(img, xx + fl[..., 0], yy + fl[..., 1], cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def grain_ncc(ref, img, tiles):
    hp = lambda a: a - cv2.GaussianBlur(a, (0, 0), 12)
    return [ncc(hp(ref[y:y + TILE, x:x + TILE]), hp(img[y:y + TILE, x:x + TILE])) for y, x in tiles]


def hp_std(img, tiles):
    return float(np.median([(img[y:y + TILE, x:x + TILE] - cv2.GaussianBlur(img[y:y + TILE, x:x + TILE], (0, 0), 40)).std()
                            for y, x in tiles]))


def main():
    reg = load_results()["register"]; res = {}
    rng = np.random.default_rng(0)
    for half in HALVES:
        try:
            ref = load_half(half, REF_EXPOSURE); tiles = blank_tiles(ref)
            valid_ref = (ref > CLIP_LO) & (ref < CLIP_HI)
            acc = np.where(valid_ref, ref, 0).astype(np.float32); cnt = valid_ref.astype(np.float32)
            fits = {}; aligned_single = {}
            for exp in EXPOSURES:
                if exp == REF_EXPOSURE:
                    continue
                img = load_half(half, exp)
                t = reg[half][exp]["tiles"]
                if reg[half][exp]["shift_max"] > 0.5:
                    dy, dx = shift_field(t, img.shape); img = warp(img, dy, dx)
                    info(f"{half} {exp}: warped by smooth shift field (|shift| up to {np.hypot(dy, dx).max():.1f} px)")
                    img = refine_dense(ref, img)
                g = grain_ncc(ref, img, tiles)
                info(f"{half} {exp}: grain NCC with {REF_EXPOSURE} at blank tiles after alignment {min(g):.2f}-{max(g):.2f}")
                valid = (img > CLIP_LO) & (img < CLIP_HI) & valid_ref
                ys = rng.integers(0, img.shape[0], FIT_SAMPLES); xs = rng.integers(0, img.shape[1], FIT_SAMPLES)
                m = valid[ys, xs]; a, b = np.polyfit(img[ys, xs][m], ref[ys, xs][m], 1)
                mapped = a * img + b; ok_px = (img > CLIP_LO) & (img < CLIP_HI)
                acc += np.where(ok_px, mapped, 0); cnt += ok_px
                fits[exp] = dict(gain=float(a), offset=float(b), clipped_frac=float(1 - ok_px.mean()),
                                 grain_ncc_blank_min=float(min(g)), grain_ncc_blank_median=float(np.median(g)))
                aligned_single[exp] = mapped
                ok(f"{half} {exp}: mapped to {REF_EXPOSURE} with gain {a:.3f}, offset {b:.1f}; clipped {1 - ok_px.mean():.1%}")
            hdr = np.where(cnt > 0, acc / np.maximum(cnt, 1), ref).astype(np.float32)
            s_ref = hp_std(ref, tiles); s_hdr = hp_std(hdr, tiles)
            pair = {}
            for e1, e2 in [("55B", "60B"), ("65B", "70B")]:
                a1 = ref if e1 == REF_EXPOSURE else aligned_single[e1]; a2 = ref if e2 == REF_EXPOSURE else aligned_single[e2]
                d = (a1 - a2) / np.sqrt(2)
                pair[f"{e1}-{e2}"] = hp_std(d, tiles)
            tifffile.imwrite(os.path.join(OUT, f"hdr_{half}.tif"), np.clip(hdr, 0, 255).astype(np.float32))
            res[half] = dict(fits=fits, blank_hp_std_60B=s_ref, blank_hp_std_hdr=s_hdr,
                             noise_reduction_frac=float(1 - s_hdr / s_ref), scanner_noise_std_from_pairs=pair,
                             coverage_min_captures=float(cnt.min()))
            ok(f"{half}: blank-paper high-pass std 60B {s_ref:.2f} -> merged {s_hdr:.2f} "
               f"({1 - s_hdr / s_ref:.1%} lower); capture-to-capture noise {pair}")
        except Exception as e:
            err(f"HDR merge failed for {half}: {e}"); raise
    save_result("hdr", res)


if __name__ == "__main__":
    main()
