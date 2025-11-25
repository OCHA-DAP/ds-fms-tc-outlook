from src.datasources.fms_outlook import (
    download_pdf_bytes,
    extract_date_and_next_line,
    get_tc_outlook_pdf_url,
)


def main():
    pdf_url = get_tc_outlook_pdf_url()
    print(f"Found PDF URL: {pdf_url}")

    pdf_bytes = download_pdf_bytes(pdf_url)

    df = extract_date_and_next_line(pdf_bytes)

    print(df)
    # or return df if you want to use it elsewhere
    return df


if __name__ == "__main__":
    main()
