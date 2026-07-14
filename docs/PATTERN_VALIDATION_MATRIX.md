# 차트고시 패턴 검증 매트릭스

최종 업데이트: 2026-07-15

이 문서는 패턴별 공식 Markdown, 문제 생성 로직, 검수 화면에서 반드시 같은 기준을 바라보게 하기 위한 운영 체크리스트다.

공식 패턴 문서는 `docs/patterns/` 아래의 패턴별 단일 파일을 기준으로 한다.

## 공통 검증 원칙

- 패턴당 공식 문서는 1개만 둔다.
- 신규 문제 생성 전에는 해당 패턴의 공식 문서와 생성 스크립트 조건을 먼저 비교한다.
- 검수 화면에서는 최소한 `pattern_evidence`, `pattern_score_breakdown`, `pattern_markers`가 함께 보이도록 한다.
- 사용자가 검수 중 질문한 핵심 지점은 다음 생성 때 재현 가능해야 한다.
- 화면에 표시되는 봉 기준은 1번째 봉부터 세며, 데이터 배열 기준 인덱스는 사용하지 않는다.
- 모든 차트는 로그 스케일을 기본으로 한다.
- 주봉은 MA10/30/40, 일반 일봉은 MA50/150/200, 눌림목 일봉은 MA5/10/20/60을 기본으로 한다.

## 패턴별 단일 원본

| 번호 | 패턴 | 공식 문서 | 기준 봉 | 검수 핵심 마커 |
|---:|---|---|---|---|
| 1 | 컵앤핸들 | `docs/patterns/01-cup-and-handle.md` | 주봉 | 급등 시작, 왼쪽림, 컵 바닥, 오른쪽림, 핸들 끝 |
| 2 | W바닥 | `docs/patterns/02-double-bottom.md` | 일봉 | 1차 저점, 넥라인, 2차 저점, 회복봉 |
| 3 | 박스권 돌파 | `docs/patterns/03-box-breakout.md` | 일봉 | 상단 저항, 하단 지지, 돌파봉 |
| 4 | 신고가 돌파 | `docs/patterns/04-new-high-breakout.md` | 일봉 | 이전 신고가, 돌파봉 |
| 5 | 눌림목 | `docs/patterns/05-pullback.md` | 일봉 | 선행 고점, 조정 시작, 확정봉 |
| 6 | 변동성축소 | `docs/patterns/06-volatility-contraction.md` | 주봉 | 국소 고점들, 수축 저점들, 피벗 돌파 |
| 7 | 깃발형 | `docs/patterns/07-high-tight-flag.md` | 주봉 | 급등 시작, 급등 고점, 조정 확인 |
| 8 | 플랫베이스 | `docs/patterns/08-flat-base.md` | 주봉 | 선행 고점, 베이스 시작, Tight 3주, MA10 근접 |
| 9 | 상승장악형 | `docs/patterns/09-bullish-engulfing.md` | 일봉 | 음봉, 양봉 장악, 다음 봉 |
| 10 | 상승초입 | `docs/patterns/10-early-stage2.md` | 주봉 | 베이스 시작, 상단들, 돌파봉 |

## 코드 동기화 체크리스트

| 점검 항목 | 확인 위치 | 완료 기준 |
|---|---|---|
| 패턴 이름/순서 | `db/seeds/patterns.sql` | 공식 문서 10개와 slug/name/sort_order가 일치 |
| 스코어보드 정의 | `db/seeds/patterns.sql`, `db/seeds/remaining_pattern_scorecards.sql` | 공식 문서의 필수 조건과 점수 항목이 반영 |
| 문제 생성 조건 | `backend/scripts/find_real_*.py` | 후보 제외 조건과 가산/감점 조건이 공식 문서와 일치 |
| 문제 근거 문구 | `questions.pattern_evidence` | 사용자가 왜 이 문제인지 이해할 수 있는 수치 포함 |
| 핵심 봉 마커 | `questions.pattern_markers` | 검수 핵심 마커가 날짜/라벨로 저장 |
| 검수 화면 | `/review/questions` | 마커의 봉 번호, 날짜, OHLC, 스코어 항목이 화면에 표시 |
| 실제 출제 화면 | `/play`, `/training/[patternKey]` | 기준 봉/이평선/로그 스케일이 패턴 문서와 일치 |

## 문제 생성 전 확인 순서

1. `docs/patterns/{패턴}.md`에서 필수 조건과 제외 조건을 확인한다.
2. 생성 스크립트의 평가 함수가 필수 조건을 먼저 탈락 처리하는지 확인한다.
3. 스코어 항목이 `pattern_score_breakdown`에 저장되는지 확인한다.
4. 핵심 봉이 `pattern_markers`에 저장되는지 확인한다.
5. `/review/questions?pattern={slug}`에서 봉 번호와 근거 문구를 검수한다.
6. 검수 승인된 문제만 사용자 출제 후보로 유지한다.

## 검수 중 자주 확인할 질문

- 이 마커가 실제로 화면에서 몇 번째 봉인가?
- 스코어 문구의 수치는 어떤 봉과 어떤 가격을 기준으로 계산했는가?
- 문제 마지막 봉이 공식 문서의 마지막 봉 정의와 일치하는가?
- 다음 5봉 정답 판정이 상승 10% 이상, 하락 -10% 이하, 그 외 횡보 기준과 일치하는가?
- 패턴 후보 제외 조건을 통과하지 못한 문제는 생성 단계에서 제거되는가?
