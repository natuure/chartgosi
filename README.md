# 차트고시

차트고시는 과거 차트 데이터를 보고 다음 5개 봉의 방향을 예측하는 차트 학습/훈련 서비스입니다. 투자 추천 서비스가 아니며, 모든 콘텐츠는 차트 학습과 자기 진단 훈련을 목적으로 합니다.

## 현재 구조

- Frontend: `frontend/` Next.js, React, TailwindCSS
- Backend: `backend/` FastAPI
- Database/Auth: Supabase PostgreSQL, Supabase Auth
- Deploy: Vercel frontend, Render backend, Supabase DB

## 로컬 실행

```bash
pnpm dev:backend
pnpm dev:frontend
```

로컬 기본 주소:

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`
- Backend API: `http://localhost:8000/api/v1`

## 환경변수

### Frontend, Vercel

Vercel 프로젝트의 Environment Variables에 설정합니다.

```text
NEXT_PUBLIC_API_BASE_URL=https://chartgosi.onrender.com/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-supabase-anon-key
```

`NEXT_PUBLIC_API_BASE_URL`에는 `/api/v1`까지 포함해야 합니다.

### Backend, Render

Render Web Service의 Environment Variables에 설정합니다.

```text
DATABASE_URL=Supabase PostgreSQL connection string
BACKEND_CORS_ORIGINS=https://your-vercel-project.vercel.app
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
ALLOW_DEV_AUTH_FALLBACK=false
```

로컬과 배포 주소를 함께 허용하려면 쉼표로 구분합니다.

```text
BACKEND_CORS_ORIGINS=http://localhost:3000,https://your-vercel-project.vercel.app
```

`ALLOW_DEV_AUTH_FALLBACK=true`는 로컬 개발 편의용입니다. Render production에서는 반드시 `false`로 둡니다.

## Render 백엔드 배포 설정

Render에서 Web Service를 만들고 다음 값을 사용합니다.

```text
Root Directory: backend
Language: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 배포 후 스모크 체크

권장 순서:

```text
Render /health → Render /api/v1/patterns → Vercel home → login → /play → /result/{answerId} → /me
```

백엔드:

```text
https://chartgosi.onrender.com/
https://chartgosi.onrender.com/health
https://chartgosi.onrender.com/api/v1/patterns
```

정상 기준:

- `/`는 서비스 이름, 상태, 주요 확인 경로를 반환합니다.
- `/health`는 `{"status":"ok","service":"chartgosi-api"}`를 반환합니다.
- `/api/v1/patterns`는 10개 패턴 JSON을 반환합니다.

프론트:

1. Vercel 홈에서 10가지 패턴 카드가 표시되는지 확인합니다.
2. `/login`에서 이메일/비밀번호 회원가입 또는 로그인이 되는지 확인합니다.
3. `/play`에서 문제를 풀고 `/result/{answerId}`로 이동하는지 확인합니다.
4. 오답 제출 후 `/wrong-notes`에 해당 문제가 표시되는지 확인합니다.
5. 패턴별 훈련을 1세트 완료한 뒤 `/training-history`에 세션이 표시되는지 확인합니다.
6. `/stats`, `/rankings`, `/me`, `/ai-report`가 로그인 사용자 기준으로 표시되는지 확인합니다.

Supabase 데이터 확인:

- `users.id`가 Supabase Auth user id와 같은 UUID로 생성되는지 확인합니다.
- `user_answers.user_id`가 로그인한 사용자 UUID로 저장되는지 확인합니다.
- 오답 제출 후 `/wrong-notes`에는 해당 사용자 오답만 표시되어야 합니다.
- 다른 계정으로 로그인했을 때 이전 계정의 오답, 통계, 훈련 기록이 보이지 않아야 합니다.

환경변수 체크리스트:

- Vercel: `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Render: `DATABASE_URL`, `BACKEND_CORS_ORIGINS`, `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `ALLOW_DEV_AUTH_FALLBACK=false`
- Supabase Auth: Site URL과 Redirect URLs가 Vercel 도메인을 포함해야 합니다.

오류 해석:

- `HTTP 401`: Render의 `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, 토큰 검증 설정을 확인합니다.
- `HTTP 404`: seed 데이터, answer/session id, 현재 로그인 사용자 소유 데이터인지 확인합니다.
- `HTTP 500`: Render 로그, `DATABASE_URL`, DB 마이그레이션/테이블 상태를 확인합니다.

## 검증 명령

```bash
pnpm test:backend
pnpm lint:frontend
pnpm --dir frontend build
```

## 문서

- `ChartGosi_Project_Concept.md`: 프로젝트 컨셉 문서
- `ChartGosi_PRD.md`: 제품 요구사항 문서
- `ChartGosi_DB_Design.md`: DB 설계서
- `ChartGosi_Codex_Roadmap.md`: 개발 로드맵
