import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from mas_failure_lab.datasets import package_dataset
from mas_failure_lab.retrieval import run_offline


class PackagingTests(unittest.TestCase):
    def test_reproducible_archive_integrity_and_modified_input_rejection(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent) as tmp:
            root = Path(tmp)
            source = root / "data"
            run_offline({"base": {"n": 1}, "seeds": [0], "trials": ["0"]}, source)
            a, b = root / "a.zip", root / "b.zip"
            package_dataset(source, a, "demo-v1")
            package_dataset(source, b, "demo-v1")
            self.assertEqual(a.read_bytes(), b.read_bytes())
            with zipfile.ZipFile(a) as archive:
                metadata = json.loads(archive.read("DATASET.json"))
                for name, info in metadata["files"].items():
                    self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), info["sha256"])
            with self.assertRaises(ValueError):
                package_dataset(source, source / "invalid.zip", "demo-v1")
            (source / "REPORT.md").write_text("changed")
            with self.assertRaises(ValueError):
                package_dataset(source, root / "changed.zip", "demo-v2")

    def test_citation_uses_verified_repository_identity(self):
        citation = json.loads(Path("CITATION.cff").read_text())
        self.assertEqual(citation["repository-code"], "https://github.com/greenboat11/mas-failure-lab")
        self.assertEqual(citation["authors"], [{"name": "greenboat11"}])
        self.assertNotIn("doi", citation)
        self.assertNotIn("license", citation)
