# 실제 국내 종목 컵앤핸들 문제 세트

작성일: 2026-07-04

## 목표

합성 차트가 아니라 실제 국내 상장 종목 주봉 데이터에서 컵앤핸들 스코어보드 80점 이상을 통과한 구간을 찾아 게임 문제로 등록했다.

## 데이터 소스

- 국내 후보 목록: Naver Finance 시가총액 페이지
- 주봉 OHLCV: Yahoo Finance chart API
- 대상 시장: KOSPI, KOSDAQ
- 제외 대상: ETF, ETN, 스팩, 레버리지/테마형 펀드성 상품
- 스캔 후보 수: 1,265개

## 선정 기준

30주 visible window와 이후 5주 actual next candles를 기준으로 아래 조건을 점수화했다.

- 5주 이내 30% 이상 급등
- 급등 이후 최소 4주 이상의 완만한 U자형 컵
- 컵 낙폭은 급등 구간 최고 종가 대비 컵 저점 종가 30% 이내
- 컵 형성 중 거래량은 급등 구간보다 감소
- 상승 주 거래량이 하락 주 거래량보다 우세
- 하락 주 거래량이 5주 거래량 평균을 상회하는 횟수 제한
- 오른쪽 림 종가는 왼쪽 림 종가 대비 90~105%
- 핸들 낙폭은 20% 이내이며 컵 낙폭보다 작음
- 실제 다음 5주 종가 흐름이 `up`으로 분류되는 구간만 선택

## 선정된 10개 문제

| No | 종목코드 | 종목명 | 시장 | 기준일 | 점수 |
| --- | --- | --- | --- | --- | --- |
| 1 | 450080 | 에코프로머티 | KOSPI | 2026-03-01 | 100.0 |
| 2 | 038540 | 상상인 | KOSDAQ | 2025-08-17 | 100.0 |
| 3 | 448280 | 에코아이 | KOSDAQ | 2025-05-11 | 100.0 |
| 4 | 041440 | 현대에버다임 | KOSDAQ | 2024-12-01 | 100.0 |
| 5 | 065450 | 빅텍 | KOSDAQ | 2024-05-19 | 100.0 |
| 6 | 148150 | 세경하이테크 | KOSDAQ | 2023-04-09 | 100.0 |
| 7 | 001570 | 금양 | KOSPI | 2023-03-12 | 100.0 |
| 8 | 190510 | 나무가 | KOSDAQ | 2022-05-01 | 100.0 |
| 9 | 005850 | 에스엘 | KOSPI | 2021-05-23 | 100.0 |
| 10 | 147830 | 제룡산업 | KOSDAQ | 2021-04-25 | 100.0 |

## 구현 파일

- `backend/scripts/find_real_cup_handle_questions.py`
  - 국내 후보 목록 수집
  - 주봉 OHLCV 다운로드
  - 컵앤핸들 스코어 계산
  - seed SQL과 후보 JSON 생성

- `db/migrations/0004_question_source_metadata.sql`
  - `questions`에 실제/합성 여부와 데이터 출처 컬럼 추가

- `db/seeds/real_cup_handle_questions.sql`
  - 실제 컵앤핸들 문제 10개 등록

- `data/real_cup_handle_candidates.json`
  - 선정 결과와 차트 데이터, 점수 breakdown 보관

## 검증 결과

```text
real_weekly_cup_handle_questions=10
first_question_id=23000000-0000-0000-0000-000000000001
first_question_source=450080.KS
first_question_synthetic=False
```

자동 검증:

```bash
pnpm test:backend
pnpm lint:frontend
pnpm --dir frontend build
```

주의: 이 스코어보드는 학습용 패턴 판정 기준이며 투자 조언, 매매 추천, 수익 예측이 아니다.
