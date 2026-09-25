"""Jev layer: for one word position, is each pair of readers' readings the same word?

Text only: Jev never sees the scan. It judges whether two transcriptions name the same word, so reader agreement
can be counted by word rather than by exact spelling.
"""
import asyncio, itertools
from typesafe_sdk import AsyncTypeSafeClient, Noul
from common import info, err

MAX_CONCURRENT_REQUESTS = 8
INSTRUCTIONS = ("Ten people independently transcribed the same word position of a blurry 1947 typed teletype. "
                "Do the two readings {a} and {b} name the same word?")
CRITERIA = {"true": "Same word: they differ only by spelling variant (DISC/DISK), abbreviation (N MEX/NMEX), spacing, "
                    "punctuation, or an obvious typo of the same word.",
            "false": "Different words, even if they look alike or share letters (VICTIMS vs VIEWING), including singular "
                     "vs plural, different tense, or a fragment of a longer word."}


def pair_key(a, b): return " || ".join(sorted([a, b]))


async def _ask_slot(client, sem, slot_id, readings):
    ids = {w: f"r{i}" for i, w in enumerate(readings)}
    pairs = list(itertools.combinations(readings, 2))
    questions = {f"q{i}": Noul(instructions=INSTRUCTIONS.format(a=f"`readings.{ids[a]}`", b=f"`readings.{ids[b]}`"),
                               criteria=CRITERIA) for i, (a, b) in enumerate(pairs)}
    async with sem:
        try:
            r = await client.system_one(state={"readings": {v: w for w, v in ids.items()}}, questions=questions)
        except Exception as e:
            err(f"Jev request failed for {slot_id}: {e}"); raise
    info(f"Jev: {slot_id}, {len(pairs)} pairs")
    return {pair_key(a, b): float(r.nouls[f"q{i}"].noul) for i, (a, b) in enumerate(pairs)}


async def _ask_all(slots):
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with AsyncTypeSafeClient() as client:
        results = await asyncio.gather(*[_ask_slot(client, sem, sid, rd) for sid, rd in slots.items()])
    return dict(zip(slots, results))


def same_word_probabilities(slots):
    """slots: {slot_id: [distinct readings]} -> {slot_id: {pair_key: P(same word)}}. Slots with <2 readings are skipped."""
    todo = {sid: rd for sid, rd in slots.items() if len(rd) >= 2}
    return asyncio.run(_ask_all(todo)) if todo else {}
