from typing import Any

from music_backend.imports.common import description_of, plain_text

# The start of the description of Lil Peep's "Hellboy" as Genius sends it: empty strings between the
# paragraphs, a link inside a paragraph, a quote with paragraphs of its own, a `br` without children.
HELLBOY: dict[str, Any] = {
    "tag": "root",
    "children": [
        {
            "tag": "p",
            "children": [{"tag": "em", "children": ["Hellboy"]}, " is the fourth mixtape."],
        },
        "",
        {
            "tag": "p",
            "children": [
                "Explained by ",
                {"tag": "a", "attributes": {"href": "https://x/s"}, "children": ["Smokeasac"]},
                ":",
            ],
        },
        "",
        {"tag": "blockquote", "children": [{"tag": "p", "children": ["I remember when."]}]},
        "",
        {"tag": "p", "children": ["Re-released.", {"tag": "br"}, "", "Again."]},
    ],
}


def test_the_text_of_a_tree_has_a_blank_line_between_blocks() -> None:
    assert plain_text(HELLBOY) == (
        "Hellboy is the fourth mixtape.\n\n"
        "Explained by Smokeasac:\n\n"
        "I remember when.\n\n"
        "Re-released.\nAgain."
    )


def test_placeholder_and_empty_descriptions_have_no_text() -> None:
    nothing: dict[str, Any] = {"tag": "root", "children": []}
    question: dict[str, Any] = {"tag": "root", "children": [{"tag": "p", "children": ["?"]}]}
    assert (description_of(nothing), description_of(question)) == (None, None)
    assert description_of(HELLBOY) is not None
