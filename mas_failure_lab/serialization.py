"""Stable JSON and compatibility-aware configuration records."""
from dataclasses import asdict, fields, MISSING
import json


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def record_config(config):
    record = asdict(config)
    legacy = getattr(config, "legacy_fields", tuple(record))
    extensions = [f for f in fields(config) if f.name not in legacy]
    if all(f.default is not MISSING and getattr(config, f.name) == f.default for f in extensions):
        return {key: value for key, value in record.items() if key in legacy}
    return record
