"""Evidence for the Jev script check (s10): what the measurements and sources say, as short plain statements.
Numbers are formatted from results.json at run time; historical claims come from sources/factcheck.md; process
statements record how this analysis was run. Each scene gets only the topics its narration draws on."""
import os
import tifffile
from common import HERE, SCANS, WHOLE_FILE, half_path
from s6_calibration import DS

FACTCHECK_MD = os.path.join(HERE, "sources", "factcheck.md")
UTA_COLLECTION_FILES = 23
SCENE_TOPICS = {
    "01_title": ["history", "process"],
    "02_tools": ["process", "readers"],
    "03_files": ["files", "process"],
    "04_register": ["register"],
    "05_scale": ["sampling", "letters"],
    "06_denoise": ["process"],
    "07_dewarp": ["lines", "process"],
    "08_straight": ["lines", "readers", "process"],
    "09_readers": ["readers", "history"],
    "10_victims": ["readers", "history", "process"],
    "11_calib": ["calibration", "process"],
    "12_synth": ["synthetic", "process"],
    "13_disputed": ["disputed"],
    "14_expect": ["history"],
    "15_verdict": ["history", "process", "register", "sampling", "synthetic", "readers"],
    "16_end": ["process"],
}


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def history(R):
    return _read(FACTCHECK_MD)


def process(R):
    ra = R["reader_agreement"]
    return [
        "Claude Opus 5.5, Anthropic's model, wrote and ran all of the image-analysis code in this project (steps 1-8): "
        "inventory of the scans, registration of the brightness files, grain and sampling measurements, line tracing and "
        "straightening, joining the two halves, the filter comparison, the known-word calibration test, the synthetic "
        "known-answer test, and the figures. It rebuilt this analysis from the raw scan files.",
        "Jev (TypeSafe, model jev-1.13.0, TypeSafe's current flagship model) accepts text only: no image, audio or video input. "
        "It answers yes/no questions with a probability and multiple-choice questions with a probability for each option.",
        f"In step 9, Jev received only the readers' transcriptions. For each word position it judged every pair of distinct "
        f"readings: the probability that the two readings name the same word ({ra['n_pairs_judged']} pairs in all).",
        "In step 10, Jev received the narration sentences of this script and this evidence, and judged whether the evidence "
        "supports each sentence. Code flags any sentence that is not supported at confidence 0.8 or higher for human review.",
        "Every threshold is set in code, not by the models: readings are grouped as the same word at probability 0.5; a "
        "word position counts as agreed when at least 6 of 10 readers agree; the script check auto-accepts at confidence 0.8.",
        "Filters compared on straightened line 2: no filter, Gaussian smoothing (sigma 8 px), total-variation denoising, "
        "non-local means, median filtering (15 px) followed by Gaussian smoothing, and Gaussian smoothing at sigma 20 px, the "
        "size of the fitted letter blur. In every case the words remain blobs without legible letters.",
        "Each text line was traced by following its pattern of letters from column to column (seeded tracking of the "
        "vertical profile), then every line was resampled flat.",
        "In the joined, straightened view, stretches where the tracer could not separate lines that crowd together on the "
        "right half are left blank.",
        "Calibration design: each known phrase was rendered in four monospace fonts over a grid of letter pitches, letter "
        "heights and blurs, and slid along its straightened line, scored by normalized cross-correlation. The letter size "
        "and blur used to test each phrase were fitted on the other four phrases only (leave-one-out). Controls: every "
        "one-letter misspelling of the phrase, and 300 strings of random letters with the same spacing.",
        "Synthetic test design: a true phrase is typeset in Courier New Bold at the fitted size, laid on real blank film "
        "(patches of the same negative with no text), at the letter strength measured on the real lines, and ranked "
        "against its one-letter misspellings and random strings with the same method.",
        "Jev flagged the script's sentence about the sharp-letter synthetic test (answer: contradicts). Reviewing that flag, "
        "Opus 5.5 found that the sharp-letter condition had been searched with blurred templates. Re-run with templates as "
        "sharp as the letters, sharp letters came first in 4 of 20 trials instead of 0 of 20, which changed the conclusion "
        "from 'the grain alone defeats template matching' to 'the blur and the grain together defeat it'.",
        "The video description summarizes the methods, the test results, and Jev's reader-agreement table.",
        "The film is a negative: the typed letters appear lighter than the background.",
    ]


def files(R):
    names = sorted(os.listdir(SCANS)); total = sum(os.path.getsize(os.path.join(SCANS, f)) for f in names)
    with tifffile.TiffFile(half_path("L", "60B")) as t:
        dtype = t.pages[0].dtype
    return [
        f"UTA Libraries' Ramey memo high-resolution scan collection lists {UTA_COLLECTION_FILES} files; this analysis used "
        f"{len(names)} of them.",
        "Eight files are the left (L) and right (R) halves of the memo at four brightness levels each (Scanpro 55B, 60B, "
        "65B, 70B), with file names labelled '800 dpi 2x'; one file is the whole memo, named "
        f"'{WHOLE_FILE}' (labelled 1000 dpi).",
        f"The nine files total {total / 1e6:.0f} MB; each is {dtype.itemsize * 8}-bit grayscale.",
    ]


def register(R):
    g, h = R["register"], R["hdr"]
    right_shift = max(g["R"][e]["shift_max"] for e in ("55B", "65B", "70B"))
    right_ncc = [g["R"][e]["ncc_aligned_median"] for e in ("55B", "65B", "70B")]
    left_shift = max(g["L"][e]["shift_max"] for e in ("65B", "70B"))
    left_p = [(g["L"][e]["shift_p10"], g["L"][e]["shift_p90"]) for e in ("65B", "70B")]
    fits = {s: h[s]["fits"] for s in "LR"}
    return [
        f"Right half: the 55B, 65B and 70B files line up with the 60B reference file to within {right_shift:.2f} px, and "
        f"their grain correlates with the reference at {min(right_ncc):.2f} to {max(right_ncc):.2f}.",
        f"Left half: 55B lines up within {g['L']['55B']['shift_max']:.2f} px, but 65B and 70B are shifted against the "
        f"reference by up to {left_shift:.1f} px, and the shift varies across the frame (10th to 90th percentile "
        f"{min(p[0] for p in left_p):.1f} to {max(p[1] for p in left_p):.1f} px), so it bends rather than being one offset.",
        f"After point-by-point re-alignment, the blank-film grain of the left-half 65B and 70B files correlates with the "
        f"reference at {fits['L']['65B']['grain_ncc_blank_median']:.2f} and {fits['L']['70B']['grain_ncc_blank_median']:.2f}; "
        f"55B, the darkest file with {fits['L']['55B']['clipped_frac']:.0%} of its pixels clipped, at "
        f"{fits['L']['55B']['grain_ncc_blank_median']:.2f}. The same grain in every file means one negative.",
        f"Merging all four brightness files reduces the noise by {h['R']['noise_reduction_frac']:.1%} (right half) and "
        f"{h['L']['noise_reduction_frac']:.1%} (left half). Because the grain is shared, merging cannot add letters "
        "that no single file shows.",
    ]


def sampling(R):
    gs = {k: R["grain_sampling"][k] for k in ("L_60B", "R_60B")}
    rep = {gs[k]["sampling"]["x"]["pattern_repeat_px"] for k in gs}
    per = [gs[k]["sampling"]["x"]["period_px"] for k in gs]
    spacing = [gs[k]["sampling"]["source_sample_spacing_px"] for k in gs]
    enl = [gs[k]["enlargement_estimate"] for k in gs]
    return [
        "The half-memo file names say '2x'.",
        f"In the half-memo files, a resampling pattern with period {per[0]:.1f} px repeats exactly every "
        f"{'/'.join(str(r) for r in sorted(rep))} px in both directions (pattern autocorrelation "
        f"{gs['L_60B']['sampling']['x']['repeat_acf']:.2f}): the files were enlarged in software.",
        f"Real image detail stops at about one source sample every {min(min(spacing), min(enl)):.1f} to "
        f"{max(max(spacing), max(enl)):.1f} file pixels.",
        f"Grain clump size (half-strength width of the grain autocorrelation): {gs['L_60B']['grain_fwhm_px']:.1f} px "
        f"(left half), {gs['R_60B']['grain_fwhm_px']:.1f} px (right half).",
    ]


def letters(R):
    c = R["calibration"]
    fit_p = {k: v["pitch"] * DS for k, v in c["fits"].items()}
    loo_p = sorted({t["geometry"]["pitch"] * DS for t in c["tests"].values()})
    sig = sorted({t["geometry"]["blur"] * DS for t in c["tests"].values()})
    fwhm = [2.3548 * s for s in sig]
    return [
        "Letter pitch (the width of one typed character) fitted on the known words, in full-resolution file pixels: "
        + ", ".join(f"{k} {v}" for k, v in fit_p.items())
        + f"; the leave-one-out tests used {', '.join(str(p) for p in loo_p)} px.",
        f"Best-fitting letter blur: Gaussian sigma {'/'.join(f'{s:g}' for s in sig)} full-resolution px, a half-strength "
        f"width (FWHM) of about {fwhm[0]:.0f} px, which is {fwhm[0] / max(loo_p):.2f} to {fwhm[0] / min(loo_p):.2f} of a "
        "letter pitch.",
        f"That gives about {min(loo_p) / 3.6:.0f} real samples across one letter.",
        "A blur that wide smears the small strokes that distinguish similar letters, such as E from F.",
    ]


def lines(R):
    L, Rh = R["lines"]["L"], R["lines"]["R"]
    drift = {s: max(max(l["knots_y"]) - min(l["knots_y"]) for l in R["lines"][s]["lines"]) for s in "LR"}
    with tifffile.TiffFile(half_path("L", "60B")) as t:
        width_L = t.pages[0].shape[1]
    hv = R["halves"]; overlap = width_L - hv["offset_dx_median"]
    length = {s: {l["line"]: l["x1"] - l["x0"] for l in R["lines"][s]["lines"]} for s in "LR"}
    full_R = max(length["R"].values())
    left_only = sorted(set(length["L"]) - set(length["R"]))
    early = [n for n, v in length["R"].items() if 0.4 * full_R < v < 0.9 * full_R]
    short_R = [n for n, v in length["R"].items() if v <= 0.4 * full_R]
    ids_R = [l["line"] for l in Rh["lines"]]
    gaps_R = {f"{a}-{b}": round(g) for a, b, g in zip(ids_R, ids_R[1:], Rh["spacing_px"])}
    return [
        f"Traced text lines: left half lines {[l['line'] for l in L['lines']]}, right half lines "
        f"{ids_R}; together, all nine lines of the memo.",
        f"Line {', '.join(map(str, left_only))} is traced only on the left half: it is the short line of the memo.",
        f"Right-half spacing between neighbouring lines (px): {gaps_R}; median {Rh['spacing_median']:.0f}.",
        f"On the right half, lines {', '.join(map(str, early))} stop early (traced lengths "
        f"{', '.join(str(length['R'][n]) for n in early)} px, against {full_R} px for a full line), where the lines crowd "
        "together and the tracer could not keep them apart; the joined view leaves those stretches blank.",
        f"Line {', '.join(map(str, short_R))}, on the right half, is short: {', '.join(str(length['R'][n]) for n in short_R)} px "
        f"traced, against {full_R} px for a full line.",
        f"The paper is curled and tilted: the largest vertical drift of one traced line across its half-scan is "
        f"{drift['L']:.0f} px (left half) and {drift['R']:.0f} px (right half); the median spacing between lines is "
        f"{L['spacing_median']:.0f} px (left) and {Rh['spacing_median']:.0f} px (right).",
        f"The two halves overlap by about {overlap:.0f} px. In {hv['n_matched']} of {len(hv['patches'])} test patches, the "
        f"grain of the left and right halves matches at a correlation of {hv['ncc_range'][0]:.2f} to {hv['ncc_range'][1]:.2f}; "
        f"the best non-matching position scores at most {hv['second_best_max']:.2f}: both halves are the same piece of film.",
    ]


def calibration(R):
    c = R["calibration"]; st = c["settings"]
    out = [f"Fonts: {', '.join(st['fonts'])}. Grid: {len(st['pitches_full_res'])} letter pitches, "
           f"{len(st['cap_ratios'])} letter heights, {len(st['blurs_sigma_full_res'])} blurs. Random strings per phrase: "
           f"{st['n_random']}."]
    for k, t in c["tests"].items():
        out.append(f"{k}: the true phrase ranked {t['rank']} of {t['n_candidates']} candidates; one-letter misspellings "
                   f"scoring higher: {t['variants_above']} of {t['n_variants']}; random strings scoring higher: "
                   f"{t['randoms_above']} of {t['n_random']}.")
    return out


def disputed(R):
    d = R["calibration"]["disputed"]
    ranks = sorted(d["ranks"].items(), key=lambda kv: kv[1])
    return [
        f"The method's best positions for OF THE WRECK and FORWARDED on line 2 are {d['found_char_gap']:.0f} letters "
        f"apart; in the memo they are {d['expected_char_gap']} letters apart. So the disputed word was searched along "
        "the whole of line 2.",
        f"Disputed-word search: {d['n_candidates']} candidates (the proposed words plus random strings). Ranks: "
        + ", ".join(f"{w} {r}" for w, r in ranks)
        + f". Random strings scoring above VICTIMS: {d['random_above_victims']}.",
    ]


def synthetic(R):
    s = R["synthetic"]; st = s["settings"]; res = s["results"]
    out = [f"Letter strength measured on the real lines: signal/grain {st['snr']:.2f}. The letter strength implied by "
           f"the true phrases' real calibration scores: {st['snr_from_calibration']:.2f} (range "
           f"{st['snr_from_calibration_range'][0]:.2f} to {st['snr_from_calibration_range'][1]:.2f}), i.e. no stronger."]
    if "search_fonts" in st:
        out.append(f"Template search in the synthetic test: all four fonts ({', '.join(st['search_fonts'])}) at letter pitches "
                   f"{', '.join(str(p) for p in st['search_pitches_full_res'])} full-resolution px; template blur "
                   f"{st['template_blur']}. The right font ({st['font']}) at the right size ({st['pitch_full_res']} px) "
                   "is among the templates searched.")
    out.append(f"Sharp letters were planted with a Gaussian blur of sigma {st['sharp_sigma_full_res']:.1f} full-resolution px "
               f"(nearly sharp); blurred letters with sigma {st['blur_sigma_full_res']:.0f} px, the blur fitted on the real memo.")
    names = {"A_sharp_grain": "Sharp letters on real grain", "B_blur_grain": "Blurred letters (as measured) on real grain",
             "C_blur_nograin": "Blurred letters with no grain"}
    for k, v in res.items():
        film = ("no film: the grain is removed" if k.endswith("nograin")
                else f"{len({r['patch'] for r in v['rows']})} patches of blank film")
        out.append(f"{names.get(k, k)}: the true phrase ranked first in {v['wins']} of {v['trials']} trials "
                   f"(median rank {v['median_rank']:g}); phrases: {', '.join(st['phrases'])}; {film}.")
    for key, label in (("sweep", "blurred letters"), ("sweep_sharp", "sharp letters")):
        if key in s:
            sw = s[key]
            out.append(f"Letter-strength sweep, {label}, {sw['phrase']} on {len(sw['rows'][0]['ranks'])} patches, rank of "
                       f"{sw['n']}: " + "; ".join(f"{r['mult']:g}x real strength: ranks {r['ranks']}, first in {r['wins']}"
                                                  for r in sw["rows"]) + ".")
    return out


READER_NAMES = {"RP": "Roswell Photointerpretation Team", "M": "Neil Morris", "R": "David Rudiak", "B": "Don Burleson",
                "C": "Tom Carey", "S": "Brad Sparks", "F": "Glenn Fishbine", "MN": "William McNeff", "BK": "Bob Koford",
                "DJ": "David Jones"}


def _names(codes): return ", ".join(READER_NAMES.get(c, c) for c in codes)


def readers(R):
    ra = R["reader_agreement"]; sm = ra["summary"]
    unanimous = [f"line {p['line']} {p['word']}" for p in ra["positions"] if p["n_readers"] == 10]
    merged = [f"line {p['line']}: {' = '.join(p['variants'])} ({p['n_readers']} readers)" for p in ra["positions"]
              if len(p["variants"]) > 1]
    def at(line, word):
        return next(p for p in ra["positions"] if str(p["line"]) == str(line) and word in p["variants"])
    def others(p): return "; ".join(f"{o['reading']} ({_names(o['readers'])})" for o in p["non_matching"])
    v, rm, dk = at(2, "VICTIMS"), at(9, "RAMEY"), at(4, "DISC")
    w7, b7 = at(7, "WEATHER"), at(7, "BALLOONS")
    lens = sorted({len(w) for w in v["variants"] + [o["reading"] for o in v["non_matching"]]})
    n_line9 = sum(1 for p in ra["positions"] if str(p["line"]) == "9")
    sens = ra["sensitivity_same_threshold"]
    agreed = {}
    for p in ra["positions"]:
        if p["status"] == "agreed": agreed.setdefault(str(p["line"]), []).append(p["word"])
    return [
        "Words agreed by 6 or more of 10 readers, in order, by line: "
        + "; ".join(f"line {ln}: {' '.join(ws)}" for ln, ws in agreed.items()) + ".",
        f"David Rudiak's compilation lists ten readers' transcriptions of the memo, side by side, across {ra['n_positions']} "
        "word positions.",
        f"Jev judged {ra['n_pairs_judged']} pairs of readings: every pair of distinct readings at each of the "
        f"{ra['n_positions_with_pairs']} positions with two or more distinct readings.",
        "Word positions where at least N of 10 readers agree, counting readings Jev judged to be the same word: "
        + "; ".join(f"{k} or more: {v['jev']} of {v['of']}" for k, v in sm.items()) + ".",
        f"Unanimous positions (10 of 10): {', '.join(unanimous)}.",
        f"Jev merged these spellings as the same word: {'; '.join(merged)}.",
        f"Line 2, the word before OF THE WRECK (every reading has {'/'.join(map(str, lens))} letters): VICTIMS, "
        f"{v['n_readers']} readers ({_names(v['readers'])}), {v['status']} at the 6-reader threshold; other readings: "
        f"{others(v)}.",
        f"Line 4, THE \"DISC\": DISK or DISC, {dk['n_readers']} readers ({_names(dk['readers'])}); other reading: {others(dk)}.",
        f"Line 7: WEATHER, {w7['n_readers']} readers; BALLOONS, {b7['n_readers']} readers.",
        f"Line 9 has {n_line9} word position, the signature: RAMEY, {rm['n_readers']} readers ({_names(rm['readers'])}), "
        f"{rm['status']} at the 6-reader threshold; other reading: {others(rm)}.",
        "Same-word threshold sensitivity (positions with 6 or more readers / unanimous): "
        + "; ".join(f"threshold {t}: {x['6']['jev']} / {x['10']['jev']}" for t, x in sens.items())
        + ". The other agreement levels do not change.",
    ]


TOPICS = dict(history=history, process=process, files=files, register=register, sampling=sampling, letters=letters,
              lines=lines, calibration=calibration, disputed=disputed, synthetic=synthetic, readers=readers)


def scene_evidence(scene_id, R):
    """{topic: statements or source text} for one scene."""
    return {t: TOPICS[t](R) for t in SCENE_TOPICS[scene_id]}
