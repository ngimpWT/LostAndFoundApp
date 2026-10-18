// The logged-in user is kept in localStorage so a page refresh keeps you signed in.
const STORAGE_KEY = "currentUser";

const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const messageBox = document.getElementById("message");

// ---------- Helpers ----------

function showMessage(text, isError = false) {
  messageBox.textContent = text;
  messageBox.className = `mb-4 rounded px-4 py-3 text-sm ${
    isError ? "bg-red-100 text-red-800" : "bg-green-100 text-green-800"
  }`;
}

function hideMessage() {
  messageBox.className = "hidden";
}

// Turn a FastAPI error response into a readable sentence.
function errorText(body) {
  if (Array.isArray(body.detail)) {
    return body.detail.map((err) => `${err.loc.at(-1)}: ${err.msg}`).join("; ");
  }
  return body.detail || "Something went wrong";
}

async function postJSON(url, data) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const body = await response.json();
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

// ---------- Session display ----------

function render() {
  const user = JSON.parse(localStorage.getItem(STORAGE_KEY));
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
}

// ---------- Form handlers ----------

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(registerForm));
  try {
    await postJSON("/users", data);
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
    const user = await postJSON("/users/login", data);
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
render();
