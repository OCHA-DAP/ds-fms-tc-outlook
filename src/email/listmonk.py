import os

import requests

BASE_URL = "https://listmonk-dev-a5a7e5hbdxh5gxem.eastus2-01.azurewebsites.net/api"  # noqa

TRISTAN_ONLY_LIST_ID = 5
TRISTAN_SUBSCRIBER_ID = "tristan.downing@un.org"
DSCI_LIST_ID = 6

BASE_CAMPAIGN_ID = 8

USERNAME = os.getenv("DSCI_LISTMONK_API_USERNAME")
PASSWORD = os.getenv("DSCI_LISTMONK_API_KEY")


def create_campaign(
    name: str = "test_campaign",
    subject: str = "Test Subject",
    list_ids: list[int] = None,
    template_id: int = BASE_CAMPAIGN_ID,
    body: str = "TEST CONTENT",
):
    if list_ids is None:
        list_ids = [TRISTAN_ONLY_LIST_ID]
    create_payload = {
        "name": name,
        "subject": subject,
        "lists": list_ids,  # list IDs to send to
        "template_id": template_id,  # your template ID
        "type": "regular",  # "regular" or "trigger"
        "content_type": "html",
        "body": body,
    }

    r = requests.post(
        f"{BASE_URL}/campaigns", auth=(USERNAME, PASSWORD), json=create_payload
    )

    r.raise_for_status()
    campaign = r.json()["data"]
    campaign_id = campaign["id"]
    return campaign_id


def send_campaign(campaign_id: int):
    r = requests.put(
        f"{BASE_URL}/campaigns/{campaign_id}/status",
        auth=(USERNAME, PASSWORD),
        json={"status": "running"},
    )
    r.raise_for_status()
