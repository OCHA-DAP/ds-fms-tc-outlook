import datetime as dt

from src.datasources.fms_outlook import (
    df_to_simple_html,
    extract_date_sections,
    parse_issue_time,
    undated_text,
)

# pdfplumber lines of the 2026-11-05 outlook (3 pages)
LINES = """5 - DAY TROPICAL CYCLONE OUTLOOK
Equator to 25S and 160E to 120W
Issue Time: 0400 UTC Thursday 5th November 2026.
Next Issue: 0400 UTC Friday 6th November 2026.
Issued by: Tropical Cyclone Centre, RSMC, and Nadi.
Existing Tropical Cyclones:
Nil.
Likelihood of a tropical cyclone formation in the region in the next five days, till Tuesday
10th November, 2026:
Friday 6th November
The potential for formation of a Tropical Cyclone in the region is VERY LOW.
Saturday 7th November
The potential for formation of a Tropical Cyclone in the region is VERY LOW.
Sunday 8th November
The potential for formation of a Tropical Cyclone in the region is VERY LOW.
Monday 9th November
The potential for formation of a Tropical Cyclone in the region is VERY LOW.
Tuesday 10th November
The potential for formation of a Tropical Cyclone in the region is VERY LOW.""".splitlines()  # noqa: E501


def test_issue_time():
    assert parse_issue_time(LINES) == dt.datetime(
        2026, 11, 5, 4, 0, tzinfo=dt.timezone.utc
    )


def test_issue_time_missing_or_unparseable():
    assert parse_issue_time(LINES[3:]) is None
    bad = ["Issue Time: 0400 UTC Thursday 31st Smarch 2026."]
    assert parse_issue_time(bad) is None


def test_sections():
    df = extract_date_sections(LINES)
    assert list(df["date"]) == [
        "Friday 6th November",
        "Saturday 7th November",
        "Sunday 8th November",
        "Monday 9th November",
        "Tuesday 10th November",
    ]
    assert df["text"].str.endswith("is VERY LOW.").all()


def test_sections_multiline_and_empty():
    lines = ["Header", "Friday 6th November", "first part", "second part"]
    df = extract_date_sections(lines)
    assert df["text"].tolist() == ["first part second part"]
    assert extract_date_sections(["no dates here"]).empty


def test_html_escapes_pdf_text():
    df = extract_date_sections(["Friday 6th November", "risk <b> & more"])
    assert "risk &lt;b&gt; &amp; more" in df_to_simple_html(df)


def test_wrapped_till_line_is_not_a_day():
    # 2025-11-28 outlook: the header wraps so the "till" date starts a line
    lines = [
        "Likelihood of a tropical cyclone formation in the region in the"
        " next five days, till",
        "Wednesday 3rd December, 2025:",
        "Saturday 29th November",
        "The potential for formation of a Tropical Cyclone in the region"
        " is VERY LOW.",
    ]
    df = extract_date_sections(lines)
    assert df["date"].tolist() == ["Saturday 29th November"]


def test_issue_time_without_colon():
    # March 2026 outlooks
    lines = ["Issue Time 0400 UTC Saturday 28th March 2026."]
    assert parse_issue_time(lines) == dt.datetime(
        2026, 3, 28, 4, 0, tzinfo=dt.timezone.utc
    )


def test_season_end_outlook_has_no_days():
    # 2026-04-30, the season's last outlook
    lines = [
        "5 - DAY TROPICAL CYCLONE OUTLOOK",
        "Issue Time: 0400 UTC Thursday 30th April 2026.",
        "Issued by: Tropical Cyclone Centre, RSMC, Nadi.",
        "Existing Tropical Cyclones: Nil",
        "The potential for formation of a Tropical Cyclone in the region for"
        " today (30/04/2026) is very low.",
        "This will be the final Tropical Cyclone Outlook for this season.",
    ]
    assert extract_date_sections(lines).empty
    text = undated_text(lines)
    assert text.startswith("Existing Tropical Cyclones: Nil The potential")
    assert text.endswith("for this season.")
    assert undated_text(["no header"]) == ""
