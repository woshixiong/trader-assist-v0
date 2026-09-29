"use strict";

const login = document.getElementById("login");
if (login) {
  document.getElementById("login-button").addEventListener("click", async () => {
    const token = document.getElementById("access-token").value;
    const response = await fetch("/api/login", {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": login.dataset.csrf },
      body: JSON.stringify({ access_token: token }),
    });
    if (response.ok) window.location.assign("/");
    else document.getElementById("login-error").textContent = "Access denied";
  });
}

const dashboard = document.getElementById("dashboard");
if (dashboard) {
  const actions = dashboard.querySelector(".actions");
  if (actions) {
    actions.querySelectorAll("button[data-action]").forEach((button) => {
      button.addEventListener("click", async () => {
        actions.querySelectorAll("button").forEach((item) => { item.disabled = true; });
        const response = await fetch("/api/action", {
          method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": dashboard.dataset.csrf },
          body: JSON.stringify({
            shadow_id: actions.dataset.shadow, package_id: actions.dataset.package,
            package_hash: actions.dataset.hash, action_key: crypto.randomUUID(),
            action: button.dataset.action,
          }),
        });
        document.getElementById("action-result").textContent = response.ok
          ? "Recorded. NOT_SUBMITTED. Refreshing current state."
          : "Action blocked. Refresh to review current evidence.";
        if (response.ok) window.location.reload();
      });
    });
  }
  const events = new EventSource("/events");
  events.addEventListener("revision", (event) => {
    if (event.data !== dashboard.dataset.revision) window.location.reload();
  });
}
