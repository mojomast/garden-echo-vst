#!/usr/bin/env python3
"""Create a *local intent draft*, never an Atlas request or paid job.

An owner-authenticated companion may review and submit this explicitly later.
No network imports, credential access, audio callback involvement, or approvals.
"""
import argparse
import datetime
import json
import pathlib
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Human label (1–80 characters)")
    parser.add_argument("--source-effect-id", required=True, help="Existing effect identifier")
    parser.add_argument("--intent", required=True, help="What should change sonically (10–500 characters)")
    parser.add_argument("--out", required=True, type=pathlib.Path, help="New local JSON draft file")
    args = parser.parse_args()
    if not 1 <= len(args.name) <= 80 or not 10 <= len(args.intent) <= 500:
        parser.error("name or intent length outside bounds")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.source_effect_id):
        parser.error("source effect ID must be safe kebab-case")
    if args.out.exists():
        parser.error("refusing to overwrite a reviewed intent")
    draft = {
        "schemaVersion": 1,
        "status": "local-draft-not-submitted",
        "name": args.name,
        "sourceEffectId": args.source_effect_id,
        "sonicIntent": args.intent,
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "nextStep": "Owner reviews provenance, estimated cost and proposed engine parameters in authenticated companion; explicit second action queues Atlas job. Import only validated frozen result by hash; retain current preset on failure.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Local unsigned draft only: {args.out}")


if __name__ == "__main__":
    main()
