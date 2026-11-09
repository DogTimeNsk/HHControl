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

## Telegram: finding a chat ID

Create a bot with [@BotFather](https://t.me/BotFather), place its token in `.env` as
`TELEGRAM_BOT_TOKEN`, and restart the `api` container. Open a private chat with the bot (or add
it to a group) and send `/start`. In the dashboard, select **Find Telegram chat_id**: the app
lists chat IDs from recent bot updates. The token is never returned by the API, displayed in the
dashboard, or logged.

Set the selected ID as `TELEGRAM_CHAT_ID` in `.env` and restart the `api` and `scheduler`
containers. When a resume has the **Collect only vacancies with fewer responses** filter enabled,
the bot sends one notification for each newly saved vacancy that passes this filter. Notifications
are sent for both manual and scheduled collection; previously saved vacancies never generate repeats.

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

## Firefox extension: live vacancy details

The standalone [Firefox extension](firefox-extension/README.md) adds a
«Данные HH» panel to an already opened `hh.ru/vacancy/<id>` page. It visualizes
the current `HH-Lux-InitialState` data locally in Firefox; it does not contact
HH Control, make API requests, or store credentials.

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

### Suitable-vacancy monitoring

For each connected resume, you can enable **Collect vacancies (hourly)**. You can also enable
the **Collect only vacancies with fewer responses** filter and set a per-resume limit (30 by
default). When the filter is on, vacancies without a response counter are not stored because the
application cannot verify that they meet the limit.

Vacancies are sorted by first-discovered time, with the newest first. Subsequent collections do
not update a saved vacancy or change its place in the list. The same HH vacancy can be stored
independently for several resumes; every record is unique by its `resume_id + hh_vacancy_id` pair.

Using the saved HH browser session, the scheduler opens the resume-based search without an
explicit `text` query and applies these filters: remote work, not from agencies, last 24 hours,
publication-date order, and 50 results per page. Each run opens no more than the first four
result pages. The database stores only newly found vacancy IDs, their title, link, employer,
salary, city, and first-discovered timestamp. Results are available in Suitable vacancy statistics.
