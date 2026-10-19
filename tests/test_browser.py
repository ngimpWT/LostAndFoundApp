"""End-to-end tests that drive the real app in a real (headless) browser.

These start the server on a spare port with its own temporary database and
upload folder, so they never touch lost_and_found.db or uploads/.

Run only these:      uv run pytest -m browser
Skip them (faster):  uv run pytest -m "not browser"
Watch them run:      uv run pytest -m browser --headed --slowmo 300
"""

import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from pathlib import Path
from uuid import uuid4

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.browser

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VIEWPORT = {"width": 1100, "height": 650}  # short enough that the page needs scrolling


# ---------- Server ----------

@pytest.fixture(scope="session")
def server_env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("browser")
    return {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{folder / 'test.db'}",
        "UPLOAD_DIR": str(folder / "uploads"),
    }


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url(server_env, tmp_path_factory):
    """Start the app with uvicorn and return its address (overrides pytest-playwright's base_url)."""
    port = free_port()
    log_path = tmp_path_factory.mktemp("logs") / "server.log"
    with open(log_path, "w") as log:
        server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--port", str(port)],
            cwd=PROJECT_ROOT, env=server_env, stdout=log, stderr=subprocess.STDOUT,
        )
    url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 15
    while True:
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except OSError:
            if server.poll() is not None or time.time() > deadline:
                server.kill()
                pytest.fail(f"Server did not start:\n{log_path.read_text()}")
            time.sleep(0.2)
    yield url
    server.terminate()
    server.wait(timeout=10)


# ---------- Pages ----------

@pytest.fixture
def new_page(browser, base_url):
    """Open a fresh browser window (its own cookies/localStorage). Fails the test on any JS error."""
    errors, contexts = [], []

    def on_console(msg):
        # The browser logs every 4xx response; those are expected (e.g. a 401 for a stale session).
        if msg.type == "error" and "Failed to load resource" not in msg.text:
            errors.append(f"console.error: {msg.text}")

    def make():
        context = browser.new_context(base_url=base_url, viewport=VIEWPORT)
        contexts.append(context)
        page = context.new_page()
        page.on("pageerror", lambda exc: errors.append(f"Uncaught JS error: {exc}"))
        page.on("console", on_console)
        return page

    yield make
    for context in contexts:
        context.close()
    assert not errors, "\n".join(errors)


def unique_email() -> str:
    return f"{uuid4().hex[:10]}@buffs.wtamu.edu"


def register_and_login(page, name: str) -> dict:
    """Sign up and log in through the UI. Returns the user's details, including id."""
    email, phone = unique_email(), "806-555-0101"
    page.goto("/")
    page.click("button[data-tab=register]")
    register = page.locator("#register-form")
    register.locator("[name=name]").fill(name)
    register.locator("[name=email]").fill(email)
    register.locator("[name=phone]").fill(phone)
    register.locator("button").click()
    expect(page.locator("#message")).to_contain_text("Account created")

    login = page.locator("#login-form")
    login.locator("[name=name]").fill(name)
    login.locator("[name=email]").fill(email)
    login.locator("[name=phone]").fill(phone)
    login.locator("button").click()
    expect(page.locator("#profile-section")).to_be_visible()

    user_id = page.evaluate("JSON.parse(localStorage.getItem('currentUser')).id")
    return {"id": user_id, "name": name, "email": email, "phone": phone}


def make_admin(server_env, email: str):
    """Promote a user by running the real make_admin.py script against the test database."""
    subprocess.run(
        [sys.executable, "make_admin.py", email], cwd=PROJECT_ROOT, env=server_env, check=True,
        capture_output=True,
    )


def api_admin(page, server_env) -> dict:
    """Create an admin through the API (no UI) and return headers for API calls."""
    email = unique_email()
    response = page.request.post(
        "/users", data={"name": "Api Admin", "email": email, "phone": "806-555-0199"}
    )
    make_admin(server_env, email)
    return {"X-User-Id": str(response.json()["id"])}


def api_post_item(page, owner_id, title, item_type="lost", location="Student Center", description="Test item"):
    response = page.request.post(
        "/items",
        data={"title": title, "description": description, "item_type": item_type, "location": location},
        headers={"X-User-Id": str(owner_id)},
    )
    assert response.ok, response.text()
    return response.json()["id"]


def api_approve(page, admin_headers, item_id):
    response = page.request.post(
        f"/items/{item_id}/reviews", data={"decision": "approve"}, headers=admin_headers
    )
    assert response.ok, response.text()


def post_item_via_form(page, title, description="Gray WT hoodie, size M", location="Student Center"):
    form = page.locator("#item-form")
    form.locator("input[value=found]").check()
    form.locator("[name=title]").fill(title)
    form.locator("[name=description]").fill(description)
    form.locator("[name=location]").fill(location)
    page.click("#item-submit-btn")
    expect(page.locator("#message")).to_contain_text("submitted")


def my_post(page, title):
    return page.locator("#my-items-list article").filter(has_text=title)


@pytest.fixture
def png_file(tmp_path):
    """A real 8x8 red PNG image on disk."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    pixels = b"".join(b"\x00" + b"\xff\x00\x00" * 8 for _ in range(8))
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 8, 8, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))
    path = tmp_path / "red.png"
    path.write_bytes(png)
    return path


def wait_until_image_loaded(page, img):
    page.wait_for_function("img => img.complete && img.naturalWidth > 0", arg=img.element_handle())


# ---------- Tests ----------

def test_signup_form_has_no_admin_option(new_page):
    page = new_page()
    page.goto("/")
    page.click("button[data-tab=register]")
    expect(page.locator("#register-form [name=role]")).to_have_count(0)


def test_full_moderation_flow(new_page, server_env):
    title = f"Gray hoodie {uuid4().hex[:6]}"

    # A student posts an item. It waits for review and stays out of the feed.
    student = new_page()
    register_and_login(student, "Sam Student")
    post_item_via_form(student, title)
    expect(my_post(student, title)).to_contain_text("Awaiting review")
    expect(student.locator("#items-list")).not_to_contain_text(title)

    # An admin (promoted with make_admin.py) sees it in the review queue after reloading.
    admin = new_page()
    admin_user = register_and_login(admin, "Ada Admin")
    make_admin(server_env, admin_user["email"])
    admin.reload()
    queued = admin.locator("#review-list article").filter(has_text=title)
    expect(queued).to_be_visible()

    # Rejecting without a reason shows a readable error the admin can actually see.
    queued.get_by_role("button", name="Reject").click()
    toast = admin.locator("#message")
    expect(toast).to_contain_text("comments are required when rejecting a post")
    expect(toast).not_to_contain_text("Value error")
    expect(toast).to_be_in_viewport()

    queued.locator("[name=comments]").fill("Please say where exactly you found it")
    queued.get_by_role("button", name="Reject").click()
    expect(toast).to_contain_text("Post rejected")
    expect(admin.locator("#review-list")).not_to_contain_text(title)

    # The student sees the feedback, edits the post, and it goes back into the queue.
    student.reload()
    expect(my_post(student, title)).to_contain_text("Rejected")
    expect(my_post(student, title)).to_contain_text("Please say where exactly you found it")
    my_post(student, title).get_by_role("button", name="Edit").click()
    student.locator("#item-form [name=description]").fill("Gray WT hoodie, left by the food court")
    student.click("#item-submit-btn")
    expect(my_post(student, title)).to_contain_text("Awaiting review")

    # The admin approves it, and it shows up in the campus feed.
    admin.reload()
    admin.locator("#review-list article").filter(has_text=title).get_by_role("button", name="Approve").click()
    expect(toast).to_contain_text("approved")
    student.reload()
    expect(student.locator("#items-list")).to_contain_text(title)

    # The admin takes it down from the feed (further down the page); the result is still visible.
    admin.reload()
    admin.once("dialog", lambda dialog: dialog.accept("Reported as spam"))
    admin.locator("#items-list article").filter(has_text=title).get_by_role("button", name="Take down").click()
    expect(toast).to_contain_text("taken down")
    expect(toast).to_be_in_viewport()


def test_photos_show_while_pending_and_after_approval(new_page, server_env, png_file):
    title = f"Red umbrella {uuid4().hex[:6]}"
    student = new_page()
    register_and_login(student, "Sam Student")
    post_item_via_form(student, title)

    # Upload a photo; the owner can see it even though the post is still pending.
    card = my_post(student, title)
    card.locator("input[type=file]").set_input_files(png_file)
    card.locator("[name=caption]").fill("Front view")
    card.get_by_role("button", name="Add photo").click()
    expect(student.locator("#message")).to_contain_text("Photo added")
    pending_img = my_post(student, title).locator("img")
    wait_until_image_loaded(student, pending_img)

    # After approval, the feed uses a normal, cacheable image URL (not a one-off blob: URL).
    item_id = student.request.get("/items/mine", headers={"X-User-Id": str(
        student.evaluate("JSON.parse(localStorage.getItem('currentUser')).id"))}).json()[0]["id"]
    api_approve(student, api_admin(student, server_env), item_id)
    student.reload()
    feed_img = student.locator("#items-list article").filter(has_text=title).locator("img")
    expect(feed_img).to_have_attribute("src", re.compile(r"^/photos/\d+/image$"))
    wait_until_image_loaded(student, feed_img)


def test_search_filters_the_feed(new_page, server_env):
    page = new_page()
    student = register_and_login(page, "Sam Student")
    admin = api_admin(page, server_env)
    tag = uuid4().hex[:6]  # other tests share this database, so search for our own posts
    for title, item_type in [(f"Blue backpack {tag}", "lost"), (f"Blue bottle {tag}", "found"),
                             (f"Car keys {tag}", "found")]:
        api_approve(page, admin, api_post_item(page, student["id"], title, item_type))
    page.reload()

    search = page.locator("#search-form [name=q]")
    count = page.locator("#result-count")
    feed = page.locator("#items-list")

    search.fill(tag)
    expect(count).to_have_text("3 posts")

    search.fill(f"blue {tag}")
    expect(count).to_have_text("2 posts")
    expect(feed).not_to_contain_text(f"Car keys {tag}")

    page.locator("#search-form [name=item_type]").select_option("found")
    expect(count).to_have_text("1 post")
    expect(feed).to_contain_text(f"Blue bottle {tag}")

    page.click("#clear-search-btn")
    expect(search).to_have_value("")
    expect(feed).to_contain_text(f"Car keys {tag}")


def test_stale_saved_session_logs_out(new_page):
    page = new_page()
    page.goto("/")
    # What the browser would remember after the database was reset.
    ghost = {"id": 999999, "name": "Ghost", "email": "ghost@buffs.wtamu.edu", "phone": "8065550000",
             "role": "student"}
    page.evaluate(f"localStorage.setItem('currentUser', {json.dumps(json.dumps(ghost))})")
    page.reload()
    expect(page.locator("#auth-section")).to_be_visible()
    expect(page.locator("#profile-section")).to_be_hidden()
    expect(page.locator("#message")).to_contain_text("session has expired")


def test_edit_form_heading_is_not_hidden_under_header(new_page):
    page = new_page()
    student = register_and_login(page, "Sam Student")
    for i in range(3):
        api_post_item(page, student["id"], f"Scroll test {i} {uuid4().hex[:6]}")
    page.reload()

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.locator("#my-items-list article").last.get_by_role("button", name="Edit").click()
    expect(page.locator("#item-form-title")).to_have_text("Edit item")

    # Wait for the smooth scroll to finish, then check the heading sits below the sticky header.
    page.wait_for_function(
        """() => {
            const header = document.querySelector('header').getBoundingClientRect();
            const heading = document.querySelector('#item-form-title').getBoundingClientRect();
            return heading.top >= header.bottom;
        }""",
        timeout=3000,
    )
