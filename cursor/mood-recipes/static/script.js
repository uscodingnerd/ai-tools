(function () {
  const STORAGE_KEY = "moodRecipesExcluded";

  /** @type {string | null} */
  let selectedMood = null;
  /** @type {{ id: number, email: string } | null} */
  let currentUser = null;
  /** @type {{ builtin: {id: string, label: string}[], custom: {slug: string, label: string, template_mood: string}[] } | null} */
  let moodsData = null;

  const moodButtons = document.getElementById("mood-buttons");
  const recipeSection = document.getElementById("recipe-section");
  const recipeLoading = document.getElementById("recipe-loading");
  const recipeContent = document.getElementById("recipe-content");
  const recipeImage = document.getElementById("recipe-image");
  const recipeTitle = document.getElementById("recipe-title");
  const recipeMeta = document.getElementById("recipe-meta");
  const recipeIngredients = document.getElementById("recipe-ingredients");
  const recipeInstructionsEl = document.getElementById("recipe-instructions");
  const recipeYoutube = document.getElementById("recipe-youtube");
  const btnAnother = document.getElementById("btn-another");
  const btnSaveFavorite = document.getElementById("btn-save-favorite");
  const errorEl = document.getElementById("error");
  const navLogin = document.getElementById("nav-login");
  const navFavorites = document.getElementById("nav-favorites");
  const navLogout = document.getElementById("nav-logout");
  const navUser = document.getElementById("nav-user");
  const addMoodSection = document.getElementById("add-mood-section");
  const formAddMood = document.getElementById("form-add-mood");
  const newMoodLabel = document.getElementById("new-mood-label");
  const newMoodTemplate = document.getElementById("new-mood-template");
  const addMoodMsg = document.getElementById("add-mood-msg");

  /** @type {Record<string, unknown> | null} */
  let lastRecipePayload = null;

  function loadExcluded() {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw);
      return typeof parsed === "object" && parsed !== null ? parsed : {};
    } catch {
      return {};
    }
  }

  function saveExcluded(map) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  }

  function getExcludedForMood(mood) {
    const map = loadExcluded();
    const list = map[mood];
    return Array.isArray(list) ? list : [];
  }

  function addExcluded(mood, id) {
    const map = loadExcluded();
    const cur = Array.isArray(map[mood]) ? map[mood] : [];
    if (!cur.includes(id)) cur.push(id);
    map[mood] = cur;
    saveExcluded(map);
  }

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.classList.remove("hidden");
  }

  function clearError() {
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }

  function setLoading(loading) {
    recipeSection.classList.remove("hidden");
    if (loading) {
      recipeLoading.classList.remove("hidden");
      recipeContent.classList.add("hidden");
    } else {
      recipeLoading.classList.add("hidden");
      recipeContent.classList.remove("hidden");
    }
  }

  function renderRecipe(data) {
    lastRecipePayload = data;
    if (data.id) recipeImage.dataset.mealId = String(data.id);
    recipeImage.src = data.image || "";
    recipeImage.alt = data.name ? `Photo of ${data.name}` : "Recipe";
    recipeTitle.textContent = data.name || "Recipe";
    const parts = [];
    if (data.category) parts.push(data.category);
    if (data.area) parts.push(data.area);
    recipeMeta.textContent = parts.join(" · ");

    recipeIngredients.innerHTML = "";
    if (Array.isArray(data.ingredients) && data.ingredients.length) {
      const ul = document.createElement("ul");
      ul.className = "list-inside list-disc space-y-1 text-sm text-slate-700";
      data.ingredients.forEach((row) => {
        const li = document.createElement("li");
        const m = row.measure ? `${row.measure} ` : "";
        li.textContent = `${m}${row.ingredient}`.trim();
        ul.appendChild(li);
      });
      const h4 = document.createElement("h4");
      h4.className = "mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500";
      h4.textContent = "Ingredients";
      recipeIngredients.appendChild(h4);
      recipeIngredients.appendChild(ul);
    }

    const instr = data.instructions || "";
    recipeInstructionsEl.textContent = instr.trim() || "No instructions listed.";

    if (data.youtube && String(data.youtube).trim()) {
      recipeYoutube.href = data.youtube;
      recipeYoutube.classList.remove("hidden");
    } else {
      recipeYoutube.classList.add("hidden");
    }

    if (currentUser && selectedMood) {
      btnSaveFavorite.classList.remove("hidden");
    } else {
      btnSaveFavorite.classList.add("hidden");
    }
  }

  async function fetchRecipe(excludeList) {
    if (!selectedMood) return;
    clearError();
    setLoading(true);

    const params = new URLSearchParams({ mood: selectedMood });
    if (excludeList.length) params.set("exclude", excludeList.join(","));

    const res = await fetch(`/api/recipe?${params.toString()}`, { credentials: "include" });
    const body = await res.json().catch(() => ({}));

    if (!res.ok) {
      let detail = body.detail ?? body.error ?? res.statusText;
      if (typeof detail === "object" && detail !== null) {
        detail = JSON.stringify(detail);
      }
      throw new Error(typeof detail === "string" && detail ? detail : "Could not load recipe.");
    }

    return body;
  }

  async function loadRecipe(excludeList) {
    try {
      const data = await fetchRecipe(excludeList);
      renderRecipe(data);
      setLoading(false);
    } catch (e) {
      setLoading(false);
      recipeContent.classList.add("hidden");
      showError(e instanceof Error ? e.message : "Something went wrong.");
    }
  }

  function unifiedMoodsList() {
    if (!moodsData) return [];
    const out = [];
    moodsData.builtin.forEach((b) => out.push({ id: b.id, label: b.label }));
    moodsData.custom.forEach((c) => out.push({ id: c.slug, label: c.label }));
    return out;
  }

  function buildMoodButtons() {
    moodButtons.innerHTML = "";
    const list = unifiedMoodsList();
    list.forEach((m) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.mood = m.id;
      btn.textContent = m.label;
      btn.className =
        "rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-orange-300 hover:bg-orange-50 focus:outline-none focus:ring-2 focus:ring-orange-400";
      btn.addEventListener("click", () => {
        selectedMood = m.id;
        document.querySelectorAll("#mood-buttons button").forEach((b) => {
          b.classList.remove("ring-2", "ring-orange-500", "bg-orange-100", "border-orange-300");
        });
        btn.classList.add("ring-2", "ring-orange-500", "bg-orange-100", "border-orange-300");
        const excluded = getExcludedForMood(m.id);
        loadRecipe(excluded);
      });
      moodButtons.appendChild(btn);
    });
  }

  function fillTemplateSelect() {
    newMoodTemplate.innerHTML = "";
    if (!moodsData) return;
    moodsData.builtin.forEach((b) => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.label;
      newMoodTemplate.appendChild(opt);
    });
  }

  async function refreshMoods() {
    const res = await fetch("/api/moods", { credentials: "include" });
    if (!res.ok) {
      showError("Could not load moods. Refresh the page.");
      return;
    }
    moodsData = await res.json();
    buildMoodButtons();
    fillTemplateSelect();
  }

  function updateNav() {
    if (currentUser) {
      navLogin.classList.add("hidden");
      navFavorites.classList.remove("hidden");
      navLogout.classList.remove("hidden");
      navUser.classList.remove("hidden");
      navUser.textContent = currentUser.email;
      addMoodSection.classList.remove("hidden");
    } else {
      navLogin.classList.remove("hidden");
      navFavorites.classList.add("hidden");
      navLogout.classList.add("hidden");
      navUser.classList.add("hidden");
      addMoodSection.classList.add("hidden");
    }
    if (lastRecipePayload) renderRecipe(lastRecipePayload);
  }

  async function initAuth() {
    const res = await fetch("/api/auth/me", { credentials: "include" });
    if (res.ok) {
      currentUser = await res.json();
    } else {
      currentUser = null;
    }
    updateNav();
  }

  navLogout.addEventListener("click", async () => {
    await fetch("/api/auth/logout", { method: "POST", credentials: "include" });
    currentUser = null;
    updateNav();
  });

  formAddMood.addEventListener("submit", async (e) => {
    e.preventDefault();
    addMoodMsg.classList.add("hidden");
    const label = newMoodLabel.value.trim();
    const template_mood = newMoodTemplate.value;
    const res = await fetch("/api/moods", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ label, template_mood }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      addMoodMsg.textContent = typeof body.detail === "string" ? body.detail : "Could not add mood.";
      addMoodMsg.classList.remove("hidden");
      return;
    }
    newMoodLabel.value = "";
    await refreshMoods();
    addMoodMsg.textContent = `Added “${body.label}”.`;
    addMoodMsg.classList.remove("hidden");
  });

  btnSaveFavorite.addEventListener("click", async () => {
    if (!currentUser || !selectedMood || !lastRecipePayload || !lastRecipePayload.id) return;
    const snapshot = {
      name: lastRecipePayload.name,
      image: lastRecipePayload.image,
      category: lastRecipePayload.category,
      area: lastRecipePayload.area,
      youtube: lastRecipePayload.youtube,
      source: lastRecipePayload.source,
    };
    const res = await fetch("/api/favorites", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        meal_id: String(lastRecipePayload.id),
        mood_slug: selectedMood,
        snapshot,
      }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      showError(typeof body.detail === "string" ? body.detail : "Could not save favorite.");
      return;
    }
    clearError();
    btnSaveFavorite.textContent = "Saved";
    setTimeout(() => {
      btnSaveFavorite.textContent = "Save to favorites";
    }, 2000);
  });

  btnAnother.addEventListener("click", () => {
    if (!selectedMood) return;
    const currentId = recipeImage.dataset.mealId;
    if (currentId) addExcluded(selectedMood, currentId);
    loadRecipe(getExcludedForMood(selectedMood));
  });

  async function boot() {
    await initAuth();
    await refreshMoods();
  }

  boot();
})();
