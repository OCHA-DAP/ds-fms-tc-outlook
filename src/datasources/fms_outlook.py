import io
import re
from urllib.parse import urljoin

import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.met.gov.fj/fiji-weather/5-day-tc-outlook/"
PREFIX = "The potential for formation of a Tropical Cyclone in the region is"
WEEKDAY_RE = re.compile(
    r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
    re.IGNORECASE,
)
ORDINAL_RE = re.compile(r"\b\d{1,2}(st|nd|rd|th)\b")


def is_date_line(line: str) -> bool:
    line = line.strip()
    return bool(WEEKDAY_RE.search(line) and ORDINAL_RE.search(line))


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


def extract_date_and_next_line(pdf_bytes: bytes) -> pd.DataFrame:
    """
    From the TC outlook PDF, extract pairs of:
      - date_line (e.g. 'Tuesday 25th November')
      - following_line (e.g. 'The potential for formation ... VERY LOW.')

    Returns a DataFrame with columns:
      - 'date'
      - 'line'
    """
    records = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = [ln.strip() for ln in text.splitlines()]

            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if is_date_line(line):
                    # Find the next non-empty line
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1

                    if j < len(lines):
                        next_line = lines[j].strip()
                    else:
                        next_line = ""

                    records.append(
                        {
                            "date": line,
                            "line": next_line,
                        }
                    )

                    # Move on from the next line
                    i = j + 1
                else:
                    i += 1

    df = pd.DataFrame(records)
    return df


def build_dataframe_from_lines(lines):
    """Create a pandas DataFrame from the extracted lines."""
    df = pd.DataFrame({"potential_line": lines})
    return df


def df_to_simple_html(df):
    """
    Convert a DataFrame with columns ['date', 'line']
    into simple, clean HTML.

    Produces something like:

      <div class="tc-outlook">
        <p><strong>Tuesday 25th November</strong><br>
           The potential for formation...</p>
        ...
      </div>
    """
    rows = []

    for _, row in df.iterrows():
        date_html = f"<strong>{row['date']}</strong>"
        line_html = row["line"]

        block = "<p>" f"{date_html}<br>" f"{line_html}" "</p>"
        rows.append(block)

    html = '<div class="tc-outlook">\n' + "\n".join(rows) + "\n</div>"
    return html
