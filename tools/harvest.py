#!/usr/bin/env python3
"""harvest — Crossref에서 새 레퍼런스 후보를 정기 수집.

    python3 tools/harvest.py run [--since 2026-06-01] [--topic genetics]
    python3 tools/harvest.py promote <DOI> [--claims C003] [--note "..."]
    python3 tools/harvest.py inbox            수집함 현황
    python3 tools/harvest.py drop <DOI>       후보 기각 (다시 올라오지 않음)

수집 결과는 **자동 등재되지 않습니다.** content/inbox/ 에 후보로 쌓이고,
사람이 읽고 `promote` 해야 references.yaml 에 들어갑니다.
초록만 읽고 등재하지 않는다는 편집 정책 §2를 도구로 강제하는 구조입니다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "content" / "harvest_queries.yaml"
REFS = ROOT / "content" / "references.yaml"
INBOX = ROOT / "content" / "inbox"
SEEN = INBOX / "seen.yaml"

UA = "saltube-harvest/1.0 (https://github.com/BudongJW/saltube; mailto:dlawodnjs@mju.ac.kr)"
API = "https://api.crossref.org/works"

# 동료평가 논문만. F1000 추천글·초록집·정오표 등은 제외.
ALLOWED_TYPES = {"journal-article"}
# 제목에 이런 문자열이 있으면 실제 논문이 아닌 부산물일 가능성이 높음
NOISE = ("Faculty Opinions recommendation", "Correction to", "Corrigendum",
         "Erratum", "Retraction", "Editorial Expression of Concern")


def load_yaml(p: Path, default=None):
    if not p.exists():
        return default
    return yaml.safe_load(p.read_text(encoding="utf-8")) or default


def dump_yaml(p: Path, data) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.dump(data, allow_unicode=True, sort_keys=False,
                           width=100, default_flow_style=False), encoding="utf-8")


def fetch(url: str) -> dict | None:
    r = subprocess.run(["curl", "-sS", "--max-time", "40", url, "-H", f"User-Agent: {UA}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def known_dois() -> set[str]:
    """이미 등재됐거나 한 번 기각한 DOI — 다시 올리지 않습니다."""
    refs = load_yaml(REFS, {"references": []})["references"]
    out = {(r.get("doi") or "").lower() for r in refs if r.get("doi")}
    seen = load_yaml(SEEN, {"promoted": [], "dropped": []})
    out |= {d.lower() for d in seen.get("promoted", [])}
    out |= {d.lower() for d in seen.get("dropped", [])}
    return out


def clean(s: str) -> str:
    import re
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ────────────────────────────── run ──────────────────────────────

def cmd_run(args) -> int:
    cfg = load_yaml(QUERIES)
    defaults = cfg.get("defaults", {})
    rows = args.rows or defaults.get("rows", 20)
    since = args.since or (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    since_year = int(since[:4])
    min_score = args.min_score if args.min_score is not None else defaults.get("min_score", 12)
    skip = known_dois()

    queries = cfg["queries"]
    if args.topic:
        queries = [q for q in queries if q.get("topic") == args.topic]
    if args.query_id:
        queries = [q for q in queries if q["id"] == args.query_id]
    if not queries:
        print("해당하는 질의가 없습니다", file=sys.stderr)
        return 1

    print(f"수집 시작 — 질의 {len(queries)}건, {since} 이후 발행분, 관련도 {min_score} 이상\n")
    candidates: dict[str, dict] = {}

    for q in queries:
        # 관련도 정렬(기본값)을 쓴다. sort=published 로 하면 관련도 순위가 버려지고
        # 발행일이 오염된 레코드(연도 2121 등)가 상위를 차지한다. 날짜는 필터로만 제한.
        url = (f"{API}?query.bibliographic={urllib.parse.quote(q['query'])}"
               f"&filter=from-pub-date:{since},type:journal-article"
               f"&rows={rows}&sort=relevance"
               "&select=DOI,title,author,issued,short-container-title,container-title,"
               "type,is-referenced-by-count,score")
        payload = fetch(url)
        if not payload:
            print(f"  {q['id']:<20} 조회 실패", file=sys.stderr)
            time.sleep(0.5)
            continue

        found = dropped = 0
        for it in payload["message"]["items"]:
            doi = it["DOI"].lower()
            if doi in skip or it.get("type") not in ALLOWED_TYPES:
                continue
            title = clean((it.get("title") or [""])[0])
            if not title or any(n.lower() in title.lower() for n in NOISE):
                continue
            # 관련도가 낮으면 주제와 무관한 결과다
            if it.get("score", 0) < min_score:
                dropped += 1
                continue
            # Crossref 에는 발행일이 오염된 레코드가 있다 (연도 2121 등)
            yr = (it.get("issued", {}).get("date-parts", [[None]])[0] or [None])[0]
            if not yr or not (since_year - 1 <= yr <= dt.date.today().year + 1):
                dropped += 1
                continue

            if doi in candidates:
                candidates[doi]["matched"].append(q["id"])
                for c in q["claims"]:
                    if c not in candidates[doi]["suggested_claims"]:
                        candidates[doi]["suggested_claims"].append(c)
                continue

            names = [a.get("family", "") for a in (it.get("author") or []) if a.get("family")]
            authors = (f"{names[0]} 외 {len(names)-1}인" if len(names) > 3
                       else ", ".join(names) or "(단체 저자)")
            container = ((it.get("container-title") or [""])[0]
                         if len((it.get("short-container-title") or [""])[0]) < 6
                         else (it.get("short-container-title") or [""])[0])
            candidates[doi] = {
                "doi": it["DOI"],
                "title": title,
                "authors": authors,
                "year": yr,
                "container": container,
                "cited_by": it.get("is-referenced-by-count", 0),
                "score": round(it.get("score", 0), 1),
                "matched": [q["id"]],
                "suggested_claims": list(q["claims"]),
                "topic": q.get("topic"),
            }
            found += 1

        print(f"  {q['id']:<20} 신규 {found:>3}건  (관련도·연도 미달 {dropped}건 제외)")
        time.sleep(0.5)

    if not candidates:
        print("\n신규 후보 없음.")
        return 0

    # 여러 질의에 걸린 것 → 우리 관심사와 겹침이 큼. 그 다음 인용수.
    ranked = sorted(candidates.values(),
                    key=lambda c: (-len(c["matched"]), -c["score"], -c["cited_by"]))

    out = INBOX / f"{dt.date.today().isoformat()}.yaml"
    dump_yaml(out, {
        "harvested": dt.date.today().isoformat(),
        "since": since,
        "count": len(ranked),
        "howto": "검토 후: python3 tools/harvest.py promote <DOI> --claims C003 --note '...'  "
                 "/ 기각: python3 tools/harvest.py drop <DOI>",
        "candidates": ranked,
    })
    print(f"\n신규 후보 {len(ranked)}건 → {out.relative_to(ROOT)}")
    print("\n상위 후보:")
    for c in ranked[:8]:
        print(f"  [질의 {len(c['matched'])} · 관련도 {c['score']:>5} · 인용 {c['cited_by']:>3}] "
              f"{c['authors']} ({c['year']}) "
              f"{c['container'][:26]}\n      {c['title'][:88]}\n      doi:{c['doi']}")
    print("\n※ 자동 등재되지 않습니다. 원문을 읽고 promote 하세요 (편집 정책 §2).")
    return 0


# ────────────────────────────── promote / drop ──────────────────────────────

def _find_candidate(doi: str) -> dict | None:
    for f in sorted(INBOX.glob("*.yaml"), reverse=True):
        if f.name == "seen.yaml":
            continue
        for c in (load_yaml(f, {}) or {}).get("candidates", []):
            if c["doi"].lower() == doi.lower():
                return c
    return None


def _mark(doi: str, bucket: str) -> None:
    seen = load_yaml(SEEN, {"promoted": [], "dropped": []})
    seen.setdefault(bucket, [])
    if doi not in seen[bucket]:
        seen[bucket].append(doi)
    dump_yaml(SEEN, seen)


def cmd_promote(args) -> int:
    cand = _find_candidate(args.doi)
    if not cand:
        print(f"수집함에서 찾을 수 없습니다: {args.doi}", file=sys.stderr)
        return 1

    data = load_yaml(REFS)
    if any((r.get("doi") or "").lower() == args.doi.lower() for r in data["references"]):
        print("이미 references.yaml 에 있습니다", file=sys.stderr)
        return 1

    claims = args.claims or cand["suggested_claims"]
    first = cand["authors"].split(",")[0].split(" 외")[0].upper()
    rid = args.id or f"S-{''.join(ch for ch in first if ch.isalpha())[:10]}-{cand['year']}"

    data["references"].append({
        "id": rid,
        "type": "article",
        "doi": cand["doi"],
        "topic": args.topic or cand.get("topic") or "evolution",
        "used_for": claims,
        "note": args.note or f"harvest {dt.date.today().isoformat()} 수집",
    })
    dump_yaml(REFS, data)
    _mark(cand["doi"], "promoted")
    print(f"등재: {rid}  (claims: {', '.join(claims)})")
    print("다음: python3 tools/refcheck.py verify && python3 tools/refcheck.py render")
    return 0


def cmd_drop(args) -> int:
    _mark(args.doi, "dropped")
    print(f"기각: {args.doi} — 다음 수집에 다시 올라오지 않습니다")
    return 0


def cmd_inbox(args) -> int:
    files = [f for f in sorted(INBOX.glob("*.yaml"), reverse=True) if f.name != "seen.yaml"]
    if not files:
        print("수집함이 비어 있습니다. `harvest run` 을 실행하세요.")
        return 0
    seen = load_yaml(SEEN, {"promoted": [], "dropped": []})
    handled = {d.lower() for d in seen.get("promoted", []) + seen.get("dropped", [])}
    print(f"수집 파일 {len(files)}개 · 처리 완료 {len(handled)}건\n")
    for f in files[:args.limit]:
        d = load_yaml(f, {}) or {}
        pending = [c for c in d.get("candidates", []) if c["doi"].lower() not in handled]
        print(f"  {f.name}  후보 {d.get('count', 0)}건 · **미처리 {len(pending)}건**")
        for c in pending[:args.show]:
            print(f"      doi:{c['doi']}  {c['authors']} ({c['year']}) — {c['title'][:62]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="Crossref에서 신규 후보 수집")
    r.add_argument("--since", help="이 날짜 이후 발행분 (YYYY-MM-DD)")
    r.add_argument("--days", type=int, default=120, help="--since 미지정 시 최근 N일 (기본 120)")
    r.add_argument("--topic", help="특정 topic 만")
    r.add_argument("--query-id", help="특정 질의 하나만")
    r.add_argument("--rows", type=int, help="질의당 최대 건수")
    r.add_argument("--min-score", type=float, help="Crossref 관련도 최소값 (기본 12)")
    r.set_defaults(func=cmd_run)

    p = sub.add_parser("promote", help="후보를 references.yaml 에 등재")
    p.add_argument("doi")
    p.add_argument("--id", help="레퍼런스 ID (미지정 시 자동 생성)")
    p.add_argument("--claims", nargs="+", help="연결할 주장 ID")
    p.add_argument("--topic")
    p.add_argument("--note")
    p.set_defaults(func=cmd_promote)

    d = sub.add_parser("drop", help="후보 기각")
    d.add_argument("doi")
    d.set_defaults(func=cmd_drop)

    i = sub.add_parser("inbox", help="수집함 현황")
    i.add_argument("--limit", type=int, default=5)
    i.add_argument("--show", type=int, default=5)
    i.set_defaults(func=cmd_inbox)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
