#!/usr/bin/env python3
"""Inspect a rooted T2 snapshot without manufacturing source authority."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from trader_assist_v0.nautilus_g4.t2_shadow import T2SourceRootSnapshot, rederive_rooted_t2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--rederive", action="store_true")
    parser.add_argument("--catalog-path", type=Path)
    parser.add_argument("--output", type=Path)
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
        if args.rederive:
            if args.catalog_path is None or args.output is None:
                parser.error("--rederive requires --catalog-path and --output")
            result_model = rederive_rooted_t2(root=root, catalog_path=args.catalog_path)
            args.output.write_text(result_model.model_dump_json(), encoding="utf-8")
            return 0
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
