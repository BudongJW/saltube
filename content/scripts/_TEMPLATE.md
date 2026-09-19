---
id: EP000
claim_id: C000
title: "화면·업로드용 제목 (40자 이내)"
pillar: A                  # A 주장해체 / B 증거소개 / C 방법론 / D 역사·판례 / E 정정
confidence: settled        # settled / strong / active  ← docs/03-editorial-policy.md §3
duration_target: 55        # 초. 쇼츠 45~60 권장
sources: [S-XXX]           # content/sources.md 의 ID. 본문 [S-XXX] 마커와 일치해야 함
logic_only: false          # true면 출처 없이도 validate 통과 (순수 논리 분석 편)
status: drafted            # drafted / recorded / published
platforms: [youtube_shorts, tiktok]
hashtags: ["#진화", "#창조과학", "#과학"]
# ── 근거 대조 — 본문의 모든 [S-XXX] 마커에 항목이 있어야 함 ──
# `python3 tools/attest.py init EP0XX` 로 뼈대 생성.
# quote 는 반드시 원문 그대로. 요약하면 attest check 에서 실패합니다.
attest:
  - source: S-XXX
    supports: "이 출처가 뒷받침하는 내용 (한국어)"
    quote: "원문 그대로의 문장"
    locator: abstract        # abstract(기계 대조) | p.123 | fig.2 (사람 서명 필요)
    checked_by: ""           # 초록 대조 불가 시 원문 확인한 사람
    checked: 2026-01-01

corrections: []            # 정정 시 추가: [{date: "2026-01-01", what: "...", episode: "EP0XX"}]

# ── 실명 대상 편에만 사용 — docs/11-format-confrontation.md ──
# named_target 을 쓰면 quotes 블록이 필수가 되고, 각 항목의
# text/source/archived/context_saved 가 없으면 validate 에서 차단됩니다.
#
# named_target: "한국창조과학회"
# quotes:
#   - text: "원문 그대로. 요약 금지."
#     source: "URL 또는 서지사항 (YYYY-MM-DD 접근)"
#     archived: "archive.today 주소 — 원문 삭제 대비"
#     context_saved: true      # 앞뒤 문단 보관 완료 여부
---

## FACT (0~10초)
> 화면: 사실을 `--evidence` 색으로 전체 화면

**사실로 시작합니다. 주장으로 시작하지 않습니다.**
단순·구체적·그럴듯해야 합니다. 여기서 이탈이 결정됩니다. [S-XXX]

## 경고 (10~13초)
"그런데 이런 말, 들어보셨을 겁니다."
주장이 나온다는 것을 미리 알립니다 — 논박 방법 §2

## MYTH (13~18초)
> 화면: 주장 인용 — `--claim` 색

주장을 **가장 강한 형태로, 단 한 번만** 인용합니다.
허수아비 금지(편집 정책 §2), 반복 금지(논박 방법 §2).

## 오류 (18~45초)
> 화면: 오류의 이름을 크게

**오류의 이름을 부릅니다.** `claims.yaml` 의 `fallacy` 항목을 쓰세요.
논법 비판은 시청자가 다음에 만날 다른 주장에도 전이됩니다 — 논박 방법 §3

그리고 **왜 그 오해가 생기는지** 설명합니다.
"틀렸습니다"로 끝내면 설명에 구멍이 남고, 시청자는 그 구멍을 원래 믿던 것으로 다시 메웁니다.

증거의 모든 사실 주장에 `[S-XXX]` 마커를 붙일 것.

## FACT 재강조 (45~57초)
**첫 사실을 다시** 말합니다. 단순 부정으로 끝내지 않습니다.
"그러므로 신은 없다"로 넘어가면 편집 정책 §1 위반입니다.

## 아웃트로
"출처는 고정 댓글에."

---

## 예상 재반박 (발행 전 필수 작성 — 영상에는 안 들어감)
- 재반박 1: → 우리 대응:
- 재반박 2: → 우리 대응:

## 고정 댓글 (발행 시 그대로 복사)
```
출처
[S-XXX] 저자, 제목, 저널 권(연도) 쪽. doi:...
```
