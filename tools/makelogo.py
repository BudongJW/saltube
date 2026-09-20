#!/usr/bin/env python3
"""makelogo — 브랜드 로고 SVG/PNG 생성.

    python3 tools/makelogo.py

필요: pip install cairosvg, ~/.fonts/Pretendard-Bold.otf (fc-cache -f)
컬러는 docs/02-brand.md §3 을 따릅니다. 색을 바꾸려면 여기만 고치세요.
"""
import pathlib
import sys

import cairosvg

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "brand"

INK, PAPER, EVID, ACCENT = "#12151A", "#F5F3EE", "#2E7D6B", "#E0A800"
FONT = "Pretendard, Helvetica, Arial, sans-serif"
SIZES = (1024, 512, 200, 96, 40)


def mark(bg: str, fg: str, line: str) -> str:
    """원형 마크 한 장. 원형 크롭을 전제로 모든 요소를 안전 영역 안에 둡니다."""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">'
        f'<circle cx="256" cy="256" r="256" fill="{bg}"/>'
        f'<text x="256" y="298" font-family="{FONT}" font-size="200" font-weight="700" '
        f'fill="{fg}" text-anchor="middle" letter-spacing="-9">1분</text>'
        f'<rect x="156" y="342" width="200" height="16" rx="8" fill="{line}"/></svg>'
    )


VARIANTS = {
    "primary": (EVID, PAPER, ACCENT),      # 기본
    "light": (PAPER, EVID, ACCENT),        # 밝은 배경·워터마크
    "mono-dark": (INK, PAPER, PAPER),      # 단색
}


def main() -> int:
    OUT.mkdir(exist_ok=True)
    for name, colors in VARIANTS.items():
        svg = mark(*colors)
        (OUT / f"logo-{name}.svg").write_text(svg, encoding="utf-8")
        for px in SIZES:
            cairosvg.svg2png(bytestring=svg.encode(), output_width=px, output_height=px,
                             write_to=str(OUT / f"logo-{name}-{px}.png"))
        print(f"  logo-{name}  svg + {'/'.join(map(str, SIZES))} px")
    print(f"\n{OUT.relative_to(ROOT)}/ 생성 완료")
    print("※ Pretendard 가 설치되지 않았으면 한글이 대체 폰트로 렌더됩니다 — 결과를 눈으로 확인하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
