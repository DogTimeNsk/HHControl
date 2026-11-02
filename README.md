# HH Control

Self-hosted dashboard for publishing and periodically updating your own hh.ru resumes through the official HeadHunter API.

## Setup

1. Copy `.env.example` to `.env` and fill in the OAuth values from `dev.hh.ru`. Set a long random `APP_SESSION_SECRET` and a Fernet `TOKEN_ENCRYPTION_KEY`.
2. In the HH application settings, set the callback URL to the exact public address of this installation, for example `https://example.org/hh/redirect`.
3. Run `make up`, then open `http://localhost:${FRONTEND_PORT}` (or the reverse-proxied public domain). The port is set in `.env` and defaults to `8080`.
4. Create the local administrator: `make admin_add`. The password is entered interactively and stored only as an Argon2 hash.
5. Sign in, choose **Подключить hh.ru**, authorize the application, then synchronize resumes. New resumes are disabled by default.

To connect a different HH account, use **Отключить hh.ru** in the dashboard. This only removes encrypted tokens from the local SQLite database; it does not delete or alter resumes on hh.ru.

The frontend routes `/hh/redirect` to the API OAuth callback. For production, put the frontend behind HTTPS and set `COOKIE_SECURE=true`.

## Public release copy

To maintain a separate public repository without transferring this repository's
Git history or local files, create a separate clone and run the following from
this repository:

```bash
./public_release.sh /path/to/public-release-repository
```

The script copies the current files with `rsync`, follows `.gitignore`, and
excludes itself. Review, commit, and push from the target repository using its
public-release Git identity.

## Architecture

- `api`: FastAPI API, local admin session, OAuth token storage, database migrations.
- `scheduler`: independent APScheduler process, using the same SQLite volume; its SQLite lock prevents overlapping jobs.
- `frontend`: Vue static dashboard served by Nginx.

SQLite uses WAL and a busy timeout. It is suitable for this single-host, two-process setup, not for a distributed deployment.

## Production deployment

For deployment behind a host Nginx with HTTPS and an IP
allowlist, follow [the Nginx deployment guide](docs/deployment-nginx.md).

## HH integration behavior

Applicant API methods are no longer available from HH, so the next integration
iteration uses Playwright to operate the user's own hh.ru cabinet. OAuth remains
available only for official methods that HH permits. Browser automation stores
an encrypted session state locally; it never stores the user's HH password.

The worker must stop and request user intervention for CAPTCHA, MFA, rate limits
or any other interactive restriction. It must not bypass such protections.

Before a browser-driven publication attempt, the worker reads the resume's
"Поднятие резюме" card. If HH shows a future availability time or the HH.pro
"Поднимать автоматически" offer, it records the raise as unavailable without
clicking anything. The dashboard shows the last observed availability and, when
HH provides it, the next available time.

The **Проверить ATS** action opens the employer-facing print view of a resume
through the saved browser session and checks for HH's "Конкретные достижения"
marker. It is a lightweight signal only, not a complete ATS evaluation.

### Browser session setup

After `docker compose up -d --build`, sign in to the dashboard and select
**Войти в hh.ru**. This opens the browser service through noVNC at
`/browser/vnc.html`. Complete the normal HH login yourself, including any MFA
or CAPTCHA. Return to the dashboard and select **Сохранить сессию**. Only then
are synchronization and publishing controls enabled.

The noVNC path must remain protected by the same IP ACL and dashboard access
controls as the application. The browser session is for one personal HH account
only; do not expose `/browser/` publicly.

The refresh token is used only after the access token expires, because HH refresh tokens are single-use. If authorization is revoked or refresh fails, reconnect through the dashboard.

If HH returns `403 forbidden` for `/resumes/mine` while the log shows
`auth_type=applicant` and `is_applicant=True`, this confirms that the applicant
API is unavailable. Do not attempt to bypass the restriction through hidden API
endpoints; use the browser worker once it is implemented.

No live publication is performed by tests or setup. Verify the OAuth flow with your own credentials after deployment.

### Мониторинг подходящих вакансий

Для каждого подключённого резюме можно включить **Собирать вакансии (раз в час)**.
Планировщик открывает через сохранённую браузерную сессию HH выдачу, связанную с
резюме, без явного `text`, с фильтрами: удалённая работа, не от кадровых агентств,
за сутки, сортировка по дате и 50 результатов на странице. В базе сохраняются
только новые ID вакансий, их название, ссылка, работодатель, зарплата, город и
время первого обнаружения. Результаты доступны в «Статистике подходящих вакансий».
