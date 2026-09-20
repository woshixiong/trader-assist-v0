#!/usr/bin/env python3
"""Compatibility CLI delegating to the packaging-stable rooted-T2 module."""

from __future__ import annotations

from trader_assist_v0.nautilus_g4.t2_shadow import main

if __name__ == "__main__":
    raise SystemExit(main())
