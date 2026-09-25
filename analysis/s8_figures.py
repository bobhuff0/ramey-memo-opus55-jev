"""Step 8: slide figures for the video, all computed from the scans and the results of steps 1-7.
Writes ../build/assets/*.png with the file names build/render.py expects. Strips and merges are stored as the
negative (ink bright); the straightened views are shown as a positive (dark ink on light paper)."""
import os, json, numpy as np, cv2, tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from skimage.restoration import denoise_tv_chambolle
from common import OUT, SCANS, WHOLE_FILE, load, load_half, load_results, save_result, info, ok, err

ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "build", "assets"))
os.makedirs(ASSETS, exist_ok=True)
EXPOSURE_CROP = (6100, 2350, 3000, 1800)       # x, y, w, h in L-half file px: lines 2-4
GRAIN_CROP = (1500, 3300)                      # strip L_3 columns: the start of FORT WORTH at full resolution
DENOISE_CROP = (0, 3600)                       # strip L_2 columns: first words of line 2
DISPLAY_BLUR = 4                               # px, full res, for the straightened views
MOSAIC_BLUR = 10
BG, GOLD, CREAM, GREY = "#102326", "#c5a477", "#efe9dc", "#a7b6b5"
TEAL = "#79c2b8"


def to_u8(a, lo=0.5, hi=99.5):
    p0, p1 = np.percentile(a, [lo, hi])
    return np.clip((a - p0) / (p1 - p0 + 1e-9) * 255, 0, 255).astype(np.uint8)


def w(name, img):
    cv2.imwrite(os.path.join(ASSETS, name), img); ok(f"asset {name} {img.shape[1]}x{img.shape[0]}")


def small(a, f): return cv2.resize(a, (a.shape[1] // f, a.shape[0] // f), interpolation=cv2.INTER_AREA)


def strip(name): return tifffile.imread(os.path.join(OUT, f"strip_{name}.tif")).astype(np.float32)


def files_and_exposures():
    a = load(os.path.join(SCANS, WHOLE_FILE))
    w("raw_all.png", np.clip(cv2.resize(a, (1800, int(1800 * a.shape[0] / a.shape[1])), interpolation=cv2.INTER_AREA), 0, 255).astype(np.uint8))
    x, y, cw, ch = EXPOSURE_CROP
    for lv in ["55B", "70B"]:
        c = load_half("L", lv)[y:y + ch, x:x + cw]
        w(f"raw_L_{lv}.png", np.clip(cv2.resize(c, (1000, 600), interpolation=cv2.INTER_AREA), 0, 255).astype(np.uint8))
    h = tifffile.imread(os.path.join(OUT, "hdr_L.tif")).astype(np.float32)[y:y + ch, x:x + cw]
    w("hdr_L.png", np.clip(cv2.resize(h, (1000, 600), interpolation=cv2.INTER_AREA), 0, 255).astype(np.uint8))


def grain_zoom():
    g = 255 - to_u8(strip("L_3")[:, GRAIN_CROP[0]:GRAIN_CROP[1]])
    w("grain_zoom.png", g); return g.shape[1]


def denoise_tiles():
    s = strip("L_2")[:, DENOISE_CROP[0]:DENOISE_CROP[1]]
    n = -(s - s.mean()) / s.std()
    u8 = to_u8(n)
    methods = [("no filter", n),
               ("Gaussian, sigma 8 px", cv2.GaussianBlur(n, (0, 0), 8)),
               ("total variation", denoise_tv_chambolle(n, weight=1.2)),
               ("non-local means", cv2.fastNlMeansDenoising(u8, None, h=40, templateWindowSize=9, searchWindowSize=35).astype(np.float32)),
               ("median 15 px + Gaussian 4 px", cv2.GaussianBlur(cv2.medianBlur(u8, 15).astype(np.float32), (0, 0), 4)),
               ("Gaussian, sigma 20 px (the fitted blur)", cv2.GaussianBlur(n, (0, 0), 20))]
    for i, (_, im) in enumerate(methods):
        w(f"denoise_{i}.png", to_u8(cv2.resize(im, (950, int(950 * im.shape[0] / im.shape[1])), interpolation=cv2.INTER_AREA), 1, 99))
    return [m[0] for m in methods]


def lines_views(R):
    h = tifffile.imread(os.path.join(OUT, "hdr_L.tif")).astype(np.float32)
    s = small(h, 4)
    vis = cv2.cvtColor(255 - to_u8(cv2.GaussianBlur(s, (0, 0), 2), 1, 99), cv2.COLOR_GRAY2BGR)
    for l in R["lines"]["L"]["lines"]:
        pts = np.array([[x / 4, y / 4] for x, y in zip(l["knots_x"], l["knots_y"])], np.int32)
        cv2.polylines(vis, [pts], False, (119, 164, 197), 3, cv2.LINE_AA)
    w("lines_overlay.png", vis[380:1480, 1000:2700])
    rows = []
    for l in R["lines"]["L"]["lines"]:
        t = small(cv2.GaussianBlur(strip(f"L_{l['line']}"), (0, 0), DISPLAY_BLUR), 4)
        rows.append(255 - to_u8(t, 1, 99)); rows.append(np.full((3, t.shape[1]), 200, np.uint8))
    w("unwarped_prev.png", cv2.cvtColor(np.vstack(rows[:-1]), cv2.COLOR_GRAY2BGR))


def mosaic(R):
    """Join each line's left and right strips at the grain-matched overlap (R col 0 = L col dx)."""
    L0 = R["lines"]["L"]["lines"][0]["x0"]; R0 = R["lines"]["R"]["lines"][0]["x0"]
    dx = R["halves"]["offset_dx_median"]; cut = int(round(dx + R0 - L0))
    have = {h: {l["line"]: l for l in R["lines"][h]["lines"]} for h in "LR"}
    width = cut + max(l["x1"] - R0 for l in have["R"].values())
    rows = []
    for n in range(1, 10):
        row = np.full((340, width), np.nan, np.float32)
        if n in have["L"]:
            row[:, :cut] = strip(f"L_{n}")[:, :cut]
        if n in have["R"]:
            r = strip(f"R_{n}"); a = cut + have["R"][n]["x0"] - R0; b = min(width, a + r.shape[1])
            row[:, a:b] = r[:, :b - a]
        m = np.isfinite(row); med = float(np.median(row[m])); sd = float(np.std(row[m]))
        z = np.where(m, (row - med) / sd, 0)
        z = small(cv2.GaussianBlur(z, (0, 0), MOSAIC_BLUR), 4)
        u = np.clip(150 - z * 110, 0, 255).astype(np.uint8)
        u[small(m.astype(np.float32), 4) < 0.99] = 30
        rows.append(u); rows.append(np.full((3, u.shape[1]), 200, np.uint8))
    mos = np.vstack(rows[:-1]); w("straightened.png", mos)
    rh = 85 + 3
    w("line2_strip.png", mos[rh:rh + 85, : cut // 4 + 1400])
    return dict(cut_col_in_L_strip=cut, width_full_res=width)


def sweep_chart(R):
    S = R["synthetic"]
    series = [("letters blurred as measured", S["sweep"], GOLD, 0.96)]
    if "sweep_sharp" in S:
        series.append(("sharp letters", S["sweep_sharp"], TEAL, 1.04))
    sw = S["sweep"]
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=150); fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    for label, s, col, nudge in series:
        rows = s["rows"]
        for r in rows:
            ax.scatter([r["mult"] * nudge] * len(r["ranks"]), r["ranks"], s=70, color=col, alpha=0.85, zorder=3,
                       edgecolor=BG, linewidth=0.8)
        ax.plot([r["mult"] * nudge for r in rows], [np.median(r["ranks"]) for r in rows], color=col, lw=2.2, zorder=2, label=label)
    ax.set_xscale("log"); mults = [r["mult"] for r in sw["rows"]]
    ax.set_xticks(mults); ax.set_xticklabels([f"{m:g}\u00d7" for m in mults]); ax.minorticks_off()
    ax.set_yscale("log"); ax.invert_yaxis(); ax.set_ylim(sw["n"] * 1.3, 0.7)
    ax.set_yticks([1, 3, 10, 30, 100]); ax.set_yticklabels(["1st", "3rd", "10th", "30th", "100th"])
    ax.axvline(1, color=CREAM, ls="--", lw=1.5)
    ax.text(1.05, sw["n"] * 0.9, "the real memo", color=CREAM, fontsize=15)
    ax.legend(loc="lower right", facecolor=BG, edgecolor=GREY, labelcolor=CREAM, fontsize=13)
    ax.set_xlabel("letter strength, relative to the real memo", color=GREY, fontsize=15)
    ax.set_ylabel(f"rank of {sw['phrase']} (of {sw['n']})", color=GREY, fontsize=15)
    ax.tick_params(colors=GREY, labelsize=13)
    for sp in ax.spines.values(): sp.set_color(GREY)
    ax.grid(color="#2c4448", lw=0.8)
    fig.tight_layout(); fig.savefig(os.path.join(ASSETS, "synthetic_sweep.png"), facecolor=BG); plt.close(fig)
    ok("asset synthetic_sweep.png")


def main():
    try:
        R = load_results(); meta = {}
        files_and_exposures()
        meta["grain_zoom_width_px"] = grain_zoom()
        meta["denoise_labels"] = denoise_tiles()
        lines_views(R)
        meta["mosaic"] = mosaic(R)
        sweep_chart(R)
        save_result("figures", meta)
    except Exception as e:
        err(f"figures failed: {e}"); raise


if __name__ == "__main__":
    main()
