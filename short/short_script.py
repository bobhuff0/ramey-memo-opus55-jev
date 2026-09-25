"""Beats of the YouTube Short. Every number comes from analysis/out/results.json (as fact-checked for the main video).

Each beat has a visual and caption chunks. A chunk is (spoken, display): `spoken` is what the narrator says and
is timed from ElevenLabs' character alignment; `display` is what appears on screen, with *starred* words in gold.
"""

BEATS = [
    dict(visual="hook", kicker="ROSWELL, 1947", chunks=[
        ("Can the newest A.I.", "CAN THE NEWEST *AI*"),
        ("read the Roswell memo?", "READ THE *ROSWELL MEMO?*"),
    ]),
    dict(visual="photo", kicker="THE RAMEY MEMO", chunks=[
        ("In 1947, General Roger Ramey", "IN 1947, GENERAL *ROGER RAMEY*"),
        ("held this typed message.", "HELD THIS *TYPED MESSAGE*"),
        ("For decades, people have argued", "FOR DECADES, PEOPLE HAVE *ARGUED*"),
        ("over what it says.", "OVER WHAT IT *SAYS*"),
    ]),
    dict(visual="tools", kicker="TWO OF THE NEWEST AIs", chunks=[
        ("We gave the high-resolution scans", "WE GAVE THE *HI-RES SCANS*"),
        ("to Claude Opus five point five,", "TO *CLAUDE OPUS 5.5*"),
        ("and TypeSafe's Jev.", "AND TYPESAFE'S *JEV*"),
    ]),
    dict(visual="readers", kicker="COUNTED BY JEV", chunks=[
        ("Ten human readers", "*TEN* HUMAN READERS"),
        ("agree on only five", "AGREE ON ONLY *FIVE*"),
        ("of its seventy-four words.", "OF ITS *74 WORDS*"),
    ]),
    dict(visual="rank", kicker="THE TEST THAT MATTERS", chunks=[
        ("Can the method even find", "CAN THE METHOD EVEN *FIND*"),
        ("words nobody disputes?", "WORDS *NOBODY DISPUTES?*"),
        ("Fort Worth, Texas ranked", "*FORT WORTH, TEX.* RANKED"),
        ("a hundred and eighty-third", "*183RD*"),
        ("out of six hundred and one.", "OUT OF *601*"),
        ("Some random strings", "SOME *RANDOM* STRINGS"),
        ("beat every true phrase.", "BEAT *EVERY* TRUE PHRASE"),
    ]),
    dict(visual="grain", kicker="WHY IT FAILS", chunks=[
        ("Why? Blurred letters,", "WHY? *BLURRED* LETTERS"),
        ("buried in film grain.", "BURIED IN *FILM GRAIN*"),
        ("Together, they defeat the method.", "TOGETHER, THEY *DEFEAT* IT"),
    ]),
    dict(visual="victims", kicker="THE DISPUTED WORD", chunks=[
        ("So does it say Victims?", "SO DOES IT SAY *VICTIMS?*"),
        ("Not from these scans.", "*NOT* FROM THESE SCANS"),
    ]),
    dict(visual="cta", kicker="THE FUTURE PAST", chunks=[
        ("The full investigation", "THE *FULL INVESTIGATION*"),
        ("is on the channel.", "IS ON THE *CHANNEL*"),
    ]),
]


def spoken_text():
    """The whole narration as one string, and the character span of every chunk inside it."""
    text, spans = "", []
    for b, beat in enumerate(BEATS):
        for c, (spoken, _) in enumerate(beat["chunks"]):
            if text:
                text += " "
            spans.append((b, c, len(text), len(text) + len(spoken)))
            text += spoken
    return text, spans
