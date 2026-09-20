#!/usr/bin/env python3
"""fetchmedia — 자유 라이선스 이미지를 검색·내려받고 출처를 기록합니다.

    python3 tools/fetchmedia.py search "Tiktaalik"
    python3 tools/fetchmedia.py get <번호> --ep EP003 --name tiktaalik
    python3 tools/fetchmedia.py credits           수집한 자료의 출처·라이선스 목록

소스 (둘 다 API 키 불필요)
    Wikimedia Commons  — 화석·복원도·표본 사진이 가장 풍부
    Openverse          — CC 통합 검색 (Flickr, 박물관 등)

Pexels/Unsplash 는 일반 스톡이라 과학 소재가 거의 없고 API 키도 필요해 넣지 않았습니다.
쓰려면 키를 받아 이 파일에 소스를 추가하세요.

**라이선스 기록이 강제됩니다.** 내려받은 자료는 assets/CREDITS.yaml 에
저작자·라이선스·원본 URL 이 남습니다 — docs/09-risk-and-compliance.md §1
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CREDITS = ASSETS / "CREDITS.yaml"
CACHE = ROOT / ".fetchmedia-last.json"
UA = "saltube/1.0 (https://github.com/BudongJW/saltube; mailto:dlawodnjs@mju.ac.kr)"

# 상업적 이용·개작이 자유로운 라이선스만. ND(개작금지)와 NC(비상업)는 제외합니다 —
# 영상에 얹어 편집하고 플랫폼 수익화를 열 수 있어야 하므로.
OK_LICENSE = re.compile(r"^(cc0|pd|public domain|cc[ -]?by([ -]sa)?)", re.I)
BAD = re.compile(r"(nc|nd)\b", re.I)


def curl(url: str) -> dict | None:
    r = subprocess.run(["curl", "-sS", "--max-time", "35", "-A", UA, url],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def license_ok(name: str) -> bool:
    return bool(OK_LICENSE.match(name or "")) and not BAD.search(name or "")


def search_commons(q: str, limit: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": q,
        "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo",
        "iiprop": "url|extmetadata|size", "iiurlwidth": 1920, "format": "json"})
    d = curl(f"https://commons.wikimedia.org/w/api.php?{params}")
    out = []
    for p in ((d or {}).get("query", {}).get("pages") or {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        m = ii.get("extmetadata", {})
        # 요청 폭이 원본보다 크면 Commons 가 썸네일 대신 오류 페이지를 줍니다.
        w = ii.get("width") or 0
        url = ii.get("thumburl") if (ii.get("thumburl") and w > 1920) else ii.get("url")
        out.append({
            "source": "commons",
            "title": p["title"].removeprefix("File:"),
            "url": url,
            "page": ii.get("descriptionurl", ""),
            "w": ii.get("width"), "h": ii.get("height"),
            "license": clean(m.get("LicenseShortName", {}).get("value", "")),
            "author": clean(m.get("Artist", {}).get("value", "")),
        })
    return out


def search_openverse(q: str, limit: int) -> list[dict]:
    params = urllib.parse.urlencode({"q": q, "page_size": limit,
                                     "license_type": "commercial,modification"})
    d = curl(f"https://api.openverse.org/v1/images/?{params}")
    out = []
    for r in (d or {}).get("results", []):
        lic = f"{r.get('license','')} {r.get('license_version','')}".strip()
        out.append({
            "source": "openverse",
            "title": r.get("title", "?"),
            "url": r.get("url"),
            "page": r.get("foreign_landing_url", ""),
            "w": r.get("width"), "h": r.get("height"),
            "license": "CC " + lic.upper() if lic else "?",
            "author": r.get("creator", "?"),
        })
    return out


def cmd_search(args) -> int:
    rows = search_commons(args.query, args.limit) + search_openverse(args.query, args.limit)
    # 세로 영상용이므로 해상도가 충분한 것 우선
    # 해상도 내림차순. 동률이면 제목순으로 고정해 실행할 때마다 순서가 흔들리지 않게.
    rows.sort(key=lambda r: (-((r.get("w") or 0) * (r.get("h") or 0)),
                             r["source"], r["title"]))
    CACHE.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

    print(f"'{args.query}' — {len(rows)}건\n")
    for i, r in enumerate(rows, 1):
        ok = license_ok(r["license"])
        mark = "✅" if ok else "⚠ "
        print(f"{i:>3}. {mark} [{r['source']:<9}] {r['title'][:52]}")
        print(f"      {r['w']}x{r['h']}  ·  {r['license']}  ·  {r['author'][:40]}")
    print("\n✅ = 상업적 이용·개작 가능. ⚠ 는 조건을 직접 확인하세요.")
    print(f"내려받기: python3 tools/fetchmedia.py get <번호> --ep EP003 --name <파일명>")
    return 0


def cmd_get(args) -> int:
    if not CACHE.exists():
        print("먼저 search 를 실행하세요", file=sys.stderr)
        return 1
    rows = json.loads(CACHE.read_text(encoding="utf-8"))
    if not (1 <= args.index <= len(rows)):
        print(f"번호는 1~{len(rows)} 사이여야 합니다", file=sys.stderr)
        return 1
    r = rows[args.index - 1]

    if not license_ok(r["license"]) and not args.force:
        print(f"라이선스 '{r['license']}' 는 자동 승인 대상이 아닙니다.\n"
              f"  원본 페이지에서 조건을 확인하고, 괜찮으면 --force 로 다시 실행하세요.\n"
              f"  {r['page']}", file=sys.stderr)
        return 1

    dst_dir = ASSETS / args.ep
    dst_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(urllib.parse.urlparse(r["url"]).path).suffix or ".jpg"
    dst = dst_dir / f"{args.name}{ext}"
    rc = subprocess.run(["curl", "-sSL", "--max-time", "90", "-A", UA,
                         "-o", str(dst), r["url"]]).returncode
    if rc != 0 or not dst.exists() or dst.stat().st_size == 0:
        print("내려받기 실패", file=sys.stderr)
        dst.unlink(missing_ok=True)
        return 1
    # 크기만 보면 오류 HTML 을 이미지로 착각합니다. 매직 바이트로 확인합니다.
    head = dst.read_bytes()[:12]
    MAGIC = (b"\xff\xd8\xff", b"\x89PNG", b"GIF8", b"RIFF", b"<svg", b"<?xml")
    if not any(head.startswith(m) for m in MAGIC):
        print(f"이미지가 아닙니다 (서버가 오류 페이지를 보냈을 수 있음):\n"
              f"  {r['url']}\n  원본 페이지: {r['page']}", file=sys.stderr)
        dst.unlink(missing_ok=True)
        return 1

    # 출처 기록 — 이게 이 도구의 핵심입니다. 기록 없는 자료는 분쟁 시 방어 불가.
    credits = yaml.safe_load(CREDITS.read_text(encoding="utf-8")) if CREDITS.exists() else {}
    credits = credits or {}
    credits[str(dst.relative_to(ROOT))] = {
        "title": r["title"], "author": r["author"], "license": r["license"],
        "source": r["source"], "page": r["page"],
        "retrieved": __import__("datetime").date.today().isoformat(),
    }
    CREDITS.write_text(
        "# 자료 화면 출처 — fetchmedia.py 가 기록합니다. 직접 지우지 마세요.\n"
        "# CC BY / CC BY-SA 는 **영상에 저작자 표시가 필요합니다.**\n"
        "# docs/09-risk-and-compliance.md §1\n\n"
        + yaml.dump(credits, allow_unicode=True, sort_keys=True, width=100),
        encoding="utf-8")

    print(f"저장: {dst.relative_to(ROOT)}  ({dst.stat().st_size/1024:.0f}KB)")
    print(f"  {r['license']} · {r['author'][:50]}")
    if re.search(r"by", r["license"], re.I) and "cc0" not in r["license"].lower():
        print("  ⚠ 저작자 표시 의무 — 영상 화면 또는 고정 댓글에 표기하세요")
    print(f"\n다음: assets/{args.ep}/shots.yaml 의 file: 에 이 경로를 넣으세요")
    return 0


def cmd_credits(args) -> int:
    if not CREDITS.exists():
        print("아직 내려받은 자료가 없습니다.")
        return 0
    d = yaml.safe_load(CREDITS.read_text(encoding="utf-8")) or {}
    need_attr = []
    print(f"자료 {len(d)}건\n")
    for path, c in sorted(d.items()):
        attr = re.search(r"by", c["license"], re.I) and "cc0" not in c["license"].lower()
        print(f"  {path}")
        print(f"     {c['license']} · {c['author'][:46]}")
        if attr:
            need_attr.append((path, c))
    if need_attr:
        print(f"\n⚠ 저작자 표시가 필요한 자료 {len(need_attr)}건 — 아래를 고정 댓글에 넣으세요:\n")
        for path, c in need_attr:
            print(f"  · {c['title']} — {c['author'][:40]} ({c['license']})")
            print(f"    {c['page']}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="자유 라이선스 이미지 검색")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=6, help="소스당 건수")
    s.set_defaults(func=cmd_search)
    g = sub.add_parser("get", help="검색 결과를 내려받고 출처 기록")
    g.add_argument("index", type=int)
    g.add_argument("--ep", required=True)
    g.add_argument("--name", required=True)
    g.add_argument("--force", action="store_true", help="라이선스 경고 무시")
    g.set_defaults(func=cmd_get)
    c = sub.add_parser("credits", help="출처·라이선스 목록")
    c.set_defaults(func=cmd_credits)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
