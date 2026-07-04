# 컵앤핸들 주봉 훈련 세트

작성일: 2026-07-04

## 목표

컵앤핸들 패턴은 일봉보다 주봉에서 구조가 더 잘 드러나는 패턴으로 보고, 패턴별 훈련장에 주봉 기준 문제 10개를 추가했다.

이번 세트는 실제 시장 데이터 자동 탐지 결과가 아니라, 현재 정의한 컵앤핸들 스코어보드 기준을 반영한 MVP용 훈련 seed다. 향후 자동 패턴 탐지 단계에서 실제 OHLCV 원천 데이터 기반 문제로 교체하거나 보강한다.

## 게임 구성

- 패턴: 컵앤핸들
- 봉 기준: 주봉
- 화면 표시 봉 수: 과거 30봉
- 정답 공개: 답안 제출 후 실제 다음 5봉을 차트에 1봉당 0.7초씩 표시
- 결과 이동: 5봉 공개 후 결과 화면으로 이동
- 색상 규칙: 양봉 빨간색, 음봉 파란색
- 문제 수: 10개
- 정답 방향: MVP 기준 모두 `up`

## 스코어보드 반영 기준

각 seed 문제는 아래 요소를 만족하도록 구성했다.

- 주봉 기준 5봉 이내 30% 이상 급등
- 급등 이후 최소 4주 이상의 완만한 U자형 컵
- 컵 저점 종가는 급등 구간 최고 종가 대비 30% 이상 하락하지 않음
- 컵 형성 중 거래량은 급등 구간보다 감소
- 컵과 핸들 구간에서 상승 주의 거래량이 하락 주보다 우세
- 하락 주 거래량이 5주 이동평균선을 크게 상회하는 구간은 제한
- 오른쪽 림 종가는 왼쪽 림 종가의 90~105% 범위
- 오른쪽 림 이후 핸들 구간 낙폭은 최대 20% 이내이며 컵 낙폭보다 작음

## 변경 파일

- `db/seeds/weekly_cup_handle_questions.sql`
  - 주봉 컵앤핸들 문제 10개 생성
  - `timeframe = '1w'`
  - `chart_data` 30봉, `actual_next_candles` 5봉 생성
  - `pattern_evidence`에 판정 근거 저장

- `backend/app/repositories/questions.py`
  - 컵앤핸들 조회 시 `timeframe = '1w'` 문제를 우선 반환
  - 질문 응답에 `timeframe` 포함

- `backend/app/repositories/answers.py`
  - 결과 응답에 `timeframe` 포함

- `frontend/src/app/training/[patternKey]/page.tsx`
  - 패턴별 훈련 세션 요청 개수를 10개로 변경

- `frontend/src/app/play/page.tsx`
- `frontend/src/components/play-client.tsx`
- `frontend/src/components/training-session-client.tsx`
- `frontend/src/components/candlestick-preview.tsx`
- `frontend/src/app/result/[answerId]/page.tsx`
  - 깨진 한글 문구 정리
  - 주봉/일봉 라벨 표시
  - 양봉/음봉 색상 문구 정리

## 검증

로컬 및 Supabase 연결 상태에서 아래 검증을 완료했다.

```bash
pnpm test:backend
pnpm lint:frontend
pnpm --dir frontend build
pnpm db:init
backend\.venv\Scripts\python.exe backend\scripts\check_db.py
backend\.venv\Scripts\python.exe backend\scripts\check_weekly_cup_questions.py
```

확인 결과:

```text
patterns=10
question_id=21000000-0000-0000-0000-000000000003
weekly_cup_handle_questions=10
```
