import gzip
import hashlib
import json
from pathlib import Path
import unittest

from mas_failure_lab import composition, model, oversight


class HistoricalCompatibility(unittest.TestCase):
    def test_saved_runs_replay_exactly_including_event_identity(self):
        for directory, cls, engine, axis in (("pilot", model.Config, model.simulate, "arm"),
                                            ("composition-pilot", composition.CompositionConfig, composition.simulate, "control"),
                                            ("oversight-pilot", oversight.OversightConfig, oversight.simulate, "arm")):
            seen = set()
            for path in sorted((Path("results") / directory / "runs").glob("*.json")):
                saved = json.loads(path.read_text())
                category = saved["config"][axis]
                if category in seen:
                    continue
                with self.subTest(directory=directory, category=category):
                    replay = engine(cls(**saved["config"]), saved["seed"])
                    events = replay.pop("events")
                    self.assertEqual(model.canonical(replay), model.canonical(saved))
                    with gzip.open(path.with_suffix(".events.jsonl.gz"), "rt") as stream:
                        self.assertEqual(model.canonical(events), model.canonical([json.loads(line) for line in stream]))
                seen.add(category)

    def test_historical_artifact_fingerprints(self):
        for directory in ("pilot", "llm-mock", "composition-pilot", "oversight-pilot"):
            root = Path("results") / directory
            manifest = json.loads((root / "manifest.json").read_text())
            for name, digest in manifest["artifacts_sha256"].items():
                self.assertEqual(hashlib.sha256((root / name).read_bytes()).hexdigest(), digest, str(root / name))
