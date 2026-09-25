# Jev script check

Model: `jev-1.13.0`. Each narration sentence was judged against the evidence for its scene (topics per scene in `evidence.py`). Checkable at P >= 0.5; auto-accepted when Jev answers 'supports' at confidence >= 0.8; everything else goes to review.

Sentences: 84 · checkable: 66 · verified by Jev: 46 · sent to review: 20

The evidence is the project's own record (measured results, the source fact-check, and a description of the process), so this checks that the narration matches the record; it does not re-measure anything.

## Sent to review (reviewer: Claude Opus 5.5, against results.json and factcheck.md)

- **01_title** — For almost forty years, researchers have tried to read that slip of paper.  
  Jev: supports (0.79); supports 0.86, contradicts 0.12, says nothing 0.02  
  Review: Confirmed: factcheck.md 2, Brad Sparks made out words in the mid-1980s; about forty years by 2026.
- **02_tools** — Claude Opus 5.5 wrote and ran every step of the image analysis: aligning the scans, measuring the film grain, straightening the typed lines, and testing whether letter matching can find words nobody disputes.  
  Jev: supports (0.76); supports 0.84, contradicts 0.13, says nothing 0.03  
  Review: Confirmed: steps s1-s8 were written and run in this session by Claude Opus 5.5.
- **03_files** — The film is a negative, so the typed letters show up light. Before reading anything, Opus 5.5 measured what the files actually contain.  
  Jev: supports (0.79); supports 0.86, contradicts 0.03, says nothing 0.11  
  Review: Confirmed: letters are lighter than the background in every file; steps s1-s5 measured the files before any reading.
- **04_register** — On the right half, the four brightness files line up to a sixth of a pixel, and their grain correlates at point eight to point nine.  
  Jev: supports (0.68); supports 0.78, contradicts 0.18, says nothing 0.04  
  Review: Confirmed: max shift 0.153 px (under 1/6 px = 0.167); grain NCC 0.80-0.92.
- **04_register** — Opus 5.5 mapped that shift point by point and undid it. The grain of the two shifted files then matched at almost point nine: one negative, with the same grain in every file.  
  Jev: supports (0.28); supports 0.52, contradicts 0.11, says nothing 0.37  
  Review: Confirmed: after dense re-alignment, left 65B 0.89 and 70B 0.87 ('almost point nine'); 55B, 21% clipped, 0.74; right half 0.80-0.92.
- **07_dewarp** — The paper is curled and tilted. Across a half-scan, one typed line drifts up or down by as much as three hundred and forty pixels, more than half the gap between lines.  
  Jev: supports (0.76); supports 0.83, contradicts 0.16, says nothing 0.01  
  Review: Confirmed: right line 5 drifts 339 px; right median spacing 547 px (ratio 0.62).
- **08_straight** — This is the cleanest view of the memo that Opus 5.5 could get from these scans: nine lines, straightened and joined.  
  Jev: supports (0.64); supports 0.76, contradicts 0.02, says nothing 0.22  
  Review: Judgment, worded as Opus 5.5's result; nine lines confirmed (left 1-8, right 1,2,4-9).
- **08_straight** — The short line: AT FORT WORTH, TEX.  
  Jev: supports (0.59); supports 0.73, contradicts 0.21, says nothing 0.06  
  Review: Confirmed: line 3 is traced only on the left half; agreed words AT FORT WORTH TEX.
- **09_readers** — Fourteen reach eight of ten readers. Twenty-two reach six, under thirty percent of the memo.  
  Jev: supports (0.78); supports 0.86, contradicts 0.14, says nothing 0.00  
  Review: Confirmed: 8+ readers at 14 of 74 positions; 6+ at 22 of 74 = 29.7%.
- **09_readers** — Jev merged the C and K spellings of DISC, so seven readers see a quoted disc. RAMEY has five readers and TEMPLE three, so at a six-reader threshold, the signature does not match.  
  Jev: contradicts (0.35); supports 0.43, contradicts 0.56, says nothing 0.01  
  Review: Confirmed: line 4 DISK = DISC, 7 readers; factcheck.md 8b 'THE + quoted disc 7/10'; RAMEY 5, TEMPLE 3.
- **09_readers** — Moving Jev's same-word threshold anywhere from point three to point nine changes these counts by at most one.  
  Jev: supports (0.40); supports 0.60, contradicts 0.39, says nothing 0.01  
  Review: Confirmed: 6+ gives 22/22/21/21 and 10/10 gives 6/5/5/5 at 0.3/0.5/0.7/0.9; others unchanged.
- **09_readers** — What survives is a skeleton: a wreck, something forwarded to Fort Worth, and weather balloons. Whether the message was a correction or a cover story is exactly what the unclear words would decide, and they don't.  
  Jev: supports (0.45); supports 0.63, contradicts 0.03, says nothing 0.34  
  Review: Interpretation of the agreed words: WRECK, FORWARDED, AT FORT WORTH TEX, WEATHER BALLOONS; the first paragraph's content words fall below 6 readers.
- **10_victims** — VICTIMS, say six of the ten readers, among them David Rudiak, who has worked on this memo for more than twenty-five years.  
  Jev: supports (0.31); supports 0.53, contradicts 0.45, says nothing 0.02  
  Review: Confirmed: VICTIMS readers include David Rudiak (R); factcheck.md 3: memo work since about 1999-2000, so more than twenty-five years.
- **10_victims** — REMAINS, say two others. FINDING, says Brad Sparks. VIEWING has been suggested too.  
  Jev: supports (0.68); supports 0.78, contradicts 0.18, says nothing 0.04  
  Review: Confirmed: REMAINS (Fishbine, McNeff), FINDING (Sparks); VIEWING suggested (factcheck.md 4d).
- **10_victims** — By Jev's count, VICTIMS just clears the six-reader bar. But agreement among readers is not evidence from the pixels.  
  Jev: supports (0.70); supports 0.80, contradicts 0.10, says nothing 0.10  
  Review: Confirmed: 6 readers equals the 6-reader threshold; second sentence is a caution, not a claim.
- **11_calib** — Opus 5.5 rendered five undisputed phrases in four monospace fonts, over a grid of letter sizes, spacings and blurs, and slid each one along its straightened line.  
  Jev: supports (0.70); supports 0.80, contradicts 0.19, says nothing 0.01  
  Review: Confirmed: 4 fonts; 9 pitches, 3 letter heights, 5 blurs; slid along each straightened line.
- **11_calib** — Some random strings beat every true phrase: eight of three hundred for WEATHER BALLOONS, and up to two hundred and nineteen for RAMEY. The method cannot reliably pick real words from random letters, let alone one letter from another.  
  Jev: supports (0.30); supports 0.53, contradicts 0.44, says nothing 0.03  
  Review: Confirmed: random strings above the truth range from 8/300 (WEATHER BALLOONS) to 219/300 (RAMEY); 65-144 one-letter misspellings beat each phrase.
- **12_synth** — Five phrases on four patches of film make twenty trials, and the search included the right font at the right size.  
  Jev: supports (0.40); supports 0.60, contradicts 0.38, says nothing 0.02  
  Review: Confirmed: A and B each 5 phrases x 4 patches = 20 trials; Courier New Bold at 216 px in the search.
- **13_disputed** — FINDING came first out of three hundred and seven. REMAINS came fourth. VICTIMS came thirty-first, behind twenty-six random strings.  
  Jev: supports (0.68); supports 0.79, contradicts 0.20, says nothing 0.01  
  Review: Confirmed: FINDING 1, REMAINS 4, VICTIMS 31 of 307; 26 random strings above VICTIMS.
- **15_verdict** — No. Not even the latest AI, not from these scans, and not by matching letter templates.  
  Jev: supports (0.56); supports 0.70, contradicts 0.24, says nothing 0.06  
  Review: Conclusion from the calibration (true phrases 149th-285th) and synthetic (blurred: 0 of 20) results.

## Every sentence

| scene | P(checkable) | Jev | conf | action | sentence |
|---|---|---|---|---|---|
| 01_title | 0.99 | supports | 0.98 | verified | On July 8, 1947, Fort Worth Star-Telegram photographer J. Bond Johnson caught General Roger Ramey holding a typed message, probably a teletype, at the press session where Roswell's flying disc became a weather balloon. |
| 01_title | 0.95 | supports | 0.79 | review | For almost forty years, researchers have tried to read that slip of paper. |
| 01_title | 0.95 | supports | 0.87 | verified | Now it has been through the latest in publicly available AI: Anthropic's Claude Opus 5.5, and Jev, from TypeSafe. |
| 01_title | 0.93 | supports | 0.94 | verified | Opus 5.5 rebuilt the image analysis from the raw scans. Jev, a new kind of model that answers narrow questions with probabilities, judged the words. |
| 01_title | 0.04 | says_nothing | 0.25 | not a claim | The question is simple: can AI read it? |
| 02_tools | 0.22 | supports | 0.81 | not a claim | Each system had a different job. |
| 02_tools | 0.97 | supports | 0.76 | review | Claude Opus 5.5 wrote and ran every step of the image analysis: aligning the scans, measuring the film grain, straightening the typed lines, and testing whether letter matching can find words nobody disputes. |
| 02_tools | 0.98 | supports | 0.94 | verified | Jev, version 1.13, cannot see images. It reads text and returns a probability for each question, so it got the questions about words. |
| 02_tools | 0.39 | contradicts | 0.25 | not a claim | When ten researchers transcribe the same spot, do two readings name the same word, like DISC spelled with a C or with a K, or different words, like VICTIMS and VIEWING? |
| 02_tools | 0.06 | supports | 0.91 | not a claim | And is each factual sentence in this script supported by the measurements? |
| 02_tools | 0.66 | supports | 0.98 | verified | In every case, code, not the models, sets the thresholds and keeps the score. |
| 03_files | 0.99 | supports | 0.83 | verified | UTA posts twenty-three scan files. Claude Opus 5.5 worked from nine of them. |
| 03_files | 0.99 | supports | 0.99 | verified | Left and right halves of the memo, labelled eight hundred dots per inch, at four brightness levels each, plus one whole-memo file labelled a thousand. |
| 03_files | 0.93 | supports | 0.79 | review | The film is a negative, so the typed letters show up light. Before reading anything, Opus 5.5 measured what the files actually contain. |
| 04_register | 0.98 | supports | 0.68 | review | On the right half, the four brightness files line up to a sixth of a pixel, and their grain correlates at point eight to point nine. |
| 04_register | 0.98 | supports | 0.96 | verified | On the left half, two of the files had shifted against the others by up to thirty-five pixels, and the shift bends across the frame. |
| 04_register | 0.96 | supports | 0.28 | review | Opus 5.5 mapped that shift point by point and undid it. The grain of the two shifted files then matched at almost point nine: one negative, with the same grain in every file. |
| 04_register | 0.97 | supports | 0.98 | verified | So merging all four files removes only five to eight percent of the noise. It adds no new letters. |
| 05_scale | 0.02 | supports | 0.34 | not a claim | Here are the numbers that govern everything. |
| 05_scale | 0.98 | supports | 0.99 | verified | The file names say 2x. The pixels say more: a tell-tale pattern repeats every eleven pixels, and the real detail stops at about one sample every three and a half file pixels. The files were enlarged in software. |
| 05_scale | 0.98 | supports | 0.97 | verified | A grain clump is about sixteen pixels across. A typed letter is about two hundred and twenty. |
| 05_scale | 0.98 | supports | 0.99 | verified | And the letters are soft. Fitting the known words, the best match came with a blur about forty-seven pixels wide, a fifth of a letter. |
| 05_scale | 0.33 | supports | 0.64 | not a claim | That smears the strokes that tell an E from an F. Then the grain covers what is left. |
| 06_denoise | 0.96 | supports | 0.92 | verified | Opus 5.5 tried Gaussian smoothing, total-variation denoising, non-local means, median filtering, and smoothing at the size of the measured blur. |
| 06_denoise | 0.91 | supports | 0.92 | verified | Every method produced the same result: words as blobs. |
| 06_denoise | 0.24 | says_nothing | 0.36 | not a claim | Light smoothing leaves the grain. Heavy smoothing takes the strokes with it. |
| 07_dewarp | 0.06 | supports | 0.36 | not a claim | What could be fixed was the geometry. |
| 07_dewarp | 0.98 | supports | 0.76 | review | The paper is curled and tilted. Across a half-scan, one typed line drifts up or down by as much as three hundred and forty pixels, more than half the gap between lines. |
| 07_dewarp | 0.93 | supports | 0.99 | verified | Opus 5.5 traced each line by following its pattern of letters from column to column, and resampled every line flat. |
| 07_dewarp | 0.99 | supports | 0.99 | verified | Then it joined the two halves where they overlap, about twenty-one hundred pixels. In six of six patches the grain matches at point nine two or better: both halves are the same piece of film. |
| 08_straight | 0.97 | supports | 0.64 | review | This is the cleanest view of the memo that Opus 5.5 could get from these scans: nine lines, straightened and joined. |
| 08_straight | 0.97 | supports | 1.00 | verified | On the right, where three lines crowd together, the tracer could not keep them apart, and those stretches are left blank. |
| 08_straight | 0.32 | contradicts | 0.21 | not a claim | Word lengths and spacing are clear. |
| 08_straight | 0.98 | supports | 0.98 | verified | A seven-letter word before OF THE WRECK on line two. |
| 08_straight | 0.97 | supports | 0.59 | review | The short line: AT FORT WORTH, TEX. |
| 08_straight | 0.98 | supports | 0.90 | verified | WEATHER BALLOONS on line seven, and a short signature on line nine. |
| 08_straight | 0.69 | supports | 0.98 | verified | Letters, though, are still blobs. |
| 09_readers | 0.02 | says_nothing | 0.78 | not a claim | So what does the memo probably say? |
| 09_readers | 0.99 | supports | 0.99 | verified | David Rudiak has compiled ten readers' transcriptions, side by side, across seventy-four word positions. |
| 09_readers | 0.99 | supports | 0.89 | verified | Jev compared every pair of readings at every position, five hundred and eleven pairs, and judged whether each pair names the same word. |
| 09_readers | 0.99 | supports | 0.80 | verified | Only five word positions are unanimous: OF and THE on line two, and AT, FORT and WORTH on line three. |
| 09_readers | 0.99 | supports | 0.78 | review | Fourteen reach eight of ten readers. Twenty-two reach six, under thirty percent of the memo. |
| 09_readers | 0.98 | contradicts | 0.35 | review | Jev merged the C and K spellings of DISC, so seven readers see a quoted disc. RAMEY has five readers and TEMPLE three, so at a six-reader threshold, the signature does not match. |
| 09_readers | 0.94 | supports | 0.40 | review | Moving Jev's same-word threshold anywhere from point three to point nine changes these counts by at most one. |
| 09_readers | 0.63 | supports | 0.45 | review | What survives is a skeleton: a wreck, something forwarded to Fort Worth, and weather balloons. Whether the message was a correction or a cover story is exactly what the unclear words would decide, and they don't. |
| 10_victims | 0.95 | supports | 0.87 | verified | The fight is over one word. Seven letters, before OF THE WRECK. |
| 10_victims | 0.99 | supports | 0.31 | review | VICTIMS, say six of the ten readers, among them David Rudiak, who has worked on this memo for more than twenty-five years. |
| 10_victims | 0.98 | supports | 0.68 | review | REMAINS, say two others. FINDING, says Brad Sparks. VIEWING has been suggested too. |
| 10_victims | 0.91 | supports | 0.70 | review | By Jev's count, VICTIMS just clears the six-reader bar. But agreement among readers is not evidence from the pixels. |
| 10_victims | 0.99 | supports | 0.92 | verified | In 2016, Rudiak reported an unpublished test: letter templates scored VICTIMS above its rivals and two nonsense words, and about as well as FORT WORTH and WEATHER BALLOONS. |
| 10_victims | 0.17 | supports | 0.39 | not a claim | Opus 5.5 asked the question that has to come first: can the method find words that nobody disputes? |
| 11_calib | 0.04 | says_nothing | 0.43 | not a claim | Here is the test. |
| 11_calib | 0.98 | supports | 0.70 | review | Opus 5.5 rendered five undisputed phrases in four monospace fonts, over a grid of letter sizes, spacings and blurs, and slid each one along its straightened line. |
| 11_calib | 0.95 | supports | 0.91 | verified | The letter size and blur were fitted on the other four phrases, so no phrase was tested on settings tuned to itself. |
| 11_calib | 0.97 | supports | 0.94 | verified | Then it scored every one-letter misspelling of each phrase, and three hundred strings of random letters with the same spacing. |
| 11_calib | 0.99 | supports | 0.97 | verified | FORT WORTH, TEX. came a hundred and eighty-third out of six hundred and one. A hundred and thirty-two misspellings beat it, and so did fifty random strings. |
| 11_calib | 0.99 | supports | 0.83 | verified | WEATHER BALLOONS came a hundred and fifty-third. OF THE WRECK, a hundred and forty-ninth. RAMEY lost to two hundred and nineteen of the three hundred random strings. |
| 11_calib | 0.98 | supports | 0.30 | review | Some random strings beat every true phrase: eight of three hundred for WEATHER BALLOONS, and up to two hundred and nineteen for RAMEY. The method cannot reliably pick real words from random letters, let alone one letter from another. |
| 12_synth | 0.92 | supports | 0.98 | verified | Why does it fail? Opus 5.5 built fake memo lines where the answer is known: a true phrase, typeset, laid on real blank film from the same negative, at the letter strength measured on the real lines. |
| 12_synth | 0.98 | supports | 0.40 | review | Five phrases on four patches of film make twenty trials, and the search included the right font at the right size. |
| 12_synth | 0.99 | supports | 0.93 | verified | With sharp letters, the true phrase usually made the top ten, and came first in four of twenty trials. |
| 12_synth | 0.98 | supports | 0.98 | verified | Blurred the way the memo's letters are, it came first in none of twenty. |
| 12_synth | 0.98 | supports | 0.99 | verified | Take the grain away, and even the blurred phrase comes first, five times out of five. |
| 12_synth | 0.98 | supports | 0.96 | verified | Turn the letters up: sharp letters start winning at one and a half times the real strength, blurred letters only at six times. |
| 12_synth | 0.74 | supports | 0.96 | verified | It takes the blur and the grain together to defeat the method, and the memo has both. Its own scores suggest its letters are, if anything, a little weaker than these tests assumed. |
| 13_disputed | 0.03 | says_nothing | 0.91 | not a claim | And the disputed word itself? |
| 13_disputed | 0.98 | supports | 0.93 | verified | The method could not even find where the known words sit: its best positions put OF THE WRECK and FORWARDED five letters apart, when the memo has seventeen between them. So Opus 5.5 searched for the disputed word along the whole of line two. |
| 13_disputed | 0.98 | supports | 0.68 | review | FINDING came first out of three hundred and seven. REMAINS came fourth. VICTIMS came thirty-first, behind twenty-six random strings. |
| 13_disputed | 0.20 | supports | 0.57 | not a claim | Because the method fails on words nobody disputes, this settles nothing, for or against VICTIMS. |
| 13_disputed | 0.07 | supports | 0.40 | not a claim | Any letter ranking on this word, from anyone, should be asked to pass the known-word test first. |
| 14_expect | 0.92 | supports | 0.99 | verified | This matters because of a 2002 experiment by James Houran and Kevin Randle. |
| 14_expect | 0.99 | supports | 0.86 | verified | A hundred and seventy-six volunteers tried to read the memo. One group was told it was about Roswell, one about atomic-bomb testing, and one only that it was a document. |
| 14_expect | 0.88 | supports | 0.91 | verified | The Roswell group found crash words, the atomic group found atomic words, and the third group read very little. |
| 14_expect | 0.96 | supports | 0.98 | verified | Yet FORT WORTH, STORY, and WEATHER BALLOONS turned up in every group. |
| 14_expect | 0.07 | says_nothing | 0.33 | not a claim | The pixels underdetermine the words, and context fills the gap. |
| 15_verdict | 0.04 | says_nothing | 0.43 | not a claim | So, can AI read the Ramey memo? |
| 15_verdict | 0.59 | supports | 0.56 | review | No. Not even the latest AI, not from these scans, and not by matching letter templates. |
| 15_verdict | 0.97 | supports | 0.85 | verified | What Claude Opus 5.5 added: evidence that every file carries one negative's grain and was enlarged in software, a straightened view of all nine lines, and a known-answer test showing that the memo's blur and grain together defeat template matching, even with the right font. |
| 15_verdict | 0.83 | supports | 0.86 | verified | What Jev added: a word-by-word count of where ten human readers truly agree, and a check of every factual sentence in this script against the measurements. |
| 15_verdict | 0.74 | supports | 0.85 | verified | One of its flags sent Opus 5.5 back to the sharp-letter test, and fixing that test changed a conclusion. |
| 15_verdict | 0.73 | supports | 0.89 | verified | The word skeleton survives. VICTIMS remains a reading, not a fact. |
| 15_verdict | 0.98 | supports | 0.95 | verified | And the ten-thousand-dollar reward, offered in 2016 for a definitive reading, has never been publicly claimed. |
| 16_end | 0.81 | supports | 0.99 | verified | The methods, the test results, and Jev's agreement table are summarized in the description. |
| 16_end | 0.15 | says_nothing | 0.87 | not a claim | This has been The Future Past. |
