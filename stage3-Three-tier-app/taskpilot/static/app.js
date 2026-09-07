/*
app.js
------
This is the "client-side" half of the presentation tier — it runs in
the user's browser, not on your server. It talks to the backend purely
through HTTP requests to /api/... endpoints, using fetch(). This is
the same pattern used by essentially every modern web frontend talking
to a backend API, just written by hand instead of via a framework
like React.
*/

const API = "/api";

async function fetchTasks() {
  const res = await fetch(`${API}/tasks`);
  const tasks = await res.json();
  renderTasks(tasks);
}

async function fetchStats() {
  const res = await fetch(`${API}/stats`);
  const stats = await res.json();
  document.getElementById("stats").textContent =
    `Weekly completion rate: ${stats.weekly_completion_rate}%`;
}

function renderTasks(tasks) {
  const list = document.getElementById("task-list");
  list.innerHTML = "";
  tasks.forEach((t) => {
    const div = document.createElement("div");
    div.className = "task" + (t.completed_today ? " done" : "");
    const streak = t.kind === "habit" ? ` · streak: ${t.streak}` : "";
    div.innerHTML = `
      <div>
        <div>${t.name}</div>
        <div class="meta">${t.kind}${streak}</div>
      </div>
      <div class="task-actions">
        <button onclick="completeTask(${t.id})">${t.completed_today ? "✓ Done" : "Complete"}</button>
        <button onclick="deleteTask(${t.id})">Delete</button>
      </div>
    `;
    list.appendChild(div);
  });
}

async function completeTask(id) {
  await fetch(`${API}/tasks/${id}/complete`, { method: "POST" });
  refresh();
}

async function deleteTask(id) {
  await fetch(`${API}/tasks/${id}`, { method: "DELETE" });
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, kind }),
  });
  document.getElementById("name-input").value = "";
  refresh();
});

refresh();
