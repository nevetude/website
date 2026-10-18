from datetime import date

import pytest

from music_backend.bio import parse_bio
from music_backend.enums import DatePrecision


@pytest.mark.parametrize(
    ("text", "name", "born", "died"),
    [
        (
            "Kendrick Lamar Duckworth (born June 17, 1987) is an American rapper.",
            "Kendrick Lamar Duckworth",
            (date(1987, 6, 17), DatePrecision.DAY),
            None,
        ),
        (
            "Lola Chantrelle Mitchell (August 7, 1979 – January 1, 2023) was a rapper.",  # noqa: RUF001
            "Lola Chantrelle Mitchell",
            (date(1979, 8, 7), DatePrecision.DAY),
            (date(2023, 1, 1), DatePrecision.DAY),
        ),
        (
            "Jerry Antoine (born 19 June, 1991), better known as Germ, is a rapper.",
            "Jerry Antoine",
            (date(1991, 6, 19), DatePrecision.DAY),
            None,
        ),
        (
            "Eddy Baker (born on August 18th, 1991, in Pomona, California), is a rapper.",
            "Eddy Baker",
            (date(1991, 8, 18), DatePrecision.DAY),
            None,
        ),
        (
            "Jamal Phillips (born 1990) is a rapper.",
            "Jamal Phillips",
            (date(1990, 1, 1), DatePrecision.YEAR),
            None,
        ),
    ],
)
def test_parses_name_and_dates(
    text: str, name: str, born: tuple[date, DatePrecision], died: tuple[date, DatePrecision] | None
) -> None:
    bio = parse_bio(text)
    assert bio is not None
    assert (bio.real_name, bio.born, bio.died) == (name, born, died)


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "Tom DeLonge is an American musician. Blink-182 (1992 – 2005, 2009 – ).",  # noqa: RUF001
        "Often praised for his versatility, Christopher Brown (born May 5, 1989) is a singer.",
    ],
)
def test_no_bio_when_description_does_not_start_with_one(text: str | None) -> None:
    assert parse_bio(text) is None
