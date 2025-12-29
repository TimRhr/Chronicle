# Chronicle

A modern social blogging platform built with Flask.

## Features

### Blogging
- **Posts** with Markdown support, images and galleries
- **Pages** to organize posts into categories
- **Tags** for flexible content organization
- **Link previews** with embed support (YouTube, Spotify, etc.)
- **Polls** can be integrated into posts
- **Version history** for posts
- **Secure HTML/JS injections** via fenced ```injection code blocks rendered inside sandboxed iframes

### Social Features
- **Reactions** with emojis (👍 ❤️ 😂 😮 😢 🎉)
- **Comments** with nested replies
- **@Mentions** to mention other users
- **Bookmarks** for posts
- **Notifications** in real-time

### Groups
- Create and manage private groups
- Group posts and file sharing
- Role-based membership (Admin/Member)

### Users
- Local registration or **Keycloak SSO**
- Profile customization (avatar, cover image, bio)
- Theme colors and layout styles (List, Grid, Masonry, Timeline)

---

## Setup

### Prerequisites

| Tool | Version (recommended) |
|------|-----------------------|
| Python | 3.11+ |
| Node.js / npm | Node 18+, npm 9+ |
| Redis | 7 (optional in dev, required in prod for rate limiting/cache) |
| PostgreSQL | 14+ |
| Docker & Docker Compose | optional, for containerized setup |

### 1. Clone Repository

```bash
git clone <repository-url>
cd chronicle-webapp
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Adjust important variables in `.env`:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Secret key (change in production!) |
| `FLASK_ENV` | `development` or `production` |
| `REGISTRATION_ENABLED` | `true`/`false` - User registration |
| `SQLALCHEMY_DATABASE_URI` | Override DB connection (Postgres in prod) |
| `REDIS_URL` | Required for rate limits/caching in production |
| `ANALYTICS_ADMIN_USERNAME` / `ANALYTICS_ADMIN_PASSWORD` | Analytics login |

### Option A – Local development (recommended for day-to-day work)

1. **Python dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend tooling**
   ```bash
   npm install
   npm run watch:css  # watches Tailwind input and builds to src/static/css/output.css
   ```

3. **Database**
   ```bash
   # PostgreSQL
   createdb chronicle_dev
   export SQLALCHEMY_DATABASE_URI=postgresql://localhost/chronicle_dev
   # or rely on the default SQLite instance for quick prototyping
   ```

4. **Run the Flask app**
   ```bash
   flask --app src.app:create_app run --debug
   # or
   python -m flask --app src.app:create_app run --debug
   ```

5. Visit **http://localhost:5000** and register the first user at `/register` (when `REGISTRATION_ENABLED=true`).

### Option B – Docker Compose

```bash
docker compose up --build
```

This automatically starts:
- **Web App** on port 5000
- **PostgreSQL** database
- **Redis** for caching and sessions

The app is available at **http://localhost:5000**.

---

## Invite-only registration (recommended for controlled access)

If you do **not** want to expose open self-registration, set:

```env
REGISTRATION_ENABLED=false
```

In this mode, users can only create a local account via an **invitation link**.

### How it works

- **Invite source:** The app reads `invites.txt` from the **project root** on startup.
  - One email address per line
  - Empty lines are ignored
  - Lines starting with `#` are treated as comments
- **Uniqueness:** Each email address receives its **own unique invite token**.
- **6-digit code:** Each invite email contains a **6-digit invitation code** that must be entered during registration.
- **Single-use:** After a successful registration, the invite is marked as used and cannot be used again.
- **Expiry:** Invites expire after **7 days**.
  - If an invite is expired (or not yet sent successfully), a new token + code will be generated and sent on the next startup.
- **Skipping existing users:** If a user with the given email already exists, the email will be skipped.

### Required configuration

Because invites are processed on startup (without an active request context), the application needs a public base URL to build absolute links for emails:

```env
# Example: https://your-domain.tld
PUBLIC_BASE_URL=http://127.0.0.1:5000
```

Additionally, you must configure SMTP settings (see `.env.example`) so the app can send invitation emails.

### Usage

1. Add emails to `invites.txt`:
   ```txt
   alice@example.com
   bob@example.com
   ```
2. Start (or restart) the server.
3. Each new email address will receive an invitation mail containing:
   - a unique registration link: `/auth/register/<token>`
   - a 6-digit invitation code
4. The invited user completes registration on the invite page.

### Invite registration endpoint

- **Invite registration:** `/auth/register/<token>`
- **Standard registration:** `/auth/register` (blocked if `REGISTRATION_ENABLED=false`)

---

## Analytics Dashboard

The Analytics dashboard provides statistics on platform usage.

### Access

1. Navigate to **http://localhost:5000/analytics**
2. Log in with the credentials from `.env`:
   - **Username:** Value of `ANALYTICS_ADMIN_USERNAME` (default: `admin`)
   - **Password:** Value of `ANALYTICS_ADMIN_PASSWORD`

### Available Metrics

- **Users:** Total, active, new registrations
- **Posts:** Total, published, by time period
- **Engagement:** Comments, reactions, bookmarks
- **Groups:** Count, members, activity
- **Top Content:** Most active users, popular tags
- **Activity Charts:** Visualization of platform activity

---

## Keycloak SSO (optional)

For Single Sign-On with Keycloak:

```env
KEYCLOAK_ENABLED=true
KEYCLOAK_SERVER_URL=https://keycloak.example.com
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=chronicle
KEYCLOAK_CLIENT_SECRET=your-client-secret
```

---

## Internationalization (i18n)

Chronicle ships with multiple languages (configured via `BABEL_SUPPORTED_LOCALES` in the app factory). Currently available:
- 🇩🇪 German (default)
- 🇬🇧 English
- 🇪🇸 Spanish
- 🇫🇷 French

### Change Language

Users can change the language via the language switcher in the navigation bar. The preference is saved in the user profile.

### Add New Translations

1. **Extract strings:**
   ```bash
   pybabel extract -F babel.cfg -k _l -o src/translations/messages.pot src/
   ```

2. **Initialize new language** (e.g. French):
   ```bash
   pybabel init -i src/translations/messages.pot -d src/translations -l fr
   ```

3. **Update existing translations:**
   ```bash
   pybabel update -i src/translations/messages.pot -d src/translations
   ```

4. **Compile translations:**
   ```bash
   pybabel compile -d src/translations
   # or
   python scripts/compile_translations.py
   ```

### Translation Files

Translations are located in `src/translations/<lang>/LC_MESSAGES/messages.po`. They must be compiled after editing.

---

## Technology Stack

- **Backend:** Flask, SQLAlchemy, Flask-Login, Flask-Babel, Flask-Limiter
- **Database:** PostgreSQL (SQLite fallback for local dev)
- **Cache & Rate Limits:** Redis (memory store fallback in dev)
- **Frontend:** Tailwind CSS (with @tailwindcss/typography), Vanilla JS, Markdown + Bleach sanitization
- **Container:** Docker

---

## Screenshots

![Feed](screenshots/feed.png)
![Group](screenshots/group.png)
![Profile](screenshots/profile.png)
