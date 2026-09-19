#!/usr/bin/env python3
"""claimctl — 대본 검수 / 백로그 현황 / 발행 캘린더 / 플랫폼 메타데이터.

사용법:
    python3 tools/claimctl.py validate [--strict]
    python3 tools/claimctl.py backlog [--pillar A] [--priority 1]
    python3 tools/claimctl.py calendar --weeks 8 [--start 2026-10-05]
    python3 tools/claimctl.py meta EP001

validate는 CI에서 실행됩니다 (.github/workflows/validate.yml).
출처 없는 사실 주장이 담긴 대본은 머지되지 않습니다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLAIMS = ROOT / "content" / "claims.yaml"
SOURCES = ROOT / "content" / "sources.md"
SCRIPTS = ROOT / "content" / "scripts"

# 한국어 발화 속도 (음절/분). docs/02-brand.md §4 — 쇼츠 표준보다 약간 느리게.
SYLLABLES_PER_MIN = 355
DURATION_MIN, DURATION_MAX = 40, 62   # 경고 범위(초)
DURATION_HARD_MAX = 70                # 초과 시 오류 — 채널 편집 기준(플랫폼 한도 아님)

REQUIRED_KEYS = {
    "id", "claim_id", "title", "pillar", "confidence",
    "duration_target", "sources", "status", "platforms",
}
VALID_PILLARS = set("ABCDE")
VALID_CONFIDENCE = {"settled", "strong", "active"}
VALID_STATUS = {"backlog", "drafted", "recorded", "published"}

SOURCE_MARKER = re.compile(r"\[(S-[A-Z0-9\-]+)\]")
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.S)
HANGUL = re.compile(r"[가-힣]")
DIGIT = re.compile(r"[0-9]")

# docs/03-editorial-policy.md §4 — 우리가 자주 저지르는 부정확한 서술.
SELF_OWN_LINT = [
    (re.compile(r"원숭이에서\s*진화"), "인간과 현생 유인원은 '공통조상'에서 갈라짐 (§4)"),
    (re.compile(r"적자생존"), "정확한 용어는 '자연선택' — '적자생존'은 동어반복 비판을 자초 (§4)"),
    (re.compile(r"과학[은이]\s*증명(했|한|됐|되)"), "과학은 '입증'이 아니라 반증 실패의 누적. '증명'은 수학 용어 (§4)"),
    (re.compile(r"진화(론)?[은는이가].*생명[의]?\s*기원[을를]?\s*설명"), "진화는 생명의 '기원'이 아니라 '변화'를 다룸 (§4)"),
    (re.compile(r"진화[는은].*(진보|발전|우월)"), "진화는 방향성이 없음 — 진보가 아님 (§4)"),
    (re.compile(r"빅뱅.*진화[의]?\s*(시작|출발)"), "우주론과 생물 진화는 별개 이론 (§4)"),
]
# 대결 포맷 §2 — 동기 추정은 '비방할 목적' 구성요건 입증에 쓰일 수 있음.
MOTIVE_LINT = [
    (re.compile(r"알면서(도)?\s*(속|숨|감추)"), "고의 추정 — 입증 책임이 우리에게 옴"),
    (re.compile(r"돈\s*(때문|벌려고|받고)"), "동기 추정"),
    (re.compile(r"지어낸\s*(숫자|말|자료)"), "단정 불가 — '출처를 찾을 수 없습니다'로"),
    (re.compile(r"사기(꾼|극)"), "인신 공격"),
    (re.compile(r"(속이|기만하)[고는려]"), "고의 추정"),
]
# docs/03-editorial-policy.md §1 — 레드라인.
REDLINE_LINT = [
    (re.compile(r"(무지|멍청|한심|어리석)[한하]"), "인신·집단 비하 표현 (레드라인 §1)"),
    (re.compile(r"거짓말쟁이"), "사람이 아니라 주장을 비판할 것 (레드라인 §1)"),
    (re.compile(r"그러므로\s*신[은는이]?\s*(없|존재하지)"), "무신론 결론은 이 채널의 범위 밖 (레드라인 §4)"),
    (re.compile(r"기독교인[은는이].*(다|들은)\s*(무지|비과학|멍청)"), "싸잡기 금지 (레드라인 §2)"),
]


# ────────────────────────────── 로딩 ──────────────────────────────

def load_claims() -> dict:
    return yaml.safe_load(CLAIMS.read_text(encoding="utf-8"))


def load_source_ids() -> set[str]:
    """sources.md 표에서 `S-XXX` 형식 ID를 추출."""
    text = SOURCES.read_text(encoding="utf-8")
    return set(re.findall(r"`(S-[A-Z0-9\-]+)`", text))


def parse_script(path: Path) -> tuple[dict, str]:
    m = FRONT_MATTER.match(path.read_text(encoding="utf-8"))
    if not m:
        raise ValueError("YAML front matter(--- 블록)를 찾을 수 없습니다")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def narration_of(body: str) -> str:
    """영상에서 실제로 읽는 부분만 추출.

    제외: 헤딩(##), 화면 지시(>), 그리고 '---' 구분선 이후의 제작 메모 전체.
    """
    out = []
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("---"):        # 제작 메모 시작 → 이후 전부 제외
            break
        if not s or s.startswith(("#", ">", "```", "|")):
            continue
        out.append(s)
    return "\n".join(out)


def estimate_seconds(narration: str) -> float:
    """한글 음절 수 기반 낭독 시간 추정. 숫자는 음절 1.5개로 환산."""
    syl = len(HANGUL.findall(narration)) + 1.5 * len(DIGIT.findall(narration))
    return round(syl / SYLLABLES_PER_MIN * 60, 1)


# ────────────────────────────── validate ──────────────────────────────

def cmd_validate(args) -> int:
    claims = load_claims()
    claim_ids = {c["id"] for c in claims["claims"]}
    logic_only_claims = {c["id"] for c in claims["claims"]
                         if str(c.get("note", "")).find("logic_only") >= 0}
    source_ids = load_source_ids()

    errors: list[str] = []
    warnings: list[str] = []
    checked = 0

    for path in sorted(SCRIPTS.glob("*.md")):
        if path.name.startswith("_"):
            continue
        checked += 1
        rel = path.relative_to(ROOT)
        try:
            fm, body = parse_script(path)
        except ValueError as e:
            errors.append(f"{rel}: {e}")
            continue

        def err(msg): errors.append(f"{rel}: {msg}")
        def warn(msg): warnings.append(f"{rel}: {msg}")

        # 1. 필수 키
        for key in sorted(REQUIRED_KEYS - set(fm)):
            err(f"front matter에 '{key}' 누락")
        if missing := (REQUIRED_KEYS - set(fm)):
            continue

        # 2. 값 검증
        if not path.name.startswith(fm["id"]):
            err(f"파일명이 id({fm['id']})로 시작하지 않음")
        if fm["pillar"] not in VALID_PILLARS:
            err(f"pillar '{fm['pillar']}' 유효하지 않음 (A~E)")
        if fm["confidence"] not in VALID_CONFIDENCE:
            err(f"confidence '{fm['confidence']}' 유효하지 않음 {sorted(VALID_CONFIDENCE)}")
        if fm["status"] not in VALID_STATUS:
            err(f"status '{fm['status']}' 유효하지 않음 {sorted(VALID_STATUS)}")
        if fm["claim_id"] not in claim_ids:
            err(f"claim_id '{fm['claim_id']}'가 claims.yaml에 없음")

        # 3. 출처 — 편집 정책 §2 1단계
        declared = set(fm.get("sources") or [])
        used = set(SOURCE_MARKER.findall(body))
        logic_only = bool(fm.get("logic_only"))

        if not declared and not logic_only:
            err("출처가 없습니다. 사실 주장이 없는 논리 분석 편이라면 logic_only: true")
        for sid in sorted(declared - source_ids):
            err(f"출처 '{sid}'가 content/sources.md에 등재되어 있지 않음")
        for sid in sorted(used - declared):
            err(f"본문 마커 [{sid}]가 front matter sources에 선언되지 않음")
        for sid in sorted(declared - used):
            warn(f"선언된 출처 '{sid}'가 본문에서 인용되지 않음")

        # 4. 길이 — 쇼츠 규격
        narration = narration_of(body)
        est = estimate_seconds(narration)
        target = fm["duration_target"]
        if est > DURATION_HARD_MAX:
            err(f"예상 {est}초 — 채널 편집 기준 초과(>{DURATION_HARD_MAX}초). 컷 필요")
        elif not (DURATION_MIN <= est <= DURATION_MAX):
            warn(f"예상 {est}초 — 권장 {DURATION_MIN}~{DURATION_MAX}초 범위 밖")
        if abs(est - target) > 12:
            warn(f"예상 {est}초 vs duration_target {target}초 — 격차 큼")

        # 5. 확실성 등급과 단정 어조 — 편집 정책 §3
        if fm["confidence"] == "active":
            hedges = ("현재로서는", "아직", "가설", "논쟁", "모릅니다", "열린 문제", "않습니다")
            if not any(h in narration for h in hedges):
                warn("confidence: active인데 유보 표현이 없음 — 단정 어조 점검 필요 (§3)")

        # 6. 자책골 / 레드라인 린트
        for pattern, msg in SELF_OWN_LINT:
            if pattern.search(narration):
                warn(f"부정확한 서술 가능성: {msg}")
        for pattern, msg in REDLINE_LINT:
            if pattern.search(narration):
                err(f"레드라인 위반 가능성: {msg}")
        for pattern, msg in MOTIVE_LINT:
            if pattern.search(narration):
                (err if fm.get("named_target") else warn)(
                    f"동기 추정 표현: {msg} (대결 포맷 §2)")

        # 7. 실명 대상 편 — 대결 포맷 §4 자료 수집 프로토콜 강제
        target = fm.get("named_target")
        if target:
            quotes = fm.get("quotes")
            if not quotes:
                err(f"named_target('{target}') 편에 quotes 블록이 없음 — "
                    "실명 편은 원문 인용 없이 발행 불가 (레드라인 §7)")
            else:
                for i, q in enumerate(quotes, 1):
                    if not isinstance(q, dict):
                        err(f"quotes[{i}] 형식 오류 — text/source/archived/context_saved 필요")
                        continue
                    for field, why in (
                        ("text", "원문 그대로의 인용문"),
                        ("source", "출처(URL 또는 서지사항)와 접근 날짜"),
                        ("archived", "아카이브 주소 — 원문 삭제 대비"),
                        ("context_saved", "앞뒤 문맥 보관 여부 — 맥락 왜곡 반박 대비"),
                    ):
                        if not q.get(field):
                            err(f"quotes[{i}]에 '{field}' 없음 ({why}) — 대결 포맷 §4")
                    if q.get("context_saved") is False:
                        err(f"quotes[{i}]: 앞뒤 문맥 미보관 — "
                            "'앞뒤 잘랐다' 반박에 대응 불가 (대결 포맷 §4)")
            if fm["confidence"] == "active":
                warn("실명 대상 편인데 confidence: active — "
                     "확정되지 않은 근거로 실명 비판 시 위험 (대결 포맷 §6)")

        # 8. 반대 심문 — 편집 정책 §2 3단계
        if "예상 재반박" not in body:
            warn("'예상 재반박' 섹션 없음 — 편집 정책 §2 3단계 미수행 (§2)")

    # ── 출력 ──
    for w in warnings:
        print(f"  warn  {w}")
    for e in errors:
        print(f"  ERROR {e}", file=sys.stderr)

    strict_fail = args.strict and warnings
    print(f"\n대본 {checked}편 검사 — 오류 {len(errors)}건, 경고 {len(warnings)}건")
    if errors:
        print("발행 불가. 오류를 해결하세요.", file=sys.stderr)
        return 1
    if strict_fail:
        print("--strict: 경고를 오류로 처리합니다.", file=sys.stderr)
        return 1
    print("통과.")
    return 0


# ────────────────────────────── backlog ──────────────────────────────

def cmd_backlog(args) -> int:
    data = load_claims()
    rows = data["claims"]
    if args.pillar:
        rows = [c for c in rows if c["pillar"] == args.pillar.upper()]
    if args.priority:
        rows = [c for c in rows if c["priority"] == args.priority]

    order = {"backlog": 0, "drafted": 1, "recorded": 2, "published": 3}
    rows = sorted(rows, key=lambda c: (c["priority"], -order.get(c["status"], 0), c["id"]))

    print(f"{'ID':<6}{'P':<3}{'난이도':<7}{'기둥':<5}{'확실성':<9}{'상태':<10}주장")
    print("─" * 100)
    for c in rows:
        claim = c["claim"]
        if len(claim) > 42:
            claim = claim[:41] + "…"
        print(f"{c['id']:<6}{c['priority']:<3}{c['difficulty']:<7}{c['pillar']:<5}"
              f"{c['confidence']:<9}{c['status']:<10}{claim}")

    # 기둥 비중 점검 — docs/01-strategy.md §6
    total = len(data["claims"])
    counts: dict[str, int] = {}
    for c in data["claims"]:
        counts[c["pillar"]] = counts.get(c["pillar"], 0) + 1
    target = {"A": 45, "B": 25, "C": 15, "D": 10, "E": 5}
    print(f"\n총 {total}건 (필터 후 {len(rows)}건)")
    print("\n기둥 비중 (목표 대비) — docs/01-strategy.md §6")
    for p in "ABCDE":
        actual = round(counts.get(p, 0) / total * 100)
        flag = "  ⚠ 편중" if actual - target[p] >= 15 else ("  ⚠ 부족" if target[p] - actual >= 10 else "")
        print(f"  {p}: {actual:>3}%  (목표 {target[p]:>2}%){flag}")
    print("\n※ A 기둥 편중은 자연스럽습니다(주장 DB이므로). 다만 실제 '발행 편수'는")
    print("  목표 비중을 지키세요 — A만 발행하면 알고리즘이 갈등 콘텐츠로 분류합니다.")
    return 0


# ────────────────────────────── calendar ──────────────────────────────

def cmd_calendar(args) -> int:
    data = load_claims()
    pending = [c for c in data["claims"] if c["status"] != "published"]
    # 우선순위 → 난이도(쉬운 것 먼저, 초반 완주율 확보) → id
    pending.sort(key=lambda c: (c["priority"], c["difficulty"], c["id"]))

    start = dt.date.fromisoformat(args.start) if args.start else dt.date.today()
    # 발행 요일: 월·수·금 — docs/04-platform-playbook.md
    while start.weekday() != 0:
        start += dt.timedelta(days=1)

    slots: list[dt.date] = []
    for w in range(args.weeks):
        base = start + dt.timedelta(weeks=w)
        slots += [base, base + dt.timedelta(days=2), base + dt.timedelta(days=4)]

    print(f"발행 캘린더 — {start} 시작, {args.weeks}주, 주 3회 (월·수·금)\n")
    print(f"{'날짜':<13}{'요일':<5}{'ID':<7}{'기둥':<5}{'난이도':<7}주장")
    print("─" * 96)
    dow = "월화수목금토일"
    for date, claim in zip(slots, pending):
        title = claim["claim"]
        if len(title) > 40:
            title = title[:39] + "…"
        print(f"{date.isoformat():<13}{dow[date.weekday()]:<5}{claim['id']:<7}"
              f"{claim['pillar']:<5}{claim['difficulty']:<7}{title}")

    if len(pending) < len(slots):
        short = len(slots) - len(pending)
        print(f"\n⚠ 백로그 {short}편 부족. claims.yaml에 주장을 추가하세요.")
    else:
        print(f"\n백로그 잔여: {len(pending) - len(slots)}편")
    return 0


# ────────────────────────────── meta ──────────────────────────────

def cmd_meta(args) -> int:
    matches = [p for p in SCRIPTS.glob(f"{args.episode}*.md")]
    if not matches:
        print(f"대본을 찾을 수 없습니다: {args.episode}", file=sys.stderr)
        return 1
    fm, body = parse_script(matches[0])
    claims = {c["id"]: c for c in load_claims()["claims"]}
    claim = claims.get(fm["claim_id"], {})
    est = estimate_seconds(narration_of(body))
    tags = fm.get("hashtags") or []

    print("=" * 72)
    print(f"  {fm['id']} — 업로드 메타데이터   (예상 길이 {est}초)")
    print("=" * 72)

    print("\n── YouTube Shorts ──")
    print(f"제목: {fm['title']}")
    print("\n설명:")
    print(f"  {claim.get('rebuttal', '').strip()}\n")
    print(f"  {' '.join(tags)} #Shorts")
    print("\n고정 댓글: 대본 하단 '고정 댓글' 블록을 그대로 복사")

    print("\n── TikTok ──")
    cap = f"{fm['title']} {' '.join(tags[:4])}"
    print(f"캡션({len(cap)}자): {cap}")
    if len(cap) > 150:
        print("  ⚠ 150자 초과 — 앞부분이 잘립니다. 줄이세요.")

    print("\n── 체크리스트 ──")
    for item in [
        "자막 번인 완료 (음소거 시청자 대비 — 쇼츠의 30~40%)",
        "출처 자막이 모든 증거 컷 하단에 고정",
        "상단 12% / 하단 20% 안전영역 확보",
        "음량 -14 LUFS 정규화",
        "고정 댓글에 출처 전문 게시",
        "'예상 재반박' 항목을 댓글 대응용으로 숙지",
    ]:
        print(f"  ☐ {item}")
    if fm["confidence"] == "active":
        print("\n  ⚠ confidence: active — 단정 어조 금지. 유보 표현 확인 (편집 정책 §3)")
    return 0


# ────────────────────────────── main ──────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="대본 형식·출처·길이·톤 검수")
    v.add_argument("--strict", action="store_true", help="경고도 오류로 처리")
    v.set_defaults(func=cmd_validate)

    b = sub.add_parser("backlog", help="주장 DB 현황")
    b.add_argument("--pillar", help="기둥 필터 (A~E)")
    b.add_argument("--priority", type=int, help="우선순위 필터 (1~3)")
    b.set_defaults(func=cmd_backlog)

    c = sub.add_parser("calendar", help="발행 캘린더 생성")
    c.add_argument("--weeks", type=int, default=4)
    c.add_argument("--start", help="시작일 YYYY-MM-DD (해당 주 월요일로 정렬)")
    c.set_defaults(func=cmd_calendar)

    m = sub.add_parser("meta", help="플랫폼 업로드 메타데이터 생성")
    m.add_argument("episode", help="예: EP001")
    m.set_defaults(func=cmd_meta)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
