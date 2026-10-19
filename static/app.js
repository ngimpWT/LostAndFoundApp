// The logged-in user is kept in localStorage so a page refresh keeps you signed in.
const STORAGE_KEY = "currentUser";

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const messageBox = document.getElementById("message");

// ---------- Helpers ----------

// Messages appear as a "toast" pinned to the bottom of the screen, so they're
// visible no matter how far down the page you've scrolled. Click to dismiss.
let messageTimer;

function showMessage(text, isError = false) {
  messageBox.textContent = text;
  messageBox.className = `fixed bottom-4 left-1/2 -translate-x-1/2 z-20 w-[calc(100%-2rem)] max-w-xl
    rounded-lg shadow-lg px-4 py-3 text-sm cursor-pointer ${
    isError ? "bg-red-600 text-white" : "bg-green-600 text-white"
  }`;
  clearTimeout(messageTimer);
  messageTimer = setTimeout(hideMessage, isError ? 8000 : 4000);
}

function hideMessage() {
  messageBox.className = "hidden";
}

messageBox.addEventListener("click", hideMessage);

// Turn a FastAPI error response into a readable sentence.
function errorText(body) {
  if (Array.isArray(body.detail)) {
    return body.detail.map((err) => {
      const message = err.msg.replace(/^Value error, /, "");
      const field = err.loc.at(-1);
      // Errors about the request as a whole (not one field) have the location "body".
      return field === "body" ? message : `${field}: ${message}`;
    }).join("; ");
  }
  return body.detail || "Something went wrong";
}

function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY));
  } catch {
    return null; // storage held something that isn't valid JSON
  }
}

// Send a request to the API. The logged-in user's id goes in the X-User-Id
// header so the backend knows who is making the request.
// `data` can be a plain object (sent as JSON) or a FormData (for file uploads).
function authHeaders() {
  const user = getCurrentUser();
  return user ? { "X-User-Id": user.id } : {};
}

async function api(method, url, data) {
  const user = getCurrentUser();
  const headers = authHeaders();

  let body;
  if (data instanceof FormData) {
    body = data; // the browser sets the multipart Content-Type itself
  } else if (data !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(data);
  }

  const response = await fetch(url, { method, headers, body });
  if (response.status === 204) return null; // e.g. after a DELETE

  // The saved login is no longer valid (e.g. the database was reset): log out.
  if (response.status === 401 && user && url !== "/users/login") {
    localStorage.removeItem(STORAGE_KEY);
    render();
    throw new Error("Your session has expired. Please log in again.");
  }

  // A server crash returns plain text ("Internal Server Error"), not JSON.
  const isJSON = response.headers.get("Content-Type")?.includes("application/json");
  if (!isJSON) {
    throw new Error(`Server error (${response.status}). Check the terminal running the server.`);
  }

  body = await response.json();
  if (!response.ok) throw new Error(errorText(body));
  return body;
}

// ---------- Tabs ----------

function showTab(name) {
  loginForm.classList.toggle("hidden", name !== "login");
  registerForm.classList.toggle("hidden", name !== "register");
  document.querySelectorAll(".tab").forEach((tab) => {
    const active = tab.dataset.tab === name;
    tab.classList.toggle("text-indigo-700", active);
    tab.classList.toggle("border-b-2", active);
    tab.classList.toggle("border-indigo-700", active);
    tab.classList.toggle("text-slate-400", !active);
  });
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    hideMessage();
    showTab(tab.dataset.tab);
  });
});

// Escape user-provided text before putting it inside HTML.
function escapeHTML(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ---------- Session display ----------

// When the page loads, check the saved login with the server. It may belong to
// a user who no longer exists (database reset), or to a different person who
// now has that id. On success, save the fresh copy so role changes (like being
// promoted with make_admin.py) take effect.
async function verifySession() {
  const saved = getCurrentUser();
  if (!saved) return;
  try {
    const user = await api("GET", "/users/me");
    if (user.email !== saved.email) throw new Error("Saved login belongs to someone else");
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
  } catch (err) {
    if (err instanceof TypeError) {
      // fetch() itself failed: the server isn't reachable, so keep the login for now.
      showMessage("Can't reach the server. Is it running?", true);
      return;
    }
    localStorage.removeItem(STORAGE_KEY);
    showMessage("Your session has expired. Please log in again.", true);
  }
}

function render() {
  const user = getCurrentUser();
  document.getElementById("auth-section").classList.toggle("hidden", !!user);
  document.getElementById("profile-section").classList.toggle("hidden", !user);
  document.getElementById("nav-user").classList.toggle("hidden", !user);

  if (user) {
    document.getElementById("nav-user-name").textContent = `${user.name} (${user.role})`;
    document.getElementById("profile-name").textContent = user.name;
    document.getElementById("profile-email").textContent = user.email;
    document.getElementById("profile-phone").textContent = user.phone;
    document.getElementById("profile-role").textContent = user.role;
  }

  // Defined in items.js
  renderItemsSection(user);
}

// ---------- Form handlers ----------

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(registerForm));
  try {
    await api("POST", "/users", data);
    registerForm.reset();
    showTab("login");
    showMessage("Account created! You can now log in.");
  } catch (err) {
    showMessage(err.message, true);
  }
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(loginForm));
  try {
    const user = await api("POST", "/users/login", data);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    loginForm.reset();
    hideMessage();
    render();
  } catch (err) {
    showMessage(err.message, true);
  }
});

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem(STORAGE_KEY);
  showTab("login");
  showMessage("You have been logged out.");
  render();
});

showTab("login");
// The first render() runs at the bottom of items.js, once every script has loaded.
