# Rensselaer Air — Fleet Maintenance & Avionics Dashboard

Self-contained HTML dashboard for grouping, filtering, and color-coding fleet maintenance findings and avionics inventory records by engineer, aircraft, and system.

> **This is a fictional demo.** All aircraft IDs, engineer names, teams, and findings are synthetic and were generated for demonstration purposes only. It is a sanitized, fully independent clone of a real internal project.

---

## 1. High-level overview

### What the dashboard does

`dashboard.html` is a single, portable web page with all data embedded inside it. It requires **no web server**, `fetch()` calls, or external files. When opened in a browser it:

- Groups records by **Lead Engineer → Source File → Aircraft ID → Avionics System**
- Color-codes cards by remediation/creation date severity
- Provides a search/filter bar for Aircraft ID and Avionics System
- Opens a detail modal when an avionics system entry is clicked
- Supports a light/dark theme toggle

### Typical workflow

1. Place the two demo CSVs in the `data/` folder (already included).
2. Run `generate_dashboard.py` to bake the data into a single `dashboard.html`.
3. Open `dashboard.html` in a modern browser.
4. Share the file — it is fully self-contained and safe for external distribution.

### Inputs and outputs

- **Inputs:** `data/Rensselaer_Air_Maintenance_Findings.csv`, `data/Rensselaer_Air_Avionics_Inventory.csv`.
- **Output:** `dashboard.html` — the final, self-contained dashboard.

---

## 2. Project structure

```
Fake HTML/
├── data/
│   ├── Rensselaer_Air_Maintenance_Findings.csv
│   └── Rensselaer_Air_Avionics_Inventory.csv
├── generate_dashboard.py      # build script
├── combined_dashboard.html    # HTML/CSS/JS template (has the placeholder)
├── dashboard.html             # generated, ready-to-view output
├── README.md
```

- **`generate_dashboard.py`** — discovers the CSVs in `data/`, loads and normalizes records, backfills a missing field (see Data Dictionary), deduplicates, and writes the final HTML by replacing the placeholder in `combined_dashboard.html`.
- **`combined_dashboard.html`** — the HTML/CSS/JS template. Not meant to be opened directly; contains the placeholder `__EMBEDDED_RECORDS_PLACEHOLDER__`.
- **`dashboard.html`** — the generated, ready-to-view dashboard. Open this in any browser.

### How files interact

```
data/*.csv
     |
     v
generate_dashboard.py
     |
     v
combined_dashboard.html (template)
     |
     v
dashboard.html (final output)
```

---

## 3. Setup & installation

### Prerequisites

- **Python 3.8+** (standard library only: `argparse`, `csv`, `json`, `pathlib`). No `pip install` or `requirements.txt` needed.
- A modern browser (Edge, Chrome, Firefox) to view the output.

### Execution steps

1. Open a terminal in the project folder.
2. Run:

   ```bash
   python generate_dashboard.py
   ```

3. Open the generated `dashboard.html` in a browser (double-click it, or drag it into a browser window).

To use custom input files, a different template, or a different output path:

```bash
python generate_dashboard.py data/Rensselaer_Air_Maintenance_Findings.csv data/Rensselaer_Air_Avionics_Inventory.csv --template combined_dashboard.html --output dashboard.html
```

### Portability

The generated `dashboard.html` has zero external dependencies — no internal databases, APIs, authentication, network resources, or file paths. It runs entirely offline from the browser's local file, and can be emailed, hosted on any static file host, or opened directly.

---

## 4. Data dictionary

### `Rensselaer_Air_Maintenance_Findings.csv` (577 rows)

Primary findings feed — analogous to a vulnerability/finding export. Drives severity coloring off **Remediation Target Date**.

| Column used by dashboard | Meaning |
|---|---|
| `Lead Engineer` | Engineer assigned to the finding (dashboard's top-level grouping) |
| `Aircraft ID` | Aircraft tail/identifier (drill-through level) |
| `Avionics System` | System associated with the finding (e.g. FlightNav Pro, AeroTrack Vision) |
| `Maintenance Event ID` | Unique identifier for the maintenance event |
| `Engineering Team` | Team the engineer belongs to |
| `Maintenance Finding` | Free-text description of the issue found |
| `Maintenance Event 2` | Numeric severity score shown alongside the finding description |
| `Remediation Target Date` | Date used to compute severity color |
| `Maintenance Event` | Date used as the record's "Created On" equivalent |

### `Rensselaer_Air_Avionics_Inventory.csv` (222 rows)

Fleet avionics inventory feed — analogous to an out-of-support/inventory export. Drives severity coloring off **Created On** (no remediation date concept applies to inventory).

| Column used by dashboard | Meaning |
|---|---|
| `Lead Engineer` | Backfilled from the Findings file |
| `Aircraft ID` | Aircraft tail/identifier |
| `Avionics System` | Installed system name |
| `Maintenance Event ID` | Unique identifier for the inventory record |
| `Engineering Team` | Owning team |
| `Created On` | Date used to compute severity color |
| `Summary` | Free-text boilerplate shown as the modal's "Finding Detail" |
| `Platform Code` | Aircraft platform/model code |

Records must have both `Lead Engineer` and `Maintenance Event ID` (after normalization) to be displayed.

---

## 5. Dashboard overview

- **Toolbar** — theme toggle, Aircraft ID filter, Avionics System filter, live record/group counts.
- **Legend** — Critical (this week or earlier) / High (through end of next month) / Medium (rest of the year) / Unknown (no date or 2027+). Findings are colored by remediation date; Inventory items are always shown and colored by creation date.
- **Accordion drill-through** — Lead Engineer → Source File → Aircraft ID → Avionics System, each level color-coded by the worst severity beneath it.
- **Modal** — clicking an Avionics System entry opens full record detail: Maintenance Event ID, category, created date, finding detail (finding text + severity score, or inventory summary), engineering team, and remediation target date.
- **Dark mode** — toggle persists via `localStorage`.

---

## 6. Architecture overview

Same architecture as the original project this was cloned from:

1. **Build-time embedding** — `generate_dashboard.py` reads CSVs, normalizes/joins/deduplicates records, serializes them to JSON, and substitutes that JSON into a `<script type="application/json">` tag inside the HTML template. No runtime fetch of data files.
2. **Client-side rendering** — `combined_dashboard.html`'s JS re-validates/deduplicates the embedded JSON, groups it into a nested `Map` structure (Engineer → Source → Aircraft → System), and renders an expandable accordion, computing severity colors from parsed dates.
3. **Self-contained artifact** — the final `dashboard.html` needs nothing else to run; it can be opened directly from disk in any modern browser.
