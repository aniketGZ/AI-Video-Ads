// Pricing page: prices and credit costs from /api/plans (pricing.py), the monthly/yearly switch,
// the plan finder, and the visitor's current plan. The HTML already holds the same numbers, so the
// page reads correctly without this script.
(function () {

  // Entrances, the bar and on-screen video playback come from /static/js/site.js.

  const nf = new Intl.NumberFormat("en-US");
  const ORDER = ["free", "starter", "pro", "studio"];
  const PAID = ["starter", "pro", "studio"];
  let data = null;       // /api/plans
  let mine = null;       // /api/plan
  let billing = "monthly";

  const usd = (n) => `$${nf.format(n)}`;
  const perMonth = (plan) => {
    const p = data.plans[plan];
    if (!p.price_usd_month) return 0;
    return billing === "annual" ? Math.round(p.price_usd_month * (1 - data.yearly_discount)) : p.price_usd_month;
  };

  // What a plan's credits buy, in the units the page uses everywhere
  function units() {
    return {
      image: data.costs.image["nano-banana-2.1"]["2K"],
      video1080: data.costs.video_per_second["1080p"] * 8,
      video720: data.costs.video_per_second["720p"] * 8,
    };
  }
  function yieldLine(plan) {
    const p = data.plans[plan];
    const u = units();
    const maxVideo = (p.limits && p.limits.max_video_res) === "720p" ? "720p" : "1080p";
    const perVideo = maxVideo === "720p" ? u.video720 : u.video1080;
    const imgs = Math.floor(p.credits / u.image);
    const vids = Math.floor(p.credits / perVideo);
    return `About ${nf.format(imgs)} image ads at 2K, or ${nf.format(vids)} eight-second video${vids === 1 ? "" : "s"} at ${maxVideo}`;
  }

  function checkoutHref(plan) {
    return `/upgrade/checkout?plan=${plan}${billing === "annual" ? "&billing=annual" : ""}`;
  }

  // ------------------------------------------------------------ fill the page
  function renderPlans() {
    ORDER.forEach((key) => {
      const card = document.querySelector(`.p4[data-plan="${key}"]`);
      const p = data.plans[key];
      if (!card || !p) return;
      const price = card.querySelector(".js-price");
      const next = usd(perMonth(key));
      if (price.textContent !== next) {
        price.classList.add("is-swapping");
        setTimeout(() => { price.textContent = next; price.classList.remove("is-swapping"); }, 160);
      }
      card.querySelector(".js-per").textContent = !p.price_usd_month ? "forever"
        : billing === "annual" ? "a month, billed yearly" : "a month";
      card.querySelector(".js-credits").textContent = nf.format(p.credits);
      card.querySelector(".js-yield").textContent = yieldLine(key);
      const cta = card.querySelector(".js-cta");
      const isMine = mine && mine.plan === key;
      card.classList.toggle("p4-mine", !!isMine);
      if (isMine) {
        cta.textContent = "Your plan";
        cta.href = "/";
        cta.classList.add("p4-current");
        cta.setAttribute("aria-disabled", "true");
      } else if (PAID.includes(key)) {
        cta.href = checkoutHref(key);
      }
    });
    document.querySelectorAll(".js-tprice").forEach((td) => {
      const key = td.dataset.plan;
      const m = perMonth(key);
      td.textContent = !m ? "$0" : billing === "annual" ? `${usd(m)} a month, yearly` : `${usd(m)} a month`;
    });
  }

  function renderCosts() {
    const img = data.costs.image;
    const names = { "nano-banana-2.1": "Creative Engine", "nano-banana-pro": "Studio Precision" };
    document.getElementById("cost_images").innerHTML = Object.keys(img).map((k) =>
      `<tr><th scope="row">${names[k] || k}</th><td>${img[k]["1K"]}</td><td>${img[k]["2K"]}</td><td>${img[k]["4K"]}</td></tr>`).join("");
    const vid = data.costs.video_per_second;
    const label = { "720p": "720p", "1080p": "1080p", "4k": "4K" };
    document.getElementById("cost_video").innerHTML = Object.keys(vid).map((k) =>
      `<tr><th scope="row">${label[k] || k}</th><td>${vid[k]}</td><td>${nf.format(vid[k] * 8)}</td></tr>`).join("");
    const t = data.costs.text;
    document.getElementById("cost_text").innerHTML = [
      ["Brand research", t.brand_analysis], ["Campaign strategy", t.campaign_strategy],
      ["Ad copy and prompt, each", t.ad_prompt], ["Competitor research", t.competitor_research],
    ].map(([n, c]) => `<tr><th scope="row">${n}</th><td>${c}</td></tr>`).join("");
    document.querySelectorAll("[data-cost]").forEach((el) => {
      const [kind, a, b2] = el.dataset.cost.split(":");
      const v = kind === "image" ? (img[a] || {})[b2] : (vid[a] || 0) * Number(b2);
      if (v) el.textContent = nf.format(v);
    });
    document.getElementById("topup_row").innerHTML = data.top_ups.map((t2) =>
      `<p class="topup"><b>${nf.format(t2.credits)}</b> credits <span>${usd(t2.price_usd)}</span></p>`).join("");
  }

  // ------------------------------------------------------------ plan finder
  const count = document.getElementById("finder_count");
  const countOut = document.getElementById("finder_count_out");

  function finderNeed() {
    const n = Number(count.value);
    const make = Array.from(document.querySelectorAll('input[name="make"]:checked')).map((i) => i.value);
    const campaigns = make.includes("campaigns");
    let images = make.includes("images");
    let videos = make.includes("videos");
    if (!images && !videos) { images = true; videos = campaigns; } // a campaign makes both
    const u = units();
    const imgN = images && videos ? Math.ceil(n / 2) : images ? n : 0;
    const vidN = n - imgN;
    let need = imgN * u.image + vidN * u.video1080;
    if (campaigns) {
      const t = data.costs.text;
      const runs = Math.ceil(n / 20); // one campaign run for every twenty ads
      need += runs * (t.brand_analysis + t.campaign_strategy + t.competitor_research) + n * t.ad_prompt;
    }
    return { need, campaigns };
  }

  function renderFinder() {
    if (!data) return;
    countOut.textContent = count.value;
    const { need, campaigns } = finderNeed();
    const fits = PAID.filter((k) => !campaigns || (data.plans[k].features || []).includes("campaign_manager"));
    const plan = fits.find((k) => data.plans[k].credits >= need) || "studio";
    const credits = data.plans[plan].credits;
    const label = data.plans[plan].label;
    document.getElementById("finder_need").textContent = nf.format(need);
    document.getElementById("finder_plan").textContent = label;
    document.getElementById("finder_meter").style.width = `${Math.min(100, Math.round((need / credits) * 100))}%`;
    let use;
    if (need > credits) {
      const pack = data.top_ups[data.top_ups.length - 1];
      const packs = Math.ceil((need - credits) / pack.credits);
      use = `That's more than ${label}'s ${nf.format(credits)} credits: add ${packs} top-up${packs === 1 ? "" : "s"} of ${nf.format(pack.credits)}.`;
    } else {
      use = `That uses about ${Math.max(1, Math.round((need / credits) * 100))}% of ${label}'s ${nf.format(credits)} credits.`;
    }
    if (campaigns && !fits.includes("starter")) use += " Full campaigns need Pro or Studio.";
    document.getElementById("finder_use").textContent = use;
    const btn = document.getElementById("finder_btn");
    if (mine && mine.plan === plan) {
      btn.textContent = "You're on this plan";
      btn.href = "/";
    } else {
      btn.textContent = `Get ${label}`;
      btn.href = checkoutHref(plan);
    }
  }

  count.addEventListener("input", renderFinder);
  document.querySelectorAll('input[name="make"]').forEach((i) => i.addEventListener("change", renderFinder));

  // ------------------------------------------------------------ monthly / yearly
  document.querySelectorAll('input[name="billing"]').forEach((r) => r.addEventListener("change", () => {
    billing = r.value;
    if (data) { renderPlans(); renderFinder(); }
  }));

  // ------------------------------------------------------------ load
  Promise.all([
    fetch("/api/plans").then((r) => (r.ok ? r.json() : null)).catch(() => null),
    fetch("/api/plan").then((r) => (r.ok ? r.json() : null)).catch(() => null),
  ]).then(([plans, me]) => {
    if (!plans || !plans.plans) return; // keep the numbers written in the page
    data = plans;
    mine = me;
    renderPlans();
    renderCosts();
    renderFinder();
  });
})();
