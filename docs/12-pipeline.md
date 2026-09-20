# 12. 자동화 파이프라인

리포에 들어온 자동화는 두 갈래입니다.

```
  [수집]  Crossref ──harvest──▶ inbox ──사람 검토──▶ references.yaml ──refcheck──▶ sources.md
                                  ▲                                                    │
                            매월 1일 PR                                                 │
                                                                                       ▼
  [제작]  claims.yaml ──▶ 대본 ──claimctl validate──▶ produce ──▶ build/  ──▶ 편집 ──▶ 발행
                                      │                              │
                                 CI에서 차단                    CI 아티팩트로 배포
```

**두 갈래 모두 사람이 끊는 지점이 있습니다.** 수집은 자동이지만 등재는 수동이고,
빌드는 자동이지만 발행은 수동입니다. 이건 게으름이 아니라 설계입니다 —
틀린 인용을 빠르게 많이 내는 것이 이 채널의 최악의 실패이기 때문입니다.
→ [08 지표](08-metrics.md) §6 피봇 트리거

---

## A. 수집 파이프라인

### 자동 (매월 1일)

`.github/workflows/harvest.yml` 이 `tools/harvest.py` 를 돌려 Crossref에서
최근 논문을 긁고, **PR을 하나 엽니다.** PR은 `content/inbox/` 에 후보 파일만 추가하며
`references.yaml` 은 건드리지 않습니다.

질의는 [`content/harvest_queries.yaml`](../content/harvest_queries.yaml) 에 정의돼 있고,
각 질의는 `claims.yaml` 의 주장 ID에 연결됩니다.
**질의를 손보는 것이 이 파이프라인의 유지보수 전부입니다.**

### 수동 검토

```bash
python3 tools/harvest.py inbox                        # 미처리 후보
python3 tools/harvest.py promote <DOI> --claims C003 --note "..."
python3 tools/harvest.py drop <DOI>                   # 기각 — 다시 안 올라옴
python3 tools/refcheck.py verify && python3 tools/refcheck.py render
```

`drop` 한 DOI는 `content/inbox/seen.yaml` 에 기록되어 다음 수집에 다시 올라오지 않습니다.
같은 후보를 매달 다시 판단하지 않아도 됩니다.

### 검색 품질에 대해

Crossref **관련도(score) 12 이상**만 통과시킵니다. 이 필터가 없으면
발행일이 오염된 레코드(연도 2121 등)와 주제 무관 논문이 상위를 채웁니다.
그래도 키워드 검색의 한계상 무관한 결과는 섞입니다 — **그래서 사람이 거릅니다.**

후보 순위는 `걸린 질의 수 → 관련도 → 인용수` 순입니다.
여러 질의에 동시에 걸린 논문은 우리 관심사와 겹침이 크다는 뜻입니다.

### 수동 수집이 필요한 영역

- **국내 자료** — 한국창조과학회 간행물 등. 자동 수집 불가.
  수집 규칙은 [11 대결 포맷](11-format-confrontation.md) §4
- **단행본·판례** — Crossref 미수록. 직접 등재 후 `manual_checked` 표기
- 역사 확정 사안(파스퇴르, 팔럭시 강 등)은 질의에서 제외했습니다

---

## B. 제작 파이프라인

### 빌드

```bash
python3 tools/claimctl.py validate    # 먼저 통과해야 함
python3 tools/produce.py EP001        # 또는 --all
```

`build/EP001/` 에 편집자가 바로 쓸 수 있는 여섯 개가 생깁니다.

| 파일 | 용도 |
|---|---|
| `narration.txt` | TTS/녹음용 낭독 원고. 큐 번호 + 예상 시각. 마크다운·출처 마커 제거됨 |
| `EP001.srt` | 번인 자막 타이밍 초안. 편집 프로그램에 그대로 불러오기 |
| `shotlist.md` | 큐별 화면 지시 + **컷별 출처 자막**. 편집자의 주 작업 문서 |
| `metadata.md` | 유튜브/틱톡 업로드 메타데이터. 실명 편이면 추가 확인 항목 포함 |
| `pinned_comment.txt` | 고정 댓글 전문 |
| `checklist.md` | 발행 전 확인 목록. 미검증 출처와 `active` 등급 경고 포함 |

`build/` 는 커밋하지 않습니다. 대본에서 언제든 재생성되는 파생물이고,
CI가 빌드해 **워크플로 아티팩트**로 올립니다(90일 보관).

### 제작 순서 — 이 순서를 지키세요

```bash
python3 tools/claimctl.py validate    # 1. 먼저 통과해야 함
python3 tools/produce.py  EP001       # 2. 낭독 원고·SRT 초안·샷리스트
python3 tools/tts.py      EP001       # 3. 음성 합성 + SRT 를 실측으로 재작성
#    ← 여기서 assets/EP001/shots.yaml 의 file: 을 채웁니다
python3 tools/render.py   EP001       # 4. 영상 (음성은 자동으로 얹힙니다)
```

**TTS 가 렌더보다 먼저여야 합니다.** 순서가 바뀌면 음절 추정 타이밍이 쓰입니다.

`produce.py` 를 다시 돌려도 실측 SRT 는 덮어쓰지 않습니다(메타데이터만 갱신).
대본 대사를 고쳤다면 `tts.py` 를 다시 돌리세요.

### 타이밍 추정

한글 음절 수 기반으로 낭독 시간을 계산합니다
(`tools/claimctl.py` 의 `SYLLABLES_PER_MIN`, 현재 **분당 302음절**).

이 값은 추정이 아니라 **실측값**입니다 — 합성된 mp3 길이를 SRT 대사의 음절 수로 나눈 것.
최초 추정치 355 는 29% 낙관적이어서 5편 전부 60초를 넘겼습니다.

> **`tts.py` 의 `RATE` 를 바꾸면 이 값도 같이 바꾸세요.**
> 안 바꾸면 추정이 조용히 어긋나서, 목표보다 길다고 착각하고 멀쩡한 문장을 잘라냅니다.
> +15% → 275, +30% → 302.

### 샷 리스트의 출처 열

증거 컷에 `[S-XXX]` 마커가 있으면 샷 리스트에 **화면에 띄울 출처 문자열**이 자동으로 채워집니다.
서지 미검증 출처는 `☐ 사람 확인 필요`로 표시됩니다.

> **출처 자막 없는 증거 컷은 편집 단계에서 반려** — [02 브랜드](02-brand.md) §3

---

## C. CI

| 워크플로 | 시점 | 하는 일 |
|---|---|---|
| `validate.yml` | push / PR | 대본 검수, 레퍼런스 현황, `sources.md` 동기화 확인 |
| `validate.yml` (references 잡) | 매월 / 수동 | 전체 DOI 재검증 — 철회·변경 감시 |
| `harvest.yml` | 매월 1일 / 수동 | 레퍼런스 후보 수집 → PR |
| `produce.yml` | content·tools 변경 시 | 제작 패키지 빌드 → 아티팩트 |

`validate.yml` 은 `sources.md` 가 `references.yaml` 과 어긋나면 빌드를 깹니다.
생성물을 손으로 고치는 것을 막기 위함입니다.

---

## D. 도구 요약

| 도구 | 역할 |
|---|---|
| `claimctl.py` | 대본 검수 · 백로그 · 발행 캘린더 · 업로드 메타데이터 |
| `refcheck.py` | Crossref DOI 검증 · 레퍼런스 검색 · `sources.md` 생성 |
| `harvest.py` | 신규 레퍼런스 정기 수집 · 후보 승격/기각 |
| `produce.py` | 검증된 대본 → 제작 패키지 |

의존성은 PyYAML 하나와 `curl` 뿐입니다. 무거운 스택을 얹지 않았습니다 —
1인 운영에서 유지보수 비용이 드는 도구는 결국 안 쓰게 됩니다.
