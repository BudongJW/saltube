#!/usr/bin/env python3
"""credits — 편별 자료 화면의 저작자 표시를 계산합니다.

produce.py(고정 댓글 생성)와 claimctl.py(발행 차단 검사)가 함께 씁니다.

라이선스 규칙 — docs/09-risk-and-compliance.md §1
    CC0 / 퍼블릭 도메인   표시 의무 없음
    CC BY / CC BY-SA     **저작자·라이선스·출처 표시 필수**
    우리가 만든 도식       의무 없음 (assets/shared/ 의 makediagram.py 산출물)
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CREDITS = ROOT / "assets" / "CREDITS.yaml"

# CC0·퍼블릭 도메인은 표시 의무가 없습니다. BY 가 들어가면 있습니다.
NO_ATTRIB = re.compile(r"(cc0|public domain|퍼블릭)", re.I)
NEEDS_ATTRIB = re.compile(r"\bby\b", re.I)
# 우리가 직접 만든 자료 — tools/makediagram.py 산출물
OWN_WORK = "assets/shared/"


def load_credits() -> dict:
    if not CREDITS.exists():
        return {}
    return yaml.safe_load(CREDITS.read_text(encoding="utf-8")) or {}


def episode_files(ep: str) -> list[str]:
    """그 편의 shots.yaml 에서 실제로 배정된 자료 경로."""
    f = ROOT / "assets" / ep / "shots.yaml"
    if not f.exists():
        return []
    d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    seen, out = set(), []
    for s in d.get("shots") or []:
        p = s.get("file")
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


def needs_attribution(license_name: str) -> bool:
    if NO_ATTRIB.search(license_name or ""):
        return False
    return bool(NEEDS_ATTRIB.search(license_name or ""))


def for_episode(ep: str) -> tuple[list[str], list[str]]:
    """반환: (고정 댓글에 넣을 표시 줄, 기록이 없는 외부 자료 경로)

    두 번째가 비어 있지 않으면 발행하면 안 됩니다 — 라이선스 위반 위험입니다.
    """
    creds = load_credits()
    lines, missing = [], []
    for path in episode_files(ep):
        if path.startswith(OWN_WORK):
            continue                      # 우리가 만든 도식
        c = creds.get(path)
        if not c:
            missing.append(path)
            continue
        if needs_attribution(c.get("license", "")):
            # Commons/Flickr 제목은 지나치게 길 때가 많습니다. 고정 댓글용으로 줄입니다.
            title = re.sub(r"\s*\([^)]*\)\s*$", "", (c.get("title") or path)).strip()
            if len(title) > 56:
                title = title[:55] + "…"
            lines.append(f"· {title} — {c.get('author', '?')} "
                         f"({c.get('license', '?')})")
            if page := c.get("page"):
                lines.append(f"  {page}")
    return lines, missing


def block(ep: str) -> str:
    """고정 댓글에 붙일 이미지 출처 블록. 표시할 게 없으면 빈 문자열."""
    lines, _ = for_episode(ep)
    if not lines:
        return ""
    return "\n".join(["", "이미지 출처"] + lines)
