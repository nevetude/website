import re
import unicodedata
from dataclasses import dataclass

# A parenthesized group with one of these words is a version of the work, not an alternative-language name.
VARIANT_WORDS = re.compile(
    r"\b(feat|ft|prod|remix|mix|edit|live|demo|deluxe|remaster(ed)?|freestyle|acoustic|instrumental|"
    r"version|reprise|skit|interlude|intro|outro|bonus|explicit|clean|radio|extended|original|"
    r"pt|part|vol|volume)\b\.?",
    re.IGNORECASE,
)
TRAILING_GROUP = re.compile(r"\s*\(([^()]*)\)\s*$")


@dataclass(slots=True, frozen=True)
class SplitName:
    base_name: str
    variant: str | None
    disambiguator: str | None


def _letters(text: str) -> list[str]:
    return [c for c in text if c.isalpha()]


def _is_latin_letter(char: str) -> bool:
    return unicodedata.name(char, "").startswith("LATIN")


def split_name(name: str) -> SplitName:
    """Split a Genius-style display name into base name, variant and alternative-language name.

    "Надоела (Freestyle) (Tired of you)" -> ("Надоела", "Freestyle", "Tired of you")
    """
    base, groups = name.strip(), []
    while (match := TRAILING_GROUP.search(base)) and match.start() > 0:
        groups.append(match.group(1).strip())
        base = base[: match.start()].strip()
    groups.reverse()

    base_is_non_latin = not all(_is_latin_letter(c) for c in _letters(base))
    variants: list[str] = []
    disambiguator = None
    for group in groups:
        letters = _letters(group)
        is_alt_name = (
            disambiguator is None
            and base_is_non_latin
            and bool(letters)
            and all(_is_latin_letter(c) for c in letters)
            and not VARIANT_WORDS.search(group)
        )
        if is_alt_name:
            disambiguator = group
        else:
            variants.append(group)
    return SplitName(base, ", ".join(variants) or None, disambiguator)
