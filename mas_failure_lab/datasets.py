"""Prepare a reproducible local dataset archive; never publish or upload."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

from .serialization import canonical


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def package_dataset(source, output, version):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", version):
        raise ValueError("invalid dataset version")
    if output.is_relative_to(source):
        raise ValueError("archive must be outside the input directory")
    if output.exists() or output.with_suffix(output.suffix + ".sha256").exists():
        raise ValueError("archive or checksum already exists")
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError("only completed outputs can be packaged")
    for name, expected in manifest.get("artifacts_sha256", {}).items():
        path = (source / name).resolve()
        if not path.is_relative_to(source) or sha256_file(path) != expected:
            raise ValueError("artifact checksum failed: " + name)
    files = sorted(p for p in source.rglob("*") if p.is_file())
    if any(p.is_symlink() or not p.resolve().is_relative_to(source) for p in files) or (source / "DATASET.json").exists():
        raise ValueError("symlinks, escaping paths and reserved DATASET.json are not allowed")
    output.parent.mkdir(parents=True, exist_ok=True)
    inventory = {}
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            digest = hashlib.sha256()
            size = 0
            with path.open("rb") as src, archive.open(info, "w") as dest:
                for chunk in iter(lambda: src.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
                    dest.write(chunk)
            inventory[name] = {"sha256": digest.hexdigest(), "bytes": size}
        metadata = {"schema_version": 1, "dataset_version": version, "publication_status": "local_only",
                    "source_commit": manifest.get("git_revision"), "source_dirty": manifest.get("git_dirty"),
                    "run_manifest": "manifest.json", "files": inventory}
        archive.writestr(zipfile.ZipInfo("DATASET.json", date_time=(1980, 1, 1, 0, 0, 0)), canonical(metadata))
    # Recheck that packaging did not capture a changed source after verification.
    for name, expected in manifest.get("artifacts_sha256", {}).items():
        if inventory[name]["sha256"] != expected:
            raise ValueError("source changed while packaging; archive must not be published")
    digest = sha256_file(output)
    output.with_suffix(output.suffix + ".sha256").write_text(digest + "  " + output.name + "\n", encoding="utf-8")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    try:
        result = package_dataset(args.input, args.output, args.version)
    except (ValueError, OSError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(f"Prepared {len(result['files'])} files locally: {args.output.resolve()}")


if __name__ == "__main__":
    main()
