/**
 * Supabase Authentication Client & UI Controller
 */

(function () {
  let supabaseClient = null;
  let currentSession = null;
  let activeTab = "signin"; // 'signin' | 'signup'

  // Expose current JWT token for API requests
  window.getAuthToken = function () {
    return currentSession ? currentSession.access_token : null;
  };

  // Monkey-patch window.fetch to automatically attach Authorization header on /api/ calls
  const origFetch = window.fetch;
  window.fetch = function (resource, init) {
    const token = window.getAuthToken();
    if (token && typeof resource === "string" && (resource.startsWith("/api/") || resource.startsWith("/upgrade/"))) {
      init = init || {};
      const headers = new Headers(init.headers || {});
      if (!headers.has("Authorization")) {
        headers.set("Authorization", `Bearer ${token}`);
      }
      init.headers = headers;
    }
    return origFetch.call(this, resource, init);
  };

  async function initAuth() {
    try {
      const res = await origFetch("/api/auth/config");
      if (!res.ok) return;
      const config = await res.json();

      if (!config.enabled || !window.supabase) {
        console.info("Supabase Auth is not active or library not loaded.");
        return;
      }

      supabaseClient = window.supabase.createClient(config.supabase_url, config.supabase_anon_key, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      });

      // Get initial session
      const { data } = await supabaseClient.auth.getSession();
      currentSession = data.session;
      updateUIForSession(currentSession);

      // Listen for auth events
      supabaseClient.auth.onAuthStateChange(async (event, session) => {
        currentSession = session;
        updateUIForSession(session);
        if (typeof window.loadPlan === "function") {
          await window.loadPlan();
          if (typeof window.applyPlanLocks === "function") {
            window.applyPlanLocks();
          }
        }
      });
    } catch (err) {
      console.warn("Failed to initialize Supabase Auth:", err);
    }
  }

  function updateUIForSession(session) {
    const pill = document.getElementById("user_pill");
    const userLabel = document.getElementById("user_pill_label");
    const userTag = document.getElementById("user_pill_tag");
    const dropdownEmail = document.getElementById("dropdown_user_email");
    const dropdownPlan = document.getElementById("dropdown_user_plan");

    if (!pill) return;

    if (session && session.user) {
      const email = session.user.email || "Account";
      const plan = (session.user.user_metadata && session.user.user_metadata.plan) || "free";

      if (userLabel) userLabel.textContent = email.split("@")[0];
      if (userTag) {
        userTag.textContent = plan;
        userTag.hidden = false;
      }
      if (dropdownEmail) dropdownEmail.textContent = email;
      if (dropdownPlan) dropdownPlan.textContent = `${plan.toUpperCase()} Plan`;
      pill.title = `Signed in as ${email}`;
      pill.dataset.authenticated = "true";
    } else {
      if (userLabel) userLabel.textContent = "Sign in";
      if (userTag) userTag.hidden = true;
      if (dropdownEmail) dropdownEmail.textContent = "Not signed in";
      pill.title = "Sign in to Ad Studio";
      pill.dataset.authenticated = "false";
    }
  }

  // Dialog Controls
  function openAuthDialog(tab = "signin") {
    const dlg = document.getElementById("auth_dialog");
    if (!dlg) return;
    setTab(tab);
    clearMsg();
    if (!dlg.open) dlg.showModal();
  }

  function closeAuthDialog() {
    const dlg = document.getElementById("auth_dialog");
    if (dlg && dlg.open) dlg.close();
  }

  function setTab(tab) {
    activeTab = tab;
    const signinTab = document.getElementById("auth_tab_signin");
    const signupTab = document.getElementById("auth_tab_signup");
    const submitBtn = document.getElementById("auth_submit_btn");
    const title = document.getElementById("auth_title");
    const lede = document.getElementById("auth_lede");

    if (tab === "signin") {
      if (signinTab) signinTab.classList.add("active");
      if (signupTab) signupTab.classList.remove("active");
      if (submitBtn) submitBtn.textContent = "Sign in";
      if (title) title.textContent = "Welcome back";
      if (lede) lede.textContent = "Sign in to access your campaigns and generations.";
    } else {
      if (signinTab) signinTab.classList.remove("active");
      if (signupTab) signupTab.classList.add("active");
      if (submitBtn) submitBtn.textContent = "Create account";
      if (title) title.textContent = "Create an account";
      if (lede) lede.textContent = "Get 300 free credits to test image and video ads.";
    }
  }

  function showMsg(text, type = "error") {
    const box = document.getElementById("auth_msg");
    if (!box) return;
    box.className = `auth-msg ${type}`;
    box.textContent = text;
    box.hidden = false;
  }

  function clearMsg() {
    const box = document.getElementById("auth_msg");
    if (box) {
      box.hidden = true;
      box.textContent = "";
    }
  }

  // Handle Sign In / Sign Up
  async function handleSubmit(e) {
    e.preventDefault();
    if (!supabaseClient) {
      showMsg("Supabase is not configured yet. Please check environment keys.");
      return;
    }

    const emailInput = document.getElementById("auth_email");
    const passInput = document.getElementById("auth_password");
    const submitBtn = document.getElementById("auth_submit_btn");

    const email = (emailInput ? emailInput.value : "").trim();
    const password = passInput ? passInput.value : "";

    if (!email || !password) {
      showMsg("Please enter both email and password.");
      return;
    }

    if (password.length < 6) {
      showMsg("Password must be at least 6 characters.");
      return;
    }

    clearMsg();
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.dataset.origText = submitBtn.textContent;
      submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Please wait...';
    }

    try {
      if (activeTab === "signin") {
        const { data, error } = await supabaseClient.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        closeAuthDialog();
        if (window.toast) window.toast("Signed in successfully", "success");
      } else {
        const { data, error } = await supabaseClient.auth.signUp({
          email,
          password,
          options: {
            data: { plan: "free" },
          },
        });
        if (error) throw error;

        if (data.session) {
          closeAuthDialog();
          if (window.toast) window.toast("Account created and signed in!", "success");
        } else {
          showMsg("Account created! Please check your email to confirm your account.", "success");
          if (emailInput) emailInput.value = "";
          if (passInput) passInput.value = "";
        }
      }
    } catch (err) {
      showMsg(err.message || "Authentication failed.");
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = submitBtn.dataset.origText || "Submit";
      }
    }
  }

  async function handleSignOut() {
    if (supabaseClient) {
      await supabaseClient.auth.signOut();
      const dd = document.getElementById("user_dropdown");
      if (dd) dd.hidden = true;
      if (window.toast) window.toast("Signed out", "info");
    }
  }

  // Setup DOM Event Listeners
  document.addEventListener("DOMContentLoaded", () => {
    initAuth();

    const pill = document.getElementById("user_pill");
    const dropdown = document.getElementById("user_dropdown");
    const closeBtn = document.getElementById("auth_close");
    const tabSignin = document.getElementById("auth_tab_signin");
    const tabSignup = document.getElementById("auth_tab_signup");
    const form = document.getElementById("auth_form");
    const signOutBtn = document.getElementById("sign_out_btn");
    const profSignOutBtn = document.getElementById("prof_btn_signout");

    if (pill) {
      pill.addEventListener("click", (e) => {
        e.stopPropagation();
        if (pill.dataset.authenticated === "true") {
          if (dropdown) dropdown.hidden = !dropdown.hidden;
        } else {
          openAuthDialog("signin");
        }
      });
    }

    // Close dropdown on click outside
    document.addEventListener("click", (e) => {
      if (dropdown && !dropdown.hidden && !e.target.closest("#user_menu_wrap")) {
        dropdown.hidden = true;
      }
    });

    if (closeBtn) closeBtn.addEventListener("click", closeAuthDialog);
    if (tabSignin) tabSignin.addEventListener("click", () => setTab("signin"));
    if (tabSignup) tabSignup.addEventListener("click", () => setTab("signup"));
    if (form) form.addEventListener("submit", handleSubmit);
    if (signOutBtn) signOutBtn.addEventListener("click", handleSignOut);
    if (profSignOutBtn) {
      profSignOutBtn.addEventListener("click", () => {
        const dlg = document.getElementById("profile_modal");
        if (dlg && dlg.open) dlg.close();
        handleSignOut();
      });
    }
  });

  window.openAuthDialog = openAuthDialog;
})();
