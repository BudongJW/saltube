#!/usr/bin/env python3
"""tts — 대본 낭독 원고를 음성으로 합성.

    python3 tools/tts.py EP001                    기본 음성으로 합성
    python3 tools/tts.py EP001 --voice ko-KR-SunHiNeural
    python3 tools/tts.py --all
    python3 tools/tts.py --voices                 사용 가능한 한국어 음성

`produce.py` 가 만든 build/<EP>/narration.txt 를 읽어 build/<EP>/<EP>.mp3 를 만듭니다.
그 뒤 `render.py <EP> --audio build/<EP>/<EP>.mp3` 로 영상에 얹습니다.

보이스 일관성
-------------
docs/02-brand.md §4 — "TTS 사용 시 보이스를 절대 바꾸지 마세요. 일관성이 신뢰도입니다."
VOICE/RATE 는 여기 상수로 고정합니다. 회차마다 바꾸지 마세요.
생성된 mp3 는 보관하세요 — 서비스 쪽에서 음성이 바뀌어도 기존 편은 영향받지 않습니다.
"""
from __future__ import annotations

import argparse
import asyncio
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claimctl import ROOT, SCRIPTS, parse_script  # noqa: E402
from produce import strip_md, walk  # noqa: E402

BUILD = ROOT / "build"

# ── 고정 설정 — 회차마다 바꾸지 말 것 ──
VOICE = "ko-KR-InJoonNeural"
RATE = "+15%"      # 기본 속도는 246음절/분으로 느립니다. +15% = 약 282음절/분
VOLUME = "+0%"


def narration_text(ep: str) -> tuple[str, dict]:
    matches = [p for p in SCRIPTS.glob(f"{ep}*.md") if not p.name.startswith("_")]
    if not matches:
        raise FileNotFoundError(f"대본 없음: {ep}")
    fm, body = parse_script(matches[0])
    lines = [strip_md(t) for kind, t, _ in walk(body) if kind == "cue"]
    return "\n".join(l for l in lines if l), fm


async def synth(text: str, dst: Path, voice: str, rate: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, volume=VOLUME).save(str(dst))


def duration(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def run(ep: str, voice: str, rate: str, quiet: bool = False) -> int:
    text, fm = narration_text(ep)
    out = BUILD / fm["id"]
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{fm['id']}.mp3"

    try:
        asyncio.run(synth(text, dst, voice, rate))
    except Exception as e:
        msg = str(e)
        if "CERTIFICATE" in msg.upper():
            msg += ("\n  프록시 환경이면 CA 번들을 certifi 에 추가하세요:\n"
                    "  cat /root/.ccr/ca-bundle.crt >> $(python3 -c 'import certifi;print(certifi.where())')")
        print(f"  {ep} 합성 실패: {msg}", file=sys.stderr)
        return 1

    if not dst.exists() or dst.stat().st_size == 0:
        print(f"  {ep}: 빈 파일이 생성됐습니다 — 네트워크를 확인하세요", file=sys.stderr)
        return 1

    dur = duration(dst)
    syl = len(re.findall(r"[가-힣]", text)) + 1.5 * len(re.findall(r"[0-9]", text))
    rate_spm = syl / dur * 60 if dur else 0
    if not quiet:
        over = "  ⚠ 60초 초과" if dur > 60 else ""
        print(f"  {fm['id']}.mp3  {dur:.1f}초  {rate_spm:.0f}음절/분  "
              f"{dst.stat().st_size/1024:.0f}KB{over}")
    return 0


def list_voices() -> int:
    r = subprocess.run([sys.executable, "-m", "edge_tts", "--list-voices"],
                       capture_output=True, text=True)
    rows = [l for l in r.stdout.splitlines() if "ko-KR" in l]
    print("한국어 음성:")
    for l in rows:
        mark = "  ← 현재 설정" if VOICE in l else ""
        print(f"  {l}{mark}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--rate", default=RATE, help=f"발화 속도 (기본 {RATE})")
    ap.add_argument("--voices", action="store_true", help="한국어 음성 목록")
    args = ap.parse_args()

    if args.voices:
        return list_voices()
    if args.voice != VOICE or args.rate != RATE:
        print(f"⚠ 기본값과 다른 설정입니다 (voice={args.voice} rate={args.rate}).\n"
              "  회차 간 보이스 일관성이 깨지면 신뢰도 손실입니다 — docs/02-brand.md §4",
              file=sys.stderr)
    if args.all:
        eps = sorted({p.name.split("-")[0] for p in SCRIPTS.glob("*.md")
                      if not p.name.startswith("_")})
        print(f"음성 합성 — {len(eps)}편  (voice={args.voice}, rate={args.rate})\n")
        rc = 0
        for e in eps:
            rc |= run(e, args.voice, args.rate)
        return rc
    if not args.episode:
        ap.error("episode 를 지정하거나 --all 을 쓰세요")
    return run(args.episode, args.voice, args.rate)


if __name__ == "__main__":
    sys.exit(main())
