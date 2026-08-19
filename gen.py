"""
Generate the day's variants: artwork from the image model, text composited on top.

Each variant is an independent art direction (prompts.VARIANTS), generated in
parallel. Every variant is checked for stray text before it is accepted, because
the one thing the model must not do is draw its own Devanagari.
"""
from __future__ import annotations

import concurrent.futures as cf
import traceback
from typing import Dict, List, Optional

import config
import imaging
import llm
import prompts

TEXT_QA_PROMPT = (
    "Does this image contain any readable letters, words or numbers in any script "
    "(Devanagari, Latin, Arabic, or other), including watermarks, signatures or logos with "
    "lettering? Decorative patterns that are not letters do not count. "
    "Answer with exactly one word: YES or NO.")


def _has_text(art: bytes) -> Optional[bool]:
    """True/False if the vision check ran, None if it could not run."""
    if not getattr(llm, "ENABLED", False):
        return None
    try:
        ans = llm.vision_text(TEXT_QA_PROMPT, art, timeout=40).strip().upper()
        if ans.startswith("YES"):
            return True
        if ans.startswith("NO"):
            return False
        return None
    except Exception as exc:  # noqa: BLE001
        print(f"[gen] text QA failed: {exc}", flush=True)
        return None


def _art(prompt: str, system: str, attempts: int = 2) -> Dict:
    """Generate artwork, retrying once if the model drew text.

    If the text check still trips on the last attempt the artwork is returned
    anyway, flagged. The check is a vision model and it false-positives on
    ornamental motifs; dropping the variant outright would lose the whole day's
    option over a maybe. The review page shows the flag so a human decides.
    """
    last_err = None
    last_art = None
    for a in range(attempts):
        try:
            p = prompt if a == 0 else (
                prompt + "\n\nPREVIOUS ATTEMPT FAILED because it contained written text. "
                "Produce the same artwork with ABSOLUTELY NO letters, words, numbers or "
                "lettered logos anywhere in the frame.")
            art = llm.image_gen(system, p, timeout=config.GEN_TIMEOUT)
            last_art = art
            has_text = _has_text(art)
            if has_text:
                last_err = "text check tripped"
                continue
            return {"art": art, "text_qa": has_text, "retried": a > 0}
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)[:200]
    if last_art is not None:
        return {"art": last_art, "text_qa": True, "retried": True, "warn": last_err}
    return {"art": None, "error": last_err or "unknown"}


LIKENESS_QA = ("Who is the person depicted in this image? If they are a recognisable public "
               "figure, answer with their name only. If the person is not recognisable as any "
               "specific real person, answer exactly: UNKNOWN")


def _likeness_ok(art: bytes, name: str) -> Optional[bool]:
    """Does the portrait actually read as the intended person?

    A wrong or generic face on a national figure's tribute is the most visible
    failure this system can produce, and it is invisible in a thumbnail. The
    check is advisory — it flags for the review page, it does not drop the
    variant, because a vision model's recall on lesser-known figures is itself
    unreliable.
    """
    if not (name and getattr(llm, "ENABLED", False)):
        return None
    try:
        ans = llm.vision_text(LIKENESS_QA, art, timeout=40).strip()
        if ans.upper().startswith("UNKNOWN"):
            return False
        want = {w for w in name.lower().replace(".", " ").split() if len(w) > 2}
        got = {w for w in ans.lower().replace(".", " ").split() if len(w) > 2}
        return bool(want & got)
    except Exception as exc:  # noqa: BLE001
        print(f"[gen] likeness QA failed: {exc}", flush=True)
        return None


def one_variant(i: int, brief: Dict) -> Dict:
    """Build variant i end to end."""
    v = prompts.variant(i)
    out = {"index": i, "style": v["name"], "ok": False}
    try:
        prompt = prompts.build_prompt(brief, v)
        system = prompts.system_for(v, allow_likeness=bool(brief.get("show_person")))
        out["prompt"] = prompt
        res = _art(prompt, system)
        if not res.get("art"):
            out["error"] = res.get("error", "generation failed")
            return out
        if brief.get("show_person"):
            out["likeness_ok"] = _likeness_ok(res["art"], brief.get("likeness_of", ""))
        img, notes = imaging.compose(res["art"], brief, i)
        if not notes.get("shaping"):
            # The whole design depends on the overlaid Hindi headline. Without
            # shaping we would ship bare artwork with no message on it, which
            # looks fine in a thumbnail and is wrong on the feed — so fail loudly.
            out["error"] = ("Devanagari shaping unavailable on this host, so the headline "
                            "could not be drawn. Install fonts-noto-devanagari + libraqm "
                            "(Linux) or pyobjc-framework-Cocoa (macOS). See README.")
            return out
        notes["likeness_ok"] = out.get("likeness_ok")
        out.update({"ok": True, "image": img, "text_qa": res.get("text_qa"),
                    "retried": res.get("retried", False), "notes": notes})
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{exc}"[:300]
        out["trace"] = traceback.format_exc()[-600:]
    return out


def build_variants(brief: Dict, n: Optional[int] = None,
                   indices: Optional[List[int]] = None,
                   on_result=None) -> List[Dict]:
    """Build variants for one brief. Failures come back as ok=False.

    `indices` picks WHICH variants to build. The index selects the theme, so a
    quiet day splitting five slots across two briefs must pass explicit,
    non-overlapping indices — otherwise both briefs render on themes 0 and 1 and
    the day's options collide.

    `on_result(result)` fires as each variant finishes, so the caller can save it
    straight away. Returning only at the end meant the review page showed nothing
    for two minutes and then everything at once.
    """
    idx = list(indices) if indices is not None else list(range(n or config.VARIANT_COUNT))
    out: Dict[int, Dict] = {}
    with cf.ThreadPoolExecutor(max_workers=max(1, min(len(idx), config.GEN_CONCURRENCY))) as ex:
        futs = {ex.submit(one_variant, i, brief): i for i in idx}
        for f in cf.as_completed(futs):
            i = futs[f]
            try:
                out[i] = f.result()
            except Exception as exc:  # noqa: BLE001
                out[i] = {"index": i, "ok": False, "error": str(exc)[:300],
                          "style": prompts.variant(i)["name"]}
            if on_result:
                try:
                    on_result(out[i])
                except Exception as exc:  # noqa: BLE001
                    print(f"[gen] on_result failed: {exc}", flush=True)
    return [out[i] for i in idx if i in out]
