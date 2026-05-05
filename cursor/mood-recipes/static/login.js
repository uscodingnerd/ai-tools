(function () {
  const titleEl = document.getElementById("page-title");
  const msgGlobal = document.getElementById("msg-global");
  const panelLogin = document.getElementById("panel-login");
  const panelRegister = document.getElementById("panel-register");
  const panelForgot = document.getElementById("panel-forgot");

  function showMsg(text, isError) {
    msgGlobal.textContent = text;
    msgGlobal.classList.remove("hidden");
    msgGlobal.classList.toggle("border-red-300", !!isError);
    msgGlobal.classList.toggle("bg-red-500/20", !!isError);
  }

  function clearMsg() {
    msgGlobal.textContent = "";
    msgGlobal.classList.add("hidden");
    msgGlobal.classList.remove("border-red-300", "bg-red-500/20");
  }

  function showPanel(name) {
    clearMsg();
    panelLogin.classList.toggle("hidden", name !== "login");
    panelRegister.classList.toggle("hidden", name !== "register");
    panelForgot.classList.toggle("hidden", name !== "forgot");
    document.getElementById("forgot-dev-hint").classList.add("hidden");
    if (name === "login") titleEl.textContent = "Login";
    if (name === "register") titleEl.textContent = "Register";
    if (name === "forgot") titleEl.textContent = "Forgot password";
  }

  document.getElementById("link-register").addEventListener("click", () => showPanel("register"));
  document.getElementById("link-forgot").addEventListener("click", () => showPanel("forgot"));
  document.getElementById("link-back-login-from-reg").addEventListener("click", () => showPanel("login"));
  document.getElementById("link-back-login-from-forgot").addEventListener("click", () => showPanel("login"));

  document.getElementById("form-login").addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMsg();
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      showMsg(body.detail || "Login failed", true);
      return;
    }
    window.location.href = "/";
  });

  document.getElementById("form-register").addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMsg();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    const password2 = document.getElementById("reg-password2").value;
    if (password !== password2) {
      showMsg("Passwords do not match.", true);
      return;
    }
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      showMsg(typeof body.detail === "string" ? body.detail : "Registration failed", true);
      return;
    }
    const loginRes = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, password }),
    });
    if (!loginRes.ok) {
      showMsg("Account created. Please log in.", false);
      showPanel("login");
      return;
    }
    window.location.href = "/";
  });

  document.getElementById("form-forgot").addEventListener("submit", async (e) => {
    e.preventDefault();
    clearMsg();
    const email = document.getElementById("forgot-email").value.trim();
    const res = await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email }),
    });
    const body = await res.json().catch(() => ({}));
    showMsg(body.detail || "Request submitted.", false);
    const dev = document.getElementById("forgot-dev-hint");
    if (body.reset_link || body.reset_token) {
      dev.classList.remove("hidden");
      dev.innerHTML =
        "<strong>Debug mode:</strong><br/>" +
        (body.reset_link
          ? `<a class="underline break-all" href="${body.reset_link}">${body.reset_link}</a>`
          : "") +
        (body.reset_token ? `<pre class="mt-2 whitespace-pre-wrap break-all">${body.reset_token}</pre>` : "");
    } else {
      dev.classList.add("hidden");
    }
  });
})();
