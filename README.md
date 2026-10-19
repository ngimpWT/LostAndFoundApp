# Campus Lost & Found

A small web app where students report lost and found items and admins review
posts before they appear on the public campus feed.

Built with **FastAPI**, **SQLite** (SQLAlchemy), and a plain **HTML + JavaScript**
frontend styled with Tailwind CSS. No Node.js or build step.

## Features

| Requirement | What it does |
|---|---|
| FR-1 User management | Register and log in with name, email, and phone |
| FR-2 Item posting | Students post lost/found items, edit them, and mark them resolved |
| FR-3 Photo attachments | Owners add captioned photos (JPEG, PNG, GIF, WebP, up to 5 MB) |
| FR-4 Moderation | New and edited posts wait in an admin review queue; every approve/reject decision is logged with comments and a timestamp |
| FR-5 Search & filtering | Keyword search (title, description, location, captions) plus lost/found and location filters |

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                # install dependencies into .venv
uv run playwright install chromium     # one-time: browser for the end-to-end tests
```

## Run the app

```bash
uv run fastapi dev
```

Open http://127.0.0.1:8000. The database (`lost_and_found.db`) and the
`uploads/` folder are created automatically.

## Make an admin

Everyone signs up as a student. To make someone an admin, have them register
on the website, then run:

```bash
uv run python make_admin.py their-email@wtamu.edu
```

They get the admin view (review queue, Take down buttons) the next time they
load the page.

## Run the tests

```bash
uv run pytest                    # everything: API tests + browser tests
uv run pytest -m "not browser"   # API tests only (fast)
uv run pytest -m browser         # browser tests only
uv run pytest -m browser --headed --slowmo 300   # watch the browser tests run
```

The tests use their own temporary database and upload folder, so they never
change your `lost_and_found.db`.

## Reset the data

Stop the server, then:

```bash
rm lost_and_found.db
rm -rf uploads
```

If you pull a version of the app whose database tables changed, the server
refuses to start and prints this same instruction.

## Demo walkthrough (for the video)

Use two browser windows, for example one normal and one private, so the
student and admin can be logged in at the same time.

1. **Register a student** (window 1) and log in. Show the profile card.
2. **Report an item**, for example "Gray hoodie", found at the Student Center. It shows
   in *My posts* as **Awaiting review** and is *not* in the campus feed.
3. **Add a photo** with a caption to that post.
4. **Register an admin** (window 2), run `make_admin.py` for that email, and reload.
   The **Review queue** appears.
5. **Reject** the post without a comment to show the validation message, then reject it
   with a comment, for example "Please say where exactly you found it".
6. Back in window 1, reload: the post shows **Rejected** with the admin's feedback.
   **Edit** it and save. It goes back to *Awaiting review*.
7. In window 2, reload and **Approve** it. In window 1, it now appears in the **Campus feed**.
8. **Search**: type a keyword in the header search bar, try the Lost/Found and
   location filters, and use **Clear**.
9. **Mark resolved** in window 1, and show it hidden from search until *Show resolved* is ticked.

## Project layout

```
main.py            App setup, routers, and startup checks
database.py        SQLite engine and session setup
models.py          Database tables (User, Item, Photo, Review)
schemas.py         Request/response validation (Pydantic)
auth.py            Who is making the request (X-User-Id header)
make_admin.py      Command-line script to promote a user to admin
routers/           API endpoints: users, items (and search), photos, moderation
static/            Frontend: index.html plus one JS file per feature
tests/             pytest API tests and Playwright browser tests
```

API docs are available at http://127.0.0.1:8000/docs while the server is running.

## Known limitations

This is a learning project, so some shortcuts are deliberate:

- **Login is not secure.** The browser identifies the user with an `X-User-Id`
  header containing their id, so anyone using the browser's developer tools
  could pretend to be another user. A real app would use passwords and signed
  session tokens.
- **Tailwind is loaded from its CDN**, which is meant for development, not production.
- **No database migrations.** When tables change, the database must be reset (see above).
