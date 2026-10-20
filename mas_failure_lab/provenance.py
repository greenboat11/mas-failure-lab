"""Source and execution provenance shared across experiments."""
import hashlib
from pathlib import Path
import platform
import subprocess
import sys
from . import __version__


def provenance():
    root = Path(__file__).resolve().parent.parent
    hashes = {str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ("mas_failure_lab", "tests", "configs", "docs", ".github") for p in sorted((root / folder).rglob("*"))
              if p.is_file() and "__pycache__" not in p.parts}
    for name in ("README.md", "pyproject.toml", "CITATION.cff", "requirements-pilot.txt"):
        path = root / name
        if path.exists():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = None, None
    return dict(version=__version__, python=sys.version, platform=platform.platform(), git_revision=revision,
                git_dirty=dirty, source_sha256=hashes, random_scheme="per-run; see configuration and seed_plans", bootstrap_repetitions=1000)
