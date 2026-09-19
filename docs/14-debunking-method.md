# 14. 논박 방법 — 연구 기반 대본 구조

> 출처: [The Debunking Handbook 2020](../content/sources.md) (22인 합의 문서) 및 관련 논문.
> 우리는 논박 채널인데, **논박의 효과에 관한 연구를 반영하지 않고 있었습니다.** 이 문서가 그것을 고칩니다.

## 0. 한 줄 요약

우리 기존 구조는 **주장 → 반박 → "틀렸습니다"** 였습니다.
연구가 권하는 구조는 **사실 → 주장 → 왜 틀렸는가(오류의 이름) → 사실 재강조** 입니다.
차이는 두 군데입니다: **사실로 시작하고**, **단순 부정으로 끝내지 않습니다.**

---

## 1. 핵심 문제 — 지속 영향 효과

> "misinformation often continues to influence people's thinking even after they receive and
> accept a correction—this is known as the **continued influence effect**"

정정을 받아들인 사람도 계속 그 오정보에 의존합니다. 그래서 **"틀렸다"고 말하는 것만으로는 부족**합니다.

---

## 2. 권장 구조 — FACT · MYTH · FALLACY · FACT

핸드북의 원문 지침을 그대로 옮깁니다.

| 단계 | 원문 지침 | 우리 대본에서 |
|---|---|---|
| **FACT** | "Lead with the facts, but only if it's clear and sticky — make it simple, concrete, and plausible." | 0~5초. 반박이 아니라 **사실 하나**로 시작 |
| **경고** | "Warn that a myth is coming." | "그런데 이런 말을 들어보셨을 겁니다" |
| **MYTH** | "Repeat the misinformation, **only once**, directly prior to the correction." | 주장을 **한 번만** 인용 |
| **FALLACY** | "Point out logical or argumentative fallacies underlying the misinformation." / "Explain how the myth misleads." | **오류의 이름을 부른다** |
| **FACT** | "Finish by reinforcing the fact. Repeat the fact multiple times if possible." | 첫 사실을 다시 |

### 바뀌는 것 두 가지

**① 사실로 시작한다 (기존: 주장으로 시작)**

기존 EP001 훅: `"진화는 이론일 뿐이잖아요."` — 주장이 첫 화면
바뀐 훅: `과학에서 '이론'은 추측의 반대말입니다.` — 사실이 첫 화면

**② 인과적 대안을 제시한다 (기존: 단순 부정)**

> "Corrections are more effective if in addition to providing a simple retraction ("not true"),
> they **propose a causal alternative**, and generally if they provide substantive, relevant
> detail and establish coherence."

`"이 주장은 증거와 맞지 않습니다"`(단순 부정) → **왜 그 오해가 생겼는지, 실제로는 무엇인지**까지.
설명에 뚫린 구멍을 그대로 두면 사람은 원래 믿던 것으로 그 구멍을 다시 메웁니다.

---

## 3. 오류의 이름을 부를 것

> "A technique- or logic-based rebuttal has the advantage that it is based on the detection of
> **generic violations of logic, and hence transfers outside a specific context**."

이게 이 채널의 레버리지입니다. `"중간화석은 있습니다"`는 그 주제에만 쓰입니다.
`"이건 빈틈에 호소하는 논증입니다"`는 **시청자가 다음에 만날 다른 주장에도 적용**됩니다.

그래서 `content/claims.yaml`의 모든 주장에 **`fallacy` 항목**을 추가했습니다.

| 주장 | 오류 |
|---|---|
| 중간화석이 없다 | 무한 후퇴 요구 — 어떤 증거로도 충족 불가 |
| 열역학 제2법칙이 진화를 반증 | 조건 생략 인용 (고립계) |
| 진화는 '이론'일 뿐 | 다의어 오류 |
| 진화론이 나치의 원인 | 발생론적 오류 + 자연주의적 오류 |
| 다윈이 임종에 회개 | 논점 일탈 |

---

## 4. 연구가 검증해준 기존 원칙

우리가 이미 하고 있던 것 중 실증적 뒷받침이 확인된 것들:

| 우리 원칙 | 근거 |
|---|---|
| **출처 강박** ([01 전략](01-strategy.md) §5) | "corrections which identify a distal source are more effective than **unsourced** corrections" |
| **집단 비하 금지** ([03 편집정책](03-editorial-policy.md) §1) | "language in some debunking texts ('vaccine denier') runs the risk of **stigmatizing** specific groups and may thus enhance polarization" |
| **인신공격 금지** | "signalling that the recipient is **valued** and the correction is not a personal attack is important" |
| **쇼츠(짧은 형식)** | "**Short debunkings** save resources and may increase the willingness to engage" / Ecker et al. 2019 |
| **싸잡기 금지, 가톨릭·주류 개신교 언급** | "Corrections that challenge people's worldviews are typically **less effective** than worldview-consonant corrections" |
| **전문가 합의 제시** | "Corrections are more effective if they come from trusted sources or **highlight expert consensus**" |

## 5. 연구가 뒤집은 우리의 걱정

| 걱정했던 것 | 연구 결과 |
|---|---|
| 주장을 화면에 띄우면 오히려 각인되지 않을까 | **"The familiarity backfire effect ... is not a robust phenomenon."** 한 번만 인용하면 괜찮습니다 |
| 반박을 여러 개 하면 역효과 아닐까 | **"The overkill backfire effect ... is not a robust empirical phenomenon."** |
| 신념을 건드리면 더 완고해지지 않을까 | **"The worldview backfire effect ... is not a robust empirical phenomenon."** 단, **"worldview backfire effects can and do occur."** 없다는 뜻이 아니라 일반적이지 않다는 뜻 |

## 6. 반대 증거 — 과신 금지

> **Swire-Thompson et al. (2021), "Correction format has a limited role when debunking misinformation"**

정정의 **형식**이 효과에 미치는 영향은 제한적이라는 결과입니다.
즉 **구조를 바꾼다고 효과가 보장되지 않습니다.**

우리 편집 정책 §2 3단계가 "상대 주장의 가장 강한 버전을 읽으라"고 요구하므로,
우리 자신의 방법론에도 같은 기준을 적용합니다. 이 논문을 `S-SWIRE-2021`로 등재했습니다.

**실무 결론**: 구조는 채택하되, **내용의 정확성이 형식보다 우선**입니다.
구조를 맞추려다 사실을 비틀면 그건 완전한 손실입니다.

## 7. 실패한 정정의 대가

> "Failed attempts at correction are likely to **strengthen belief** in the initial misinformation."

틀린 논박은 0점이 아니라 **마이너스**입니다. 상대 주장을 더 굳힙니다.
[08 지표](08-metrics.md) §6의 피봇 트리거 — "정정 사안 2회 이상 발생 시 발행 중단" — 의 근거가 이것입니다.

## 8. 선제 대응 (접종) — 향후 과제

> "Because misinformation is sticky, it's best **preempted**. This can be achieved by explaining
> misleading or manipulative argumentation strategies to people—a technique known as
> **'inoculation'**."

논박보다 **선제 접종이 1차 방어선**입니다. 새 콘텐츠 기둥 후보:

> **《이런 논법이 나오면 의심하세요》** — 특정 주장이 아니라 **논법 자체**를 먼저 가르치는 편.
> C 기둥(방법론)의 확장이며, §3의 "전이 가능성" 원리와 같은 이유로 효율이 높습니다.

→ 백로그 추가 대상. [01 전략](01-strategy.md) §6

---

## 9. 체크리스트 (대본 작성 시)

```
☐ 사실로 시작하는가 (주장이 아니라)
☐ 그 사실이 단순·구체적·그럴듯한가
☐ 주장을 인용하기 전에 경고했는가
☐ 주장을 한 번만 인용했는가
☐ 오류의 이름을 불렀는가          ← 가장 자주 빠지는 항목
☐ 인과적 대안을 제시했는가 (단순 부정 X)
☐ 마지막에 첫 사실을 다시 강조했는가
☐ 집단을 지칭하는 낙인 표현이 없는가
```

`tools/claimctl.py validate` 가 이 중 기계로 검사 가능한 항목을 확인합니다.
