#!/usr/bin/env python3
"""Inspect a rooted T2 snapshot without manufacturing source authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trader_assist_v0.nautilus_g4.t2_shadow import T2SourceRootSnapshot


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    if args.source_root is None:
        result = {
            "R3_RUNTIME_T2_STATUS": "NONDECISIVE_REAL_INPUT_ABSENT",
            "CURRENT_REAL_SOURCE_ROOT": "ABSENT",
            "CURRENT_REAL_T2_SOURCE_BUNDLE": "ABSENT",
            "REAL_T2_CREDIT": "NO",
            "G4_PROMOTION": "NO",
            "FORMAL_G4": "NO",
            "DEPLOYMENT_READY": "NO",
            "TRADING_READY": "NO",
        }
    else:
        root = T2SourceRootSnapshot.model_validate_json(args.source_root.read_bytes())
        result = {
            "R3_RUNTIME_T2_STATUS": "ROOT_SNAPSHOT_VALID_CANDIDATE_NOT_ACCEPTED",
            "ACCEPTED_T2_SOURCE_ROOT_HASH": root.accepted_t2_source_root_hash,
            "REAL_T2_CREDIT": "NO",
            "G4_PROMOTION": "NO",
            "FORMAL_G4": "NO",
            "DEPLOYMENT_READY": "NO",
            "TRADING_READY": "NO",
        }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
