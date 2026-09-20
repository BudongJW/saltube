# 나노 바나나(Gemini) 프로필 사진 프롬프트

> 브랜드 컬러 — `#2E7D6B` 청록(사실) / `#B4472F` 벽돌(주장) / `#E0A800` 금(수치)
> / `#F5F3EE` 크림 / `#12151A` 먹. → [02 브랜드](../docs/02-brand.md) §3

## 먼저 알아둘 것

**한글 텍스트는 AI 이미지 모델이 자주 깨뜨립니다.** "1분"이 "1뷴", "1푼"으로 나오거나
획이 뭉개지는 일이 흔합니다. 그래서 두 갈래로 준비했습니다.

- **A그룹 — 글자 없는 심볼**: 실패 확률 낮음. 나중에 "1분"을 직접 얹으면 됩니다
- **B그룹 — 글자 포함**: 한 번에 끝나지만 **글자 모양을 반드시 확대해 확인**하세요

프로필은 **원형으로 잘립니다.** 모든 프롬프트에 여백 지시를 넣어뒀습니다.

---

## A그룹 — 글자 없는 심볼 (권장)

### A1. 초침이 쓸고 간 1분

```
A flat vector app icon. A minimalist clock face on a solid deep teal (#2E7D6B)
circular background. Only four tick marks at 12, 3, 6, 9 in cream (#F5F3EE),
thin and short. A single bold hand points from center to the 1-minute position
(just past 12), drawn in warm gold (#E0A800), with a translucent gold wedge
sweeping from 12 to that hand showing the elapsed minute. Perfectly centered,
generous margin so nothing touches the edge. Flat design, no gradient, no shadow,
no texture, no outline glow. Clean geometric shapes only. Must stay legible when
scaled down to 40 pixels. Square 1:1 composition.
```

### A2. 지층 — 아래로 갈수록 오래된

```
A flat vector app icon. Five horizontal rock strata bands stacked inside a
circular composition, on a near-black (#12151A) background. The bands are cream
(#F5F3EE) at varying opacity, getting more solid toward the bottom. The topmost
band is warm gold (#E0A800). Bands have slightly rounded corners and even gaps.
Centered with clear margin from the circle edge. Flat vector, no gradient,
no shadow, no texture, no text. Geological cross-section feel, clean and
diagrammatic. Legible at 40 pixels. Square 1:1.
```

### A3. 돋보기와 지층

```
A flat vector app icon on a solid deep teal (#2E7D6B) circular background.
A thick cream (#F5F3EE) magnifying glass outline positioned slightly upper-left,
its handle extending to the lower right. Inside the lens, three simple horizontal
rock strata lines in warm gold (#E0A800). Bold uniform stroke weight, minimum
detail. Centered composition with breathing room. Flat design, no gradient,
no shadow, no highlights on the glass, no text. Must read clearly at 40 pixels.
Square 1:1.
```

---

## B그룹 — 한글 "1분" 포함

### B1. 타이포 중심 (가장 안전한 글자 안)

```
A flat vector app icon. Solid deep teal (#2E7D6B) circular background.
In the exact center, the Korean text "1분" in a heavy geometric sans-serif,
cream colored (#F5F3EE), very large and bold, occupying about 55% of the width.
Directly beneath the text, a short thick horizontal bar in warm gold (#E0A800)
with rounded ends, slightly narrower than the text. The Korean characters must
be rendered accurately: the digit "1" followed by the Hangul syllable "분"
(consonant ㅂ, vowel ㅜ, final consonant ㄴ). Flat design, no gradient, no shadow,
no texture, no additional decoration. Centered with generous margin.
Legible at 40 pixels. Square 1:1.
```

> **확인 절차**: 생성 후 확대해서 `분`의 받침 `ㄴ`이 제대로 붙었는지,
> `ㅜ`의 세로획이 있는지 보세요. 하나라도 이상하면 재생성하거나 A그룹으로 가세요.

### B2. 시계 + 글자

```
A flat vector app icon. Solid deep teal (#2E7D6B) circular background with four
minimal cream tick marks at 12, 3, 6, 9 near the edge. In the center, the Korean
text "1분" in a heavy geometric sans-serif, cream (#F5F3EE), bold and large.
A single thin gold (#E0A800) clock hand points from center toward the 1-minute
mark, passing behind the text without overlapping the letterforms. The Hangul
syllable "분" must be rendered correctly and cleanly. Flat vector, no gradient,
no shadow, no texture. Centered, ample margin. Legible at 40 pixels. Square 1:1.
```

---

## 한국어 프롬프트 (같은 내용)

나노 바나나는 한국어 프롬프트도 받습니다. 다만 색상 지정은 헥스 코드를 그대로 쓰세요.

### A1 한국어판
```
플랫 벡터 앱 아이콘. 진한 청록색(#2E7D6B) 원형 배경 위의 미니멀 시계 문자판.
12, 3, 6, 9 위치에만 짧고 가는 크림색(#F5F3EE) 눈금. 중심에서 1분 위치(12시
바로 오른쪽)로 뻗은 굵은 바늘 하나, 따뜻한 금색(#E0A800). 12시부터 그 바늘까지
반투명 금색 부채꼴로 지나간 1분을 표시. 정중앙 배치, 가장자리에 닿지 않도록
여백 충분히. 평면 디자인, 그라데이션·그림자·질감·글자 없음. 기하학적 도형만.
40픽셀로 줄여도 알아볼 수 있어야 함. 정사각형 1:1.
```

---

## 생성 후 필수 확인

```
☐ 원형으로 잘라도 핵심 요소가 안 잘리는가
☐ 40px로 축소해서 뭉개지지 않는가        ← 대부분 여기서 탈락
☐ 다크 배경(틱톡)과 밝은 배경 양쪽에서 뜨는가
☐ (B그룹) "분" 글자가 정확한가 — 확대해서 확인
☐ 그라데이션·그림자가 끼어들지 않았는가
```

## 재생성이 필요할 때 덧붙일 문장

| 증상 | 추가할 문장 |
|---|---|
| 너무 복잡함 | `Extremely simple. Maximum three shapes. Icon-level reduction.` |
| 그라데이션이 생김 | `Strictly flat solid colors only. Absolutely no gradient or shading.` |
| 요소가 가장자리에 닿음 | `Add 15% empty padding on all sides. Nothing touches the edge.` |
| 3D처럼 보임 | `2D flat illustration. No perspective, no depth, no bevel.` |
| 글자가 깨짐 | `Render the Korean text with precise, correct Hangul letterforms.` 또는 A그룹으로 전환 |
