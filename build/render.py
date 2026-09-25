import os, json, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps
from script import SCENES

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets"); OUT = os.path.join(HERE, "stills"); os.makedirs(OUT, exist_ok=True)
FONTS = os.path.join(HERE, "fonts")
S = 1.1; W, H = int(1920 * S), int(1080 * S)
BG, GOLD, CREAM, GREY, INK = (16, 35, 38), (197, 164, 119), (239, 233, 220), (167, 182, 181), (10, 22, 24)
SERIF = os.path.join(FONTS, "LiberationSerif-Regular.ttf")
SANS = os.path.join(FONTS, "LiberationSans-Regular.ttf")
SANSB = os.path.join(FONTS, "LiberationSans-Bold.ttf")
MONO = os.path.join(FONTS, "LiberationMono-Regular.ttf")
MONOB = os.path.join(FONTS, "LiberationMono-Bold.ttf")
RESULTS_PATH = os.path.join(HERE, "..", "analysis", "out", "results.json")
JEV_NAME = "TYPESAFE JEV 1.13"
OPUS_NAME = "ANTHROPIC CLAUDE OPUS 5.5"
VERDICT_SYNTH_LINE = "Opus 5.5: the memo’s blur plus grain defeats template matching"


def results():
    try:
        with open(RESULTS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise SystemExit(f"render: cannot read {RESULTS_PATH}: {e}")


def F(path, size): return ImageFont.truetype(path, int(size * S))
def P(v): return int(v * S)


class Slide:
    def __init__(self):
        self.im = Image.new("RGB", (W, H), BG); self.d = ImageDraw.Draw(self.im)
        self.d.rectangle([0, 0, W, P(12)], fill=GOLD)
        self.text((95, 1003), "THE FUTURE PAST", F(SANS, 27), GOLD)

    def text(self, xy, s, font, fill, anchor_top=True, tracking=0):
        x, y = P(xy[0]), P(xy[1])
        if tracking:
            cx = x
            top = self.d.textbbox((0, 0), "H", font=font)[1]   # common cap-top offset for every glyph
            for ch in s:
                b = self.d.textbbox((0, 0), ch, font=font); self.d.text((cx - b[0], y - top), ch, font=font, fill=fill)
                cx += font.getlength(ch) + P(tracking)
            return
        b = self.d.textbbox((0, 0), s, font=font); self.d.text((x - b[0], y - b[1]), s, font=font, fill=fill)

    def para(self, xy, s, font, fill, width_chars, leading=1.35):
        y = xy[1]
        for line in textwrap.wrap(s, width_chars):
            self.text((xy[0], y), line, font, fill); y += font.size / S * leading
        return y

    def kicker(self, s): self.text((90, 185), s, F(SERIF, 42), GOLD, tracking=2)
    def head(self, l1, l2=None, size=150):
        self.text((90, 300), l1, F(SERIF, size), CREAM)
        if l2: self.text((92, 300 + size * 1.15), l2, F(SERIF, size), CREAM)
    def rule(self, y, x0=97, x1=706): self.d.line([(P(x0), P(y)), (P(x1), P(y))], fill=GOLD, width=P(2))
    def label(self, xy, s, size=27, fill=GOLD): self.text(xy, s, F(SANS, size), fill)

    def image(self, path, box, fit="cover", align="center"):
        """Paste an image into box (1920-coords). Returns the rect actually painted, in canvas px."""
        x0, y0, x1, y1 = [P(v) for v in box]
        im = Image.open(path).convert("RGB")
        if fit == "cover": im = ImageOps.fit(im, (x1 - x0, y1 - y0), Image.LANCZOS)
        else:
            im.thumbnail((x1 - x0, y1 - y0), Image.LANCZOS)
        px = x0 if align == "left" else x0 + ((x1 - x0) - im.width) // 2
        py = y0 + ((y1 - y0) - im.height) // 2
        self.im.paste(im, (px, py))
        return (px, py, px + im.width, py + im.height)

    def save(self, name): self.im.save(f"{OUT}/{name}.png")



def title(sc):
    s = Slide()
    s.image(f"{A}/photo_panel.png", (825, 151, 1865, 929))
    s.label((830, 80), "THE ACTUAL PHOTOGRAPH")
    s.kicker("THE RAMEY MEMO"); s.head("CAN AI", "READ IT?"); s.rule(691)
    s.label((97, 734), OPUS_NAME, 42)
    s.label((97, 792), JEV_NAME, 42)
    s.label((97, 866), "the latest in publicly available AI", 28, GREY)
    s.text((827, 1002), "Archive: UTA Libraries • crop from the Ramey photograph", F(SANS, 23), GREY)
    return s


def tools(sc):
    s = Slide(); s.kicker("TWO AI SYSTEMS, TWO JOBS")
    n_pairs = results()["reader_agreement"]["n_pairs_judged"]
    boxes = [(OPUS_NAME, "reads the pixels", ["aligned the nine scans", "measured the grain and the enlargement",
                                               "traced and straightened all nine lines", "known-word and known-answer letter tests"]),
             (JEV_NAME, "judges the words \u2014 text only",
              [f"{n_pairs} pairs of readers\u2019 readings:", "\u2003same word, or different words?",
               "every factual sentence of this script:", "\u2003supported by the measurements?"])]
    for i, (name, role, items) in enumerate(boxes):
        x0 = 90 + i * 885
        s.d.rectangle([P(x0), P(260), P(x0 + 855), P(800)], outline=GOLD, width=P(2))
        s.text((x0 + 36, 300), name, F(SANSB, 40), GOLD); s.text((x0 + 36, 370), role, F(SERIF, 50), CREAM)
        y = 480
        for it in items:
            s.text((x0 + 36, y), it if it.startswith("\u2003") else "\u2014  " + it, F(SANS, 31), CREAM if not it.startswith("\u2003") else GREY)
            y += 66
    s.text((90, 860), "Code, not the models, sets every threshold and keeps the score.", F(SERIF, 48), GOLD)
    return s


def readers(sc):
    s = Slide(); s.kicker("WHAT TEN READERS AGREE ON \u2014 COUNTED BY JEV")
    ra = results()["reader_agreement"]; sm = ra["summary"]; n = ra["n_positions"]
    y = 290
    for key, what in [("10", "unanimous \u2014 10 of 10 readers"), ("8", "reach 8 of 10 readers"), ("6", "reach 6 of 10 readers")]:
        s.text((97, y), str(sm[key]["jev"]), F(SERIF, 110), CREAM); s.text((290, y + 40), what, F(SANS, 34), GOLD); y += 140
    s.text((97, y + 6), f"of {n} word positions \u00b7 {ra['n_pairs_judged']} reading pairs judged", F(SANS, 28), GREY)
    by_line = {}
    for p in ra["positions"]: by_line.setdefault(str(p["line"]), []).append(p)
    def cnt(line, *words):
        ps = by_line[str(line)]
        for i in range(len(ps) - len(words) + 1):
            if all(words[j] in ps[i + j]["variants"] for j in range(len(words))):
                return " \u00b7 ".join(str(ps[i + j]["n_readers"]) for j in range(len(words)))
        raise SystemExit(f"render: {' '.join(words)} not found on line {line}")
    ramey = next(p for p in by_line["9"] if "RAMEY" in p["variants"])
    temple = next(len(o["readers"]) for o in ramey["non_matching"] if o["reading"] == "TEMPLE")
    rows = [("line 2", "OF THE WRECK", cnt(2, "OF", "THE", "WRECK")),
            ("line 3", "AT FORT WORTH, TEX.", cnt(3, "AT", "FORT", "WORTH", "TEX")),
            ("line 4", "\u201cDISC\u201d = \u201cDISK\u201d", f"{cnt(4, 'DISC')}  merged by Jev"),
            ("line 7", "WEATHER BALLOONS", cnt(7, "WEATHER", "BALLOONS")),
            ("line 2", "VICTIMS", f"{cnt(2, 'VICTIMS')}  clears 6 of 10"),
            ("line 9", "RAMEY  (TEMPLE)", f"{cnt(9, 'RAMEY')} \u00b7 {temple}  below 6 of 10")]
    s.text((870, 285), "readers per word", F(SANS, 24), GOLD)
    y = 330
    for k, v, c in rows:
        s.text((870, y + 8), k, F(SANS, 24), GOLD); s.text((985, y), v, F(MONOB, 34), CREAM); s.text((1480, y + 6), c, F(SANS, 27), GREY); y += 74
    sens = ra["sensitivity_same_threshold"]; six = sorted({v["6"]["jev"] for v in sens.values()})
    s.rule(790, 97, 1820)
    s.para((97, 815), f"Jev gave the probability that each pair of readings names the same word; readings were grouped at 0.5. "
                      f"Any threshold from {min(sens)} to {max(sens)} gives {six[0]}\u2013{six[-1]} positions at six readers. Readings, not restored letters.",
           F(SANS, 28), GREY, 110)
    return s


def files(sc):
    s = Slide(); s.kicker("THE SOURCE FILES"); s.head("NINE", "SCANS", 140); s.rule(691)
    y = 730
    for line in ["L + R halves · “800 dpi” · four brightness files each", "whole memo · “1000 dpi” · one file",
                 "9 of the 23 files UTA posts · 8-bit · 721 MB"]:
        s.label((97, y), line, 27, GREY); y += 40
    s.label((830, 80), "UTA LIBRARIES · PROCESSED HDR WORKING FILES")
    s.image(f"{A}/raw_all.png", (825, 130, 1865, 500)); s.label((830, 505), "All-55B 1000 dpi.tif", 22, GREY)
    s.image(f"{A}/raw_L_55B.png", (825, 560, 1335, 900)); s.label((830, 905), "L Scanpro 55B (darkest file)", 22, GREY)
    s.image(f"{A}/raw_L_70B.png", (1355, 560, 1865, 900)); s.label((1360, 905), "L Scanpro 70B (lightest file)", 22, GREY)
    return s


def exposures(sc):
    s = Slide(); s.kicker("FOUR FILES, ONE GRAIN")
    for i, (f, lab) in enumerate([("raw_L_55B.png", "55B — darkest file"), ("raw_L_70B.png", "70B — lightest file"),
                                  ("hdr_L.png", "merge of all four, re-aligned")]):
        x0 = 90 + i * 590
        s.image(f"{A}/{f}", (x0, 260, x0 + 560, 600)); s.label((x0 + 4, 610), lab, 26)
    s.text((90, 690), "right half: aligned to \u2264 0.15 px \u00b7 grain correlation 0.80 \u2013 0.92", F(SERIF, 50), CREAM)
    s.text((90, 760), "left half: 65B and 70B shifted by up to 35 px, bending across the frame", F(SERIF, 50), CREAM)
    s.text((90, 850), "After re-alignment the grain matches (0.87 \u2013 0.89): one negative. Merging removes only 5 \u2013 8% of the noise.", F(SANS, 30), GREY)
    return s


def scale(sc):
    s = Slide(); s.kicker("THE LIMITING NUMBERS")
    y = 250
    for big, small in [("3.4\u20133.6 px", "real sample spacing \u2014 11 px repeat pattern: enlarged in software"), ("~16 px", "one grain clump (half-strength width)"),
                       ("~216 px", "one letter (pitch fitted on known words)"), ("~47 px", "letter blur, fitted on known words (half-strength width)")]:
        s.text((90, y), big, F(SERIF, 80), CREAM); s.label((100, y + 94), small, 26, GOLD); y += 152
    s.rule(870, 97, 760)
    s.text((97, 890), "~60 real samples per letter; blur ~1/5 of it", F(SANS, 28), GREY)
    box = s.image(f"{A}/grain_zoom.png", (860, 300, 1860, 760), fit="contain")
    s.label((860, 250), "LINE 3, \u201cFORT WO\u2026\u201d \u2014 MERGED PIXELS, NO SMOOTHING (POSITIVE)", 24)
    # scale bar = one letter (216 file px; the crop is 1800 file px wide)
    shown = box[2] - box[0]; bar = int(shown * 216 / 1800)
    s.d.line([(box[0], box[3] + P(28)), (box[0] + bar, box[3] + P(28))], fill=GOLD, width=P(4))
    s.text(((box[0]) / S + 4, box[3] / S + 36), "one letter", F(SANS, 22), GOLD)
    return s


def denoise(sc):
    s = Slide(); s.kicker("FIVE FILTERS, NO LETTERS")
    labels = ["no filter", "Gaussian \u03c3 = 8 px", "total variation", "non-local means", "median + Gaussian", "Gaussian \u03c3 = 20 px (the fitted blur)"]
    for i, l in enumerate(labels):          # 2 columns x 3 rows; each tile is line 2 around the disputed word
        c, r = i % 2, i // 2
        x0 = 90 + c * 880; y0 = 250 + r * 225
        s.label((x0 + 2, y0), l, 24)
        s.image(f"{A}/denoise_{i}.png", (x0, y0 + 36, x0 + 860, y0 + 36 + 160), fit="contain", align="left")
    s.text((90, 935), "line 2, left half, straightened \u2014 every filter yields the same word-blobs", F(SANS, 28), GREY)
    return s


def dewarp(sc):
    s = Slide(); s.kicker("STRAIGHTENING THE LINES")
    s.image(f"{A}/lines_overlay.png", (90, 250, 950, 620)); s.label((94, 630), "traced text lines on the merged left half", 24)
    s.image(f"{A}/unwarped_prev.png", (970, 250, 1830, 620)); s.label((974, 630), "the same lines, resampled flat", 24)
    s.text((90, 720), "lines drift by up to 290 px (left) and 340 px (right)", F(SERIF, 60), CREAM)
    s.text((90, 810), "over half the line spacing \u00b7 halves overlap ~2,100 px: grain match 0.92 \u2013 0.94 in 6 of 6 patches, next best 0.17", F(SANS, 28), GREY)
    return s


def straightened(sc):
    s = Slide(); s.kicker("THE CLEANEST VIEW THESE SCANS ALLOW")
    # image box (90,250)-(1830,850) left empty: encode.py pans assets/straightened.png inside it (MOTION "panbox")
    s.text((90, 880), "nine lines, straightened and joined \u2014 word lengths and spacing are clear; letters are not", F(SANS, 28), GREY)
    s.text((90, 925), "shown as a positive \u00b7 dark blocks: no scan there, or stretches where the tracer could not separate crowded lines", F(SANS, 24), GREY)
    return s


def estimate(sc):
    s = Slide(); s.kicker("WHAT TEN READERS AGREE ON — READINGS, NOT RESTORED LETTERS")
    rows = [("line 2", "… [7 letters] OF THE WRECK YOU FORWARDED TO THE", "9 · 6 of 10"),
            ("line 3", "AT FORT WORTH, TEX.", "10 \u00b7 TEX. 9"),
            ("line 4", "THE “DISC” / “DISK”", "7 of 10"),
            ("line 6", "… MEANING OF STORY AND …", "5 of 10"),
            ("line 7", "… WEATHER BALLOONS …", "8 of 10"),
            ("line 8", "… LAND … CREWS.", "6 · 5 of 10"),
            ("line 9", "RAMEY  (TEMPLE)", "5 · 3 of 10")]
    y = 290
    s.text((1560, 250), "readers", F(SANS, 24), GOLD)
    for k, v, n in rows:
        s.text((97, y + 10), k, F(SANS, 26), GOLD); s.text((240, y), v, F(MONOB, 38), CREAM); s.text((1560, y + 8), n, F(SANS, 28), GREY); y += 74
    s.rule(y + 6, 97, 1820)
    s.text((97, y + 34), "Whole-word recount of Rudiak’s ten-reader table: 6+ agree on 28% of words, 8+ on 19%.", F(SANS, 28), GREY)
    s.text((97, y + 78), "The unclear first paragraph would decide correction vs. cover story — and it does not resolve.", F(SANS, 28), GREY)
    return s


def victims(sc):
    s = Slide(); s.kicker("ONE WORD, SEVEN LETTERS")
    s.image(f"{A}/line2_strip.png", (90, 245, 1830, 425), fit="contain"); s.label((94, 432), "line 2, straightened and joined: THE [? ? ? ? ? ? ?] OF THE WRECK YOU \u2026", 22, GREY)
    y = 500
    for w, who in [("VICTIMS", "6 of 10 readers, incl. Rudiak"), ("REMAINS", "Kirby 1999; Fishbine & McNeff 2003"),
                   ("FINDING", "Brad Sparks"), ("VIEWING", "suggested by several; none of the ten")]:
        s.text((97, y), w, F(MONOB, 64), CREAM); s.text((520, y + 22), who, F(SANS, 28), GREY); y += 90
    s.text((97, 890), "Rudiak (2016, unpublished): templates scored VICTIMS above its rivals and two nonsense controls.", F(SANS, 28), GOLD)
    return s


def calibration(sc):
    s = Slide(); s.kicker("CAN THE METHOD FIND WORDS NOBODY DISPUTES?")
    hdr = [(97, "known phrase"), (640, "whole phrase"), (840, "rank of the true phrase"), (1290, "beaten by misspellings"), (1640, "by random")]
    for x, t in hdr: s.text((x, 250), t, F(SANS, 24), GOLD)
    rows = [("FORT WORTH, TEX.", "10/10*", "183rd of 601", "132 of 300", "50 of 300"),
            ("WEATHER BALLOONS", "8/10", "153rd of 676", "144 of 375", "8 of 300"),
            ("OF THE WRECK", "9/10", "149th of 551", "115 of 250", "33 of 300"),
            ("FORWARDED", "6/10", "243rd of 526", "92 of 225", "150 of 300"),
            ("RAMEY", "5/10", "285th of 426", "65 of 125", "219 of 300")]
    y = 300
    for word, rd, rank, var, rnd in rows:
        s.text((97, y), word, F(MONOB, 40), CREAM); s.text((640, y + 6), rd, F(SANS, 30), GREY)
        s.text((840, y), rank, F(SERIF, 42), CREAM); s.text((1290, y + 2), var, F(SERIF, 38), GREY); s.text((1640, y + 2), rnd, F(SERIF, 38), GREY); y += 84
    s.rule(y + 4, 97, 1820)
    s.text((97, y + 30), "4 monospace fonts \u00b7 letter size and blur fitted on the other four phrases \u00b7 normalised cross-correlation along the straightened line \u00b7 *TEX. 9/10", F(SANS, 26), GREY)
    s.text((97, y + 70), "controls: every one-letter change + 300 strings of random letters with the same spacing", F(SANS, 26), GREY)
    s.text((97, y + 125), "Some random strings beat every true phrase. So do dozens of misspellings.", F(SERIF, 40), GOLD)
    return s


def synthetic(sc):
    s = Slide(); s.kicker("WHY IT FAILS: FAKE LINES WITH A KNOWN ANSWER")
    syn = results()["synthetic"]; res = syn["results"]; st = syn["settings"]
    s.text((97, 250), "true phrase ranked first", F(SANS, 24), GOLD)
    y = 300
    for key, cond, hi in [("A_sharp_grain", "sharp letters + real grain", True), ("B_blur_grain", "blurred letters + real grain", True),
                          ("C_blur_nograin", "blurred letters, no grain", False)]:
        r = res[key]
        s.text((97, y), cond, F(SERIF, 40), CREAM); s.text((600, y), f"{r['wins']} of {r['trials']}", F(SERIF, 44), GOLD if hi else GREY)
        s.text((780, y + 12), f"median rank {r['median_rank']:g}", F(SANS, 24), GREY); y += 80
    s.para((97, y + 20), f"{len(st['phrases'])} undisputed phrases \u00b7 four fonts searched, including the right one at the right size \u00b7 "
                         f"template blur matches the letters \u00b7 laid on four patches of blank film from the same negative \u00b7 letter "
                         f"strength measured on the real lines ({st['snr']:.2f} of the grain; the real scores imply {st['snr_from_calibration']:.2f})",
           F(SANS, 26), GREY, 52)
    s.label((1000, 250), "TURNING THE LETTERS UP", 24)
    s.image(f"{A}/synthetic_sweep.png", (990, 285, 1840, 760), fit="contain")
    first = {k: next(r["mult"] for r in syn[k]["rows"] if r["wins"]) for k in ("sweep_sharp", "sweep")}
    s.para((1000, 790), f"Sharp letters start winning at {first['sweep_sharp']:g}\u00d7 the real strength; blurred letters only at {first['sweep']:g}\u00d7.",
           F(SANS, 28), CREAM, 52)
    s.text((97, 880), "Blur plus grain defeats it \u2014 even with the right font.", F(SERIF, 52), GOLD)
    return s


def disputed(sc):
    s = Slide(); s.kicker("THE DISPUTED WORD, SAME TEST")
    s.image(f"{A}/line2_strip.png", (90, 240, 1830, 380), fit="contain")
    s.label((94, 388), "line 2, straightened and joined (positive)", 22, GREY)
    y = 450
    for w, r, hi in [("FINDING", "1st", False), ("REMAINS", "4th", False), ("SIGHTED", "9th", False), ("HOLDING", "28th", False),
                     ("VICTIMS", "31st", True), ("PACKING", "34th", False), ("VIEWING", "78th", False)]:
        col = CREAM if hi else GREY
        s.text((97, y), w, F(MONOB, 46), col); s.text((460, y + 4), r + " of 307", F(SERIF, 40), col); y += 64
    s.para((960, 450), "Best-fitting positions put OF THE WRECK and FORWARDED 5 letters apart; the memo has 17. So the word was searched along all of line 2.", F(SANS, 30), CREAM, 50)
    s.text((960, 640), "26 random strings outscore VICTIMS.", F(SERIF, 44), CREAM)
    s.para((960, 720), "The method fails on words nobody disputes, so this settles nothing, for or against VICTIMS.", F(SANS, 30), GOLD, 50)
    return s


def expect(sc):
    s = Slide(); s.kicker("HOURAN & RANDLE, 2002 — JOURNAL OF SCIENTIFIC EXPLORATION 16(1)")
    for i, (told, n, got) in enumerate([("told: Roswell", "N = 59", "→ crash words"), ("told: atomic-bomb test", "N = 58", "→ atomic words"),
                                        ("told: “a document”", "N = 59", "→ very few words")]):
        x0 = 90 + i * 590
        s.d.rectangle([P(x0), P(280), P(x0 + 560), P(560)], outline=GOLD, width=P(2))
        s.text((x0 + 30, 330), told, F(SERIF, 48), CREAM); s.text((x0 + 30, 420), n, F(SANS, 30), GREY)
        s.text((x0 + 30, 480), got, F(SANS, 30), GOLD)
    s.text((90, 660), "what people read depended on what they were told", F(SERIF, 64), CREAM)
    s.text((90, 760), "Yet FORT WORTH, STORY and WEATHER BALLOONS appeared in every group.", F(SANS, 30), GREY)
    s.text((90, 810), "The pixels underdetermine the words; context fills the gap.", F(SANS, 30), GREY)
    return s


def verdict(sc):
    s = Slide()
    bg = Image.open(f"{A}/straightened.png").convert("RGB")
    bg = bg.crop((0, int(bg.height * 0.34), bg.width, int(bg.height * 0.88)))      # lines 4-8
    bg = ImageOps.fit(bg, (W, H), Image.LANCZOS)
    bg = Image.blend(bg, Image.new("RGB", (W, H), BG), 0.82); s.im.paste(bg, (0, 0)); s.d = ImageDraw.Draw(s.im)
    s.d.rectangle([0, 0, W, P(12)], fill=GOLD); s.text((95, 1003), "THE FUTURE PAST", F(SANS, 27), GOLD)
    s.kicker("CAN AI READ THE RAMEY MEMO?"); s.head("NO.", None, 190); s.rule(540, 97, 700)
    ra = results()["reader_agreement"]
    y = 575
    for line in ["Opus 5.5: every file carries one negative’s grain, enlarged in software", "Opus 5.5: a straightened view of all nine lines",
                 VERDICT_SYNTH_LINE,
                 f"Jev: six of ten readers agree on {ra['summary']['6']['jev']} of {ra['n_positions']} word positions",
                 "VICTIMS remains a reading, not a fact"]:
        s.text((97, y), "—  " + line, F(SANS, 34), CREAM); y += 58
    s.text((97, 880), "$10,000 reward (2016): never publicly claimed", F(SERIF, 44), GOLD)
    return s


def end(sc):
    s = Slide()
    s.image(f"{A}/photo_panel.png", (825, 151, 1865, 929)); s.label((830, 80), "THE ACTUAL PHOTOGRAPH")
    s.kicker("THE RAMEY MEMO"); s.head("THE", "FUTURE PAST", 104); s.rule(691)
    s.label((97, 734), "image analysis: Anthropic’s Claude Opus 5.5", 28)
    s.label((97, 778), "word agreement and fact check: TypeSafe’s Jev 1.13", 28)
    s.label((97, 822), "scans: UTA Libraries", 28)
    s.label((97, 878), "methods and test results in the description", 28, GREY)
    s.text((827, 1002), "Archive: UTA Libraries • crop from the Ramey photograph", F(SANS, 23), GREY)
    return s


LAYOUTS = dict(title=title, tools=tools, files=files, exposures=exposures, scale=scale, denoise=denoise, dewarp=dewarp,
               straightened=straightened, estimate=estimate, readers=readers, victims=victims, calibration=calibration,
               synthetic=synthetic, disputed=disputed, expect=expect, verdict=verdict, end=end)

if __name__ == "__main__":
    for sc in SCENES:
        LAYOUTS[sc["layout"]](sc).save(sc["id"]); print("rendered", sc["id"])
