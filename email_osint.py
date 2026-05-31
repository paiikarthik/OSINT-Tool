#!/usr/bin/env python3
"""
email_hunt.py – A lightweight OSINT tool that searches for
any online accounts linked to a given email address.
"""

import os
import json
import time
import logging
import requests
from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
)
load_dotenv()
BASE_HEADERS = {"User-Agent": "email-hunt/1.0 (+https://example.com)"}

# ----------------------------------------------------------------------
# Helper: Generic GET with retry
# ----------------------------------------------------------------------
def safe_get(url, headers=None, params=None, timeout=10, retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == retries:
                logging.warning(f"GET failed: {url} – {e}")
                return None
            time.sleep(1)

# ----------------------------------------------------------------------
# 1) Hunter.io – Email search
# ----------------------------------------------------------------------
def hunter_search(email):
    key = os.getenv("HUNTER_API_KEY")
    if not key:
        return None
    url = f"https://api.hunter.io/v2/email-search?email={email}&api_key={key}"
    data = safe_get(url, headers=BASE_HEADERS)
    if data and data.get("data"):
        return {"hunter": data["data"]}
    return None

# ----------------------------------------------------------------------
# 2) Emailrep.io – Reputation & social links
# ----------------------------------------------------------------------
def emailrep_search(email):
    key = os.getenv("EMAILREP_API_KEY")
    if not key:
        return None
    url = f"https://emailrep.io/{email}"
    headers = {"Authorization": f"Bearer {key}"}
    data = safe_get(url, headers=headers)
    if data:
        return {"emailrep": data}
    return None

# ----------------------------------------------------------------------
# 3) FullContact – Contact enrichment
# ----------------------------------------------------------------------
def fullcontact_search(email):
    key = os.getenv("FULLCONTACT_API_KEY")
    if not key:
        return None
    url = "https://api.fullcontact.com/v3/person.enrich"
    params = {"email": email}
    headers = {"Authorization": f"Bearer {key}", **BASE_HEADERS}
    data = safe_get(url, headers=headers, params=params)
    if data:
        return {"fullcontact": data}
    return None

# ----------------------------------------------------------------------
# 4) Clearbit – Enrichment
# ----------------------------------------------------------------------
def clearbit_search(email):
    key = os.getenv("CLEARBIT_API_KEY")
    if not key:
        return None
    url = f"https://person.clearbit.com/v2/people/find?email={email}"
    headers = {"Authorization": f"Bearer {key}", **BASE_HEADERS}
    data = safe_get(url, headers=headers)
    if data:
        return {"clearbit": data}
    return None

# ----------------------------------------------------------------------
# 5) Pipl – People search
# ----------------------------------------------------------------------
def pipl_search(email):
    key = os.getenv("PIPL_API_KEY")
    if not key:
        return None
    url = "https://api.pipl.com/search/"
    payload = {
        "search": {"email": email},
        "api_key": key,
        "format": "json",
    }
    r = requests.post(url, json=payload, headers=BASE_HEADERS, timeout=10)
    if r.ok:
        return {"pipl": r.json()}
    logging.warning(f"Pipl request failed for {email}")
    return None

# ----------------------------------------------------------------------
# 6) Google Custom Search – fallback for “profile” pages
# ----------------------------------------------------------------------
def google_cse_search(email):
    cse_id = os.getenv("GOOGLE_CSE_ID")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not cse_id or not api_key:
        return None
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cse_id,
        "q": f"site:linkedin.com OR site:github.com OR site:twitter.com {email}",
    }
    data = safe_get(url, params=params)
    if data and "items" in data:
        return {"google_cse": data["items"]}
    return None

# ----------------------------------------------------------------------
# Main orchestrator
# ----------------------------------------------------------------------
def search_email(email):
    results = {}

    # 1. Hunter.io
    hunter = hunter_search(email)
    if hunter: results.update(hunter)

    # 2. Emailrep.io
    rep = emailrep_search(email)
    if rep: results.update(rep)

    # 3. FullContact
    fc = fullcontact_search(email)
    if fc: results.update(fc)

    # 4. Clearbit
    cb = clearbit_search(email)
    if cb: results.update(cb)

    # 5. Pipl
    pipl = pipl_search(email)
    if pipl: results.update(pipl)

    # 6. Google CSE fallback
    gcs = google_cse_search(email)
    if gcs: results.update(gcs)

    return results

# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys

    parser = argparse.ArgumentParser(
        description="Search for all online accounts linked to an email address."
    )
    parser.add_argument("email", help="Target email address")
    args = parser.parse_args()

    email = args.email.strip()
    logging.info(f"Searching for accounts linked to: {email}")

    out = search_email(email)
    if not out:
        logging.info("No results found or all services missing.")
        sys.exit(0)

    print(json.dumps(out, indent=2, ensure_ascii=False))