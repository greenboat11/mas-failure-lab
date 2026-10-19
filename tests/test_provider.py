from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mas_failure_lab.agents import LLMAgent
from mas_failure_lab.llm_pilot import plan, run_pilot
from mas_failure_lab.model import Config, canonical, simulate
from mas_failure_lab.providers import ProviderError, ReplayTransport, ResponsesTransport, parse_response


def fake_response(payload, key, timeout):
    return {"id": "fake-response", "model": payload["model"], "status": "completed",
            "usage": {"input_tokens": 10, "output_tokens": 8},
            "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"verify":true,"adopt_event":null}'}]}]}, "fake-request"


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent)
        self.path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def transport(self, **kwargs):
        return ResponsesTransport(model="fake", api_key="secret-test-key", audit_path=self.path / "audit.jsonl",
                                  max_calls=8, send=fake_response, source="mock", **kwargs)

    def test_schema_and_no_credentials_in_audit(self):
        transport = self.transport()
        self.assertEqual(transport({"agent": 0}), {"verify": True, "adopt_event": None})
        lines = (self.path / "audit.jsonl").read_text()
        self.assertNotIn("secret-test-key", lines)
        request, response = [json.loads(line) for line in lines.splitlines()]
        self.assertTrue(request["payload"]["text"]["format"]["strict"])
        self.assertFalse(request["payload"]["store"])
        self.assertEqual(response["request_id"], "fake-request")
        self.assertEqual((transport.input_tokens, transport.output_tokens), (10, 8))

    def test_call_limit_before_network(self):
        transport = self.transport()
        for _ in range(8):
            transport({})
        with self.assertRaises(ProviderError):
            transport({})
        self.assertEqual(transport.calls, 8)

    def test_refusal_incomplete_and_malformed(self):
        for response in ({"status": "incomplete"}, {"status": "completed", "output": []},
                         {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal"}]}]},
                         {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "bad json"}]}]}):
            with self.assertRaises(ProviderError):
                parse_response(response)

    def test_replay_full_simulation(self):
        transport = self.transport()
        config = Config(n=2, ticks=2)
        transport.context = {"config": asdict(config), "seed": 0}
        agent = LLMAgent(transport, model="fake", settings=transport.metadata())
        original = simulate(config, 0, agent)
        replay = ReplayTransport(self.path / "audit.jsonl")
        replay.context = transport.context
        replay_agent = LLMAgent(replay, model="fake", settings=transport.metadata())
        self.assertEqual(canonical(original), canonical(simulate(config, 0, replay_agent)))
        replay.assert_consumed()
        with self.assertRaises(ProviderError):
            replay({})

    def test_replay_rejects_changed_observations(self):
        transport = self.transport()
        transport({"agent": 0})
        replay = ReplayTransport(self.path / "audit.jsonl")
        with self.assertRaises(ProviderError):
            replay({"agent": 1})

    def test_plan_and_missing_credentials(self):
        spec = json.loads(Path("configs/llm_smoke.json").read_text())
        self.assertEqual(plan(spec)["planned_calls"], 128)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
                run_pilot(spec, self.path / "run", model="fake", max_calls=128)
        self.assertFalse((self.path / "run").exists())
        with self.assertRaisesRegex(ValueError, "above max_calls"):
            run_pilot(spec, self.path / "run", model="fake", max_calls=1, api_key="fake")

    def test_pilot_end_to_end(self):
        spec = {"base": {"n": 2, "ticks": 2}, "axes": {"arm": ["cascade", "isolated_seed"]}, "seeds": [0]}
        manifest = run_pilot(spec, self.path / "run", model="fake", max_calls=8, api_key="fake", send=fake_response, source="mock")
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["completed_runs"], 2)
        self.assertEqual(manifest["input_tokens_reported"], 80)
        self.assertEqual(manifest["source"], "mock")

    def test_failed_run_preserves_audit_without_secret(self):
        def fail(payload, key, timeout):
            raise OSError("secret-test-key")
        spec = {"base": {"n": 2, "ticks": 2}, "seeds": [0]}
        with self.assertRaises(ProviderError):
            run_pilot(spec, self.path / "run", model="fake", max_calls=8, api_key="fake", send=fail, source="mock")
        manifest = json.loads((self.path / "run" / "manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(manifest["completed_runs"], 0)
        audit = (self.path / "run" / "provider.jsonl").read_text()
        self.assertNotIn("secret-test-key", audit)
        self.assertIn("transport_error", audit)
        with self.assertRaises(ProviderError):
            ReplayTransport(self.path / "run" / "provider.jsonl")
