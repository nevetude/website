import pytest

from music_backend.names import SplitName, split_name


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Надоела (Freestyle) (Tired of you)", SplitName("Надоела", "Freestyle", "Tired of you")),
        ("Надоела (Tired of you) (Freestyle)", SplitName("Надоела", "Freestyle", "Tired of you")),
        ("Группа крови (Blood Type)", SplitName("Группа крови", None, "Blood Type")),
        ("КИНО (KINO)", SplitName("КИНО", None, "KINO")),
        ("Русский (In Russian)", SplitName("Русский", None, "In Russian")),
        ("Creep (Live)", SplitName("Creep", "Live", None)),
        ("Canal St. (feat. A$AP Rocky)", SplitName("Canal St.", "feat. A$AP Rocky", None)),
        ("Надоела (Remix)", SplitName("Надоела", "Remix", None)),
        (
            "Mr. Brightside (Jacques Lu Cont's Thin White Duke Mix)",
            SplitName("Mr. Brightside", "Jacques Lu Cont's Thin White Duke Mix", None),
        ),
        (
            "(What's the Story) Morning Glory?",
            SplitName("(What's the Story) Morning Glory?", None, None),
        ),
        ("Don’t F**k Around", SplitName("Don’t F**k Around", None, None)),
    ],
)
def test_split_name(name: str, expected: SplitName) -> None:
    assert split_name(name) == expected
