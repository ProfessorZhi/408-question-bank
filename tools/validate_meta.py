#!/usr/bin/env python3
"""用 schema/paper-meta.schema.json 校验所有 papers/*/*/meta.yml。

为什么需要它：骨架是脚本生成的，脚本一错就静默写坏数据。
本工具已实际抓到过一次真实缺陷 —— bootstrap 生成的 YAML 里键名 `no` 未加引号，
被 YAML 1.1 解析成布尔 False，题号**静默丢失**，肉眼看不出来。

用法：
  python tools/validate_meta.py
  python tools/validate_meta.py --dir papers/exams
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="papers")
    args = ap.parse_args(argv)

    try:
        import jsonschema
        import yaml
    except Exception as exc:
        raise SystemExit(f"[validate] 需要 pyyaml + jsonschema：{exc}") from exc

    schema = json.loads((REPO / "schema" / "paper-meta.schema.json")
                        .read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)

    files = sorted(glob.glob(str(REPO / args.dir / "*" / "*" / "meta.yml")))
    bad = 0
    for f in files:
        rel = Path(f).relative_to(REPO).as_posix()
        try:
            meta = yaml.safe_load(Path(f).read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"⛔ {rel}  YAML 解析失败：{exc}")
            bad += 1
            continue
        errs = sorted(validator.iter_errors(meta), key=lambda e: list(e.path))
        if errs:
            bad += 1
            for e in errs[:5]:
                print(f"⛔ {rel}  @ {list(e.path)}  {e.message[:140]}")
        # 额外语义检查：题号必须 1..47 且不重不漏
        nos = [q.get("no") for q in (meta.get("questions") or [])]
        if nos and nos != list(range(1, 48)):
            print(f"⚠️  {rel}  questions 题号非 1..47 连续："
                  f"{len(nos)} 条，缺 {sorted(set(range(1, 48)) - set(nos))[:8]}")
    print(f"[validate] {len(files)} 份 meta.yml，不合规 {bad} 份。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
