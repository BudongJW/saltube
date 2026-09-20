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
FCN = "Noto Sans CJK SC, sans-serif"   # fc-query 로 확인한 실제 패밀리명
FTW = "Noto Sans TC, sans-serif"       # 번체 — SC 와 자형이 다릅니다


def svg(inner: str, bg: str = EVID) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="{bg}"/>'
            f'{inner}</svg>')


def text(x, y, s, size=56, fill=PAPER, weight=700, anchor="middle", opacity=1):
    return (f'<text x="{x}" y="{y}" font-family="{F}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'opacity="{opacity}">{s}</text>')



# ─────────────────────── EP001 — 2012 한국 교과서 사건 ───────────────────────

def ep001_archaeopteryx():
    """시조새가 지워질 뻔한 교과서 — 경고 톤."""
    return svg(
        f'<rect x="90" y="300" width="900" height="640" rx="20" fill="{PAPER}"/>'
        + f'<rect x="90" y="300" width="900" height="640" rx="20" fill="none" '
          f'stroke="{CLAIM}" stroke-width="16"/>'
        + text(540, 420, "고등학교 생명과학", 44, INK, opacity=0.5)
        + text(540, 570, "시조새", 140, INK)
        + f'<path d="M 250 470 L 830 700" stroke="{CLAIM}" stroke-width="22" '
          f'stroke-linecap="round"/>'
        + text(540, 730, "말의 진화", 72, INK, opacity=0.45)
        + f'<path d="M 300 700 L 780 800" stroke="{CLAIM}" stroke-width="18" '
          f'stroke-linecap="round" opacity="0.8"/>'
        + text(540, 880, "삭제 요청", 48, CLAIM)
        + text(540, 1040, "2012년 · 대한민국", 46, PAPER, opacity=0.8))


def ep001_pipeline():
    """청원 → 교과부 → 출판사. 세로 3단."""
    steps = []
    for i, (label, sub, col) in enumerate([
            ("창조과학회 산하 단체", "청원 제출", CLAIM),
            ("교육과학기술부", "그대로 전달", ACCENT),
            ("출판사", "삭제 동의", PAPER)]):
        y = 330 + i * 230
        steps.append(f'<rect x="130" y="{y}" width="820" height="150" rx="16" '
                     f'fill="{col}" opacity="{0.9 if col != PAPER else 0.18}"/>')
        steps.append(text(540, y + 62, label, 46, INK if col != PAPER else PAPER))
        steps.append(text(540, y + 118, sub, 36, INK if col != PAPER else PAPER,
                          opacity=0.75))
        if i < 2:
            steps.append(f'<path d="M 540 {y + 158} L 540 {y + 214} M 512 {y + 186} '
                         f'L 540 {y + 214} L 568 {y + 186}" stroke="{PAPER}" '
                         f'stroke-width="9" fill="none" stroke-linecap="round" opacity="0.6"/>')
    return svg("".join(steps))


def ep001_panel():
    """한국과학기술한림원 패널 기각 — 결말."""
    return svg(
        text(540, 350, "2012년 9월", 48, PAPER, opacity=0.6)
        + text(540, 450, "한국과학기술한림원", 58, PAPER)
        + f'<rect x="240" y="520" width="600" height="110" rx="55" fill="{PAPER}" opacity="0.14"/>'
        + text(540, 592, "전문가 11인", 56, PAPER)
        + f'<rect x="200" y="700" width="680" height="150" rx="20" fill="{EVID}" '
          f'stroke="{ACCENT}" stroke-width="10"/>'
        + text(540, 800, "청원 기각", 92, ACCENT)
        + text(540, 950, "시조새는 교과서에 남았습니다", 48, PAPER)
        + text(540, 1050, "Nature 2012", 34, PAPER, opacity=0.5))


# ─────────────────────── EP001 (기존) ───────────────────────

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


def ep001_claim():
    """반박 대상 주장을 그대로 인용 — 주장은 반드시 `--claim` 색으로 표시합니다.

    편집 정책 §4: 주장과 사실을 같은 색으로 그리면 시청자가 둘을 구분하지 못합니다.
    """
    return svg(
        text(540, 340, "가장 흔한 반론", 44, PAPER, opacity=0.6)
        + f'<rect x="110" y="410" width="860" height="330" rx="20" fill="{CLAIM}"/>'
        + text(540, 545, "\u201c진화는", 76, PAPER)
        + text(540, 655, "이론일 뿐이잖아요\u201d", 76, PAPER)
        + text(540, 860, "이 문장 하나로", 46, PAPER, opacity=0.7)
        + text(540, 940, "교과서를 고치려 했습니다", 46, PAPER, opacity=0.7))


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



# ─────────────────────── CN01 — 중국어판 ───────────────────────

def _cn(x, y, s, size=56, fill=PAPER, weight=700, anchor="middle", opacity=1,
        family=None):
    return (f'<text x="{x}" y="{y}" font-family="{family or FCN}" font-size="{size}" '
            f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}" '
            f'opacity="{opacity}">{s}</text>')


def _cross(cx, cy, r=42, w=16, fill=CLAIM):
    """✗ — 글리프 대신 선으로 그립니다. 폰트에 없으면 두부(tofu)가 됩니다."""
    return (f'<line x1="{cx - r}" y1="{cy - r}" x2="{cx + r}" y2="{cy + r}" '
            f'stroke="{fill}" stroke-width="{w}" stroke-linecap="round"/>'
            f'<line x1="{cx + r}" y1="{cy - r}" x2="{cx - r}" y2="{cy + r}" '
            f'stroke="{fill}" stroke-width="{w}" stroke-linecap="round"/>')


def _tick(cx, cy, r=42, w=16, fill=ACCENT):
    """✓ — 같은 이유로 선으로 그립니다."""
    return (f'<polyline points="{cx - r},{cy} {cx - r * 0.2},{cy + r * 0.7} '
            f'{cx + r},{cy - r * 0.8}" fill="none" stroke="{fill}" '
            f'stroke-width="{w}" stroke-linecap="round" stroke-linejoin="round"/>')


# ───────────────── 2012 교과서 사건 — 중국어 도식 ─────────────────
#
# 간체(CN01)와 번체(TW01)는 **같은 레이아웃**을 씁니다.
# 따로 그리면 한쪽만 고치는 실수가 납니다 — 문구만 아래 표에서 갈라집니다.
#
# 번체는 글자만 바꾸는 게 아닙니다:
#   進化 → 演化   대만 교과서·학계 표준 용어. 進化 는 "향상" 뉘앙스라 학술 맥락에 안 씁니다
#   報道 → 報導   /  咨询 → 諮詢  /  里 → 裡  /  下属 → 旗下
#   《自然》은 期刊(학술지)이지 雜誌 가 아닙니다
ZH = {
    "zh-CN": {
        "font": FCN,
        "tb_sub": "高中生物教科书", "tb_main": "始祖鸟", "tb_second": "马的进化",
        "tb_tag": "要求删除", "tb_when": "2012年 · 韩国",
        "pl": [("创造科学会下属团体", "提交请愿"),
               ("教育科学技术部", "未经审查，直接转交"),
               ("出版社", "同意删除")],
        "nt_when": "2012年6月", "nt_impact": "全球科学界哗然",
        "pn_when": "同年 9月", "pn_org": "韩国科学技术翰林院",
        "pn_count": "11位专家", "pn_verdict": "驳回请愿",
        "pn_after": "始祖鸟留在了教科书里",
        "cc_top": "科学结论", "cc_mid": "不由请愿书决定", "cc_bot": "由证据决定",
        "wh_label": "请愿方", "wh_org": "韩国创造科学会", "wh_sub": "下属团体",
        "wh_name": "教科书进化论改正推进委员会", "wh_note": "不代表韩国基督教整体",
        "dm_title": "要求删除的内容", "dm_rows": ["始祖鸟", "马的进化"],
        "dm_count": "共 2 项", "dm_note": "请愿书直接送到了教育部",
        "nc_who": "韩国的生物学家", "nc_what": "事先完全没有被咨询",
        "nc_note": "教科书要改，却没问研究者",
        "vd_q": "挡住请愿的是什么？", "vd_no": "舆论", "vd_yes": "专家审议",
        "vd_note": "不是吵赢的，是审出来的",
    },
    "zh-TW": {
        "font": FTW,
        "tb_sub": "高中生物教科書", "tb_main": "始祖鳥", "tb_second": "馬的演化",
        "tb_tag": "要求刪除", "tb_when": "2012年 · 韓國",
        "pl": [("創造科學會旗下團體", "提交請願"),
               ("教育科學技術部", "未經審查，直接轉交"),
               ("出版社", "同意刪除")],
        "nt_when": "2012年6月", "nt_impact": "全球科學界譁然",
        "pn_when": "同年 9月", "pn_org": "韓國科學技術翰林院",
        "pn_count": "11位專家", "pn_verdict": "駁回請願",
        "pn_after": "始祖鳥留在教科書裡",
        "cc_top": "科學結論", "cc_mid": "不由請願書決定", "cc_bot": "由證據決定",
        "wh_label": "請願方", "wh_org": "韓國創造科學會", "wh_sub": "旗下團體",
        "wh_name": "教科書演化論改正推進委員會", "wh_note": "不代表韓國基督教整體",
        "dm_title": "要求刪除的內容", "dm_rows": ["始祖鳥", "馬的演化"],
        "dm_count": "共 2 項", "dm_note": "請願書直接送到了教育部",
        "nc_who": "韓國的生物學家", "nc_what": "事先完全沒有被諮詢",
        "nc_note": "教科書要改，卻沒問研究者",
        "vd_q": "擋下請願的是什麼？", "vd_no": "輿論", "vd_yes": "專家審議",
        "vd_note": "不是吵贏的，是審出來的",
    },
}


def zh_textbook(t):
    """始祖鳥 삭제 요구 — 교과서에 줄."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    return svg(
        f'<rect x="90" y="310" width="900" height="600" rx="20" fill="{PAPER}"/>'
        + f'<rect x="90" y="310" width="900" height="600" rx="20" fill="none" '
          f'stroke="{CLAIM}" stroke-width="16"/>'
        + f(540, 420, t["tb_sub"], 46, INK, opacity=0.5)
        + f(540, 580, t["tb_main"], 150, INK)
        + f'<path d="M 250 480 L 830 700" stroke="{CLAIM}" stroke-width="24" '
          f'stroke-linecap="round"/>'
        + f(540, 740, t["tb_second"], 72, INK, opacity=0.45)
        + f'<path d="M 300 710 L 780 810" stroke="{CLAIM}" stroke-width="18" '
          f'stroke-linecap="round" opacity="0.8"/>'
        + f(540, 870, t["tb_tag"], 50, CLAIM)
        + f(540, 1030, t["tb_when"], 46, PAPER, opacity=0.8))


def zh_pipeline(t):
    """請願 → 教育部 → 出版社."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    steps = []
    for i, ((label, sub), col) in enumerate(zip(t["pl"], (CLAIM, ACCENT, PAPER))):
        y = 330 + i * 230
        steps.append(f'<rect x="110" y="{y}" width="860" height="150" rx="16" '
                     f'fill="{col}" opacity="{0.9 if col != PAPER else 0.18}"/>')
        steps.append(f(540, y + 62, label, 46, INK if col != PAPER else PAPER))
        steps.append(f(540, y + 118, sub, 34, INK if col != PAPER else PAPER,
                       opacity=0.75))
        if i < 2:
            steps.append(f'<path d="M 540 {y + 158} L 540 {y + 214} M 512 {y + 186} '
                         f'L 540 {y + 214} L 568 {y + 186}" stroke="{PAPER}" '
                         f'stroke-width="9" fill="none" stroke-linecap="round" opacity="0.6"/>')
    return svg("".join(steps))


def zh_nature(t):
    """《自然》 보도 — 국제적 파장."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    return svg(
        f'<rect x="150" y="420" width="780" height="260" rx="18" fill="{PAPER}"/>'
        + f'<text x="540" y="560" font-family="Helvetica, Arial, sans-serif" '
          f'font-size="110" font-weight="700" fill="{INK}" text-anchor="middle">nature</text>'
        + f(540, 640, t["nt_when"], 40, INK, opacity=0.55)
        + f(540, 790, t["nt_impact"], 62, PAPER)
        + f(540, 900, "doi:10.1038/486014a", 32, PAPER, opacity=0.5))


def zh_panel(t):
    """翰林院 11인 전문가 기각."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    return svg(
        f(540, 350, t["pn_when"], 48, PAPER, opacity=0.6)
        + f(540, 450, t["pn_org"], 56, PAPER)
        + f'<rect x="270" y="520" width="540" height="110" rx="55" fill="{PAPER}" opacity="0.14"/>'
        + f(540, 592, t["pn_count"], 56, PAPER)
        + f'<rect x="230" y="700" width="620" height="150" rx="20" fill="{EVID}" '
          f'stroke="{ACCENT}" stroke-width="10"/>'
        + f(540, 800, t["pn_verdict"], 88, ACCENT)
        + f(540, 950, t["pn_after"], 48, PAPER))


def zh_conclusion(t):
    """科學不靠投票."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    return svg(
        f(540, 480, t["cc_top"], 72, PAPER, opacity=0.7)
        + f(540, 620, t["cc_mid"], 72, PAPER, opacity=0.7)
        + f'<rect x="240" y="700" width="600" height="8" rx="4" fill="{PAPER}" opacity="0.25"/>'
        + f(540, 860, t["cc_bot"], 104, ACCENT))


def zh_who(t):
    """청원 주체 — 창조과학회 산하 단체. 개신교 전체로 번지지 않게 이름을 못 박습니다."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    return svg(
        f(540, 330, t["wh_label"], 44, PAPER, opacity=0.6)
        + f'<rect x="150" y="380" width="780" height="130" rx="18" fill="{CLAIM}"/>'
        + f(540, 465, t["wh_org"], 60, PAPER)
        + f'<line x1="540" y1="530" x2="540" y2="600" stroke="{PAPER}" '
          f'stroke-width="10" opacity="0.55"/>'
        + f'<polygon points="540,630 518,596 562,596" fill="{PAPER}" opacity="0.55"/>'
        + f'<rect x="150" y="660" width="780" height="200" rx="18" '
          f'fill="{PAPER}" opacity="0.13"/>'
        + f(540, 730, t["wh_sub"], 44, PAPER, opacity=0.7)
        + f(540, 805, t["wh_name"], 46, PAPER)
        + f(540, 960, t["wh_note"], 42, ACCENT))


def zh_demands(t):
    """삭제 요구 2건."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    rows = ""
    for label, y in zip(t["dm_rows"], (400, 560)):
        rows += (f'<rect x="170" y="{y}" width="740" height="120" rx="14" fill="{PAPER}"/>'
                 + f(540, y + 82, label, 68, INK)
                 + f'<line x1="215" y1="{y + 92}" x2="865" y2="{y + 30}" '
                   f'stroke="{CLAIM}" stroke-width="14" stroke-linecap="round"/>')
    return svg(
        f(540, 330, t["dm_title"], 46, PAPER, opacity=0.65)
        + rows
        + f(540, 800, t["dm_count"], 56, ACCENT)
        + f(540, 900, t["dm_note"], 42, PAPER, opacity=0.8))


def zh_notconsulted(t):
    """생물학자들이 사전에 자문받지 못했다는 Nature 보도 내용."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    return svg(
        f(540, 350, t["nc_who"], 56, PAPER)
        + f'<rect x="150" y="410" width="780" height="170" rx="18" '
          f'fill="{PAPER}" opacity="0.13" stroke="{CLAIM}" stroke-width="8"/>'
        + f(540, 515, t["nc_what"], 60, PAPER)
        + _cross(540, 700, r=54, w=20)
        + f(540, 870, t["nc_note"], 44, PAPER, opacity=0.8))


def zh_verdict(t):
    """막은 것은 여론이 아니라 전문가 심의 — 이 편의 요점."""
    f = lambda *a, **k: _cn(*a, family=t["font"], **k)
    return svg(
        f(540, 330, t["vd_q"], 48, PAPER, opacity=0.65)
        + f'<rect x="140" y="400" width="800" height="150" rx="18" '
          f'fill="{PAPER}" opacity="0.08"/>'
        + _cross(250, 475, r=38, w=14)
        + f(600, 495, t["vd_no"], 60, PAPER, opacity=0.62)
        + f'<rect x="140" y="600" width="800" height="150" rx="18" '
          f'fill="{ACCENT}" opacity="0.18" stroke="{ACCENT}" stroke-width="6"/>'
        + _tick(250, 675, r=38, w=14)
        + f(600, 695, t["vd_yes"], 60, ACCENT)
        + f(540, 890, t["vd_note"], 44, PAPER))


ZH_DIAGRAMS = {
    "textbook": zh_textbook, "who": zh_who, "demands": zh_demands,
    "pipeline": zh_pipeline, "nature": zh_nature, "notconsulted": zh_notconsulted,
    "panel": zh_panel, "verdict": zh_verdict, "conclusion": zh_conclusion,
}


DIAGRAMS = {
    # 2012 교과서 사건 — 간체/번체는 같은 레이아웃에서 생성됩니다 (ZH).
    **{f"{pfx}01-{k}": (lambda fn=fn, t=ZH[lg]: fn(t))
       for lg, pfx in (("zh-CN", "cn"), ("zh-TW", "tw"))
       for k, fn in ZH_DIAGRAMS.items()},
    "ep001-archaeopteryx": ep001_archaeopteryx,
    "ep001-pipeline": ep001_pipeline,
    "ep001-panel": ep001_panel,
    "ep001-theory-def": ep001_theory_def,
    "ep001-ladder": ep001_ladder,
    "ep001-claim": ep001_claim,
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
