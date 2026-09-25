"""Render the YouTube Short (1080x1920, 30 fps) from out/timing.json and out/narration.wav.

Every frame is drawn with PIL and piped to ffmpeg. Layout keeps captions and key text out of the bottom
320 px and the right-hand 140 px, where the Shorts player draws its buttons.

Run from short/:  python3 short_render.py [--stills]
Writes ../Ramey-Memo-Short.mp4 (and out/stills/*.png with --stills).
"""
import os, sys, json, math, random, subprocess, argparse
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from termcolor import cprint

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
ASSETS = os.path.join(ROOT, "build", "assets")
STILLS = os.path.join(ROOT, "build", "stills")
FONTS = os.path.join(ROOT, "build", "fonts")
TIMING_JSON = os.path.join(OUT, "timing.json")
NARRATION_WAV = os.path.join(OUT, "narration.wav")
FINAL_MP4 = os.path.join(ROOT, "Ramey-Memo-Short.mp4")

W, H, FPS = 1080, 1920, 30
BG, GOLD, CREAM, GREY, INK = (16, 35, 38), (197, 164, 119), (239, 233, 220), (167, 182, 181), (10, 22, 24)
VIS_Y, VIS_H = 300, 1000            # visual band
CAP_Y = 1455                        # caption centre line
CAP_MAX_W = 900
XFADE_S = 0.22
POP_S = 0.14

HEAVY = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
SERIF = os.path.join(FONTS, "LiberationSerif-Regular.ttf")
SANSB = os.path.join(FONTS, "LiberationSans-Bold.ttf")
SANS = os.path.join(FONTS, "LiberationSans-Regular.ttf")
MONOB = os.path.join(FONTS, "LiberationMono-Bold.ttf")
_FONT_CACHE = {}


def F(path, size):
    k = (path, int(size))
    if k not in _FONT_CACHE:
        _FONT_CACHE[k] = ImageFont.truetype(path, int(size))
    return _FONT_CACHE[k]


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def cover(img, w, h):
    """scale-and-crop an image to fill w x h"""
    s = max(w / img.width, h / img.height)
    im = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


def kenburns(img, u, w, h, z0, z1, c0, c1):
    """crop a zooming, panning window from img. c0/c1 are window centres as fractions of the image."""
    z = z0 + (z1 - z0) * u
    ar = w / h
    ch = img.height / z; cw = ch * ar
    if cw > img.width:
        cw = img.width / z; ch = cw / ar
    cx = (c0[0] + (c1[0] - c0[0]) * u) * img.width; cy = (c0[1] + (c1[1] - c0[1]) * u) * img.height
    x0 = min(max(cx - cw / 2, 0), img.width - cw); y0 = min(max(cy - ch / 2, 0), img.height - ch)
    return img.resize((w, h), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


def text_c(d, xy, s, font, fill, stroke=0, stroke_fill=INK, anchor="mm"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=stroke_fill)


def band_fade(im):
    """soft fade of the visual band's top and bottom edges into the background"""
    grad = Image.new("L", (1, VIS_H), 255)
    for y in range(VIS_H):
        a = min(1.0, y / 90, (VIS_H - 1 - y) / 140)
        grad.putpixel((0, y), int(255 * max(0.0, a)))
    mask = grad.resize((W, VIS_H))
    base = Image.new("RGB", (W, VIS_H), BG)
    return Image.composite(im, base, mask)


# ---------------------------------------------------------------- assets
def load_assets():
    try:
        a = dict(
            photo=Image.open(os.path.join(ASSETS, "photo_panel.png")).convert("RGB"),
            neg=ImageOps.invert(Image.open(os.path.join(ASSETS, "raw_all.png")).convert("L")).convert("RGB"),
            grain=Image.open(os.path.join(ASSETS, "grain_zoom.png")).convert("RGB"),
            straight=Image.open(os.path.join(ASSETS, "straightened.png")).convert("RGB"),
            hdr=Image.open(os.path.join(ASSETS, "hdr_L.png")).convert("RGB"),
            title=Image.open(os.path.join(STILLS, "01_title.png")).convert("RGB"),
        )
    except Exception as e:
        sys.exit(f"could not load assets: {e}")
    a["hdr_dim"] = Image.blend(cover(a["hdr"], W, VIS_H), Image.new("RGB", (W, VIS_H), BG), 0.72)
    a["title_card"] = a["title"].resize((900, int(900 * a["title"].height / a["title"].width)), Image.LANCZOS)
    return a


# ---------------------------------------------------------------- visuals (each returns a W x VIS_H image)
def chunk_starts(T, b):
    return [c["start"] for c in T["chunks"] if c["beat"] == b]


def v_hook(A, T, b, t, u):
    punch = 0.25 * (1 - ease(t / 0.35))
    im = kenburns(A["photo"], ease(u), W, VIS_H, 1.0 + punch, 1.35, (0.55, 0.55), (0.60, 0.52))
    return band_fade(im)


def v_photo(A, T, b, t, u):
    cs = chunk_starts(T, b)
    if t < cs[2]:
        k = (t - cs[0]) / max(0.1, cs[2] - cs[0])
        im = kenburns(A["photo"], k, W, VIS_H, 1.35, 1.9, (0.60, 0.52), (0.48, 0.62))
    else:
        k = (t - cs[2]) / max(0.1, T["beats"][b]["end"] - cs[2])
        im = kenburns(A["neg"], k, W, VIS_H, 1.0, 1.15, (0.30, 0.5), (0.70, 0.5))
        if t - cs[2] < XFADE_S:
            prev = kenburns(A["photo"], 1.0, W, VIS_H, 1.35, 1.9, (0.60, 0.52), (0.48, 0.62))
            im = Image.blend(prev, im, (t - cs[2]) / XFADE_S)
    return band_fade(im)


def card(im, x, y, w, h, name, maker, role, alpha):
    if alpha <= 0:
        return
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 26, fill=(10, 22, 24, 235), outline=GOLD + (255,), width=5)
    d.text((44, 40), maker, font=F(SANSB, 38), fill=GOLD)
    d.text((44, 92), name, font=F(HEAVY, 76), fill=CREAM)
    d.text((44, 196), role, font=F(SANS, 40), fill=GREY)
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda p: int(p * alpha)))
    im.paste(layer, (int(x), int(y)), layer)


def v_tools(A, T, b, t, u):
    im = A["hdr_dim"].copy()
    cs = chunk_starts(T, b)
    k1 = ease((t - cs[1] + 0.1) / 0.35); k2 = ease((t - cs[2] + 0.1) / 0.35)
    card(im, 60 - 400 * (1 - k1), 170, 900, 280, "CLAUDE OPUS 5.5", "ANTHROPIC", "ran the image analysis", k1)
    card(im, 60 + 400 * (1 - k2), 520, 900, 280, "JEV 1.13", "TYPESAFE", "counted readers, checked the script", k2)
    return band_fade(im)


def v_readers(A, T, b, t, u):
    im = Image.new("RGB", (W, VIS_H), BG); d = ImageDraw.Draw(im)
    cs = chunk_starts(T, b)
    k = ease((t - cs[1]) / 0.6)
    n = max(0, min(5, round(5 * k))) if t >= cs[1] else 10
    label = "READERS" if t < cs[1] else "WORDS ALL TEN AGREE ON"
    pop = 1 + 0.12 * max(0.0, 1 - (t - cs[1]) / 0.25) if t >= cs[1] else 1
    text_c(d, (W // 2 - 70, 330), str(n), F(HEAVY, int(330 * pop)), GOLD if t >= cs[1] else CREAM)
    if t >= cs[2]:
        a = ease((t - cs[2]) / 0.3)
        text_c(d, (W // 2 - 70, 560), "OF 74", F(HEAVY, 120), tuple(int(BG[i] + (CREAM[i] - BG[i]) * a) for i in range(3)))
    text_c(d, (W // 2 - 70, 110), label, F(SANSB, 44), GREY)
    if t >= cs[1]:
        words = ["OF", "THE", "AT", "FORT", "WORTH"]
        x = 90
        for i, wd in enumerate(words):
            if t >= cs[1] + 0.12 * i:
                box = d.textbbox((0, 0), wd, font=F(MONOB, 54))
                bw = box[2] - box[0] + 36
                d.rounded_rectangle([x, 720, x + bw, 800], 14, outline=GOLD, width=4)
                d.text((x + 18, 732), wd, font=F(MONOB, 54), fill=CREAM)
                x += bw + 18
        d.text((90, 830), "the only unanimous word positions", font=F(SANS, 36), fill=GREY)
    return im


RANDOM_POOL = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def v_rank(A, T, b, t, u):
    im = Image.new("RGB", (W, VIS_H), BG); d = ImageDraw.Draw(im)
    cs = chunk_starts(T, b)
    d.rounded_rectangle([70, 60, W - 150, 200], 20, outline=GOLD, width=5)
    d.text((110, 92), "FORT WORTH, TEX.", font=F(MONOB, 70), fill=CREAM)
    d.text((110, 215), "a phrase nobody disputes", font=F(SANS, 36), fill=GREY)
    if t >= cs[3]:
        k = ease((t - cs[3]) / max(0.3, cs[4] - cs[3]))
        n = max(1, int(round(183 * k)))
        suf = "RD" if n % 10 == 3 and n % 100 != 13 else "ST" if n % 10 == 1 and n % 100 != 11 else "ND" if n % 10 == 2 and n % 100 != 12 else "TH"
        text_c(d, (W // 2 - 60, 450), f"{n}{suf}", F(HEAVY, 250), GOLD)
    if t >= cs[4]:
        a = ease((t - cs[4]) / 0.3)
        text_c(d, (W // 2 - 60, 640), "OF 601", F(HEAVY, 110), tuple(int(BG[i] + (CREAM[i] - BG[i]) * a) for i in range(3)))
    if t >= cs[5]:
        rng = random.Random(int(t * 12))
        for row in range(3):
            s = "".join(rng.choice(RANDOM_POOL) for _ in range(4)) + " " + "".join(rng.choice(RANDOM_POOL) for _ in range(5)) + ", " + "".join(rng.choice(RANDOM_POOL) for _ in range(3)) + "."
            d.text((110, 760 + row * 70), s, font=F(MONOB, 50), fill=(120, 140, 138))
        d.text((640, 830), "beat it", font=F(SANSB, 44), fill=GOLD)
    return im


def v_grain(A, T, b, t, u):
    im = kenburns(A["hdr"], ease(u), W, VIS_H, 1.0, 1.3, (0.45, 0.5), (0.55, 0.45))
    d = ImageDraw.Draw(im)
    cs = chunk_starts(T, b)
    if t >= cs[1]:
        text_c(d, (W // 2 - 50, 880), "THE LETTERS, UNDER THE GRAIN", F(SANSB, 46), CREAM, stroke=6)
    return band_fade(im)


def v_victims(A, T, b, t, u):
    im = Image.new("RGB", (W, VIS_H), BG); d = ImageDraw.Draw(im)
    memo = A["straight"]
    mh = 520; mw = int(memo.width * mh / memo.height)
    big = memo.resize((mw, mh), Image.BICUBIC)
    x = int(-(mw - W) * (0.05 + 0.30 * ease(u)))
    top = 300
    im.paste(big, (x, top))
    row = mh / 9
    d.rectangle([0, int(top + row) - 4, W, int(top + 2 * row) + 4], outline=GOLD, width=6)
    d.text((80, 255), "THE MEMO, STRAIGHTENED · LINE 2 BOXED", font=F(SANSB, 34), fill=GREY)
    cs = chunk_starts(T, b)
    pop = 1 + 0.2 * max(0.0, 1 - (t - cs[0]) / 0.2)
    text_c(d, (W // 2 - 60, 150), "VICTIMS?", F(HEAVY, int(150 * pop)), GOLD, stroke=6)
    if t >= cs[1]:
        k = ease((t - cs[1]) / 0.18)
        stamp = Image.new("RGBA", (820, 170), (0, 0, 0, 0)); sd = ImageDraw.Draw(stamp)
        sd.rounded_rectangle([4, 4, 815, 165], 18, outline=CREAM + (255,), width=8)
        sd.text((410, 88), "NOT READABLE", font=F(HEAVY, 88), fill=CREAM, anchor="mm")
        stamp = stamp.rotate(-7, expand=True, resample=Image.BICUBIC)
        s = 1.6 - 0.6 * k
        stamp = stamp.resize((int(stamp.width * s), int(stamp.height * s)), Image.BICUBIC)
        im.paste(stamp, (W // 2 - 60 - stamp.width // 2, 885 - stamp.height // 2), stamp)
    return im


def v_cta(A, T, b, t, u):
    im = Image.new("RGB", (W, VIS_H), BG); d = ImageDraw.Draw(im)
    k = ease(u * 3)
    tc = A["title_card"]; s = 0.9 + 0.1 * k
    card_im = tc.resize((int(tc.width * s), int(tc.height * s)), Image.LANCZOS)
    x = (W - 60 - card_im.width) // 2; y = 150
    d.rectangle([x - 6, y - 6, x + card_im.width + 5, y + card_im.height + 5], outline=GOLD, width=6)
    im.paste(card_im, (x, y))
    cx, cy = (W - 60) // 2, y + card_im.height + 200
    d.polygon([(cx - 330, cy - 45), (cx - 330, cy + 45), (cx - 250, cy)], fill=GOLD)
    d.text((cx - 220, cy), "FULL 10-MIN VIDEO", font=F(HEAVY, 70), fill=CREAM, anchor="lm")
    d.text((cx, cy + 110), "on The Future Past", font=F(SANS, 44), fill=GREY, anchor="mm")
    return im


VISUALS = dict(hook=v_hook, photo=v_photo, tools=v_tools, readers=v_readers, rank=v_rank, grain=v_grain,
               victims=v_victims, cta=v_cta)


# ---------------------------------------------------------------- captions
def caption_image(display):
    """render a caption chunk; *starred* words in gold. Returns RGBA."""
    font = F(HEAVY, 96)
    words, gold, star = [], [], False
    for raw in display.split():
        if raw.startswith("*"): star = True
        wd = raw.strip("*")
        words.append(wd); gold.append(star)
        if raw.endswith("*"): star = False
    space = font.getlength(" ")
    lines, cur, cur_w = [], [], 0
    for wd, g in zip(words, gold):
        ww = font.getlength(wd)
        if cur and cur_w + space + ww > CAP_MAX_W:
            lines.append((cur, cur_w)); cur, cur_w = [], 0
        cur_w = cur_w + (space if cur else 0) + ww; cur.append((wd, g, ww))
    if cur: lines.append((cur, cur_w))
    lh = 118
    img = Image.new("RGBA", (W, lh * len(lines) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i, (ln, lw) in enumerate(lines):
        x = (W - 60 - lw) / 2
        for wd, g, ww in ln:
            d.text((x, 20 + i * lh), wd, font=font, fill=GOLD if g else CREAM, stroke_width=9, stroke_fill=INK)
            x += ww + space
    return img


def current_chunk(T, t):
    ch = T["chunks"]
    for i, c in enumerate(ch):
        nxt = ch[i + 1]["start"] if i + 1 < len(ch) else T["duration"]
        if (c["start"] <= t or i == 0) and t < nxt and t <= c["end"] + 0.6:
            return i, c
    return None, None


# ---------------------------------------------------------------- frame
def frame(A, T, caps, t):
    beats = T["beats"]
    b = next(i for i, bt in enumerate(beats) if bt["start"] <= t < bt["end"] or i == len(beats) - 1)
    bt = beats[b]
    u = (t - bt["start"]) / max(0.1, bt["end"] - bt["start"])
    vis = VISUALS[bt["visual"]](A, T, b, t, u)
    if b > 0 and t - bt["start"] < XFADE_S:
        pb = beats[b - 1]
        prev = VISUALS[pb["visual"]](A, T, b - 1, bt["start"] - 1e-3, 1.0)
        vis = Image.blend(prev, vis, (t - bt["start"]) / XFADE_S)
    im = Image.new("RGB", (W, H), BG)
    im.paste(vis, (0, VIS_Y))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 12], fill=(40, 60, 62))
    d.rectangle([0, 0, int(W * t / T["duration"]), 12], fill=GOLD)
    d.text((70, 70), "THE FUTURE PAST", font=F(SANSB, 34), fill=GOLD)
    kp = 1 + 0.15 * max(0.0, 1 - (t - bt["start"]) / 0.18)
    d.text((70, 165), bt["kicker"], font=F(SERIF, int(78 * kp)), fill=CREAM, anchor="lm")
    d.line([(70, 225), (330, 225)], fill=GOLD, width=5)
    i, c = current_chunk(T, t)
    if c is not None:
        cap = caps[i]
        k = (t - c["start"]) / POP_S
        s = 0.82 + 0.18 * ease(k) if 0 <= k < 1 else 1.0
        if s != 1.0:
            cap = cap.resize((int(cap.width * s), int(cap.height * s)), Image.BICUBIC)
        im.paste(cap, ((W - cap.width) // 2, CAP_Y - cap.height // 2), cap)
    return im


def main():
    p = argparse.ArgumentParser(); p.add_argument("--stills", action="store_true", help="write a still per beat and stop")
    a = p.parse_args()
    try:
        with open(TIMING_JSON, encoding="utf-8") as f:
            T = json.load(f)
    except Exception as e:
        sys.exit(f"could not read {TIMING_JSON} (run short_tts.py first): {e}")
    A = load_assets()
    caps = [caption_image(c["display"]) for c in T["chunks"]]
    if a.stills:
        os.makedirs(os.path.join(OUT, "stills"), exist_ok=True)
        for bt in T["beats"]:
            t = min(bt["end"] - 0.05, bt["start"] + 0.8 * (bt["end"] - bt["start"]))
            path = os.path.join(OUT, "stills", f"{bt['beat']:02d}_{bt['visual']}.png")
            frame(A, T, caps, t).save(path); cprint(f"[ ok ] {path}", "green")
        return
    n = int(math.ceil(T["duration"] * FPS))
    cprint(f"[info] rendering {n} frames ({T['duration']:.1f} s) -> {FINAL_MP4}", "cyan")
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", NARRATION_WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", FINAL_MP4]
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for k in range(n):
            proc.stdin.write(frame(A, T, caps, k / FPS).tobytes())
            if k % 150 == 0:
                cprint(f"[info] frame {k}/{n}", "cyan")
        proc.stdin.close(); proc.wait()
        if proc.returncode:
            sys.exit(f"ffmpeg failed with code {proc.returncode}")
    except Exception as e:
        sys.exit(f"render failed: {e}")
    cprint(f"[ ok ] wrote {FINAL_MP4}", "green")


if __name__ == "__main__":
    main()
