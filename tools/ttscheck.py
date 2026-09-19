#!/usr/bin/env python3
"""ttscheck — TTS 발음 시험용 단어 목록을 대본에서 추출.

    python3 tools/ttscheck.py            시험 목록 출력
    python3 tools/ttscheck.py --save     build/tts-test.txt 로 저장

왜 필요한가
-----------
TTS 채택 전 반드시 **우리가 실제로 쓰는 단어**로 시험해야 합니다.
"틱타알릭", "등시선", "내인성 레트로바이러스" 같은 용어의 발음이 깨지면
그 자체로 신뢰도 손실입니다. 일반 문장으로 시험하면 이 문제가 안 드러납니다.
→ docs/13-external-tools.md §4
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "content" / "scripts"
BUILD = ROOT / "build"

# 카테고리별 시험 대상 — TTS 가 자주 틀리는 유형
PATTERNS = {
    "학명·고유명사": re.compile(r"[가-힣]*(?:알릭|케투스|케투르|르투스|도르돈|사우루스|피테쿠스)[가-힣]*"),
    "외래어 용어": re.compile(r"[가-힣]{2,}(?:로미어|바이러스|아제|오미어|토미어|센트로미어)[가-힣]*"),
    "한자어 전문용어": re.compile(r"(?:등시선|동위원소|반감기|퇴적|증발암|사층리|위유전자|흔적기관|종분화|계통수|광수용|분비장치|호상점토)"),
}
# 숫자 읽기 — TTS 가 가장 자주 틀리는 부분
NUMBER = re.compile(r"\d[\d,\.]*\s*(?:억|만|천|년|초|퍼센트|제곱|배|개|조)?")


def narration_text() -> str:
    out = []
    for p in sorted(SCRIPTS.glob("*.md")):
        if p.name.startswith("_"):
            continue
        body = p.read_text(encoding="utf-8").split("\n---\n")
        body = body[1] if len(body) > 1 else body[0]
        for line in body.split("\n---\n")[0].split("\n"):
            s = line.strip()
            if s and not s.startswith(("#", ">", "```", "|", "-", "attest", "  ")):
                out.append(re.sub(r"\[S-[A-Z0-9\-]+\]|\*\*|`", "", s))
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args()

    text = narration_text()
    L = ["# TTS 발음 시험 목록",
         "#",
         "# 사용법: 아래 항목을 후보 TTS 에 그대로 넣고 들어보세요.",
         "# 하나라도 알아들을 수 없으면 그 TTS 는 이 채널에 못 씁니다.",
         "# → docs/13-external-tools.md §4",
         ""]

    for label, pat in PATTERNS.items():
        found = sorted({m.group(0) for m in pat.finditer(text) if len(m.group(0)) > 1})
        if found:
            L += [f"## {label} ({len(found)}개)", ""] + [f"  {w}" for w in found] + [""]

    nums = sorted({m.group(0).strip() for m in NUMBER.finditer(text)}, key=len, reverse=True)
    nums = [n for n in nums if any(c.isdigit() for c in n)][:24]
    L += [f"## 숫자 읽기 ({len(nums)}개) — 가장 자주 틀리는 부분", ""]
    L += [f"  {n}" for n in nums] + [""]

    L += ["## 통문장 시험 — 숫자와 학명이 함께 나오는 구간", ""]
    for line in text.split("\n"):
        if re.search(r"\d", line) and len(line) > 24:
            L.append(f"  {line.strip()}")
            if sum(1 for x in L if x.startswith("  ") and len(x) > 26) > 30:
                break
    L += ["",
          "## 판정 기준", "",
          "  ☐ 학명을 한 번에 알아들을 수 있는가",
          "  ☐ '45.4억 년'을 '사십오점사억 년'으로 읽는가 (숫자 나열 X)",
          "  ☐ '10의 17제곱'을 수식으로 읽는가",
          "  ☐ 같은 문장을 두 번 생성했을 때 억양이 동일한가 (회차 간 일관성)",
          "  ☐ 문장 끝 어미가 뚝 끊기지 않는가",
          ""]

    text_out = "\n".join(L)
    if args.save:
        BUILD.mkdir(exist_ok=True)
        (BUILD / "tts-test.txt").write_text(text_out + "\n", encoding="utf-8")
        print(f"build/tts-test.txt 저장")
    else:
        print(text_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
