/*
app.js
------
Phase 4 update: added login/register, and every /api/tasks call now
sends an "Authorization: Bearer <token>" header. The token itself is
kept in localStorage so it survives a page refresh (this is a real,
standalone webpage running in your own browser — not a sandboxed
Claude artifact — so normal browser storage APIs work fine here).

Note on this being "basic auth" in the learning sense: it's JWT-based,
not the HTTP Basic Auth scheme technically named that, but it plays
the same beginner-friendly role — simple username/password login.
*/

const API = "/api";

function getToken() {
  return localStorage.getItem("taskpilot_token");
}

function setToken(token) {
  localStorage.setItem("taskpilot_token", token);
}

function clearToken() {
  localStorage.removeItem("taskpilot_token");
}

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}` };
}

function showApp(username) {
  document.getElementById("auth-section").style.display = "none";
  document.getElementById("app-section").style.display = "block";
  document.getElementById("whoami").textContent = `Logged in as ${username}`;
}

function showAuth(message = "") {
  document.getElementById("auth-section").style.display = "block";
  document.getElementById("app-section").style.display = "none";
  document.getElementById("auth-message").textContent = message;
}

// ---- Auth ----

document.getElementById("login-btn").addEventListener("click", async (e) => {
  e.preventDefault();
  await login();
});

document.getElementById("register-btn").addEventListener("click", async () => {
  const username = document.getElementById("username-input").value.trim();
  const password = document.getElementById("password-input").value;
  if (!username || !password) return;

  const res = await fetch(`${API}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (res.status === 201) {
    document.getElementById("auth-message").textContent = "Account created. Logging in...";
    await login();
  } else {
    const err = await res.json();
    document.getElementById("auth-message").textContent = err.detail || "Registration failed.";
  }
});

async function login() {
  const username = document.getElementById("username-input").value.trim();
  const password = document.getElementById("password-input").value;
  if (!username || !password) return;

  // /api/token expects FORM data (OAuth2PasswordRequestForm), not JSON.
  const body = new URLSearchParams();
  body.set("username", username);
  body.set("password", password);

  const res = await fetch(`${API}/token`, { method: "POST", body });

  if (res.ok) {
    const data = await res.json();
    setToken(data.access_token);
    showApp(username);
    refresh();
  } else {
    document.getElementById("auth-message").textContent = "Incorrect username or password.";
  }
}

document.getElementById("logout-btn").addEventListener("click", () => {
  clearToken();
  showAuth();
});

// ---- Tasks ----

async function fetchTasks() {
  const res = await fetch(`${API}/tasks`, { headers: authHeaders() });
  if (res.status === 401) return handleAuthError();
  renderTasks(await res.json());
}

async function fetchStats() {
  const res = await fetch(`${API}/stats`, { headers: authHeaders() });
  if (res.status === 401) return handleAuthError();
  const stats = await res.json();
  document.getElementById("stats").textContent =
    `Weekly completion rate: ${stats.weekly_completion_rate}%`;
}

function handleAuthError() {
  clearToken();
  showAuth("Session expired, please log in again.");
}

function renderTasks(tasks) {
  const list = document.getElementById("task-list");
  list.innerHTML = "";
  tasks.forEach((t) => {
    const div = document.createElement("div");
    div.className = "task" + (t.completed_today ? " done" : "");
    const streak = t.kind === "habit" ? ` · streak: ${t.streak}` : "";
    const category = t.category ? ` · ${t.category}` : "";
    div.innerHTML = `
      <div>
        <div>${t.name}</div>
        <div class="meta">${t.kind}${streak}${category}</div>
      </div>
      <div class="task-actions">
        <button onclick="completeTask(${t.id})">${t.completed_today ? "✓ Done" : "Complete"}</button>
        <button onclick="categorizeTask(${t.id})" title="Ask AI to categorize">🏷️</button>
        <button onclick="deleteTask(${t.id})">Delete</button>
      </div>
    `;
    list.appendChild(div);
  });
}

async function completeTask(id) {
  await fetch(`${API}/tasks/${id}/complete`, { method: "POST", headers: authHeaders() });
  refresh();
}

async function deleteTask(id) {
  await fetch(`${API}/tasks/${id}`, { method: "DELETE", headers: authHeaders() });
  refresh();
}

async function categorizeTask(id) {
  const res = await fetch(`${API}/tasks/${id}/categorize`, { method: "POST", headers: authHeaders() });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "Could not categorize this task.");
    return;
  }
  refresh();
}

async function refresh() {
  await fetchTasks();
  await fetchStats();
}

document.getElementById("task-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("name-input").value.trim();
  const kind = document.getElementById("kind-input").value;
  if (!name) return;
  await fetch(`${API}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ name, kind }),
  });
  document.getElementById("name-input").value = "";
  refresh();
});

// ---- Phase 5: AI features ----

document.getElementById("quick-add-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("quick-add-input");
  const text = input.value.trim();
  if (!text) return;

  const res = await fetch(`${API}/tasks/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ text }),
  });

  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "AI suggestion failed.");
    return;
  }

  // AI only SUGGESTS — we still go through the normal create endpoint,
  // so nothing gets added to your list without an explicit create call.
  const suggestion = await res.json();
  await fetch(`${API}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(suggestion),
  });

  input.value = "";
  refresh();
});

document.getElementById("summary-btn").addEventListener("click", async () => {
  const btn = document.getElementById("summary-btn");
  const textEl = document.getElementById("summary-text");
  btn.disabled = true;
  textEl.textContent = "Thinking...";

  const res = await fetch(`${API}/summary`, { headers: authHeaders() });
  if (res.ok) {
    const data = await res.json();
    textEl.textContent = data.summary;
  } else {
    const err = await res.json();
    textEl.textContent = err.detail || "Could not generate summary.";
  }
  btn.disabled = false;
});

// ---- Startup ----

if (getToken()) {
  // We don't know the username without decoding the token, so just
  // show a generic label; a real app might store username separately.
  showApp("you");
  refresh();
} else {
  showAuth();
}
