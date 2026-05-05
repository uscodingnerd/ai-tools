(function () {
  const params = new URLSearchParams(window.location.search);
  const tokenInput = document.getElementById("token");
  tokenInput.value = params.get("token") || "";

  const msg = document.getElementById("msg");
  function showMsg(text, err) {
    msg.textContent = text;
    msg.classList.remove("hidden");
    msg.classList.toggle("border-red-300", !!err);
    msg.classList.toggle("bg-red-500/20", !!err);
  }

  document.getElementById("form-reset").addEventListener("submit", async (e) => {
    e.preventDefault();
    const token = tokenInput.value.trim();
    const newPassword = document.getElementById("new-password").value;
    const newPassword2 = document.getElementById("new-password2").value;
    if (!token) {
      showMsg("Missing reset token. Open the link from your email.", true);
      return;
    }
    if (newPassword !== newPassword2) {
      showMsg("Passwords do not match.", true);
      return;
    }
    const res = await fetch("/api/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      showMsg(body.detail || "Reset failed", true);
      return;
    }
    showMsg(body.detail || "Success. Redirecting…", false);
    setTimeout(() => {
      window.location.href = "/login.html";
    }, 1500);
  });
})();
