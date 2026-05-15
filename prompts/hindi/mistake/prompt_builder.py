"""
Hindi medium mistake card prompt builder.
All cards generated in pure Devanagari Hindi with Hindi technical terminology.
"""
import pathlib
import random

_BASE = pathlib.Path(__file__).parent

# Subject name keywords → subject file name (order matters — more specific first)
_SUBJECT_MAP = [
    ("physics",   "physics"),
    ("chemistry", "physics"),
    ("भौतिक",     "physics"),
    ("रसायन",     "physics"),
    ("math",      "physics"),
    ("maths",     "physics"),
    ("गणित",      "physics"),
    ("biology",   "biology"),
    ("botany",    "biology"),
    ("zoology",   "biology"),
    ("जीव",       "biology"),
    ("वनस्पति",   "biology"),
    ("accounts",  "commerce"),
    ("economics", "commerce"),
    ("business",  "commerce"),
    ("लेखा",      "commerce"),
    ("वाणिज्य",   "commerce"),
    ("history",           "history"),
    ("इतिहास",            "history"),
    ("political science", "political_science"),
    ("polity",            "political_science"),
    ("civics",            "political_science"),
    ("rajniti",           "political_science"),
    ("राजनीति",           "political_science"),
    ("geography",         "geography"),
    ("bhugol",            "geography"),
    ("भूगोल",             "geography"),
    ("english",   "english_subject"),
    ("अंग्रेज़ी",  "english_subject"),
    ("hindi",     "hindi_subject"),
    ("हिंदी",     "hindi_subject"),
    ("sanskrit",  "sanskrit"),
    ("संस्कृत",   "sanskrit"),
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
    # fallback to commerce.txt for hindi medium since it has Hindi terminology
    fallback = _BASE / "subjects" / "physics.txt"
    return fallback, "physics"


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
    ctx = chapter_context or "[पाठ्यक्रम डेटा उपलब्ध नहीं — इस अध्याय की सामान्य बोर्ड परीक्षा गलतियों का उपयोग करें]"
    format_instruction = (
        f"महत्त्वपूर्ण: ऊपर दिए गए संदर्भ उदाहरण का layout (Format {format_hint}) हूबहू अपनाएँ। "
        f"इसी layout structure में इस अध्याय की ताज़ा सामग्री लिखें। कोई अन्य layout न चुनें।"
    )

    # Hindi medium: always pure Devanagari with Hindi terminology
    tone_instruction = "शुद्ध हिंदी — देवनागरी लिपि (सभी विषयों के लिए अनिवार्य)"
    tone_details = (
        "- कार्ड का प्रत्येक शब्द देवनागरी हिंदी में होना चाहिए — कोई Roman script या अंग्रेज़ी नहीं\n"
        "- तकनीकी शब्द भी हिंदी में लिखें: मोलरता, चिह्न नियम, फोकस दूरी, नाम पक्ष, जमा पक्ष, प्रकाश संश्लेषण\n"
        "- गलत/सही लेबल: ✗ गलत / ✓ सही\n"
        "- नियम बॉक्स: 💡 **नियम:** से शुरू करें\n"
        "- टोन: सम्मानजनक और आत्मीय — 'समझो', 'देखो', 'याद रखो' — कभी आरोपात्मक शब्द नहीं\n"
        "- कार्ड शीर्षक: पर्यवेक्षणात्मक ('यहाँ अंक जाते हैं!') — आरोपात्मक नहीं ('भूल गए?')"
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
