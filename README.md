# ds-fms-tc-outlook

Daily email of the Fiji Meteorological Service (RSMC Nadi)
[5-day tropical cyclone outlook](https://www.met.gov.fj/fiji-weather/5-day-tc-outlook/).
The pipeline scrapes the latest outlook PDF, pulls out the cyclone formation
risk for each day and sends it as a Listmonk campaign.

## Schedule

GitHub Actions, `.github/workflows/run_update_fms_outlook.yml`, cron
`0 5 * * *`. FMS issues the outlook at 04:00 UTC during the South Pacific
cyclone season (1 November to 30 April). GitHub usually starts the run 50 to
70 minutes late, so the email arrives at about 06:00 UTC.

Turn the workflow off at the end of the season (Actions → the workflow →
Disable workflow) and back on in November.

## Run modes

Set as repository variables; the code and the workflow fall back to the safe
value when they are unset (KB `infrastructure/email-testing.md`).

| variable | `true` | `false` |
|---|---|---|
| `TEST_EMAIL` | test list (id 5); campaign tagged `[TEST]` | real list (id 9, "FMS TC outlook") |
| `DRY_RUN` | print the email, no Listmonk calls | send |

A manual run (Actions → Run workflow) takes the same two values as inputs.
The Listmonk credentials are the OCHA-DAP organisation secrets
`DSCI_LISTMONK_API_URL`, `DSCI_LISTMONK_API_USERNAME` and
`DSCI_LISTMONK_API_KEY`.

Each outlook is sent once: the campaign name carries the outlook's issue
date, and a run that finds a sent campaign with the same name skips. So a
re-run, or a run before FMS has posted the day's outlook, sends nothing.

## Local run

```bash
uv sync
uv run pytest
uv run python -m pipelines.update_fms_outlook   # dry run, prints the email
```

`TEST_EMAIL=true DRY_RUN=false` sends to the test list; that needs the three
`DSCI_LISTMONK_*` variables in the environment, with the URL as
`DSCI_LISTMONK_BASE_URL`.
