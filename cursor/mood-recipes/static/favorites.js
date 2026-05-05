(function () {
  const listEl = document.getElementById("favorites-list");
  const emptyEl = document.getElementById("empty");
  const errorEl = document.getElementById("error");
  const navLogin = document.getElementById("nav-login");
  const navLogout = document.getElementById("nav-logout");
  const navUser = document.getElementById("nav-user");

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove("hidden");
  }

  function moodLabelMap(moodsJson) {
    const map = {};
    if (!moodsJson) return map;
    moodsJson.builtin.forEach((b) => {
      map[b.id] = b.label;
    });
    moodsJson.custom.forEach((c) => {
      map[c.slug] = c.label;
    });
    return map;
  }

  function formatSavedAt(iso) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  }

  async function load() {
    const meRes = await fetch("/api/auth/me", { credentials: "include" });
    if (!meRes.ok) {
      navLogin.classList.remove("hidden");
      navLogout.classList.add("hidden");
      navUser.classList.add("hidden");
      showError("Please log in to see your favorites.");
      emptyEl.classList.add("hidden");
      return;
    }
    const user = await meRes.json();
    navLogin.classList.add("hidden");
    navLogout.classList.remove("hidden");
    navUser.classList.remove("hidden");
    navUser.textContent = user.email;

    const moodsRes = await fetch("/api/moods", { credentials: "include" });
    const moodsJson = moodsRes.ok ? await moodsRes.json() : { builtin: [], custom: [] };
    const labels = moodLabelMap(moodsJson);

    const favRes = await fetch("/api/favorites", { credentials: "include" });
    if (!favRes.ok) {
      showError("Could not load favorites.");
      return;
    }
    const items = await favRes.json();
    listEl.innerHTML = "";
    if (!items.length) {
      emptyEl.classList.remove("hidden");
      return;
    }
    emptyEl.classList.add("hidden");

    items.forEach((f) => {
      const snap = f.snapshot || {};
      const title = snap.name || `Meal ${f.meal_id}`;
      const img = snap.image || "";
      const moodLabel = labels[f.mood_slug] || f.mood_slug;
      const saved = formatSavedAt(f.created_at);
      const mealUrl = `https://www.themealdb.com/meal.php?i=${encodeURIComponent(f.meal_id)}`;
      const thumb = img
        ? `<img src="${escapeAttr(img)}" alt="" class="h-full w-full object-cover" loading="lazy" />`
        : `<div class="flex h-full w-full items-center justify-center bg-slate-200 text-center text-[11px] text-slate-500">No image</div>`;

      const li = document.createElement("li");
      li.className =
        "flex gap-4 rounded-2xl border border-white/60 bg-white/80 p-4 shadow-sm backdrop-blur";
      li.innerHTML = `
        <a href="${mealUrl}" target="_blank" rel="noopener noreferrer" class="shrink-0 overflow-hidden rounded-xl bg-slate-100 w-28 h-20 sm:w-36 sm:h-24">
          ${thumb}
        </a>
        <div class="min-w-0 flex-1">
          <h2 class="font-display text-lg font-semibold text-slate-900">
            <a href="${mealUrl}" target="_blank" rel="noopener noreferrer" class="hover:text-orange-700">${escapeHtml(
        title,
      )}</a>
          </h2>
          <p class="mt-1 text-sm text-slate-600">Mood: <span class="font-medium text-slate-800">${escapeHtml(
            moodLabel,
          )}</span></p>
          <p class="mt-0.5 text-xs text-slate-500">Saved ${escapeHtml(saved)}</p>
          <div class="mt-2 flex flex-wrap gap-2">
            ${
              snap.youtube
                ? `<a href="${escapeAttr(snap.youtube)}" target="_blank" rel="noopener noreferrer" class="text-sm text-orange-700 underline hover:text-orange-900">Video</a>`
                : ""
            }
            <button type="button" class="text-sm font-medium text-red-700 hover:text-red-900" data-del="${f.id}">Remove</button>
          </div>
        </div>
      `;
      listEl.appendChild(li);
    });

    listEl.querySelectorAll("[data-del]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-del");
        const res = await fetch(`/api/favorites/${id}`, { method: "DELETE", credentials: "include" });
        if (!res.ok) {
          showError("Could not remove favorite.");
          return;
        }
        load();
      });
    });
  }

  function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  document.getElementById("nav-logout").addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    window.location.href = "/login";
  });

  load();
})();
