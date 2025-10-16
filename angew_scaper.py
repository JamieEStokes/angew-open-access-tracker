import requests
import csv
import os
from datetime import datetime
import time

CSV_FILE = "angew_open_access_papers.csv"
START_DATE = "2025-07-01"

def find_open_access_angew_papers_from(start_date="2025-07-01", rows=50):
    """
    Find open-access *Angewandte Chemie International Edition* papers since start_date.
    Includes abstracts from Crossref (when available).
    """
    url = "https://api.crossref.org/works"
    params = {
        "filter": f"container-title:Angewandte Chemie International Edition,license.url:*,from-pub-date:{start_date}",
        "rows": rows,
        "sort": "published",
        "order": "desc"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    papers = []
    for item in data.get("message", {}).get("items", []):
        title = item.get("title", ["No title"])[0]
        doi = item.get("DOI", "")
        url = item.get("URL", "")
        license_info = item.get("license", [{}])[0].get("URL", "No license info")
        year = item.get("issued", {}).get("date-parts", [[None]])[0][0]
        abstract = item.get("abstract", "").replace("\n", " ").strip()

        papers.append({
            "title": title,
            "doi": doi,
            "url": url,
            "license": license_info,
            "year": year,
            "abstract": abstract or None
        })

    return papers

def get_abstract_from_europepmc(doi):
    """
    Retrieve the abstract of a paper from Europe PMC using its DOI.
    Returns None if not found.
    """
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    params = {"query": f"DOI:{doi}", "format": "json"}
    try:
        response = requests.get(url, params=params, timeout=10)
        if not response.ok:
            return None

        data = response.json()
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return None

        abstract = results[0].get("abstractText")
        return abstract.strip() if abstract else None
    except Exception:
        return None

def save_results_to_csv(papers, csv_file=CSV_FILE):
    """Append new papers to CSV if not already recorded."""
    existing_dois = set()
    if os.path.exists(csv_file):
        with open(csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_dois.add(row["doi"])

    new_entries = [p for p in papers if p["doi"] not in existing_dois]

    if not new_entries:
        print("✅ No new open-access papers found.")
        return

    # Get missing abstracts from Europe PMC if needed
    for p in new_entries:
        if not p["abstract"]:
            print(f"🔎 Fetching abstract from Europe PMC for DOI: {p['doi']}")
            abstract = get_abstract_from_europepmc(p["doi"])
            p["abstract"] = abstract or "Abstract not available"
            time.sleep(1)  # be polite to the API

    file_exists = os.path.exists(csv_file)
    with open(csv_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "year", "doi", "url", "license", "abstract", "retrieved"])
        if not file_exists:
            writer.writeheader()

        for p in new_entries:
            p["retrieved"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            writer.writerow(p)

    print(f"🧾 Added {len(new_entries)} new papers to {csv_file}.")

if __name__ == "__main__":
    print(f"🔬 Searching for open-access *Angew. Chem. Int. Ed.* papers since {START_DATE}...")
    papers = find_open_access_angew_papers_from(START_DATE)
    save_results_to_csv(papers)
