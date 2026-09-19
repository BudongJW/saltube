#!/usr/bin/env python3
"""refcheck — 레퍼런스를 Crossref로 검증하고 sources.md를 생성.

    python3 tools/refcheck.py verify [--force]   DOI를 Crossref로 검증·메타데이터 기록
    python3 tools/refcheck.py render             content/sources.md 재생성
    python3 tools/refcheck.py search "질의"       새 레퍼런스의 DOI 찾기
    python3 tools/refcheck.py status             검증 현황 요약

원칙: 서지 메타데이터를 손으로 적지 않습니다. Crossref가 채웁니다.
기억에서 적은 DOI는 틀릴 수 있고, 틀린 인용은 이 채널이 가장 크게 잃는 실수입니다.
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
SOURCES = ROOT / "content" / "sources.md"
CLAIMS = ROOT / "content" / "claims.yaml"

# Crossref는 연락처가 있는 요청을 우선 처리합니다 (polite pool).
UA = "saltube-refcheck/1.0 (https://github.com/BudongJW/saltube; mailto:dlawodnjs@mju.ac.kr)"
API = "https://api.crossref.org/works"

TOPIC_LABEL = {
    "paleontology": "고생물학", "geology": "지질학", "geochronology": "연대측정",
    "genetics": "유전학", "evolution": "진화생물학", "biology": "생물학",
    "astronomy": "천문학", "cosmology": "우주론", "physics": "물리학",
    "methodology": "과학방법론", "legal": "판례", "history": "과학사",
}
TOPIC_ORDER = ["paleontology", "geology", "geochronology", "genetics", "evolution",
               "biology", "astronomy", "cosmology", "physics", "methodology",
               "legal", "history"]


def load() -> dict:
    return yaml.safe_load(REFS.read_text(encoding="utf-8"))


def fetch(url: str) -> dict | None:
    r = subprocess.run(["curl", "-sS", "--max-time", "30", url, "-H", f"User-Agent: {UA}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def clean_title(s: str) -> str:
    """Crossref 제목에 섞인 HTML 태그와 줄바꿈·연속 공백을 제거."""
    s = re.sub(r"<[^>]+>", "", s)                 # <i>, <sub> 등
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return re.sub(r"\s+", " ", s).strip()


def summarize(msg: dict, override: str | None = None) -> dict:
    """Crossref 레코드에서 인용에 필요한 필드만 추출.

    컨소시엄 논문(EPICA, 침팬지 게놈 등)은 Crossref에 개인 저자가 없어
    publisher 이름이 저자 자리에 들어옵니다. 그런 항목은 references.yaml의
    authors_override로 정확한 단체명을 지정합니다.
    """
    authors = msg.get("author") or []
    names = [f"{a.get('family', '')}".strip() for a in authors if a.get("family")]
    if override:
        author_str = override
    elif len(names) > 3:
        author_str = f"{names[0]} 외 {len(names) - 1}인"
    elif names:
        author_str = ", ".join(names)
    else:
        author_str = "(단체 저자 — references.yaml에 authors_override 지정 필요)"
    issued = msg.get("issued", {}).get("date-parts", [[None]])[0]
    short = (msg.get("short-container-title") or [""])[0]
    full = (msg.get("container-title") or [""])[0]
    # 일부 저널은 short-container-title이 'gsr' 같은 비표준 약어라 화면 인용에 부적합
    container = full if (len(short) < 6 and full) else (short or full)
    return {
        "authors": author_str,
        "author_count": len(names),
        "title": clean_title((msg.get("title") or [""])[0]),
        "container": container,
        "year": issued[0] if issued else None,
        "volume": msg.get("volume"),
        "page": msg.get("page"),
        "type": msg.get("type"),
    }


# ────────────────────────────── verify ──────────────────────────────

def cmd_verify(args) -> int:
    data = load()
    today = dt.date.today().isoformat()
    ok = failed = skipped = manual = 0
    mismatches: list[str] = []

    for ref in data["references"]:
        rid = ref["id"]
        if ref["type"] != "article":
            manual += 1
            continue
        if ref.get("verified", {}).get("status") == "ok" and not args.force:
            skipped += 1
            continue

        doi = ref.get("doi")
        if not doi:
            print(f"  ERROR {rid}: type=article인데 doi 없음", file=sys.stderr)
            failed += 1
            continue

        payload = fetch(f"{API}/{urllib.parse.quote(doi, safe='')}")
        if not payload or payload.get("status") != "ok":
            print(f"  FAIL  {rid}  doi:{doi} — Crossref에서 찾을 수 없음", file=sys.stderr)
            ref["verified"] = {"status": "not_found", "checked": today}
            failed += 1
            time.sleep(0.4)
            continue

        meta = summarize(payload["message"], ref.get("authors_override"))
        meta["status"] = "ok"
        meta["checked"] = today
        ref["verified"] = meta
        ok += 1

        # id에 박아둔 연도와 실제 발행연도가 다르면 경고 (온라인/인쇄 발행 차이)
        parts = rid.rsplit("-", 1)
        if len(parts) == 2 and parts[1].isdigit() and meta["year"]:
            if int(parts[1]) != meta["year"]:
                mismatches.append(f"{rid}: id는 {parts[1]}, Crossref 발행연도는 {meta['year']}")

        print(f"  ok    {rid:<24} {meta['authors'][:22]:<24} {meta['year']}  {meta['container'][:26]}")
        time.sleep(0.4)

    REFS.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, width=100, default_flow_style=False),
        encoding="utf-8")

    for m in mismatches:
        print(f"  warn  연도 불일치 — {m}")
    print(f"\n검증 {ok}건 / 실패 {failed}건 / 건너뜀 {skipped}건 / 사람 확인 필요 {manual}건")
    if failed:
        print("실패 항목의 DOI를 확인하세요. `refcheck search`로 올바른 DOI를 찾을 수 있습니다.",
              file=sys.stderr)
        return 1
    return 0


# ────────────────────────────── search ──────────────────────────────

def cmd_search(args) -> int:
    q = urllib.parse.quote(args.query)
    payload = fetch(f"{API}?query.bibliographic={q}&rows={args.rows}"
                    "&select=DOI,title,author,issued,short-container-title,container-title,type")
    if not payload:
        print("검색 실패 — 네트워크를 확인하세요", file=sys.stderr)
        return 1
    items = payload["message"]["items"]
    if not items:
        print("결과 없음")
        return 0
    for it in items:
        m = summarize(it)
        # 동료평가 논문이 아닌 항목(F1000 추천글 등)은 표시해 걸러낼 수 있게 함
        tag = "" if m["type"] == "journal-article" else f"  [{m['type']}]"
        print(f"\n  doi:{it['DOI']}{tag}")
        print(f"    {m['authors']} ({m['year']}) {m['container']}")
        print(f"    {m['title'][:96]}")
    return 0


# ────────────────────────────── render ──────────────────────────────

def cite(ref: dict) -> str:
    v = ref.get("verified") or {}
    if v.get("status") == "ok":
        bits = f"{v['authors']} ({v['year']}). \"{v['title']}\". *{v['container']}*"
        if v.get("volume"):
            bits += f" {v['volume']}"
        if v.get("page"):
            bits += f", {v['page']}"
        return bits + "."
    return ref.get("citation", "(서지사항 미기재)")


def ident(ref: dict) -> str:
    if ref.get("doi"):
        return f"doi:{ref['doi']}"
    if ref.get("isbn"):
        return f"ISBN {ref['isbn']}"
    if ref.get("pmid"):
        return f"PMID {ref['pmid']}"
    if ref.get("url"):
        return ref["url"]
    return "—"


def cmd_render(args) -> int:
    data = load()
    refs = data["references"]
    claims = {c["id"]: c for c in yaml.safe_load(CLAIMS.read_text(encoding="utf-8"))["claims"]}
    today = dt.date.today().isoformat()

    n_ok = sum(1 for r in refs if (r.get("verified") or {}).get("status") == "ok")
    n_manual = sum(1 for r in refs if r["type"] != "article")
    n_manual_done = sum(1 for r in refs if r["type"] != "article" and r.get("manual_checked"))

    L = [
        "# 출처 마스터 목록",
        "",
        "> ⚠️ **이 파일은 자동 생성됩니다. 직접 편집하지 마세요.**",
        "> 원장은 [`content/references.yaml`](references.yaml)이고, 아래 명령으로 재생성합니다.",
        "> ```bash",
        "> python3 tools/refcheck.py verify   # Crossref 검증",
        "> python3 tools/refcheck.py render   # 이 파일 재생성",
        "> ```",
        "",
        f"생성 시각: {today} · 총 {len(refs)}건 "
        f"· **Crossref 검증 완료 {n_ok}건** · 사람 확인 필요 {n_manual - n_manual_done}건",
        "",
        "## 검증 수준",
        "",
        "| 표시 | 의미 |",
        "|---|---|",
        "| ✅ | Crossref API로 DOI·저자·제목·저널·연도 **기계 검증 완료**. 서지사항은 Crossref 레코드 그대로 |",
        "| ☐ | 단행본·판례·기관 자료. 기계 검증 불가 — **인용 전 사람이 원문 확인 필요** |",
        "",
        "> ✅는 **그 문헌이 실재하고 서지사항이 정확하다**는 뜻이지,",
        "> **우리가 그 논문을 올바르게 해석했다는 뜻이 아닙니다.**",
        "> 대본에 쓰기 전 원문 대조(편집 정책 §2 2단계)는 여전히 필요합니다.",
        "",
        "## 규칙",
        "",
        "1. **1차 출처만.** 논문·학술서·정부/연구기관 데이터·판결문.",
        "2. 블로그·위키백과·유튜브는 배경 조사용. 등재 불가.",
        "3. 새 레퍼런스는 `refcheck search`로 DOI를 찾아 `references.yaml`에 추가 후 `verify`.",
        "4. 초록만 읽고 등재 금지. → [편집 정책](../docs/03-editorial-policy.md) §2",
        "",
        "---",
        "",
    ]

    by_topic: dict[str, list[dict]] = {}
    for r in refs:
        by_topic.setdefault(r["topic"], []).append(r)

    for topic in TOPIC_ORDER + [t for t in by_topic if t not in TOPIC_ORDER]:
        group = by_topic.get(topic)
        if not group:
            continue
        L += [f"## {TOPIC_LABEL.get(topic, topic)}", "",
              "| | ID | 서지사항 | 식별자 | 사용처 |", "|---|---|---|---|---|"]
        for r in sorted(group, key=lambda x: x["id"]):
            mark = "✅" if (r.get("verified") or {}).get("status") == "ok" else (
                "✅" if r.get("manual_checked") else "☐")
            used = ", ".join(r.get("used_for") or []) or "—"
            L.append(f"| {mark} | `{r['id']}` | {cite(r)} | {ident(r)} | {used} |")
        L.append("")
        notes = [r for r in group if r.get("note")]
        if notes:
            L.append("<details><summary>메모</summary>\n")
            for r in notes:
                L.append(f"- **`{r['id']}`** — {r['note']}")
            L.append("\n</details>\n")

    # 주장별 역색인 — 대본 쓸 때 "이 주장의 출처가 뭐였지"를 바로 찾기 위함
    L += ["---", "", "## 주장별 역색인", "",
          "`claims.yaml`의 각 주장에 어떤 출처가 붙어 있는지.", "",
          "| 주장 | 내용 | 출처 |", "|---|---|---|"]
    index: dict[str, list[str]] = {}
    for r in refs:
        for c in r.get("used_for") or []:
            index.setdefault(c, []).append(r["id"])
    for cid in sorted(index):
        claim = claims.get(cid, {})
        text = claim.get("claim", "(claims.yaml에 없음)")
        if len(text) > 34:
            text = text[:33] + "…"
        L.append(f"| `{cid}` | {text} | {', '.join(f'`{s}`' for s in sorted(index[cid]))} |")
    orphan = sorted(set(claims) - set(index))
    L += ["",
          f"**출처 미확보 주장 {len(orphan)}건**: "
          + (", ".join(f"`{c}`" for c in orphan) if orphan else "없음"),
          "",
          "> 미확보 주장은 대본 작성 전에 `refcheck search`로 출처를 찾아 등재해야 합니다.",
          "> 출처 없는 대본은 `claimctl validate`에서 차단됩니다.",
          ""]

    # 국내 자료 — 기계 수집 불가. 대결 포맷의 자료 수집 프로토콜과 연결
    L += ["---", "", "## 국내 자료 (직접 수집 필요)", "",
          "채널의 핵심 차별점은 **국내 유통 주장을 직접 인용해 반박**하는 것입니다.",
          "이 영역은 자동 수집이 불가능하며, 수집 규칙은",
          "[11 대결 포맷](../docs/11-format-confrontation.md) §4를 따릅니다.", "",
          "```",
          "☐ 한국창조과학회 공식 간행물·웹 게시물",
          "☐ 교과서 개정 관련 청원·보도자료      ← 공익성 입증이 가장 쉬운 최우선 소재",
          "☐ 학교·공공기관 창조과학 강연 배포 자료",
          "☐ 국내 학술단체 공식 입장문",
          "```", "",
          "수집 시 **원문 캡처·URL·접근 날짜·아카이브 주소·앞뒤 문맥**을 함께 보관하세요.",
          "`named_target` 대본은 이 항목들이 없으면 `claimctl validate`에서 차단됩니다.", ""]

    SOURCES.write_text("\n".join(L), encoding="utf-8")
    print(f"content/sources.md 생성 — {len(refs)}건 (검증 {n_ok}건), 미확보 주장 {len(orphan)}건")
    return 0


# ────────────────────────────── status ──────────────────────────────

def cmd_status(args) -> int:
    refs = load()["references"]
    ok = [r for r in refs if (r.get("verified") or {}).get("status") == "ok"]
    bad = [r for r in refs if (r.get("verified") or {}).get("status") == "not_found"]
    pend = [r for r in refs if r["type"] == "article" and not r.get("verified")]
    manual = [r for r in refs if r["type"] != "article" and not r.get("manual_checked")]
    print(f"전체 {len(refs)}건")
    print(f"  ✅ Crossref 검증 완료   {len(ok)}")
    print(f"  ❌ DOI 확인 실패        {len(bad)}")
    print(f"  ⏳ 미검증(article)      {len(pend)}")
    print(f"  ☐  사람 확인 필요       {len(manual)}")
    for r in bad:
        print(f"    실패: {r['id']}  doi:{r.get('doi')}")
    if manual:
        print("\n  사람이 원문을 확인한 뒤 references.yaml에 manual_checked: true 를 기록하세요:")
        for r in manual:
            print(f"    {r['id']:<22} ({r['type']})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="DOI를 Crossref로 검증")
    v.add_argument("--force", action="store_true", help="검증 완료 항목도 다시 조회")
    v.set_defaults(func=cmd_verify)

    s = sub.add_parser("search", help="Crossref에서 레퍼런스 검색")
    s.add_argument("query")
    s.add_argument("--rows", type=int, default=5)
    s.set_defaults(func=cmd_search)

    r = sub.add_parser("render", help="content/sources.md 재생성")
    r.set_defaults(func=cmd_render)

    t = sub.add_parser("status", help="검증 현황")
    t.set_defaults(func=cmd_status)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
