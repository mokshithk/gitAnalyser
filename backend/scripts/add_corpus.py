import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.db.database import SessionLocal
from backend.db.models import ReferenceCorpus
from backend.ingestion.git_cloner import clone_repository
from backend.ingestion.safety import safe_rmtree
from backend.similarity.engine import extract_repo_fingerprints, CORPUS_CACHE_FILE

def main():
    if len(sys.argv) < 2:
        print("Usage: python backend/scripts/add_corpus.py <repo_url>")
        sys.exit(1)

    repo_url = sys.argv[1].strip()
    print(f"Adding reference corpus repository: {repo_url}")

    db = SessionLocal()
    try:
        existing = db.query(ReferenceCorpus).filter(ReferenceCorpus.repo_url == repo_url).first()
        if not existing:
            corpus_entry = ReferenceCorpus(repo_url=repo_url, language="python")
            db.add(corpus_entry)
            db.commit()
            print("Registered repository in database table 'reference_corpus'.")
        else:
            print("Repository is already registered in database.")

        # Clone and index fingerprints
        tmp_dir = Path(settings.WORKDIR) / "corpus_indexing_tmp"
        print(f"Cloning {repo_url} into {tmp_dir} for fingerprint indexing...")
        clone_repository(repo_url, tmp_dir)

        fps = extract_repo_fingerprints(tmp_dir)
        print(f"Successfully extracted {len(fps)} qualifying Python function fingerprints.")

        # Update cache file
        cache = {}
        if CORPUS_CACHE_FILE.exists():
            try:
                cache = json.loads(CORPUS_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                cache = {}

        cache[repo_url] = [fp.to_dict() for fp in fps]
        CORPUS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CORPUS_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
        print(f"Corpus index cache updated at: {CORPUS_CACHE_FILE}")

        safe_rmtree(tmp_dir)
        print("Done. Repository is ready for similarity triage.")

    except Exception as e:
        print(f"Error adding corpus repository: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
