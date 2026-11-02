"""Local-only ingestion CLI."""

import argparse
import json
from pathlib import Path

from app.db import create_database_engine, session_factory
from app.ingestion.service import ingest_pdf

parser = argparse.ArgumentParser()
parser.add_argument("paths", nargs="+", type=Path)

if __name__ == "__main__":
    args = parser.parse_args()
    sessions = session_factory(create_database_engine())
    with sessions() as session, session.begin():
        results = [ingest_pdf(session, path) for path in args.paths]
    for result in results:
        print(json.dumps(result.__dict__, default=list, sort_keys=True))
