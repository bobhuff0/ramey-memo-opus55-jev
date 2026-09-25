# Roswell's Ramey Memo: Can the Latest AI Read It? (Claude Opus 5.5 + TypeSafe Jev)

This is the code behind a 10-minute documentary video that re-analyses the "Ramey memo": the paper held by
Gen. Roger Ramey in the July 1947 Fort Worth Star-Telegram photographs. It works from the nine high-resolution
TIFF scans posted by the University of Texas at Arlington (UTA) Libraries.

- **Claude Opus 5.5** (Anthropic) wrote and ran every step of the image analysis. That covers registration, grain and sampling
  measurements, the HDR merge, line tracing and straightening, template-matching calibration, and a known-answer synthetic test.
- **Jev 1.13** (TypeSafe, text only) did two jobs. It judged which of ten published readers' transcriptions name the same word
  at each position, and it checked every factual sentence of the narration against the measured results.
- Code, not the models, sets every threshold and keeps every count.

**Bottom line:** at the strength and blur measured on these scans, whole-phrase template matching cannot pick
the true text out of the film grain. Only 5 of 74 word positions are read the same way by all ten readers.

## Layout

| path | what it is |
|---|---|
| `analysis/s1_register.py` … `s8_figures.py` | Image analysis, steps 1–8 (Opus 5.5). All numbers go to `analysis/out/results.json`. |
| `analysis/s9_reader_agreement.py`, `jev_same_word.py`, `agreement.py` | Step 9: Jev reader agreement. |
| `analysis/s10_script_check.py`, `jev_claims.py`, `evidence.py` | Step 10: Jev fact-checks the narration against the results. |
| `analysis/out/` | The results the video was built from: `results.json`, Jev's raw answers, and both Jev reports. |
| `analysis/sources/factcheck.md` | Sources for the historical claims in the narration. |
| `build/script.py` | The narration, scene by scene. |
| `build/render.py`, `revoice.py`, `encode.py` | Slides, ElevenLabs narration with captions, and the final MP4. |
| `build/verify_audio.py`, `build/qc/audio_artifacts.py` | Audio QC: transcription check, and a scan for breaths or clipped syllables at sentence edges. |
| `publish/` | The title, description, comparison description, captions and script as published. |

## Not included

- **The scans.** Download the nine TIFFs from UTA Libraries' Ramey memo collection. By default they're read from
  `../UT Images` next to the repo folder; set `RAMEY_SCANS=/path/to/folder` to use another location.
- **Figures made from the scans** (`build/assets/`, `analysis/out/fig/`). `s8_figures.py` regenerates them,
  apart from `build/assets/photo_panel.png`, which is a crop of the UTA photograph that you supply.
- **David Rudiak's reader table** (`analysis/sources/rudiak_slot_matrix_latest.json`), which step 9 reads. It
  is his compilation of ten readers' transcriptions. Jev's answers built from it are in `analysis/out/jev_same_word.json`.
- **Fonts.** Put the Liberation fonts (Mono Regular/Bold, Sans Regular/Bold, Serif Regular) from
  <https://github.com/liberationfonts/liberation-fonts> in `build/fonts/`.
- The narration audio, caches and the MP4 itself.

## Run

API keys are read from system environment variables: `TYPESAFE_API_KEY` for Jev, `ELEVENLABS_API_KEY` for the
narration, and `OPENAI_API_KEY` for caption timing and audio QC.

```zsh
pip install -r requirements.txt
cd analysis
python3 s1_register.py && python3 s2_grain_sampling.py && python3 s3_hdr.py && python3 s4_lines.py
python3 s5_halves_pitch.py && python3 s6_calibration.py && python3 s7_synthetic.py && python3 s8_figures.py
python3 s9_reader_agreement.py && python3 s10_script_check.py
cd ../build
python3 render.py && python3 revoice.py --provider elevenlabs --per-sentence && python3 verify_audio.py
python3 qc/audio_artifacts.py
```

`revoice.py` requests one clip per sentence from ElevenLabs (`eleven_multilingual_v2`, voice Andrew
`gUABw7pXQjhjt0kNFBTF`, fixed seed), passing the neighbouring sentences as context. With that context the model
sometimes leaves a breath or the first sound of the next sentence after the last word. `tidy_clip` drops those
edge bursts, caps pauses inside a sentence at 0.7 s and fades each clip in and out; `--no-tidy` turns it off.
`build/qc/spec_0059_before.png` and `spec_0059_after.png` show one such join, before and after.

## Key results (`analysis/out/results.json`)

- The right-half brightness files align to within 0.15 px. On the left half, the 65B and 70B files are shifted by up to 35 px
  and were re-aligned with dense optical flow. Merging exposures removes 5–8% of the noise.
- Real sample spacing is 3.4–3.6 file pixels (the files are software enlargements). A grain clump is about 16 px across.
- Letter pitch is about 216–224 px, and the fitted blur is sigma 20 px.
- The two halves overlap by about 2,100 px, and the grain matches in 6 of 6 patches.
- **Known-word test:** true phrases rank 149th–285th of 426–676 candidates, and some random strings beat every one.
- **Known-answer test** at the measured letter strength, with four fonts searched and template blur matching the letters:
  - sharp letters plus grain: the true phrase ranks first in 4 of 20 trials;
  - blurred letters plus grain: 0 of 20;
  - blurred letters without grain: 5 of 5.

  Sharp letters start winning at 1.5× the real strength, blurred letters only at 6×. It takes the blur and the grain together to defeat the method.
- **Disputed word:** FINDING ranks 1st, REMAINS 4th and VICTIMS 31st of 307 candidates.
- **Jev reader agreement:** 511 pairs of readings judged. Of 74 positions, 5 are unanimous, 14 reach 8 of 10 readers,
  and 22 reach 6. Any same-word threshold from 0.3 to 0.9 changes those counts by at most one.
- **Jev script check:** of 84 narration sentences, 66 are checkable claims. Jev verified 46, and the other 20 were
  reviewed against the results (notes in `analysis/out/script_check.md`). Reviewing one flag found that the sharp-letter
  test had been searched with blurred templates; fixing it changed a conclusion.

## License

Code: MIT (see `LICENSE`). Images, transcriptions and texts quoted from third parties belong to their owners.
