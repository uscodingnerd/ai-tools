import argparse
import csv
import json
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).with_name("annotations.db")
CSV_FILE = Path(__file__).with_name("multi_annotator_dataset_list.csv")


def ensure_table(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS annotations (
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                annotator_1 TEXT,
                annotator_2 TEXT,
                annotator_3 TEXT
            )
            """
        )


def parse_annotations(raw: str) -> list[str]:
    try:
        values = json.loads(raw)
        if isinstance(values, list):
            return [str(v) for v in values]
    except json.JSONDecodeError as err:
        raise ValueError(f"Invalid annotation payload: {raw}") from err
    raise ValueError(f"Annotations must be a list, got: {raw}")


def import_csv(csv_path: Path, connection: sqlite3.Connection) -> int:
    inserted = 0
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            annotations = parse_annotations(row.get("annotations", "[]"))
            data = {
                "id": int(row["id"]),
                "text": row["text"],
                "annotator_1": annotations[0] if len(annotations) > 0 else None,
                "annotator_2": annotations[1] if len(annotations) > 1 else None,
                "annotator_3": annotations[2] if len(annotations) > 2 else None,
            }
            with connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO annotations
                        (id, text, annotator_1, annotator_2, annotator_3)
                    VALUES
                        (:id, :text, :annotator_1, :annotator_2, :annotator_3)
                    """,
                    data,
                )
            inserted += 1
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Import multi-annotator CSV into SQLite.")
    parser.add_argument("--csv", type=Path, default=CSV_FILE, help="Path to the CSV file.")
    parser.add_argument("--db", type=Path, default=DB_FILE, help="Path to the SQLite database.")
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"CSV file not found at {args.csv}")

    with sqlite3.connect(args.db) as conn:
        ensure_table(conn)
        count = import_csv(args.csv, conn)

    print(f"Imported {count} rows into {args.db}.")


if __name__ == "__main__":
    main()
