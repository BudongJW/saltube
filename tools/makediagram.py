#!/usr/bin/env python3
"""makediagram — 자료 화면 도식을 생성합니다.

    python3 tools/makediagram.py            전체 생성 → assets/shared/

세로 영상(1080×1920)에 맞춰 설계합니다. 가로형 배치는 세로 공간을 버립니다.

레이아웃 규칙 (assets/README.md)
    y <  230   상단 안전영역 — 비움
    y 230~1100 실질 작업 영역 ← 모든 내용이 여기 들어가야 함
    y > 1100   자막 + 어둠막 영역 — 내용 금지
"""
import pathlib
import sys

import cairosvg

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "shared"
W, H = 1080, 1920
TOP, BOT = 230, 1100          # 실질 작업 영역

# docs/02-brand.md §3
INK, PAPER, EVID, CLAIM, ACCENT = "#12151A", "#F5F3EE", "#2E7D6B", "#B4472F", "#E0A800"
F = "Pretendard, Helvetica, Arial, sans-serif"


def svg(inner: str, bg: str = EVID) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="{bg}"/>'
            f'{inner}</svg>')


def text(x, y, s, size=56, fill=PAPER, weight=700, anchor="middle", opacity=1):
    return (f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'opacity="{opacity}">{s}</text>')


# ─────────────────────── EP001 ───────────────────────

def ep001_theory_def():
    """'충분히 입증된 설명' — 정의 카드."""
    return svg(
        text(540, 430, "과학에서", 54, PAPER, opacity=0.6)
        + text(540, 590, "이론", 180, PAPER)
        + f'<rect x="300" y="650" width="480" height="10" rx="5" fill="{ACCENT}"/>'
        + text(540, 810, "충분히", 70, ACCENT)
        + text(540, 900, "입증된 설명", 70, ACCENT)
        + text(540, 1030, "추측의 반대말입니다", 44, PAPER, opacity=0.65))


def ep001_ladder():
    """'가설 → 이론 → 사실' 사다리에 X — 세로로 쌓고 가로지르는 X.

    그리는 순서가 중요합니다. X 를 먼저, 글자를 나중에 그려야 글자가 살아납니다.
    """
    boxes, labels = [], []
    for i, (label, y) in enumerate([("사실", 330), ("이론", 560), ("가설", 790)]):
        boxes.append(f'<rect x="330" y="{y}" width="420" height="120" rx="14" '
                     f'fill="{PAPER}" opacity="0.16"/>')
        labels.append(text(540, y + 82, label, 66, PAPER, opacity=0.9))
        if i < 2:
            boxes.append(f'<path d="M 540 {y + 200} L 540 {y + 140} M 512 {y + 172} '
                         f'L 540 {y + 140} L 568 {y + 172}" stroke="{PAPER}" '
                         f'stroke-width="9" fill="none" stroke-linecap="round" opacity="0.4"/>')
    x_mark = (f'<path d="M 280 300 L 800 940 M 800 300 L 280 940" stroke="{CLAIM}" '
              f'stroke-width="30" stroke-linecap="round" opacity="0.92"/>')
    # 캡션은 청록 배경에서 벽돌색 대비가 낮습니다. 크림 바탕 위에 올립니다.
    caption = (f'<rect x="230" y="1000" width="620" height="92" rx="46" fill="{PAPER}"/>'
               + text(540, 1062, "이런 사다리는 없습니다", 48, CLAIM))
    return svg("".join(boxes) + x_mark + "".join(labels) + caption)


def ep001_fallacy():
    """'다의어 오류' — 한 단어, 두 뜻."""
    return svg(
        text(540, 350, "다의어 오류", 92, ACCENT)
        + f'<rect x="120" y="470" width="840" height="230" rx="18" fill="{PAPER}" opacity="0.1"/>'
        + text(540, 545, "일상어", 40, PAPER, opacity=0.55)
        + text(540, 640, "이론 = 추측", 72, PAPER)
        + f'<rect x="120" y="740" width="840" height="230" rx="18" fill="{ACCENT}" opacity="0.18"/>'
        + text(540, 815, "과학 용어", 40, ACCENT, opacity=0.9)
        + text(540, 910, "이론 = 입증된 설명", 66, ACCENT)
        + text(540, 1050, "같은 단어, 다른 뜻", 46, PAPER, opacity=0.6))


# ─────────────────────── EP002 ───────────────────────

def ep002_isolated():
    """제2법칙 원문에서 '고립계'만 강조."""
    return svg(
        text(540, 340, "열역학 제2법칙", 48, PAPER, opacity=0.55)
        + f'<rect x="250" y="430" width="580" height="150" rx="16" fill="{ACCENT}" opacity="0.22"/>'
        + text(540, 540, "고립계", 120, ACCENT)
        + text(540, 700, "의 엔트로피는", 62, PAPER)
        + text(540, 800, "감소하지 않는다", 62, PAPER)
        + f'<path d="M 400 900 L 680 900" stroke="{PAPER}" stroke-width="5" opacity="0.3"/>'
        + text(540, 1000, "빠진 세 글자가", 46, PAPER, opacity=0.7)
        + text(540, 1070, "전부입니다", 46, PAPER, opacity=0.7))


def ep002_energy():
    """태양 → 지구 에너지 유입 — 세로 배치.

    단위 주의: 와트(W)가 이미 '초당 에너지'입니다. W/s 는 틀린 표기입니다.
    """
    rays = "".join(
        f'<path d="M {440 + i*50} 580 L {440 + i*50} 840" stroke="{ACCENT}" '
        f'stroke-width="7" stroke-linecap="round" opacity="{0.3 + 0.1*(i % 3)}"/>'
        f'<path d="M {418 + i*50} 812 L {440 + i*50} 844 L {462 + i*50} 812" '
        f'stroke="{ACCENT}" stroke-width="7" fill="none" stroke-linecap="round" '
        f'opacity="{0.3 + 0.1*(i % 3)}"/>'
        for i in range(5))
    return svg(
        f'<circle cx="540" cy="430" r="118" fill="{ACCENT}"/>'
        + text(540, 450, "태양", 56, INK)
        + rays
        + f'<circle cx="540" cy="1000" r="108" fill="{PAPER}"/>'
        + text(540, 1020, "지구", 54, EVID)
        # 수치는 광선 옆으로 빼서 겹치지 않게
        + text(830, 690, "10", 72, PAPER, anchor="middle")
        + text(878, 652, "17", 42, PAPER, anchor="start")
        + text(830, 760, "와트", 44, PAPER, anchor="middle", opacity=0.8))


def ep002_condition():
    """'조건 생략 인용' — 문장에서 조건이 떨어져 나가는 그림."""
    return svg(
        text(540, 340, "조건 생략 인용", 88, ACCENT)
        + f'<rect x="150" y="470" width="780" height="140" rx="16" fill="{PAPER}" opacity="0.14"/>'
        + text(540, 560, "고립계의 엔트로피는 증가", 50, PAPER, opacity=0.85)
        + text(540, 700, "↓", 70, CLAIM)
        + f'<rect x="150" y="760" width="780" height="140" rx="16" fill="{CLAIM}" opacity="0.2"/>'
        + text(540, 850, "엔트로피는 증가", 50, CLAIM)
        + text(540, 1000, "전제가 먼저", 46, PAPER, opacity=0.7)
        + text(540, 1070, "떨어져 나갑니다", 46, PAPER, opacity=0.7))


# ─────────────────────── EP004 ───────────────────────

def ep004_count3():
    """나이테·호상점토·빙하코어 3분할 — 세로로 쌓고 수치 대비를 막대 길이로."""
    rows, y = [], 320
    for name, num, w in [("나이테", "12,600", 0.28),
                         ("호상점토", "52,800", 0.52),
                         ("빙하 코어", "800,000", 1.0)]:
        rows.append(text(110, y - 26, name, 46, PAPER, anchor="start", opacity=0.75))
        rows.append(f'<rect x="110" y="{y}" width="{int(860 * w)}" height="16" rx="8" '
                    f'fill="{ACCENT}" opacity="0.9"/>')
        rows.append(text(110, y + 108, num, 82, PAPER, anchor="start"))
        rows.append(text(110, y + 158, "년치", 36, PAPER, anchor="start", opacity=0.55))
        y += 265
    return svg("".join(rows)
               + text(540, 1070, "방사능 없이 그냥 셉니다", 50, ACCENT))


def ep004_agree():
    """연층 계수 vs 탄소-14 — 두 방법이 일치함을 보이는 산점도.

    단일 계열 + 기준선이므로 범례 없음(제목이 계열을 지시).
    기준선은 눈에 띄지 않게, 데이터 점이 주인공.
    """
    # 정사각 플롯. 세로 영상이므로 화면 폭에 맞추고 세로 여유를 위아래로.
    px, py, size = 160, 380, 760
    # 두 방법이 거의 일치 — 대각선 부근에 흩어진 점
    pts = [(0.06, 0.07), (0.14, 0.13), (0.22, 0.24), (0.31, 0.30), (0.38, 0.40),
           (0.47, 0.46), (0.55, 0.57), (0.63, 0.62), (0.71, 0.73), (0.80, 0.78),
           (0.88, 0.90), (0.95, 0.94)]
    dots = "".join(
        f'<circle cx="{px + x*size:.0f}" cy="{py + size - y*size:.0f}" r="13" '
        f'fill="{ACCENT}" stroke="{EVID}" stroke-width="3"/>' for x, y in pts)
    return svg(
        # 기준선 — 회색조로 후퇴
        f'<line x1="{px}" y1="{py+size}" x2="{px+size}" y2="{py}" '
        f'stroke="{PAPER}" stroke-width="4" stroke-dasharray="14 12" opacity="0.35"/>'
        # 축
        + f'<line x1="{px}" y1="{py+size}" x2="{px+size}" y2="{py+size}" '
          f'stroke="{PAPER}" stroke-width="3" opacity="0.45"/>'
        + f'<line x1="{px}" y1="{py}" x2="{px}" y2="{py+size}" '
          f'stroke="{PAPER}" stroke-width="3" opacity="0.45"/>'
        + dots
        + text(540, 300, "두 방법이 같은 답을 냅니다", 52, PAPER)
        + text(px + size/2, py + size + 70, "연층을 센 나이 →", 40, PAPER,
               opacity=0.7)
        + f'<text x="60" y="{py + size/2}" font-family="{F}" font-size="40" '
          f'font-weight="700" fill="{PAPER}" opacity="0.7" text-anchor="middle" '
          f'transform="rotate(-90 60 {py + size/2})">탄소-14 나이 →</text>')


def ep004_skepticism():
    """'선택적 회의' — 한쪽에만 들이대는 잣대.

    대비 주의: 벽돌색 박스 위에 벽돌색 글자를 올리면 읽히지 않습니다.
    박스만 색을 쓰고 글자는 크림으로 갑니다.
    """
    return svg(
        text(540, 320, "선택적 회의", 92, ACCENT)
        + f'<rect x="100" y="450" width="400" height="320" rx="18" fill="{CLAIM}"/>'
        + text(300, 530, "상대 방법", 40, PAPER, opacity=0.85)
        + text(300, 640, "엄격", 84, PAPER)
        + text(300, 715, "가정 하나하나 검증", 30, PAPER, opacity=0.8)
        + f'<rect x="580" y="450" width="400" height="320" rx="18" fill="{PAPER}" opacity="0.12"/>'
        + text(780, 530, "자기 논증", 40, PAPER, opacity=0.6)
        + text(780, 640, "관대", 84, PAPER, opacity=0.55)
        + text(780, 715, "더 강한 가정을 씀", 30, PAPER, opacity=0.5)
        + text(540, 920, "같은 잣대를", 50, PAPER, opacity=0.8)
        + text(540, 1000, "양쪽에 대보세요", 50, ACCENT))


DIAGRAMS = {
    "ep001-theory-def": ep001_theory_def,
    "ep001-ladder": ep001_ladder,
    "ep001-fallacy": ep001_fallacy,
    "ep002-isolated": ep002_isolated,
    "ep002-energy": ep002_energy,
    "ep002-condition": ep002_condition,
    "ep004-count3": ep004_count3,
    "ep004-agree": ep004_agree,
    "ep004-skepticism": ep004_skepticism,
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in DIAGRAMS.items():
        s = fn()
        cairosvg.svg2png(bytestring=s.encode(), output_width=W, output_height=H,
                         write_to=str(OUT / f"{name}.png"))
        print(f"  {name}.png")
    print(f"\n{len(DIAGRAMS)}종 → assets/shared/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
