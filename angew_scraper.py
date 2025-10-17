import requests
import csv
import datetime
import os

# --- Configuration ---
JOURNAL = "Angewandte Chemie International Edition"
QUERY = "organic chemistry"
ROWS = 50  # number of results to fetch each run
OUTPUT_FILE = "angew_open_access_papers.csv"

# --- Helper function ---
def get_crossref_data(from_date):
    url = "https://api.crossref.org/works"
    params = {
        "filter": f"from-pub-date:{from_date},container-title:{JOURNAL},type:journal-article,license.url:*",
        "query": QUERY,
        "rows": ROWS,
        "select": "DOI,title,author,issued,URL,license,abstract"
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

# --- Load existing DOIs to avoid duplicates ---
def load_existing_dois():
    if not os.path.exists(OUTPUT_FILE):
        return set()
    with open(OUTPUT_FILE, newline='', encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["DOI"] for row in reader}

# --- Save new results ---
def append_to_csv(results):
    file_exists = os.path.exists(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline='', encoding="utf-8") as f:
        fieldnames = ["Title", "Authors", "DOI", "URL", "Date", "Abstract"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for item in results:
            writer.writerow(item)

# --- Main script ---
def main():
    today = datetime.date.today()
    from_date = "2024-07-01"  # your start date
    print(f"Fetching {JOURNAL} papers since {from_date}...")

    data = get_crossref_data(from_date)
    items = data.get("message", {}).get("items", [])
    existing_dois = load_existing_dois()

    new_entries = []
    for i in items:
        doi = i.get("DOI", "")
        if not doi or doi in existing_dois:
            continue
        title = " ".join(i.get("title", []))
        authors = ", ".join([a.get("family", "") for a in i.get("author", []) if "family" in a])
        date_parts = i.get("issued", {}).get("date-parts", [[None]])
        pub_date = "-".join(str(p) for p in date_parts[0] if p)
        abstract = i.get("abstract", "").replace("<jats:p>", "").replace("</jats:p>", "").strip()
        url = i.get("URL", "")
        new_entries.append({
            "Title": title,
            "Authors": authors,
            "DOI": doi,
            "URL": url,
            "Date": pub_date,
            "Abstract": abstract
        })

    if new_entries:
        append_to_csv(new_entries)
        print(f"Added {len(new_entries)} new papers.")
    else:
        print("No new papers found.")

if __name__ == "__main__":
    main()
