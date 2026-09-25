# Narration script — Roswell’s Ramey Memo: Can the Latest AI Read It? Claude Opus 5.5 + TypeSafe Jev

Runtime 10:11. Scene starts are from the rendered file.

## 00:00  01_title — Can the latest AI read the Ramey memo?
*Visual: title*

- [00:00] On July 8, 1947, Fort Worth Star-Telegram photographer J. Bond Johnson caught General Roger Ramey holding a typed message, probably a teletype, at the press session where Roswell's flying disc became a weather balloon.
- [00:14] For almost forty years, researchers have tried to read that slip of paper.
- [00:18] Now it has been through the latest in publicly available AI: Anthropic's Claude Opus 5.5, and Jev, from TypeSafe.
- [00:26] Opus 5.5 rebuilt the image analysis from the raw scans. Jev, a new kind of model that answers narrow questions with probabilities, judged the words.
- [00:37] The question is simple: can AI read it?

## 00:40  02_tools — Two AI systems, two jobs
*Visual: tools*

- [00:40] Each system had a different job.
- [00:42] Claude Opus 5.5 wrote and ran every step of the image analysis: aligning the scans, measuring the film grain, straightening the typed lines, and testing whether letter matching can find words nobody disputes.
- [00:56] Jev, version 1.13, cannot see images. It reads text and returns a probability for each question, so it got the questions about words.
- [01:05] When ten researchers transcribe the same spot, do two readings name the same word, like DISC spelled with a C or with a K, or different words, like VICTIMS and VIEWING?
- [01:16] And is each factual sentence in this script supported by the measurements?
- [01:20] In every case, code, not the models, sets the thresholds and keeps the score.

## 01:25  03_files — What the scans contain
*Visual: files*

- [01:25] UTA posts twenty-three scan files. Claude Opus 5.5 worked from nine of them.
- [01:32] Left and right halves of the memo, labelled eight hundred dots per inch, at four brightness levels each, plus one whole-memo file labelled a thousand.
- [01:40] The film is a negative, so the typed letters show up light. Before reading anything, Opus 5.5 measured what the files actually contain.

## 01:49  04_register
*Visual: exposures*

- [01:50] On the right half, the four brightness files line up to a sixth of a pixel, and their grain correlates at point eight to point nine.
- [01:56] On the left half, two of the files had shifted against the others by up to thirty-five pixels, and the shift bends across the frame.
- [02:04] Opus 5.5 mapped that shift point by point and undid it. The grain of the two shifted files then matched at almost point nine: one negative, with the same grain in every file.
- [02:16] So merging all four files removes only five to eight percent of the noise. It adds no new letters.

## 02:22  05_scale — The numbers that govern everything
*Visual: scale*

- [02:23] Here are the numbers that govern everything.
- [02:25] The file names say 2x. The pixels say more: a tell-tale pattern repeats every eleven pixels, and the real detail stops at about one sample every three and a half file pixels. The files were enlarged in software.
- [02:39] A grain clump is about sixteen pixels across. A typed letter is about two hundred and twenty.
- [02:45] And the letters are soft. Fitting the known words, the best match came with a blur about forty-seven pixels wide, a fifth of a letter.
- [02:53] That smears the strokes that tell an E from an F. Then the grain covers what is left.

## 02:59  06_denoise
*Visual: denoise*

- [02:59] Opus 5.5 tried Gaussian smoothing, total-variation denoising, non-local means, median filtering, and smoothing at the size of the measured blur.
- [03:09] Every method produced the same result: words as blobs.
- [03:12] Light smoothing leaves the grain. Heavy smoothing takes the strokes with it.

## 03:17  07_dewarp — Straightening the lines
*Visual: dewarp*

- [03:17] What could be fixed was the geometry.
- [03:19] The paper is curled and tilted. Across a half-scan, one typed line drifts up or down by as much as three hundred and forty pixels, more than half the gap between lines.
- [03:30] Opus 5.5 traced each line by following its pattern of letters from column to column, and resampled every line flat.
- [03:38] Then it joined the two halves where they overlap, about twenty-one hundred pixels. In six of six patches the grain matches at point nine two or better: both halves are the same piece of film.

## 03:50  08_straight
*Visual: straightened*

- [03:50] This is the cleanest view of the memo that Opus 5.5 could get from these scans: nine lines, straightened and joined.
- [03:58] On the right, where three lines crowd together, the tracer could not keep them apart, and those stretches are left blank.
- [04:04] Word lengths and spacing are clear.
- [04:07] A seven-letter word before OF THE WRECK on line two.
- [04:10] The short line: AT FORT WORTH, TEX.
- [04:12] WEATHER BALLOONS on line seven, and a short signature on line nine.
- [04:16] Letters, though, are still blobs.

## 04:18  09_readers — What ten readers agree on, counted by Jev
*Visual: readers*

- [04:19] So what does the memo probably say?
- [04:21] David Rudiak has compiled ten readers' transcriptions, side by side, across seventy-four word positions.
- [04:28] Jev compared every pair of readings at every position, five hundred and eleven pairs, and judged whether each pair names the same word.
- [04:37] Only five word positions are unanimous: OF and THE on line two, and AT, FORT and WORTH on line three.
- [04:44] Fourteen reach eight of ten readers. Twenty-two reach six, under thirty percent of the memo.
- [04:49] Jev merged the C and K spellings of DISC, so seven readers see a quoted disc. RAMEY has five readers and TEMPLE three, so at a six-reader threshold, the signature does not match.
- [05:01] Moving Jev's same-word threshold anywhere from point three to point nine changes these counts by at most one.
- [05:08] What survives is a skeleton: a wreck, something forwarded to Fort Worth, and weather balloons. Whether the message was a correction or a cover story is exactly what the unclear words would decide, and they don't.

## 05:21  10_victims — Victims, and one word's evidence
*Visual: victims*

- [05:22] The fight is over one word. Seven letters, before OF THE WRECK.
- [05:26] VICTIMS, say six of the ten readers, among them David Rudiak, who has worked on this memo for more than twenty-five years.
- [05:34] REMAINS, say two others. FINDING, says Brad Sparks. VIEWING has been suggested too.
- [05:41] By Jev's count, VICTIMS just clears the six-reader bar. But agreement among readers is not evidence from the pixels.
- [05:48] In 2016, Rudiak reported an unpublished test: letter templates scored VICTIMS above its rivals and two nonsense words, and about as well as FORT WORTH and WEATHER BALLOONS.
- [06:00] Opus 5.5 asked the question that has to come first: can the method find words that nobody disputes?

## 06:07  11_calib — The calibration test
*Visual: calibration*

- [06:08] Here is the test.
- [06:09] Opus 5.5 rendered five undisputed phrases in four monospace fonts, over a grid of letter sizes, spacings and blurs, and slid each one along its straightened line.
- [06:21] The letter size and blur were fitted on the other four phrases, so no phrase was tested on settings tuned to itself.
- [06:27] Then it scored every one-letter misspelling of each phrase, and three hundred strings of random letters with the same spacing.
- [06:35] FORT WORTH, TEX. came a hundred and eighty-third out of six hundred and one. A hundred and thirty-two misspellings beat it, and so did fifty random strings.
- [06:44] WEATHER BALLOONS came a hundred and fifty-third. OF THE WRECK, a hundred and forty-ninth. RAMEY lost to two hundred and nineteen of the three hundred random strings.
- [06:54] Some random strings beat every true phrase: eight of three hundred for WEATHER BALLOONS, and up to two hundred and nineteen for RAMEY. The method cannot reliably pick real words from random letters, let alone one letter from another.

## 07:09  12_synth — Why the method fails
*Visual: synthetic*

- [07:09] Why does it fail? Opus 5.5 built fake memo lines where the answer is known: a true phrase, typeset, laid on real blank film from the same negative, at the letter strength measured on the real lines.
- [07:22] Five phrases on four patches of film make twenty trials, and the search included the right font at the right size.
- [07:29] With sharp letters, the true phrase usually made the top ten, and came first in four of twenty trials.
- [07:35] Blurred the way the memo's letters are, it came first in none of twenty.
- [07:38] Take the grain away, and even the blurred phrase comes first, five times out of five.
- [07:43] Turn the letters up: sharp letters start winning at one and a half times the real strength, blurred letters only at six times.
- [07:50] It takes the blur and the grain together to defeat the method, and the memo has both. Its own scores suggest its letters are, if anything, a little weaker than these tests assumed.

## 08:01  13_disputed — The disputed word
*Visual: disputed*

- [08:01] And the disputed word itself?
- [08:03] The method could not even find where the known words sit: its best positions put OF THE WRECK and FORWARDED five letters apart, when the memo has seventeen between them. So Opus 5.5 searched for the disputed word along the whole of line two.
- [08:18] FINDING came first out of three hundred and seven. REMAINS came fourth. VICTIMS came thirty-first, behind twenty-six random strings.
- [08:27] Because the method fails on words nobody disputes, this settles nothing, for or against VICTIMS.
- [08:33] Any letter ranking on this word, from anyone, should be asked to pass the known-word test first.

## 08:38  14_expect — How expectations shape a reading
*Visual: expect*

- [08:38] This matters because of a 2002 experiment by James Houran and Kevin Randle.
- [08:43] A hundred and seventy-six volunteers tried to read the memo. One group was told it was about Roswell, one about atomic-bomb testing, and one only that it was a document.
- [08:53] The Roswell group found crash words, the atomic group found atomic words, and the third group read very little.
- [08:59] Yet FORT WORTH, STORY, and WEATHER BALLOONS turned up in every group.
- [09:05] The pixels underdetermine the words, and context fills the gap.

## 09:09  15_verdict — What remains unresolved
*Visual: verdict*

- [09:09] So, can AI read the Ramey memo?
- [09:12] No. Not even the latest AI, not from these scans, and not by matching letter templates.
- [09:17] What Claude Opus 5.5 added: evidence that every file carries one negative's grain and was enlarged in software, a straightened view of all nine lines, and a known-answer test showing that the memo's blur and grain together defeat template matching, even with the right font.
- [09:35] What Jev added: a word-by-word count of where ten human readers truly agree, and a check of every factual sentence in this script against the measurements.
- [09:44] One of its flags sent Opus 5.5 back to the sharp-letter test, and fixing that test changed a conclusion.
- [09:51] The word skeleton survives. VICTIMS remains a reading, not a fact.
- [09:56] And the ten-thousand-dollar reward, offered in 2016 for a definitive reading, has never been publicly claimed.

## 10:04  16_end
*Visual: end*

- [10:04] The methods, the test results, and Jev's agreement table are summarized in the description.
- [10:09] This has been The Future Past.
