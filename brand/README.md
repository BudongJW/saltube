# 브랜드 자산

## 로고 파일

| 파일 | 용도 |
|---|---|
| `logo-primary.*` | **기본.** 청록 배경 + 크림 "1분" + 금색 바. 틱톡·유튜브 프로필 |
| `logo-light.*` | 밝은 배경·워터마크용 (크림 배경 + 청록 글자) |
| `logo-mono-dark.*` | 단색. 흑백 인쇄, 썸네일 오버레이 |

각 변형마다 `.svg` + `1024 / 512 / 200 / 96 / 40` px PNG.
**업로드는 512px 이상**을 쓰세요. 40px 파일은 축소 가독성 확인용입니다.

`_preview.png` — 다크·라이트 UI에서 120/56/40px로 본 대조 시트.

## 사양

- 폰트: **Pretendard Bold** (오픈소스, 상업 이용 가능)
- 컬러: `#2E7D6B` 청록 / `#E0A800` 금 / `#F5F3EE` 크림 / `#12151A` 먹
  → [02 브랜드](../docs/02-brand.md) §3
- 원형 크롭 전제. 모든 요소가 안전 영역 안에 있음

## 재생성

```bash
pip install cairosvg
# Pretendard Bold 를 ~/.fonts/ 에 두고 fc-cache -f
python3 tools/makelogo.py
```

## AI 이미지로 만들고 싶다면

[`PROMPTS.md`](PROMPTS.md) — 나노 바나나(Gemini)용 프롬프트 5종.
글자 없는 심볼 안과 한글 포함 안을 나눠뒀습니다.
