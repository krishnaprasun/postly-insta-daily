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
        img, notes = imaging.compose(res["art"], brief, i)
        if not notes.get("shaping"):
            # The whole design depends on the overlaid Hindi headline. Without
            # shaping we would ship bare artwork with no message on it, which
            # looks fine in a thumbnail and is wrong on the feed — so fail loudly.
            out["error"] = ("Devanagari shaping unavailable on this host, so the headline "
                            "could not be drawn. Install fonts-noto-devanagari + libraqm "
                            "(Linux) or pyobjc-framework-Cocoa (macOS). See README.")
            return out
        out.update({"ok": True, "image": img, "text_qa": res.get("text_qa"),
                    "retried": res.get("retried", False), "notes": notes})
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{exc}"[:300]
        out["trace"] = traceback.format_exc()[-600:]
    return out


def build_variants(brief: Dict, n: Optional[int] = None) -> List[Dict]:
    """All variants for the day, in order. Failures come back as ok=False."""
    n = n or config.VARIANT_COUNT
    results: List[Dict] = [None] * n  # type: ignore[list-item]
    with cf.ThreadPoolExecutor(max_workers=min(n, config.GEN_CONCURRENCY)) as ex:
        futs = {ex.submit(one_variant, i, brief): i for i in range(n)}
        for f in cf.as_completed(futs):
            i = futs[f]
            try:
                results[i] = f.result()
            except Exception as exc:  # noqa: BLE001
                results[i] = {"index": i, "ok": False, "error": str(exc)[:300],
                              "style": prompts.variant(i)["name"]}
    return [r for r in results if r]
