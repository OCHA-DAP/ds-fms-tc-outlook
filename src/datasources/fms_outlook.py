import datetime as dt
import html
import io
import re
from urllib.parse import urljoin

import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.met.gov.fj/fiji-weather/5-day-tc-outlook/"
# A day heading is the whole line, e.g. "Friday 6th November". The wrapped
# "...till Wednesday\n3rd December, 2025:" header must not match.
DATE_LINE_RE = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+"
    r"\d{1,2}(st|nd|rd|th)?\s+[A-Za-z]+\.?",
    re.IGNORECASE,
)
# e.g. "Issue Time: 0400 UTC Thursday 5th November 2026." (the colon after
# "Time" was missing in March 2026)
ISSUE_TIME_RE = re.compile(
    r"Issue\s+Time\s*:?\s*(\d{2}):?(\d{2})\s*UTC\s+[A-Za-z]+,?\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+),?\s+(\d{4})",
    re.IGNORECASE,
)


def is_date_line(line: str) -> bool:
    return bool(DATE_LINE_RE.fullmatch(line.strip()))


def get_tc_outlook_pdf_url(base_url: str = BASE_URL) -> str:
    """
    Fetch the 5-day TC outlook page and extract the PDF URL
    from the 'Preview PDF' button.
    """
    resp = requests.get(base_url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Option 1: find all PDF links and filter by text containing "Preview PDF"
    pdf_links = soup.select('a[href$=".pdf"]')
    for a in pdf_links:
        text = a.get_text(strip=True)
        if "Preview PDF" in text:
            pdf_href = a["href"]
            return urljoin(base_url, pdf_href)

    # Option 2 (fallback): any <a> whose text mentions "Preview PDF"
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        if "Preview PDF" in text and a.get("href"):
            return urljoin(base_url, a["href"])

    # Optional: print some debug info before failing
    print("Found PDF links:", [a.get("href") for a in pdf_links])
    raise RuntimeError("Could not find 'Preview PDF' link on the page.")


def download_pdf_bytes(pdf_url: str) -> bytes:
    """Download the PDF and return its raw bytes."""
    resp = requests.get(pdf_url, timeout=60)
    resp.raise_for_status()
    return resp.content


def pdf_lines(pdf_bytes: bytes) -> list[str]:
    """All non-empty, stripped text lines of the PDF, in page order."""
    lines = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            lines.extend(ln.strip() for ln in text.splitlines() if ln.strip())
    return lines


def parse_issue_time(lines: list[str]) -> dt.datetime | None:
    """The outlook's issue time (UTC) from its 'Issue Time:' line, or None."""
    for line in lines:
        m = ISSUE_TIME_RE.search(line)
        if not m:
            continue
        hh, mm, day, month, year = m.groups()
        try:
            return dt.datetime.strptime(
                f"{year} {month} {day} {hh}{mm}", "%Y %B %d %H%M"
            ).replace(tzinfo=dt.timezone.utc)
        except ValueError:
            return None
    return None


def extract_date_sections(lines: list[str]) -> pd.DataFrame:
    """
    Group lines into sections, each starting with a date line
    (weekday + ordinal, e.g. "Friday 6th November"). All text after the date
    line (until the next date) is joined into one block; text before the
    first date line is ignored.

    Returns a DataFrame with columns ``date`` and ``text``.
    """
    records = []
    current_date = None
    current_lines = []

    for line in lines:
        if is_date_line(line):
            if current_date is not None:
                records.append(
                    {"date": current_date, "text": " ".join(current_lines)}
                )
            current_date = line
            current_lines = []
        elif current_date is not None:
            current_lines.append(line)

    if current_date is not None:
        records.append({"date": current_date, "text": " ".join(current_lines)})

    return pd.DataFrame(records, columns=["date", "text"])


def extract_date_sections_from_pdf(pdf_bytes: bytes) -> pd.DataFrame:
    return extract_date_sections(pdf_lines(pdf_bytes))


def undated_text(lines: list[str]) -> str:
    """Everything after the 'Issued by:' header line, joined.

    Fallback for outlooks without day headings, e.g. the last one of the
    season (2026-04-30: "...for today (30/04/2026) is very low. This will be
    the final Tropical Cyclone Outlook for this season..."). Empty if there
    is no 'Issued by:' line.
    """
    for i, line in enumerate(lines):
        if line.lower().startswith("issued by"):
            return " ".join(lines[i + 1 :])
    return ""


def df_to_simple_html(df):
    parts = []

    for _, row in df.iterrows():
        heading = (
            f"<strong>{html.escape(row['date'])}</strong><br>"
            if row["date"]
            else ""
        )
        block = f"<p>{heading}{html.escape(row['text'])}</p>"
        parts.append(block)

    return "<div class='tc-outlook'>\n" + "\n".join(parts) + "\n</div>"
