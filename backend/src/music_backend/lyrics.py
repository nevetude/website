"""The lyrics of a song from a local text file, written the way Genius shows them: a line in square brackets
(`[Chorus: Artist]`) names the stanza under it, and the lines below belong to it until a blank line or the next name."""

from dataclasses import dataclass


@dataclass(slots=True)
class Stanza:
    title: (
        str | None
    )  # the name line as written, brackets included; none for lines that have no name
    lines: list[str]


def parse_lyrics(text: str) -> list[Stanza]:
    stanzas: list[Stanza] = []
    current: Stanza | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            current = None
        elif line.startswith("[") and line.endswith("]"):
            current = Stanza(line, [])
            stanzas.append(current)
        else:
            if current is None:
                current = Stanza(None, [])
                stanzas.append(current)
            current.lines.append(line)
    return stanzas
