/**
 * Supabase Authentication Client & UI Controller
 */

(function () {
  let supabaseClient = null;
  let currentSession = null;
  let activeTab = "signin"; // 'signin' | 'signup'
  let initAuthPromise = null;

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

      if (!config.enabled) {
        console.info("Supabase Auth is not enabled in backend config.");
        return;
      }

      // Wait briefly for window.supabase if the CDN script is still evaluating
      if (!window.supabase) {
        for (let i = 0; i < 30 && !window.supabase; i++) {
          await new Promise((r) => setTimeout(r, 100));
        }
      }

      if (!window.supabase) {
        console.warn("Supabase library not loaded.");
        return;
      }

      supabaseClient = window.supabase.createClient(config.supabase_url, config.supabase_anon_key, {
        auth: {
          persistSession: true,
          autoRefreshToken: true,
          detectSessionInUrl: true,
        },
      });

      showGoogleIfEnabled(config);

      // Get initial session
      const { data } = await supabaseClient.auth.getSession();
      currentSession = data.session;
      updateUIForSession(currentSession);
      maybeOnboard(currentSession); // back from Google: the session arrives with the page

      // Listen for auth events
      supabaseClient.auth.onAuthStateChange(async (event, session) => {
        currentSession = session;
        updateUIForSession(session);
        if (event === "SIGNED_IN") maybeOnboard(session);
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
      const meta = session.user.user_metadata || {};
      const isTopUser = email.toLowerCase() === "aniket@growthz.ai" || meta.is_admin;
      const plan = isTopUser ? "enterprise" : ((meta.plan || "free").toLowerCase());

      if (userLabel) userLabel.textContent = meta.name || email.split("@")[0];
      if (userTag) {
        userTag.textContent = isTopUser ? "MAX ACCESS" : plan.toUpperCase();
        userTag.hidden = false;
        if (isTopUser) {
          userTag.style.background = "var(--accent)";
          userTag.style.color = "#fff";
        }
      }
      if (dropdownEmail) dropdownEmail.textContent = email;
      if (dropdownPlan) dropdownPlan.textContent = isTopUser ? "ENTERPRISE (MAX ACCESS)" : `${plan.toUpperCase()} Plan`;
      pill.title = `Signed in as ${email} (${isTopUser ? "Enterprise Max" : plan.toUpperCase()})`;
      pill.dataset.authenticated = "true";
    } else {
      if (userLabel) userLabel.textContent = "Sign in";
      if (userTag) userTag.hidden = true;
      if (dropdownEmail) dropdownEmail.textContent = "Not signed in";
      if (dropdownPlan) dropdownPlan.textContent = "Free Plan";
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

    if (!supabaseClient && initAuthPromise) {
      await initAuthPromise;
    }

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

        // If on landing/external page, redirect to /app
        const p = window.location.pathname;
        if (p === "/" || p === "/landing" || (p.endsWith("index.html") && !p.includes("/app"))) {
          window.location.href = "/app";
        }
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
          const p = window.location.pathname;
          if (p === "/" || p === "/landing" || (p.endsWith("index.html") && !p.includes("/app"))) {
            window.location.href = "/app";
          }
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

  // The Google button only shows once Google is switched on in Supabase, so it never leads to an error
  async function showGoogleIfEnabled(config) {
    const btn = document.getElementById("auth_google_btn");
    const or = btn && btn.nextElementSibling && btn.nextElementSibling.classList.contains("auth-or") ? btn.nextElementSibling : null;
    const set = (on) => { if (btn) btn.hidden = !on; if (or) or.hidden = !on; };
    if (!btn) return;
    set(false);
    try {
      const res = await origFetch(`${config.supabase_url}/auth/v1/settings`, { headers: { apikey: config.supabase_anon_key } });
      const s = res.ok ? await res.json() : null;
      set(!!(s && s.external && s.external.google));
    } catch (_) { /* can't tell: keep it hidden */ }
  }

  // First run: a new account is asked what it came to make, once, and that studio opens.
  // Only accounts made in the last day see it, so existing users on a new device don't.
  function maybeOnboard(session) {
    const dlg = document.getElementById("onboard_dialog");
    const user = session && session.user;
    if (!dlg || !user || dlg.open) return;
    const key = `ad_studio_onboarded:${user.id}`;
    try {
      if (localStorage.getItem(key)) return;
      const ageMs = Date.now() - new Date(user.created_at || 0).getTime();
      if (!(ageMs >= 0 && ageMs < 24 * 3600 * 1000)) {
        localStorage.setItem(key, "existing");
        return;
      }
      if (/[?&]template=/.test(window.location.search)) return; // came for a template: let them use it
      localStorage.setItem(key, "shown");
    } catch (_) {
      return; // no storage: we couldn't remember it was shown, so don't show it every time
    }
    if (!dlg.dataset.wired) {
      dlg.dataset.wired = "1";
      dlg.addEventListener("click", (e) => {
        const card = e.target.closest("[data-intent]");
        if (card) {
          try { localStorage.setItem("ad_studio_intent", card.dataset.intent); } catch (_) {}
        }
        if (e.target === dlg || e.target.closest("#onboard_skip")) dlg.close();
      });
    }
    closeAuthDialog();
    dlg.showModal();
  }

  // Continue with Google (Supabase OAuth). Needs the Google provider switched on in Supabase
  // (Authentication > Providers > Google) and this site's /app URL in its redirect allow-list.
  async function handleGoogle() {
    if (!supabaseClient && initAuthPromise) await initAuthPromise;
    if (!supabaseClient) {
      showMsg("Sign-in isn't set up on this server yet.");
      return;
    }
    const btn = document.getElementById("auth_google_btn");
    if (btn) btn.disabled = true;
    clearMsg();
    // Come back to the same place in the studio; from the landing page, go into the studio
    const onLanding = !window.location.pathname.startsWith("/app") && !window.location.pathname.startsWith("/studio");
    const back = onLanding ? "/app" : window.location.pathname + window.location.search + window.location.hash;
    try {
      const { error } = await supabaseClient.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: window.location.origin + back },
      });
      if (error) throw error;
      // The browser now leaves for Google
    } catch (err) {
      showMsg(err.message || "Couldn't open Google sign-in.");
      if (btn) btn.disabled = false;
    }
  }

  async function handleSignOut() {
    if (supabaseClient) {
      try {
        await supabaseClient.auth.signOut();
      } catch (_) {}
    }
    currentSession = null;
    updateUIForSession(null);
    const dd = document.getElementById("user_dropdown");
    if (dd) dd.hidden = true;
    if (typeof window.loadPlan === "function") {
      try {
        await window.loadPlan();
        if (typeof window.applyPlanLocks === "function") {
          window.applyPlanLocks();
        }
      } catch (_) {}
    }
    if (window.toast) window.toast("Signed out", "info");
  }

  // Setup DOM Event Listeners
  function initDOM() {
    initAuthPromise = initAuth();

    const pill = document.getElementById("user_pill");
    const dropdown = document.getElementById("user_dropdown");
    const dlg = document.getElementById("auth_dialog");
    const closeBtn = document.getElementById("auth_close");
    const tabSignin = document.getElementById("auth_tab_signin");
    const tabSignup = document.getElementById("auth_tab_signup");
    const form = document.getElementById("auth_form");
    const signOutBtn = document.getElementById("sign_out_btn");
    const profSignOutBtn = document.getElementById("prof_btn_signout");

    // Wire up all [data-auth-modal] triggers (navbar, footer, pricing cards, hero)
    document.querySelectorAll("[data-auth-modal]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        const tab = btn.dataset.authModal || "signin";
        openAuthDialog(tab);
      });
    });

    // Wire up user pill on app header
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

    // Close user dropdown on click outside or escape key
    document.addEventListener("click", (e) => {
      if (dropdown && !dropdown.hidden && !e.target.closest("#user_menu_wrap")) {
        dropdown.hidden = true;
      }
    });

    // Close user dropdown when any action item inside it is clicked
    if (dropdown) {
      dropdown.querySelectorAll(".user-dropdown-item, a").forEach((item) => {
        item.addEventListener("click", () => {
          dropdown.hidden = true;
        });
      });
    }

    // Dialog backdrop click & escape handling
    if (dlg) {
      dlg.addEventListener("click", (e) => {
        // Clicking directly on the dialog backdrop (outside dialog-body) closes it
        if (e.target === dlg) {
          closeAuthDialog();
        }
      });
      dlg.addEventListener("cancel", () => {
        closeAuthDialog();
      });
    }

    if (closeBtn) closeBtn.addEventListener("click", closeAuthDialog);
    if (tabSignin) tabSignin.addEventListener("click", () => setTab("signin"));
    if (tabSignup) tabSignup.addEventListener("click", () => setTab("signup"));
    if (form) form.addEventListener("submit", handleSubmit);
    const googleBtn = document.getElementById("auth_google_btn");
    if (googleBtn) googleBtn.addEventListener("click", handleGoogle);
    if (signOutBtn) signOutBtn.addEventListener("click", handleSignOut);
    if (profSignOutBtn) {
      profSignOutBtn.addEventListener("click", () => {
        const profileDlg = document.getElementById("profile_modal");
        if (profileDlg && profileDlg.open) profileDlg.close();
        handleSignOut();
      });
    }

    // Global escape key to close dropdowns and auth dialog
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        if (dropdown && !dropdown.hidden) {
          dropdown.hidden = true;
        }
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initDOM);
  } else {
    initDOM();
  }

  window.openAuthDialog = openAuthDialog;
  window.closeAuthDialog = closeAuthDialog;
})();
