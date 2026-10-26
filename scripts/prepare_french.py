"""Prepare a pinned, observed research proxy; never label it investable price data."""

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile


def parse_value_weighted(raw):
    lines = raw.splitlines()
    marker = next(i for i, line in enumerate(lines) if line.strip() == "Average Value Weighted Returns -- Daily")
    rows = []
    for row in csv.reader(lines[marker + 1 :]):
        if row and row[0].strip() == "" and not rows:
            if [x.strip() for x in row[1:]] != ["Cnsmr", "Manuf", "HiTec", "Hlth", "Other"]:
                raise ValueError("Unexpected industry columns")
            continue
        if not row or not row[0].strip():
            if rows:
                break
            continue
        date = datetime.strptime(row[0].strip(), "%Y%m%d").date()
        values = [float(x) for x in row[1:]]
        if len(values) != 5 or any(x in (-99.99, -999) or not -100 <= x < 1000 for x in values):
            raise ValueError("Invalid or missing research return")
        if "2015-01-01" <= str(date) <= "2025-12-31":
            rows.append([str(date), *[x / 100 for x in values]])
    if not rows or rows != sorted(rows) or len({r[0] for r in rows}) != len(rows):
        raise ValueError("No usable unique chronological observations")
    return rows


def main():
    root = Path(__file__).resolve().parents[1]
    archive = root / "data/research/french_5_industry_daily.zip"
    with ZipFile(archive) as source:
        if source.namelist() != ["5_Industry_Portfolios_Daily.csv"]:
            raise ValueError("Unexpected archive layout")
        raw = source.read(source.namelist()[0]).decode("utf-8")
    rows = parse_value_weighted(raw)
    output = archive.with_name("french_5_industry_daily.csv")
    with output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["date", "Cnsmr", "Manuf", "HiTec", "Hlth", "Other"])
        writer.writerows(rows)
    metadata = {
        "provider": "Kenneth R. French Data Library / CRSP-derived academic portfolios",
        "source_url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/5_Industry_Portfolios_daily_CSV.zip",
        "retrieved_at": datetime.fromtimestamp(archive.stat().st_mtime, timezone.utc).isoformat(),
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "source_header": raw.splitlines()[:6],
        "currency": "USD", "frequency": "daily", "return_type": "simple_total_return",
        "units": "decimal", "adjustment": "total_return",
        "adjustment_description": "Published value-weighted portfolio returns including distributions; not adjusted ETF prices",
        "permitted_usage": "Public academic research download; no redistribution license or trading-data entitlement asserted. Retain copyright and consult provider for other uses.",
        "kind": "observed", "observed": True, "synthetic": False, "investable": False,
        "start": rows[0][0], "end": rows[-1][0], "observations": len(rows),
        "coverage_start": rows[0][0], "coverage_end": rows[-1][0],
        "expected_sessions": [row[0] for row in rows],
        "calendar_source": "Dated rows of the published French value-weighted daily block; not independently verified against an exchange calendar",
        "session_coverage_verified": False,
        "coverage": "Fixed five published industry portfolios; current revised snapshot, not point-in-time vintage",
    }
    output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"csv": str(output), "observations": len(rows), "sha256": metadata["csv_sha256"]}))


if __name__ == "__main__":
    main()
