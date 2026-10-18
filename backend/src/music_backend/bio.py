"""The real name and the dates of birth and death of a person, which Genius has only as the first words of
the description: "Kendrick Lamar Duckworth (born June 17, 1987) is ..." or "Lola Mitchell (August 7, 1979
- January 1, 2023) was ...". Places are told in free sentences and are not taken."""

import re
from dataclasses import dataclass
from datetime import date, datetime

from music_backend.enums import DatePrecision

_MONTH = r"[A-Z][a-z]{2,8}\.?"
_DAY = r"\d{1,2}(?:st|nd|rd|th)?"
_DATE = rf"(?:{_MONTH} {_DAY},? \d{{4}}|{_DAY} {_MONTH},? \d{{4}}|{_MONTH},? \d{{4}}|\d{{4}})"
_BIO = re.compile(
    rf"^(?P<name>[^()\n]{{2,80}}?)\s*"
    rf"\((?:(?:born:?|b\.)\s*(?:on\s+)?)?(?P<born>{_DATE})(?:\s*[–—-]\s*(?P<died>{_DATE}))?"  # noqa: RUF001  # the dash of real descriptions
    # "born June 17, 1987, in Compton, California": the place is not taken
    rf"(?:,?\s+in\s+[^()]*)?\)"
)
# A name is capitalised words; a lowercase word means the match is a sentence, not a name.
_PARTICLES = {
    "de",
    "da",
    "di",
    "del",
    "van",
    "von",
    "der",
    "bin",
    "ibn",
    "al",
    "el",
    "la",
    "le",
    "dos",
    "y",
}
# From the most to the least complete; the precision is what the format keeps.
_FORMATS = (
    ("%B %d %Y", DatePrecision.DAY),
    ("%b %d %Y", DatePrecision.DAY),
    ("%d %B %Y", DatePrecision.DAY),
    ("%d %b %Y", DatePrecision.DAY),
    ("%B %Y", DatePrecision.MONTH),
    ("%b %Y", DatePrecision.MONTH),
    ("%Y", DatePrecision.YEAR),
)

type PartialDate = tuple[date, DatePrecision]


@dataclass(slots=True, frozen=True)
class Bio:
    real_name: str
    born: PartialDate
    died: PartialDate | None


def _parse_date(text: str) -> PartialDate | None:
    text = re.sub(r"(?<=\d)(?:st|nd|rd|th)", "", text).replace(".", "").replace(",", "")
    for pattern, precision in _FORMATS:
        try:
            return datetime.strptime(text, pattern).date(), precision
        except ValueError:
            continue
    return None


def parse_bio(description: str | None) -> Bio | None:
    """The bio at the very start of the description, or None when it does not start with one."""
    if not description or not (found := _BIO.match(description.strip())):
        return None
    born = _parse_date(found["born"])
    died = _parse_date(found["died"]) if found["died"] else None
    if born is None or (found["died"] and died is None):
        return None
    name = found["name"].strip()
    if any(
        not (word[0].isupper() or word[0] in "“\"'(" or word in _PARTICLES) for word in name.split()
    ):
        return None
    return Bio(name, born, died)
