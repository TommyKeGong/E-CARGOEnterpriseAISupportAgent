"""CLI entry point for resumable local embedding generation."""

import json
import logging

from app.db import create_database_engine, session_factory
from app.embeddings.local import generate_local_embeddings, get_local_encoder


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    engine = create_database_engine()
    session = session_factory(engine)()
    try:
        result = generate_local_embeddings(session, get_local_encoder())
        session.commit()
        logging.info(json.dumps(result.__dict__, sort_keys=True))
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    main()
