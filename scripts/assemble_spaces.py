#!/usr/bin/env python3
"""Assemble the reviewed three-space snapshot with full cross-pack verification.

Usage: assemble_spaces.py --source-root HUB_OR_ARCHIVED_SOURCES --out EMPTY_DIR
The shared importer now performs curation and assembly together so sidecar
claims cannot be accepted independently of their source hashes and actual WAVs.
"""
import sys

from import_impulse_kernel import main

if __name__ == "__main__":
    sys.exit(main())
