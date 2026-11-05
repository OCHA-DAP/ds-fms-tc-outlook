"""Email the Fiji Meteorological Service (RSMC Nadi) 5-day TC outlook.

Scrapes the latest outlook PDF from the FMS website, pulls out the per-day
cyclone formation risk and sends it as a Listmonk campaign.

Run modes (KB infrastructure/email-testing.md), both default to true:
  TEST_EMAIL  true -> test list (id 5), campaign name/subject tagged [TEST]
  DRY_RUN     true -> print the email, no Listmonk calls at all

Send-once: the campaign name carries the outlook's issue date, so a run that
finds an outlook already sent (e.g. FMS has not posted today's yet, or the
workflow is re-run) skips instead of sending a duplicate. An outlook issued
more than a day ago is not sent, and a PDF without a readable issue time
fails the run rather than sending.

Run from the repo root: uv run python -m pipelines.update_fms_outlook
"""

import datetime as dt

import pandas as pd
import requests
from ocha_relay.listmonk import ListmonkClient

from src.datasources.fms_outlook import (
    BASE_URL,
    df_to_simple_html,
    download_pdf_bytes,
    extract_date_sections,
    get_tc_outlook_pdf_url,
    parse_issue_time,
    pdf_lines,
    undated_text,
)
from src.flags import mode

LIST_ID = 9  # "FMS TC outlook" (private, untagged)
TEST_LIST_ID = 5  # "Tristan only"
SEARCH_TOKEN = "Outlook"  # campaign search is a tsquery: one plain word
MAX_AGE_DAYS = 1  # send an outlook issued today or yesterday, nothing older

HTML_INTRO = """
Dear colleagues,
<br><br>
Fiji Meteorological Services has issued their
5 Day TC Outlook for {issued}.
This specific outlook is available online <a href="{pdf_url}">here</a>,
and the most up-to-date outlook can always be found on the FMS website
<a href="{base_url}">here</a>.
<br><br>
The risk of cyclone formation over the next five days is indicated below.
Note that if the point refers to a "shaded region" or something else on a map,
please refer to the actual PDF of this specific outlook, available online
<a href="{pdf_url}">here</a>.
<br><br>
"""

HTML_CONCLUSION = """
<br>
Best regards,<br>
OCHA Centre for Humanitarian Data
"""


def build_email(df, pdf_url, issue_time):
    issued = f"{issue_time:%H%M} UTC {issue_time.day} {issue_time:%B %Y}"
    html_df_indented = (
        '<div style="padding-left:20px;font-style:italic;">\n'
        + df_to_simple_html(df)
        + "\n</div>"
    )
    html_intro = HTML_INTRO.format(
        issued=issued, pdf_url=pdf_url, base_url=BASE_URL
    )
    return html_intro + html_df_indented + HTML_CONCLUSION


def existing_campaigns(client, name):
    """Campaigns with exactly this name (newest first)."""
    r = requests.get(
        f"{client.base_url}/campaigns",
        auth=(client.username, client.password),
        params={
            "query": SEARCH_TOKEN,
            "per_page": 50,
            "order_by": "created_at",
            "order": "desc",
            "no_body": "true",
        },
        timeout=client.timeout,
    )
    r.raise_for_status()
    return [c for c in r.json()["data"]["results"] if c["name"] == name]


def main():
    m = mode()
    test_email, dry_run = m["TEST_EMAIL"], m["DRY_RUN"]

    pdf_url = get_tc_outlook_pdf_url()
    print(f"Found PDF URL: {pdf_url}")
    lines = pdf_lines(download_pdf_bytes(pdf_url))

    # The issue date keys send-once, so without it nothing is sent: a
    # reworded line must not turn into the same outlook sent every day.
    issue_time = parse_issue_time(lines)
    if issue_time is None:
        print("First lines of the PDF:", lines[:8])
        raise RuntimeError(
            "No readable 'Issue Time' line in the outlook PDF; the format may"
            " have changed. Not sending."
        )
    print(f"Outlook issued {issue_time:%Y-%m-%d %H:%M} UTC")
    issue_date = issue_time.date()
    # Yesterday's outlook can still go out (FMS late, yesterday's run
    # failed) and send-once stops a repeat; anything older is stale, e.g.
    # the season's last outlook still on the site in May or October.
    age = dt.datetime.now(dt.timezone.utc).date() - issue_date
    if age > dt.timedelta(days=MAX_AGE_DAYS):
        print(f"The latest outlook is {age.days} days old; nothing to send")
        return

    df = extract_date_sections(lines)
    if df.empty:
        # e.g. the season's last outlook, which has no day headings
        text = undated_text(lines)
        if not text:
            raise RuntimeError(
                "No text found in the outlook PDF; the format may have"
                " changed. Not sending an empty email."
            )
        print("WARNING: no day headings in the PDF; sending its text as is")
        df = pd.DataFrame([{"date": "", "text": text}])
    print(df.to_string())

    html_body = build_email(df, pdf_url, issue_time)
    name = f"FMS TC Outlook issued {issue_date:%Y-%m-%d}"
    if test_email:
        name = f"[TEST] {name}"
    list_id = TEST_LIST_ID if test_email else LIST_ID

    if dry_run:
        print(f"DRY_RUN: would send {name!r} to list {list_id}:")
        print(html_body)
        return

    client = ListmonkClient.from_env()
    previous = existing_campaigns(client, name)
    sent = [c for c in previous if c["status"] != "draft"]
    if sent:
        print(f"Already sent {name!r} (campaign {sent[0]['id']}); skipping")
        return

    campaign_id = client.create_campaign(
        name=name, subject=name, body=html_body, list_ids=[list_id]
    )
    print(f"Created campaign {campaign_id} for list {list_id}")
    client.send_campaign(campaign_id, skip_confirmation=True)
    print("Campaign sent.")


if __name__ == "__main__":
    main()
