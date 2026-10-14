// Tasklet fixture app (synthetic) for the observe-mode recorder tests.
"use strict";
const token = () => sessionStorage.getItem("token") || "";

async function signIn(ev) {
  ev.preventDefault();
  const body = {email: document.getElementById("email").value,
                password: document.getElementById("password").value};
  const res = await fetch("/api/session", {method: "POST", body: JSON.stringify(body),
                                            headers: {"Content-Type": "application/json"}});
  const data = await res.json();
  sessionStorage.setItem("token", data.token);
  sessionStorage.setItem("email", body.email);
  location.href = "/tasks";
}

function addTask(task) {
  const li = document.createElement("li");
  li.className = "task";
  const a = document.createElement("a");
  a.className = "task-link";
  a.href = `/tasks/${task.id}`;
  a.textContent = task.title;
  li.append(a);
  document.getElementById("task-list").append(li);
}

async function loadTasks() {
  const res = await fetch(`/api/tasks?page=1&token=${encodeURIComponent(token())}`,
                          {headers: {"Authorization": `Bearer ${token()}`}});
  document.getElementById("task-list").replaceChildren();
  (await res.json()).forEach(addTask);
}

async function createTask(ev) {
  ev.preventDefault();
  const body = {title: document.getElementById("title").value,
                due: document.getElementById("due").value || null};
  const res = await fetch("/api/tasks", {method: "POST", body: JSON.stringify(body),
    headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token()}`}});
  addTask(await res.json());
  document.getElementById("new-task").reset();
}

function live() {
  const ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onopen = () => ws.send(JSON.stringify({type: "subscribe", channel: "tasks", token: token()}));
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "task.created") document.getElementById("live").textContent = "A task was added";
  };
}

async function loadExtras() {
  // GraphQL with an inline literal and the user's e-mail as a variable; a map keyed by user ID.
  const query = 'query TaskCounts($owner: String!) { counts(owner: $owner, scope: "personal") ' +
                '{ open done } me: viewer { email } }';
  const res = await fetch("/graphql", {method: "POST",
    headers: {"Content-Type": "application/json", "Authorization": `Bearer ${token()}`},
    body: JSON.stringify({operationName: "TaskCounts", query,
                          variables: {owner: sessionStorage.getItem("email")}})});
  await res.json();
  await (await fetch("/api/members")).json();
  console.error(`sync failed: https://${location.host}/api/sync?token=${token()} for ` +
                sessionStorage.getItem("email"));
}

async function loadTask() {
  const id = location.pathname.split("/").pop();
  const res = await fetch(`/api/tasks/${id}`, {headers: {"Authorization": `Bearer ${token()}`}});
  const task = await res.json();
  document.getElementById("detail").textContent = `${task.title} — due ${task.due || "never"}`;
}

const signInForm = document.getElementById("sign-in-form");
if (signInForm) signInForm.addEventListener("submit", signIn);
if (document.getElementById("task-list")) {
  loadTasks();
  loadExtras();
  live();
  document.getElementById("refresh").addEventListener("click", loadTasks);
  document.getElementById("new-task").addEventListener("submit", createTask);
}
if (document.getElementById("detail")) loadTask();
