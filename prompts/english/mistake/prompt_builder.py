"""
Builds the HTML-generation prompt for the mistake card.
Maps subject name → mistakes file, loads base_template, fills variables.
Format is chosen deterministically per chapter using subject-driven pools.
Mistakes list is shuffled randomly so each generation picks a different mistake.
"""
import pathlib
import random

_BASE = pathlib.Path(__file__).parent

# Subject name keywords → subject file name (order matters — more specific first)
_SUBJECT_MAP = [
    ("physics",   "physics"),
    ("chemistry", "physics"),
    ("math",      "physics"),
    ("maths",     "physics"),
    ("biology",   "biology"),
    ("botany",    "biology"),
    ("zoology",   "biology"),
    ("accounts",  "commerce"),
    ("economics", "commerce"),
    ("business",  "commerce"),
    ("history",           "history"),
    ("political science", "political_science"),
    ("polity",            "political_science"),
    ("civics",            "political_science"),
    ("rajniti",           "political_science"),
    ("geography",         "geography"),
    ("bhugol",            "geography"),
    ("english",   "english_subject"),
    ("hindi",     "hindi_subject"),
    ("sanskrit",  "sanskrit"),
]

# hindi_subject always uses format 5 (pure Devanagari layout)
# commerce always uses format 4 (table layout)
# everything else picks randomly from [1, 2, 3]
_FORMAT_POOLS = {
    "hindi_subject": [5],
    "commerce":      [4],
}


def _resolve_subject_file(subject_name: str) -> tuple[pathlib.Path, str]:
    """Returns (path_to_subject_file, subject_key)."""
    sl = subject_name.lower()
    for keyword, fname in _SUBJECT_MAP:
        if keyword in sl:
            p = _BASE / "subjects" / f"{fname}.txt"
            if p.exists():
                return p, fname
    return _BASE / "subjects" / "physics.txt", "physics"


def _pick_format(subject_key: str, force: int | None = None) -> int:
    """Randomly picks a format number from the subject's pool, or [1,2,3] by default."""
    if force is not None:
        return force  # user explicitly selected — always respect it
    pool = _FORMAT_POOLS.get(subject_key, [1, 2, 3])
    return random.choice(pool)


def _clean_chapter(chapter: str) -> str:
    """Strip trailing part suffixes like '- II', '- III' from chapter names."""
    import re
    return re.sub(r'\s*-\s*(I{1,3}|IV|V?I{0,3})\s*$', '', (chapter or "").strip(), flags=re.IGNORECASE).strip()


def build_mistake_html_prompt(
    subject: str,
    chapter: str,
    class_level: str,
    board: str,
    chapter_context: str = "",
    stream: str = "",
    force_format: int | None = None,
) -> tuple[str, int]:
    """Returns (prompt_text, format_number_used)."""
    chapter = _clean_chapter(chapter)
    base_tmpl = (_BASE / "base_template.txt").read_text(encoding="utf-8")
    subject_file, subject_key = _resolve_subject_file(subject)
    raw_mistakes = subject_file.read_text(encoding="utf-8").strip()

    # Shuffle mistake blocks so LLM picks a different one each generation
    blocks = [b.strip() for b in raw_mistakes.split("---") if b.strip()]
    random.shuffle(blocks)
    mistakes_list = "\n\n---\n\n".join(blocks)

    format_hint = _pick_format(subject_key, force=force_format)
    ctx = chapter_context or "[No syllabus data — use your knowledge of common board exam mistakes for this chapter]"
    format_instruction = (
        f"IMPORTANT: You MUST use the reference example layout above (Format {format_hint}). "
        f"Recreate that exact layout structure with fresh content for this chapter. Do not switch to a different layout."
    )

    if subject_key == "hindi_subject":
        tone_instruction = "PURE HINDI — DEVANAGARI ONLY (mandatory for Hindi subject)"
        tone_details = (
            "- Every single word in the card must be in Devanagari Hindi script — no English, no Hinglish\n"
            "- Card title, subtitle, labels, values, notes, rule box — ALL in Devanagari\n"
            "- Wrong/right labels: use ✗ गलत / ✓ सही\n"
            "- Rule box starts with: 💡 नियम:\n"
            "- Tone: warm and direct — use आप/आपका, समझो, देखो, याद रखो\n"
            "- Example 5 shows the correct style — follow it exactly"
        )
    else:
        tone_instruction = "HINGLISH ONLY — STRICT (mandatory for all non-Hindi subjects)"
        tone_details = (
            "- Day-to-day conversation language: Hinglish Roman script — NO Devanagari anywhere in the card\n"
            "- Technical / subject terms: ALWAYS in English (Molarity, Sign Convention, T-account, Osmosis, Hegemony, etc.) — never translate them\n"
            "- Respectful and warm — use \"samjho\", \"dekho\", \"yaad rakho\" — NOT \"kar dete ho\", \"bhool gaye\", \"galti karte ho\"\n"
            "- Card title: observational/warm (e.g. \"Sign convention — yahan marks jaate hain!\"), NOT accusatory (\"Kyun bhoolte ho?\")\n"
            "- Wrong/right labels: pick from \"❌ Galat\" / \"✅ Sahi\" OR \"90% students ne yeh likha\" / \"Sahi jawab\"\n"
            "- Rule box: one simple, memorable trick in Hinglish — no paragraph, just one punchline\n"
            "- If the mistakes list contains Devanagari text, translate it to Hinglish Roman script before using it"
        )

    format_file = _BASE / "formats" / f"format_{format_hint}.html"
    format_example = format_file.read_text(encoding="utf-8").strip() if format_file.exists() else ""

    result = base_tmpl
    result = result.replace("{subject}", subject)
    result = result.replace("{chapter}", chapter)
    result = result.replace("{class_level}", class_level)
    result = result.replace("{board}", board)
    result = result.replace("{stream}", stream)
    result = result.replace("{chapter_context}", ctx)
    result = result.replace("{mistakes_list}", mistakes_list)
    result = result.replace("{format_example}", format_example)
    result = result.replace("{format_instruction}", format_instruction)
    result = result.replace("{tone_instruction}", tone_instruction)
    result = result.replace("{tone_instruction_details}", tone_details)
    return result, format_hint
