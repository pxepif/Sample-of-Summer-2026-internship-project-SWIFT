#!/usr/bin/env python3
"""
generate_dashboard.py

Builds a single, self-contained `dashboard.html` from the Rensselaer Air
demo CSV exports, by embedding the combined record set directly into the
dashboard's HTML template. The resulting file has no external
dependencies: no fetch(), no JSON/CSV files, no localhost, no web server
required. Just double click to open it in a browser.

Usage:
    python generate_dashboard.py [csv_files...]
    python generate_dashboard.py --template combined_dashboard.html --output dashboard.html

If no input files are given, the script auto-discovers every *.csv file
in the `data/` folder next to this script.

CSV columns are expected to use the same field names the dashboard's JS
helpers already understand, e.g.:
    "Lead Engineer"
    "Aircraft ID"
    "Avionics System"
    "Maintenance Event ID"
    "Engineering Team"

Any extra columns are preserved and passed through untouched.

This is a sanitized, fictional-data demo project. It ships with exactly
two data sources:
    - Rensselaer_Air_Maintenance_Findings.csv  (per-aircraft maintenance
      findings, analogous to a "vulnerability/finding" feed; severity is
      driven by "Remediation Target Date")
    - Rensselaer_Air_Avionics_Inventory.csv    (fleet avionics inventory,
      analogous to an "out-of-support inventory" feed; severity is driven
      by "Created On" since there is no remediation date)
"""

import argparse
import csv
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_TEMPLATE = SCRIPT_DIR / "combined_dashboard.html"
DEFAULT_OUTPUT = SCRIPT_DIR / "dashboard.html"
PLACEHOLDER = "__EMBEDDED_RECORDS_PLACEHOLDER__"

# Source identifiers, matched against a loaded file's stem (filename
# without extension). Used to decide which normalization/join logic
# applies to which records.
FINDINGS_SOURCE_FILE = "Rensselaer_Air_Maintenance_Findings"
INVENTORY_SOURCE_FILE = "Rensselaer_Air_Avionics_Inventory"


def normalize_assigned(record):
    return (record.get("Lead Engineer") or "Unassigned").strip() if record.get("Lead Engineer") else "Unassigned"


def normalize_host(record):
    return record.get("Aircraft ID") or "Aircraft ID not available"


def normalize_software(record):
    return record.get("Avionics System") or "Avionics System not available"


def normalize_unique_id(record):
    return record.get("Maintenance Event ID") or "Maintenance Event ID not available"


def record_key(record):
    # NOTE: __sourceFile is included in the key (unlike the original
    # project) because both demo CSVs independently reuse the same
    # "Maintenance Event ID" numbering per aircraft. Without the source
    # file in the key, an Inventory row and a Findings row for the same
    # aircraft/avionics system can collide and incorrectly deduplicate
    # into a single record.
    return "|".join([
        record.get("__sourceFile") or "Unknown",
        normalize_assigned(record),
        normalize_host(record),
        normalize_software(record),
        normalize_unique_id(record),
    ])


def validate_record(record):
    has_assigned = "Lead Engineer" in record
    has_unique_id = "Maintenance Event ID" in record
    return has_assigned and has_unique_id


def load_csv_records(path):
    """
    Read a CSV file into a list of dicts, preserving all columns.

    Tries UTF-8 (with BOM support) first, then falls back to cp1252,
    since some of the generated demo names/text contain accented
    characters that were not saved as UTF-8.
    """
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with open(path, newline="", encoding=encoding) as f:
                reader = csv.DictReader(f)
                records = []
                for row in reader:
                    # Drop the csv.DictReader "None" key that can appear for
                    # rows with more columns than the header (rare, but safe).
                    row.pop(None, None)
                    row = {k: (v if v != "" else None) for k, v in row.items() if k is not None}
                    row["__sourceFile"] = path.stem
                    records.append(row)
            return records
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not decode {path} as utf-8-sig or cp1252")


def discover_default_inputs():
    return sorted(DATA_DIR.glob("*.csv"))


def is_junk_engineer(value):
    """
    The raw Inventory CSV's "Lead Engineer" column is mostly blank or
    filled with meaningless placeholder tokens (e.g. "RA_17631") rather
    than a real-looking name. Treat both as "missing".
    """
    if not value:
        return True
    value = value.strip()
    if not value:
        return True
    return value.startswith("RA_")


def backfill_inventory_lead_engineer(records):
    """
    ASSUMPTION: The Inventory source has no reliable "Lead Engineer"
    value, but every Inventory "Aircraft ID" also appears in the
    Findings source, which does have a real-looking engineer name per
    aircraft. Build an Aircraft ID -> Lead Engineer lookup from the
    Findings records and use it to backfill missing/junk Inventory
    engineer names, so both sources can be grouped by the same concept.
    """
    aircraft_to_engineer = {}
    for record in records:
        if record.get("__sourceFile") != FINDINGS_SOURCE_FILE:
            continue
        aircraft_id = record.get("Aircraft ID")
        engineer = record.get("Lead Engineer")
        if aircraft_id and engineer and not is_junk_engineer(engineer):
            aircraft_to_engineer[aircraft_id] = engineer

    for record in records:
        if record.get("__sourceFile") != INVENTORY_SOURCE_FILE:
            continue
        if is_junk_engineer(record.get("Lead Engineer")):
            aircraft_id = record.get("Aircraft ID")
            replacement = aircraft_to_engineer.get(aircraft_id)
            if replacement:
                record["Lead Engineer"] = replacement

    return records


def build_combined_records(input_paths):
    combined = []
    for path in input_paths:
        combined.extend(load_csv_records(path))

    backfill_inventory_lead_engineer(combined)

    unique = {}
    for record in combined:
        if not validate_record(record):
            continue
        unique[record_key(record)] = record

    return list(unique.values())


def escape_for_script_tag(json_text):
    """
    Prevent a literal "</script" substring inside the embedded JSON from
    prematurely closing the <script type="application/json"> tag when the
    browser tokenizes the raw HTML.
    """
    return json_text.replace("</script", "<\\/script")


def generate(input_paths, template_path, output_path):
    records = build_combined_records(input_paths)

    if not records:
        raise SystemExit("No valid records found in the given input files.")

    json_text = json.dumps(records, ensure_ascii=False)
    json_text = escape_for_script_tag(json_text)

    template_html = template_path.read_text(encoding="utf-8")

    if PLACEHOLDER not in template_html:
        raise SystemExit(
            f"Template {template_path} is missing the {PLACEHOLDER} marker. "
            "Make sure you're using the updated combined_dashboard.html template."
        )

    output_html = template_html.replace(PLACEHOLDER, json_text)

    output_path.write_text(output_html, encoding="utf-8")

    print(f"Wrote {output_path} with {len(records):,} unique records "
          f"from {len(input_paths)} input file(s):")
    for p in input_paths:
        print(f"  - {p.name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs", nargs="*",
        help="CSV files to combine. Defaults to all *.csv files in the "
             "data/ folder next to this script."
    )
    parser.add_argument(
        "--template", default=str(DEFAULT_TEMPLATE),
        help="Path to the dashboard HTML template (default: combined_dashboard.html)."
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help="Path to write the standalone dashboard (default: dashboard.html)."
    )
    args = parser.parse_args()

    if args.inputs:
        input_paths = [Path(p) for p in args.inputs]
    else:
        input_paths = discover_default_inputs()

    if not input_paths:
        raise SystemExit(
            "No input files found. Provide CSV paths as arguments, "
            "or place them in the data/ folder next to this script."
        )

    missing = [p for p in input_paths if not p.exists()]
    if missing:
        raise SystemExit(f"Input file(s) not found: {', '.join(str(m) for m in missing)}")

    generate(input_paths, Path(args.template), Path(args.output))


if __name__ == "__main__":
    main()
