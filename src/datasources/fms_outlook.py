import io
import re
from urllib.parse import urljoin

import pandas as pd
import pdfplumber
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.met.gov.fj/fiji-weather/5-day-tc-outlook/"
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


def df_to_simple_html(df):
    parts = []

    for _, row in df.iterrows():
        block = (
            "<p>" f"<strong>{row['date']}</strong><br>" f"{row['text']}" "</p>"
        )
        parts.append(block)

    return "<div class='tc-outlook'>\n" + "\n".join(parts) + "\n</div>"


def extract_date_sections_from_pdf(pdf_bytes: bytes) -> pd.DataFrame:
    """
    Extract sections from the PDF where each section starts with a date line.
    All text after the date line (until the next date) is grouped together.

    Returns a DataFrame with:
      - date
      - text   (joined block for that date)
    """
    records = []

    current_date = None
    current_lines = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            for raw_line in text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue

                if is_date_line(line):
                    # Save previous block
                    if current_date is not None:
                        records.append(
                            {
                                "date": current_date,
                                "text": " ".join(current_lines),
                            }
                        )

                    # Start new block
                    current_date = line
                    current_lines = []

                else:
                    # Only collect lines if we've seen a date already
                    if current_date is not None:
                        current_lines.append(line)

        # Save final block
        if current_date is not None:
            records.append(
                {
                    "date": current_date,
                    "text": " ".join(current_lines),
                }
            )

    return pd.DataFrame(records)
