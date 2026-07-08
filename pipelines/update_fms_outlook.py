import datetime

from src.datasources.fms_outlook import (
    df_to_simple_html,
    download_pdf_bytes,
    extract_date_sections_from_pdf,
    get_tc_outlook_pdf_url,
)
from src.email.listmonk import create_campaign, send_campaign

LIST_ID = 9
TRISTAN_ONLY_LIST_ID = 5

HTML_INTRO = """
Dear colleagues,
<br><br>
Fiji Meteorological Services has issued their
5 Day TC Outlook for {current_date}.
This specific outlook is available online <a href="{pdf_url}">here</a>,
and the most up-to-date outlook can always be found on the FMS website
<a href="https://www.met.gov.fj/fiji-weather/5-day-tc-outlook/">here</a>.
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


def main():
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    pdf_url = get_tc_outlook_pdf_url()
    print(f"Found PDF URL: {pdf_url}")

    pdf_bytes = download_pdf_bytes(pdf_url)

    df = extract_date_sections_from_pdf(pdf_bytes)
    print(df)

    html_df = df_to_simple_html(df)

    html_df_indented = (
        '<div style="padding-left:20px;font-style:italic;">\n'
        + html_df
        + "\n</div>"
    )

    html_intro = HTML_INTRO.format(
        current_date=current_date,
        pdf_url=pdf_url,
    )

    html_body = html_intro + html_df_indented + HTML_CONCLUSION

    subject = "FMS TC Outlook issued " + current_date

    campaign_id = create_campaign(
        name=subject,
        subject=subject,
        list_ids=[LIST_ID],
        body=html_body,
    )

    print(f"Created campaign with ID: {campaign_id}")
    send_campaign(campaign_id=campaign_id)
    print("Campaign sent.")


if __name__ == "__main__":
    main()
