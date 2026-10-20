"""Small artifact-writing helpers; experiment semantics stay in their engines."""
import csv
import gzip
from pathlib import Path

from .serialization import canonical


def write_csv(path, rows):
    # Nullable optional mechanism metrics can differ across treatments.
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_run(path, result):
    events = result.pop("events")
    with path.with_suffix(".events.jsonl.gz").open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as stream:
            for event in events:
                stream.write((canonical(event) + "\n").encode())
    path.with_suffix(".json").write_text(canonical(result) + "\n", encoding="utf-8")
