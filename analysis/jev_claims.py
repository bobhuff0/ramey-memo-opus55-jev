"""Jev layer for the script check: is each narration sentence a checkable claim, and does the evidence support it?

Text only. One request per scene: the scene's evidence and its sentences are the state, with two questions per
sentence (a Noul for 'checkable', a Choice for how the evidence relates to it).
"""
import asyncio
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul
from common import info, err

JEV_MODEL = "jev-1.13.0"
MAX_CONCURRENT_REQUESTS = 6
CHECKABLE = ("Does `sentences.{sid}` assert at least one specific, checkable fact, such as a number, count, measurement, "
             "date, name, quotation, or test result?")
CHECKABLE_CRITERIA = {"true": "It states a specific fact that the evidence could confirm or refute.",
                      "false": "It is a question, a transition, a summary judgment, or a statement of what comes next, "
                               "with no specific fact."}
RELATION = ("How does `evidence` relate to the factual content of `sentences.{sid}`? The sentence is spoken narration: "
            "numbers are written as words and rounded (for example 'about sixteen' for 15.7, 'a fifth' for 0.21, "
            "'point nine two or better' for a minimum of 0.92), and such rounding is fine.")
RELATION_CRITERIA = {"supports": "The evidence states or directly implies every specific fact in the sentence.",
                     "contradicts": "The evidence makes at least one specific fact in the sentence false.",
                     "says_nothing": "The evidence does not address at least one specific fact in the sentence, "
                                     "either way."}
PROMPT_VERSION = "v1"


async def _ask_scene(client, sem, scene_id, evidence, sentences):
    sids = {f"s{i}": s for i, s in enumerate(sentences)}
    questions = {}
    for sid in sids:
        questions[f"checkable_{sid}"] = Noul(instructions=CHECKABLE.format(sid=sid), criteria=CHECKABLE_CRITERIA)
        questions[f"relation_{sid}"] = Choice(instructions=RELATION.format(sid=sid), criteria=RELATION_CRITERIA)
    async with sem:
        try:
            r = await client.system_one(state={"evidence": evidence, "sentences": sids}, questions=questions,
                                        model=JEV_MODEL)
        except Exception as e:
            err(f"Jev request failed for {scene_id}: {e}"); raise
    out = []
    for sid, text in sids.items():
        rel = r.choices[f"relation_{sid}"]
        out.append(dict(sentence=text, p_checkable=float(r.nouls[f"checkable_{sid}"].noul), relation=rel.choice,
                        confidence=float(rel.confidence),
                        probabilities={k: float(v) for k, v in dict(rel.probabilities).items()}))
    info(f"Jev: {scene_id}, {len(sids)} sentences, model {r.model}")
    return dict(model=r.model, sentences=out)


async def _ask_all(jobs):
    sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    async with AsyncTypeSafeClient() as client:
        res = await asyncio.gather(*[_ask_scene(client, sem, sid, ev, sents) for sid, (ev, sents) in jobs.items()])
    return dict(zip(jobs, res))


def check_scenes(jobs):
    """jobs: {scene_id: (evidence, [sentences])} -> {scene_id: {model, sentences: [per-sentence answers]}}."""
    return asyncio.run(_ask_all(jobs)) if jobs else {}
