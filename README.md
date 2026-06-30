# 차트고시

차트고시는 과거 차트 데이터를 보고 다음 5개의 봉을 예측하는 게임형 투자 학습 서비스입니다.

## 핵심 컨셉

- 과거 차트만 보고 다음 5봉의 방향을 예측합니다.
- 사용자의 선택, 확신도, 선택 이유, 풀이 시간을 저장합니다.
- 축적된 판단 데이터를 기반으로 투자 판단 습관과 취약 패턴을 분석합니다.

## 문서

- `ChartGosi_Project_Concept.md`: 프로젝트 컨셉 문서
- `ChartGosi_PRD.md`: 제품 요구사항 문서
- `ChartGosi_DB_Design.md`: DB 설계서
- `ChartGosi_Codex_Roadmap.md`: 개발 로드맵

## 기술 스택 초안

- Frontend: Next.js, React, TailwindCSS, TradingView Lightweight Charts
- Backend: FastAPI
- DB: PostgreSQL
- Cache: Redis
- AI: OpenAI
- Batch: Python, Pandas

## 고지

차트고시는 실거래나 투자 추천 서비스가 아닙니다. 모든 콘텐츠는 차트 학습과 판단 훈련 목적입니다.
