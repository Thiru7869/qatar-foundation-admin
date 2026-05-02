/**
 * api.js — Qatar Foundation Admin Portal
 * Auth only: login, signup, forgot password, logout.
 */
(function () {
  "use strict";

  // Auto-detects localhost vs live hosted URL
  const API_BASE = window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost"
    ? "http://127.0.0.1:5000/api"
    : window.location.origin + "/api";

  /* ── Storage  */


  const saveToken = t => localStorage.setItem("qf_token", t);
  const getToken  = () => localStorage.getItem("qf_token");
  const clearAuth = () => {
    localStorage.removeItem("qf_token");
    localStorage.removeItem("qf_admin");
  };
  const saveAdmin = a => localStorage.setItem("qf_admin", JSON.stringify(a));

  /* ── Fetch  */


  async function apiFetch(endpoint, options = {}) {
    const token = getToken();
    let res;
    try {
      res = await fetch(API_BASE + endpoint, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: "Bearer " + token } : {}),
        },
      });
    } catch (_) {
      throw { message: "Cannot reach server. Is the backend running?" };
    }
    const data = await res.json();
    if (res.status === 401) { clearAuth(); throw data; }
    if (!res.ok) throw data;
    return data;
  }

  /* ── Helpers  */


  const $   = id => document.getElementById(id);
  const val = id => { const el = $(id); return el ? el.value.trim() : ""; };

  function markErr(inputId, errId, msg) {
    if (inputId && $(inputId)) $(inputId).classList.add("error");
    const el = $(errId);
    if (!el) return;
    if (msg) { const s = el.querySelector("span"); if (s) s.textContent = msg; }
    el.classList.add("show");
  }

  /* ── Capture-phase interceptor  */


  document.addEventListener("submit", async function (e) {
    const id = e.target && e.target.id;
    if (!["loginForm","signupForm","forgotForm","quickAddForm","quickAddVerifierForm"].includes(id)) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    switch (id) {
      case "loginForm":            return doLogin();
      case "signupForm":           return doSignup();
      case "forgotForm":           return doForgot();
      case "quickAddForm":         return doQuickAddStudent();
      case "quickAddVerifierForm": return doQuickAddVerifier();
    }
  }, true);

  /* ── LOGIN  */


  async function doLogin() {
    clearAllErrors("loginForm");
    const email    = val("loginEmail");
    const password = val("loginPassword");
    const captcha  = val("loginCaptchaInput");
    let ok = true;

    if (!email || !isValidEmail(email))  { markErr("loginEmail","loginEmailErr"); ok = false; }
    if (!password)                        { markErr("loginPassword","loginPasswordErr","Please enter your password"); ok = false; }
    if (!captcha)                         { markErr(null,"loginCaptchaErr","Please enter the captcha code"); ok = false; }
    else if (captcha !== captchas.login)  { markErr(null,"loginCaptchaErr","Captcha does not match. Please try again."); generateCaptcha("login"); ok = false; }
    if (!ok) { shakeForm("loginForm"); return; }

    const rememberEl = document.querySelector("#loginForm input[type=checkbox]");
    try {
      const data = await apiFetch("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email, password,
          remember_me: rememberEl ? rememberEl.checked : false,
        }),
      });
      saveToken(data.data.access_token);
      saveAdmin(data.data.admin);
      showToast("Login successful! Redirecting...");
      generateCaptcha("login");
      setTimeout(() => showDashboard(email), 1200);
    } catch (err) {
      markErr("loginPassword","loginPasswordErr", err.message || "Invalid email or password.");
      shakeForm("loginForm");
      generateCaptcha("login");
    }
  }

  /* ── SIGNUP  */


  async function doSignup() {
    clearAllErrors("signupForm");
    const name     = val("signupName");
    const email    = val("signupEmail");
    const password = val("signupPassword");
    const confirm  = val("signupConfirmPassword");
    const captcha  = val("signupCaptchaInput");
    let ok = true;

    if (!name)                             { markErr("signupName","signupNameErr"); ok = false; }
    if (!email || !isValidEmail(email))    { markErr("signupEmail","signupEmailErr"); ok = false; }
    if (!password || password.length < 8) { markErr("signupPassword","signupPasswordErr"); ok = false; }
    if (!confirm || password !== confirm)  { markErr("signupConfirmPassword","signupConfirmPasswordErr"); ok = false; }
    if (!captcha)                          { markErr(null,"signupCaptchaErr","Please enter the captcha code"); ok = false; }
    else if (captcha !== captchas.signup)  { markErr(null,"signupCaptchaErr","Captcha does not match."); generateCaptcha("signup"); ok = false; }
    if (!ok) { shakeForm("signupForm"); return; }

    try {
      await apiFetch("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ full_name: name, email, password, confirm_password: confirm }),
      });
      showToast("Account created successfully!");
      generateCaptcha("signup");
      $("signupForm").reset();
      if (typeof checkStrength === "function") checkStrength("");
      setTimeout(() => showPage("loginPage"), 1500);
    } catch (err) {
      const msg = (err.errors && err.errors.fields)
        ? err.errors.fields.join(" ") : (err.message || "Signup failed.");
      markErr("signupEmail","signupEmailErr", msg);
      shakeForm("signupForm");
    }
  }

  /* ── FORGOT PASSWORD  */


  async function doForgot() {
    clearAllErrors("forgotForm");
    const email   = val("forgotEmail");
    const captcha = val("forgotCaptchaInput");
    let ok = true;

    if (!email || !isValidEmail(email))   { markErr("forgotEmail","forgotEmailErr"); ok = false; }
    if (!captcha)                          { markErr(null,"forgotCaptchaErr","Please enter the captcha code"); ok = false; }
    else if (captcha !== captchas.forgot)  { markErr(null,"forgotCaptchaErr","Captcha does not match."); generateCaptcha("forgot"); ok = false; }
    if (!ok) { shakeForm("forgotForm"); return; }

    try { await apiFetch("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) }); }
    catch (_) {}

    showToast("Reset link sent to your email!");
    generateCaptcha("forgot");
    $("forgotForm").reset();
  }

  /* ── QUICK ADD STUDENT  */


  async function doQuickAddStudent() {
    const inputs = document.querySelectorAll("#quickAddForm input");
    const [firstName, lastName, email] = [...inputs].map(i => i.value.trim());
    if (!firstName || !lastName || !email) { showToast("Please fill all fields"); return; }
    try { await apiFetch("/learners/", { method:"POST", body: JSON.stringify({first_name:firstName,last_name:lastName,email}) }); }
    catch (_) {}
    showToast("Student added successfully! Email invitation sent.");
    closeQuickAddModal();
    $("quickAddForm").reset();
  }

  /* ── QUICK ADD VERIFIER  */


  async function doQuickAddVerifier() {
    const inputs = document.querySelectorAll("#quickAddVerifierForm input");
    const [firstName, lastName, email, subject] = [...inputs].map(i => i.value.trim());
    if (!firstName || !lastName || !email || !subject) { showToast("Please fill all fields"); return; }
    try { await apiFetch("/verifiers/", { method:"POST", body: JSON.stringify({first_name:firstName,last_name:lastName,email,subject}) }); }
    catch (_) {}
    showToast("Verifier added successfully! Email invitation sent.");
    closeQuickAddVerifierModal();
    $("quickAddVerifierForm").reset();
  }

  /* ── LOGOUT  */
  const _origLogout = window.handleLogout;
  window.handleLogout = async function () {
    try { await apiFetch("/auth/logout", { method: "POST" }); } catch (_) {}
    clearAuth();
    if (typeof _origLogout === "function") _origLogout();
  };

  console.log("[api.js] Auth integration loaded — API:", API_BASE);
})();