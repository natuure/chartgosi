# 차트고시 구현 업데이트 정리

작성일: 2026-07-03

## 1. 현재 상태 요약

차트고시는 현재 웹 MVP 기준으로 `Vercel frontend + Render backend + Supabase PostgreSQL/Auth` 구조까지 연결되어 있다.

핵심 루프는 다음 단계까지 동작한다.

1. 홈 진입
2. 로그인/회원가입
3. 오늘의 문제 또는 패턴별 문제 조회
4. 답안 제출
5. 차트에서 실제 다음 5봉 확인
6. 결과 화면 확인
7. 오답노트, 통계, 랭킹, AI 리포트, 훈련 기록 확인

서비스 포지셔닝은 투자 추천이 아니라 **차트 패턴 학습/훈련 서비스**다.

## 2. 배포 및 인프라

### Frontend

- 위치: `frontend/`
- 스택: Next.js App Router, React, TypeScript, TailwindCSS
- 배포: Vercel
- 주요 환경변수:
  - `NEXT_PUBLIC_API_BASE_URL`
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Backend

- 위치: `backend/`
- 스택: FastAPI, SQLAlchemy async, asyncpg, httpx
- 배포: Render
- 주요 환경변수:
  - `DATABASE_URL`
  - `BACKEND_CORS_ORIGINS`
  - `SUPABASE_URL`
  - `SUPABASE_JWT_SECRET`
  - `ALLOW_DEV_AUTH_FALLBACK=false`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`

### Database/Auth

- Supabase PostgreSQL
- Supabase Auth 이메일/비밀번호 로그인
- `users.id`는 Supabase Auth user id와 같은 UUID를 사용
- 인증된 사용자별로 답안, 오답, 통계, 랭킹, 즐겨찾기, AI 리포트가 분리됨

## 3. 구현 완료 기능

### MVP 문제 풀이 루프

- `GET /api/v1/questions/today`
- `GET /api/v1/questions/{question_id}`
- `POST /api/v1/questions/{question_id}/answers`
- `GET /api/v1/answers/{answer_id}/result`

동작:

- 문제는 DB의 `questions.chart_data` JSONB 기반으로 렌더링
- 사용자는 `up`, `sideways`, `down` 3지선다로 답안 제출
- 답안은 `user_answers`에 저장
- 정답 여부, 선택 비율, 실제 다음 5봉, 해설을 결과 화면에서 확인

### 게임 화면 차트 UX

- 과거 봉은 최대 30개 표시
- 답안 제출 후 실제 다음 5봉을 차트에 1개씩 공개
- 공개 간격은 봉 1개당 0.7초
- 다음 5봉 공개 후 `다음: 결과 화면 보기` 버튼으로 결과 화면 이동
- 양봉은 빨간색, 음봉은 파란색으로 표시

### 오답노트

- 별도 테이블 없이 `user_answers.is_correct=false` 기반으로 구현
- 사용자별 오답만 조회
- 같은 문제를 여러 번 틀린 경우 최신 오답 1개를 목록에 표시
- 오답 상세는 기존 결과 화면 재사용

### 패턴별 훈련장

- 10개 기본 패턴 제공
- 단일 문제 풀이와 5문제 연속 훈련 지원
- 연속 훈련은 `session_id`로 묶어 저장
- `/training-history`에서 최근 훈련 기록 확인
- 훈련 상세에서 문제별 결과 확인

### 랭킹/통계

- 답안 제출 시 사용자 랭킹 집계 갱신
- 일간/주간/월간/전체 랭킹 구조 지원
- 내 통계 화면에서 풀이 수, 정답률, 패턴별 성과 확인

### 즐겨찾기

- `favorite_questions` 테이블 추가
- 문제 화면에서 즐겨찾기 토글 가능
- 내 정보 화면에서 즐겨찾기 문제 확인

### 로그인/사용자 데이터 분리

- Supabase Auth 기반 로그인/회원가입
- FastAPI에서 Bearer token 검증
- Supabase JWKS 기반 토큰 검증 지원
- 사용자 소유 API는 인증 필수
- 공개 API는 토큰 없이 조회 가능

## 4. AI 리포트 고도화

AI 리포트는 OpenAI Responses API 기반으로 고도화되었다.

### 동작 방식

1. 최근 30일 답안 기록 조회
2. 패턴별 정답률, 평균 풀이 시간, 최근 답안 이력 구성
3. 답안이 3개 미만이면 OpenAI 호출 없이 데이터 부족 리포트 생성
4. 답안이 3개 이상이면 OpenAI API 호출
5. OpenAI 응답을 JSON Schema 형태로 파싱
6. `ai_reports`에 저장
7. `/ai-report` 화면에서 표시

### fallback 정책

- `OPENAI_API_KEY`가 없으면 rule-based fallback 사용
- OpenAI 호출 실패 또는 응답 파싱 실패 시 `rule-based-v1-fallback` 저장
- 답안 부족 시 `data-insufficient-v1` 저장
- 정상 OpenAI 호출 시 `model_name`에 실제 모델명 저장

### 화면 표시

- 종합 점수
- AI 코멘트
- 성향 점수
  - 추세 읽기
  - 속도 조절
  - 일관성
- 패턴별 정답률
- 맞춤 훈련 추천
- 투자 조언 아님 고지

## 5. 패턴별 정의/판정 근거

패턴 신뢰도를 높이기 위해 패턴 정의와 문제별 판정 근거를 추가했다.

### DB 변경

`patterns`:

- `definition jsonb`

`questions`:

- `pattern_evidence jsonb`

### 패턴 정의 구조

각 패턴은 다음 정보를 가진다.

- `summary`: 패턴 요약
- `structure`: 핵심 구조
- `confirmation`: 확인 포인트
- `invalidation`: 무효 조건
- `confusing_with`: 자주 헷갈리는 패턴

### 적용된 10개 패턴

1. 컵앤핸들
2. W바닥
3. 박스권 돌파
4. 신고가 돌파
5. 눌림목
6. 삼각수렴
7. 플래그
8. 역헤드앤숄더
9. 이동평균선 돌파
10. 거래량 급증

### UI 반영 위치

- 패턴별 훈련장 카드
- 단일 문제 화면
- 연속 훈련 화면
- 결과 화면

이제 사용자는 문제 화면과 결과 화면에서 “왜 이 패턴으로 분류했는지”를 확인할 수 있다.

## 6. 주요 DB 마이그레이션

- `0001_init.sql`
  - 핵심 테이블 생성
  - `users`, `questions`, `patterns`, `user_answers`, `ai_reports`, `rankings`, `subscriptions`
- `0002_favorite_questions.sql`
  - 즐겨찾기 테이블 추가
- `0003_pattern_definitions.sql`
  - 패턴 정의 JSONB 추가
  - 문제별 판정 근거 JSONB 추가

## 7. 주요 커밋 히스토리

- `94f5552 feat: connect mvp loop to supabase`
- `1ca6836 feat: add supabase auth user separation`
- `e1a9a23 feat: add pattern training sessions`
- `df5dffe feat: aggregate rankings on answer submit`
- `e72ff9b feat: add training session history`
- `a22ca66 fix: support supabase jwks auth tokens`
- `489a439 fix: improve answer submission reliability`
- `4c27148 feat: reveal answer candles in play flow`
- `5708515 feat: generate ai reports with openai`
- `1b76cf4 feat: add pattern definitions and rationale`

## 8. 검증 기준

현재 주요 변경 시 아래 검증을 사용한다.

```bash
pnpm test:backend
pnpm lint:frontend
pnpm --dir frontend build
```

배포 후 확인:

- Render `/health`
- Render `/api/v1/patterns`
- Vercel 홈
- 로그인
- `/play`
- `/result/{answerId}`
- `/wrong-notes`
- `/stats`
- `/rankings`
- `/ai-report`
- `/training-history`

## 9. 다음 추천 작업

### 1순위: 차트 위 패턴 구간 시각화

패턴 정의와 판정 근거는 텍스트로 추가되었지만, 아직 차트 위에 직접 표시되지는 않는다.

다음 작업 후보:

- 컵 구간, 핸들 구간, 돌파 지점 라벨 표시
- 지지/저항선 표시
- neckline, box range, moving average breakout 라벨 표시
- 결과 화면에서 “근거 보기” 모드 제공

### 2순위: 문제 품질 관리 구조

- 문제별 패턴 적합도 점수
- 문제 검수 상태
- 자동 생성 문제와 수동 검수 문제 구분
- 관리자용 문제 검수 화면

### 3순위: 모바일 출시 안정화

- 모바일 차트 가독성
- 버튼 크기/간격 최적화
- 첫 사용자 온보딩
- 앱 설치형 PWA 설정

### 4순위: 구독/사용 제한

- 무료 사용자 일일 문제 제한
- 프리미엄 AI 리포트
- 결제 연동

