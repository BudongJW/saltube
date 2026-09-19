# saltube

> 창조과학(creation science)이 내세우는 **경험적 주장**을 과학적 증거로 검증·논박하는
> 유튜브 쇼츠 / 틱톡 채널 운영 리포지토리.

이 저장소는 영상 파일을 담지 않습니다. 채널을 **굴러가게 만드는 것들** — 전략, 편집 원칙,
주장 데이터베이스, 대본, 출처, 검수 도구, 런칭 계획 — 을 버전 관리합니다.

---

## 이 채널이 하는 일 / 하지 않는 일

| 한다 | 하지 않는다 |
|---|---|
| "지구는 6000년 되었다" 같은 **검증 가능한 주장**을 데이터로 반박 | 신자 개인·교단·특정 인물을 조롱 |
| 증거를 1차 출처(논문·데이터셋)까지 추적해 제시 | "종교 = 비과학" 식의 싸잡기 |
| 틀렸을 때 **공개 정정 영상**을 올림 | 출처 없는 단정, 인용 왜곡 |
| 과학적 방법 자체를 가르침 | 무신론 전도 |

핵심 전제: **창조과학은 신앙이 아니라 과학을 참칭한 주장들의 집합이다.**
신앙 그 자체는 반증 대상이 아니고, 우리 소재도 아닙니다. 우리가 다루는 건
"방사성 연대측정은 신뢰할 수 없다", "중간화석은 없다"처럼 **참/거짓을 가릴 수 있는 문장**뿐입니다.
이 경계선이 채널의 신뢰도이자, 플랫폼 정지를 피하는 방어선입니다. → [편집 정책](docs/03-editorial-policy.md)

---

## 저장소 구조

```
docs/                 전략·정책·운영 문서 (읽는 순서대로 번호)
content/claims.yaml   창조론 주장 데이터베이스 = 에피소드 백로그
content/scripts/      쇼츠 대본 (YAML front matter + 본문)
content/sources.md    인용 출처 마스터 목록
tools/claimctl.py     대본 검수 / 발행 캘린더 / 플랫폼 메타데이터 생성 CLI
```

## 빠른 시작

```bash
python3 tools/claimctl.py validate          # 대본 형식·길이·출처 검수
python3 tools/claimctl.py backlog           # 주장 DB 현황 (우선순위/난이도)
python3 tools/claimctl.py calendar --weeks 8 --start 2026-10-05
python3 tools/claimctl.py meta EP001        # 유튜브/틱톡 업로드 메타데이터
```

`validate`는 CI에서도 돌아갑니다. **출처 없는 주장이 들어간 대본은 머지되지 않습니다.**

## 문서

| 문서 | 내용 |
|---|---|
| [01 전략](docs/01-strategy.md) | 포지셔닝, 타깃, 채널명, 차별점 |
| [02 브랜드](docs/02-brand.md) | 톤앤매너, 비주얼, 타이포, 사운드 |
| [03 편집 정책](docs/03-editorial-policy.md) | 사실검증 3단계, 레드라인, 정정 절차 |
| [04 플랫폼 운영](docs/04-platform-playbook.md) | 쇼츠 vs 틱톡 차이, 업로드 규격, 알고리즘 |
| [05 제작 파이프라인](docs/05-production-pipeline.md) | 기획→대본→녹음→편집→발행 |
| [06 커뮤니티 대응](docs/06-community-moderation.md) | 댓글 정책, 악성 유입, 반론 처리 |
| [07 런칭 90일](docs/07-launch-90days.md) | 0주차~12주차 실행 계획 |
| [08 지표](docs/08-metrics.md) | KPI, 판단 기준, 피봇 트리거 |
| [09 리스크](docs/09-risk-and-compliance.md) | 저작권, 명예훼손, 플랫폼 정지 대응 |
| [10 포맷 검토](docs/10-format-review-ai-drama.md) | AI 인물 드라마 연재 검토 — 판정과 대안 |
