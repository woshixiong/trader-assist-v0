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

let dashboard = document.getElementById("dashboard");
if (dashboard) {
  let countdownStart = performance.now();
  function countdown() {
    const card = dashboard.querySelector(".opportunity");
    const label = card?.querySelector("[data-countdown]");
    if (!card || !label) return;
    const remainingAtRender = Number(card.dataset.expiry) - Number(card.dataset.observed);
    if (!Number.isFinite(remainingAtRender)) return;
    const remaining = Math.max(0, remainingAtRender - (performance.now() - countdownStart));
    const seconds = Math.ceil(remaining / 1000);
    label.textContent = `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} · server expiry authoritative`;
  }
  async function updateDashboard(focusCard = false) {
    try {
      const response = await fetch("/", { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) return;
      const documentFromServer = new DOMParser().parseFromString(await response.text(), "text/html");
      const next = documentFromServer.getElementById("dashboard");
      if (!next) return;
      const changed = next.dataset.packageId !== dashboard.dataset.packageId ||
        next.dataset.revision !== dashboard.dataset.revision ||
        next.dataset.state !== dashboard.dataset.state;
      if (changed || focusCard) {
        const newOpportunity = next.dataset.packageId && next.dataset.packageId !== dashboard.dataset.packageId;
        dashboard.replaceWith(next);
        dashboard = next;
        countdownStart = performance.now();
        countdown();
        if (focusCard) dashboard.querySelector(".opportunity")?.focus({ preventScroll: true });
        if (focusCard) dashboard.querySelector(".opportunity")?.scrollIntoView({ block: "start" });
        if (newOpportunity) dashboard.querySelector(".opportunity")?.classList.add("arrived");
      }
    } catch (_) { /* Server-rendered facts remain available. */ }
  }
  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.classList.contains("actions")) return;
    event.preventDefault();
    const submitter = event.submitter;
    if (!(submitter instanceof HTMLButtonElement)) return;
    const fields = new FormData(form);
    const buttons = form.querySelectorAll("button");
    buttons.forEach((button) => { button.disabled = true; });
    try {
      const response = await fetch("/api/action", {
        method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": dashboard.dataset.csrf },
        body: JSON.stringify({
          shadow_id: fields.get("shadow_id"), package_id: fields.get("package_id"),
          package_hash: fields.get("package_hash"), action_key: fields.get("action_key"),
          action: submitter.value,
        }),
      });
      if (!response.ok) {
        form.querySelectorAll("button").forEach((button) => { button.disabled = false; });
        const result = dashboard.querySelector("#action-result");
        if (result) result.textContent = "Action blocked. Refresh current evidence.";
      }
      await updateDashboard(response.ok);
    } catch (_) {
      form.querySelectorAll("button").forEach((button) => { button.disabled = false; });
      const result = dashboard.querySelector("#action-result");
      if (result) result.textContent = "Request unavailable. Refresh current evidence.";
    }
  });
  const events = new EventSource("/events");
  events.addEventListener("revision", (event) => {
    if (event.data !== dashboard.dataset.revision) void updateDashboard();
  });
  setInterval(countdown, 1000);
  setInterval(() => { void updateDashboard(); }, 5000);
  countdown();
}
