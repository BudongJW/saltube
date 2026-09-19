#!/usr/bin/env python3
"""attest — 대본의 각 인용이 실제로 무엇에 근거하는지 대조.

    python3 tools/attest.py init EP004      대본의 [S-XXX] 마커로 근거 항목 뼈대 생성
    python3 tools/attest.py fetch           Crossref 초록을 references.yaml 에 캐시
    python3 tools/attest.py check           근거 대조 검사 (CI에서 실행)

왜 이 도구가 있는가
-------------------
`claimctl validate` 는 출처 마커가 **있는지**만 봅니다. 그 문장이 그 출처로
**뒷받침되는지**는 보지 못합니다. 실재하는 논문을 인용하면서 그 논문이 하지 않은
말을 하는 것 — 이것이 창조과학의 대표적 기법(quote mining)이고, 우리가 하면 채널은 끝납니다.

기계는 한국어 대본과 영어 초록 사이의 의미 일치를 판정할 수 없습니다.
그래서 판정하지 않습니다. 대신 이렇게 강제합니다:

  1. 대본의 모든 [S-XXX] 마커에 근거 항목이 있어야 한다
  2. 근거 항목의 quote 는 **원문 그대로**여야 하고, 초록을 받을 수 있으면
     그 안에 실제로 존재해야 한다  ← 지어낸 인용을 여기서 잡습니다
  3. 기계가 확인할 수 없는 근거(본문 인용, 초록 미제공)는
     사람이 서명(checked_by)해야 한다

즉 기계가 판단을 대신하는 게 아니라, **사람이 원문을 봤다는 증거를 남기게** 합니다.
→ docs/03-editorial-policy.md §2 2단계 / docs/13-external-tools.md §5
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
REFS = ROOT / "content" / "references.yaml"
SCRIPTS = ROOT / "content" / "scripts"
UA = "saltube-attest/1.0 (https://github.com/BudongJW/saltube; mailto:dlawodnjs@mju.ac.kr)"
API = "https://api.crossref.org/works"

MARKER = re.compile(r"\[(S-[A-Z0-9\-]+)\]")
FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S)
# locator 가 이것이면 초록에서 기계 대조가 가능
ABSTRACT_LOCATOR = "abstract"


def load_refs() -> dict:
    return yaml.safe_load(REFS.read_text(encoding="utf-8"))


def dump_refs(d: dict) -> None:
    REFS.write_text(yaml.dump(d, allow_unicode=True, sort_keys=False, width=100,
                              default_flow_style=False), encoding="utf-8")


def scripts() -> list[Path]:
    return sorted(p for p in SCRIPTS.glob("*.md") if not p.name.startswith("_"))


def parse(path: Path) -> tuple[dict, str]:
    m = FRONT.match(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError("front matter 없음")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def body_markers(body: str) -> list[str]:
    """제작 메모('---' 이후)를 제외한 본문의 출처 마커."""
    return MARKER.findall(body.split("\n---\n")[0])


def normalize(s: str) -> str:
    """JATS 태그·공백·인용부호 차이를 제거해 대조 가능한 형태로."""
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("‘", "'").replace("’", "'")
          .replace("“", '"').replace("”", '"')
          .replace("–", "-").replace("—", "-"))
    return re.sub(r"\s+", " ", s).strip().lower()


# ────────────────────────────── fetch ──────────────────────────────

def _curl(url: str) -> dict | None:
    r = subprocess.run(["curl", "-sS", "--max-time", "30", url, "-H", f"User-Agent: {UA}"],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def abstract_for(doi: str) -> tuple[str | None, str]:
    """초록을 Crossref → Europe PMC → Semantic Scholar 순으로 찾습니다.

    Nature 계열은 Crossref 에 초록을 넣지 않아 단일 출처로는 절반도 못 채웁니다.
    반환: (초록, 출처 이름)
    """
    if d := _curl(f"{API}/{urllib.parse.quote(doi, safe='')}"):
        if a := (d.get("message") or {}).get("abstract"):
            return a, "crossref"
    time.sleep(0.3)

    q = urllib.parse.quote(f'DOI:"{doi}"')
    if d := _curl(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search"
                  f"?query={q}&resultType=core&format=json&pageSize=1"):
        res = ((d.get("resultList") or {}).get("result") or [])
        if res and res[0].get("abstractText"):
            return res[0]["abstractText"], "europepmc"
    time.sleep(0.3)

    if d := _curl(f"https://api.semanticscholar.org/graph/v1/paper/"
                  f"DOI:{urllib.parse.quote(doi, safe='')}?fields=abstract"):
        if a := d.get("abstract"):
            return a, "semanticscholar"
    return None, ""


def cmd_fetch(args) -> int:
    d = load_refs()
    got = skip = none = 0
    for r in d["references"]:
        if r["type"] != "article" or not r.get("doi"):
            continue
        if r.get("abstract") and not args.force:
            skip += 1
            continue
        abstract, origin = abstract_for(r["doi"])
        if abstract:
            r["abstract"] = normalize(abstract)
            r["abstract_source"] = origin
            r.pop("abstract_available", None)
            got += 1
            print(f"  ok    {r['id']:<24} {len(r['abstract']):>5}자  [{origin}]")
        else:
            r["abstract_available"] = False
            none += 1
            print(f"  --    {r['id']:<24} 초록 미제공")
        time.sleep(0.3)
    dump_refs(d)
    print(f"\n초록 {got}건 캐시 / 건너뜀 {skip} / 미제공 {none}")
    if none:
        print("미제공 출처는 초록 대조가 불가능합니다 — locator 에 쪽수를 쓰고 사람이 서명하세요.")
    return 0


# ────────────────────────────── init ──────────────────────────────

def cmd_init(args) -> int:
    matches = [p for p in scripts() if p.name.startswith(args.episode)]
    if not matches:
        print(f"대본 없음: {args.episode}", file=sys.stderr)
        return 1
    path = matches[0]
    fm, body = parse(path)
    refs = {r["id"]: r for r in load_refs()["references"]}
    used = list(dict.fromkeys(body_markers(body)))
    existing = {a["source"] for a in (fm.get("attest") or [])}

    todo = [s for s in used if s not in existing]
    if not todo:
        print(f"{args.episode}: 모든 마커에 근거 항목이 이미 있습니다")
        return 0

    print(f"# {args.episode} — 아래를 front matter 의 attest: 아래에 붙여넣고 채우세요\n")
    print("attest:")
    for sid in todo:
        r = refs.get(sid, {})
        has_abs = bool(r.get("abstract"))
        loc = "abstract" if has_abs else "p.???"
        hint = ("초록에 있는 문장을 그대로" if has_abs
                else "초록 미제공 — 본문에서 인용하고 쪽수를 쓸 것")
        print(f"""  - source: {sid}
    supports: "이 출처가 뒷받침하는 내용 (한국어, 대본 문장에 대응)"
    quote: "원문 그대로의 문장 — {hint}"
    locator: {loc}
    checked_by: ""           # 원문을 확인한 사람. 비우면 check 에서 차단
    checked: {dt.date.today().isoformat()}""")
    print("\n# quote 는 반드시 원문 그대로. 요약하면 attest check 에서 실패합니다.")
    return 0


# ────────────────────────────── check ──────────────────────────────

def cmd_check(args) -> int:
    refs = {r["id"]: r for r in load_refs()["references"]}
    errors: list[str] = []
    warnings: list[str] = []
    stats = {"machine": 0, "human": 0, "total": 0}

    for path in scripts():
        rel = path.relative_to(ROOT)
        fm, body = parse(path)
        used = list(dict.fromkeys(body_markers(body)))
        attests = {a["source"]: a for a in (fm.get("attest") or []) if isinstance(a, dict)}

        if fm.get("logic_only") and not used:
            continue

        # 초안 단계에서 근거가 비어 있는 건 정상이다. 막아야 할 지점은 발행이다.
        # docs/05-production-pipeline.md 의 게이트 구조와 같은 원칙.
        draft = fm.get("status") == "drafted"
        sink = warnings if draft else errors
        tag = "[초안] " if draft else ""

        for sid in used:
            stats["total"] += 1
            a = attests.get(sid)
            if not a:
                sink.append(f"{tag}{rel}: [{sid}] 인용에 근거 항목(attest)이 없음 — "
                              f"`attest init {fm['id']}` 로 뼈대를 만드세요")
                continue
            for field in ("supports", "quote", "locator"):
                if not a.get(field):
                    sink.append(f"{tag}{rel}: attest[{sid}] 에 '{field}' 없음")
            if not a.get("quote") or not a.get("locator"):
                continue

            ref = refs.get(sid, {})
            abstract = ref.get("abstract")
            loc = str(a["locator"]).strip().lower()

            if loc == ABSTRACT_LOCATOR and abstract:
                # 지어낸 인용을 잡는 지점
                if normalize(a["quote"]) in abstract:
                    stats["machine"] += 1
                else:
                    errors.append(
                        f"{rel}: attest[{sid}] 의 quote 가 초록에 없습니다. "
                        f"원문 그대로인지 확인하거나, 본문 인용이면 locator 를 쪽수로 바꾸세요")
            elif loc == ABSTRACT_LOCATOR and not abstract:
                sink.append(f"{tag}{rel}: attest[{sid}] locator 가 abstract 인데 초록이 없습니다 — "
                              f"`attest fetch` 실행 후에도 없으면 본문 쪽수를 쓰세요")
            else:
                # 기계가 확인할 수 없음 → 사람 서명 필수
                if not a.get("checked_by"):
                    sink.append(f"{tag}{rel}: attest[{sid}] 는 기계 확인 불가(locator={a['locator']}). "
                                  f"원문을 확인한 사람을 checked_by 에 적으세요")
                else:
                    stats["human"] += 1

            # 오래된 확인은 경고 — 논문이 철회·정정됐을 수 있음
            if a.get("checked"):
                try:
                    age = (dt.date.today() - dt.date.fromisoformat(str(a["checked"]))).days
                    if age > 365:
                        warnings.append(f"{rel}: attest[{sid}] 확인일이 {age}일 전 — 재확인 권장")
                except ValueError:
                    sink.append(f"{tag}{rel}: attest[{sid}] 의 checked 날짜 형식 오류 (YYYY-MM-DD)")

        for sid in set(attests) - set(used):
            warnings.append(f"{rel}: attest[{sid}] 가 본문에서 인용되지 않음")

    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}", file=sys.stderr)

    print(f"\n인용 {stats['total']}건 — 기계 대조 {stats['machine']} / 사람 서명 {stats['human']} "
          f"/ 미비 {stats['total'] - stats['machine'] - stats['human']}")
    print(f"오류 {len(errors)}건, 경고 {len(warnings)}건")
    if any("[초안]" in w for w in warnings):
        print("초안(status: drafted)의 근거 미비는 경고입니다. "
              "status 를 recorded/published 로 올리기 전에 채우세요.")
    if errors:
        print("근거 대조 실패. 발행 불가.", file=sys.stderr)
        return 1
    print("통과.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="Crossref 초록 캐시")
    f.add_argument("--force", action="store_true")
    f.set_defaults(func=cmd_fetch)

    i = sub.add_parser("init", help="대본의 마커로 근거 항목 뼈대 생성")
    i.add_argument("episode")
    i.set_defaults(func=cmd_init)

    c = sub.add_parser("check", help="근거 대조 검사")
    c.set_defaults(func=cmd_check)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
