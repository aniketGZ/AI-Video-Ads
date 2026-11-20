/**
 * Ad Studio — Landing Page Interactive Controller
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Hero Cinema Video Sound Toggle
  const heroVideo = document.getElementById("hero_video");
  const heroAudioBtn = document.getElementById("hero_audio_btn");
  if (heroVideo && heroAudioBtn) {
    heroAudioBtn.addEventListener("click", () => {
      heroVideo.muted = !heroVideo.muted;
      if (heroVideo.muted) {
        heroAudioBtn.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> Unmute Reel';
      } else {
        heroAudioBtn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Mute Audio';
        heroVideo.play().catch(() => {});
      }
    });
  }

  // 2. Generation Grid Hover Video Playback
  const videoCards = document.querySelectorAll(".gen-card video");
  videoCards.forEach((vid) => {
    const card = vid.closest(".gen-card");
    if (!card) return;

    card.addEventListener("mouseenter", () => {
      vid.play().catch(() => {});
    });

    card.addEventListener("mouseleave", () => {
      vid.pause();
    });
  });

  // 3. Category Filter Tabs
  const filterBtns = document.querySelectorAll(".filter-btn");
  const genCards = document.querySelectorAll(".gen-card");

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      const filter = btn.dataset.filter;
      genCards.forEach((card) => {
        if (filter === "all" || card.dataset.category.includes(filter)) {
          card.style.display = "";
        } else {
          card.style.display = "none";
        }
      });
    });
  });

  // 4. "One Live Thing": Interactive Simulator State & Presets
  const PRESET_DATA = {
    woodland: {
      url: "woodlandworldwide.com",
      brand: "Woodland Worldwide",
      angles: {
        "us-vs-them": {
          title: "Us vs. Them (High CTR)",
          format: "4:5",
          model: "Nano Banana Pro (gemini-3-pro-image)",
          media: "/static/demo/woodland/ad_s01.jpg",
          isVideo: false,
          prompt: `[SPLIT-SCREEN COMPARISON AD]\nLEFT: Soggy, torn white mesh sneakers sitting in a cold puddle of mud and dirty water. Desaturated cold lighting. Caption overlay: 'City Sneakers Fail'.\n\nRIGHT: Rugged waterproof oiled nubuck leather boots standing unshakeable on wet granite rock. Golden morning sun highlights, crisp leather grain texture, zero moisture penetration. Bold headline: 'Woodland Prevails'.\n\n[ANATOMY & LIGHTING]\nPhotoreal lighting, 4K resolution, authentic tactile materials.`,
        },
        "mud-splash": {
          title: "Freeze-Frame Action Splash",
          format: "9:16",
          model: "Omni Flash 1.2 (gemini-omni-1.2-flash)",
          media: "/static/demo/woodland/video_1.mp4",
          isVideo: true,
          prompt: `[EXTREME SLOW-MOTION VIDEO REEL]\nClose-up macro tracking shot at 120fps. A rugged brown leather boot impacts a mountain trail puddle, sending high-speed liquid water droplets flying through the air in sharp focus. Synchronous audio of deep muddy impact and rushing river spray.\n\n[CAMERA & LIGHTING]\nLow-angle dynamic tracking, volumetric rim lighting, genuine outdoor grit.`,
        },
        "ugc-review": {
          title: "UGC Honest Stress Test",
          format: "4:5",
          model: "Nano Banana Pro (gemini-3-pro-image)",
          media: "/static/demo/woodland/ad_s05.jpg",
          isVideo: false,
          prompt: `[UGC CREATOR SMARTPHONE SHOT]\nReal hiker in mountain trail gear holding boot at chest level against a scenic foggy pine ridge. Hand-held smartphone depth of field, authentic daylight, visible mud splatter across the rubber lug sole. Authentic candid testimonial aesthetic.`,
        },
        "cinematic-orbit": {
          title: "360° Mountain Ridge Orbit",
          format: "9:16",
          model: "Omni Flash 1.2 (gemini-omni-1.2-flash)",
          media: "/static/demo/woodland/video_2.mp4",
          isVideo: true,
          prompt: `[CINEMA DRONE REEL]\n360-degree sweeping crane movement over a misty Himalayan peak. Hiker steps confidently onto slippery lichen-covered granite rocks. Spatial ambient wind and crunch of gravel underfoot. High-production outdoor commercial grade.`,
        },
      },
    },
    hyphen: {
      url: "letshyphen.com",
      brand: "Hyphen Skincare",
      angles: {
        "us-vs-them": {
          title: "Barrier Repair vs Strip",
          format: "4:5",
          model: "Nano Banana Pro (gemini-3-pro-image)",
          media: "/static/generated/banana_ad_002a038076b64559b41108b2cec2bf10.png",
          isVideo: false,
          prompt: `[EDITORIAL BEAUTY COMPARISON]\nSplit-screen cosmetic ad: Left side irritated red dry skin patch; Right side radiant, deeply hydrated dewy glass-skin glow with peptide barrier glaze. Soft daylight studio bounce, micro skin pores visible, zero plastic beauty filter.`,
        },
        "mud-splash": {
          title: "Hydration Splash & Texture",
          format: "9:16",
          model: "Omni Flash 1.2 (gemini-omni-1.2-flash)",
          media: "/static/generated/studio_video_0014e7457bae4a10a61a106d776b335c.mp4",
          isVideo: true,
          prompt: `[LIQUID SPLASH MACRO REEL]\nHigh-speed macro capture of clear botanical serum droplet colliding with smooth water surface, blooming outwards in radiant circular ripples. Translucent glass dropper bottle reflecting soft pastel studio lighting. Crisp water splash audio.`,
        },
        "ugc-review": {
          title: "Morning Routine UGC",
          format: "4:5",
          model: "Nano Banana Pro (gemini-3-pro-image)",
          media: "/static/generated/banana_ad_006ac9e3d36b482ea68b1edb0cdc8922.png",
          isVideo: false,
          prompt: `[AUTHENTIC UGC MORNING SHOT]\nNatural creator in clean bathroom holding the peptide cream tube near cheek. Gentle morning golden window light, visible skin texture, relatable lifestyle candid aesthetic.`,
        },
        "cinematic-orbit": {
          title: "Floating Bottle Studio Orbit",
          format: "9:16",
          model: "Omni Flash 1.2 (gemini-omni-1.2-flash)",
          media: "/static/generated/studio_video_04116a64df2d49ce902c40a08c7927bb.mp4",
          isVideo: true,
          prompt: `[LUXURY COSMETIC COMMERCIAL]\nFloating amber glass vial rotating slowly against a soft beige marble pedestal. Subtle iridescent lens flare, gentle upward camera tilt, high-end editorial lighting.`,
        },
      },
    },
    greensoul: {
      url: "greensoul.online",
      brand: "Green Soul Ergonomics",
      angles: {
        "us-vs-them": {
          title: "Ergonomic Alignment vs Slouch",
          format: "4:5",
          model: "Nano Banana Pro (gemini-3-pro-image)",
          media: "/static/demo/woodland/ad_s10.jpg",
          isVideo: false,
          prompt: `[POSTURE COMPARISON AD]\nDirect comparison graphic: Left shows painful spine slouch on standard wooden dining chair; Right shows orthopedically aligned spine support on breathable mesh executive chair. Clear anatomical callouts.`,
        },
        "mud-splash": {
          title: "Kinetic Cushion Stress Test",
          format: "9:16",
          model: "Omni Flash 1.2 (gemini-omni-1.2-flash)",
          media: "/static/generated/studio_video_00527f8106b64b48a44e561522920e15.mp4",
          isVideo: true,
          prompt: `[HIGH-SPEED IMPACT REEL]\nHeavy weight dropping onto high-density moulded foam seat, immediately rebounding and absorbing kinetic shock. Studio spotlight highlights breathable honeycomb fabric weave.`,
        },
        "ugc-review": {
          title: "10-Hour Coding Setup Review",
          format: "4:5",
          model: "Nano Banana Pro (gemini-3-pro-image)",
          media: "/static/demo/woodland/ad_s15.jpg",
          isVideo: false,
          prompt: `[REAL TECH WORKSPACE]\nDeveloper desk setup at night with ultra-wide monitor, warm desk lamp, and ergonomic chair. Relaxed working posture, honest testimonial caption overlay.`,
        },
        "cinematic-orbit": {
          title: "Precision Engineering Orbit",
          format: "9:16",
          model: "Omni Flash 1.2 (gemini-omni-1.2-flash)",
          media: "/static/generated/ad_video_47b985e97f524aab8eb9b0254eacac83.mp4",
          isVideo: true,
          prompt: `[INDUSTRIAL DESIGN COMMERCIAL]\n360-degree tracking shot around cold-rolled steel wheel base and pneumatic gas-lift cylinder. Smooth cinematic motion with soft studio rim lighting.`,
        },
      },
    },
  };

  let activeBrandKey = "woodland";
  let activeAngleKey = "mud-splash";

  const urlInput = document.getElementById("sim_url");
  const brandChips = document.querySelectorAll(".chip-btn");
  const angleCards = document.querySelectorAll(".angle-card");
  const simTitle = document.getElementById("sim_pane_title");
  const simModel = document.getElementById("sim_pane_model");
  const simPrompt = document.getElementById("sim_prompt");
  const simMediaStage = document.getElementById("sim_media_stage");
  const simLaunchBtn = document.getElementById("sim_launch_btn");

  function renderSimulator() {
    const brand = PRESET_DATA[activeBrandKey] || PRESET_DATA.woodland;
    const angle = brand.angles[activeAngleKey] || brand.angles["mud-splash"];

    if (urlInput) urlInput.value = brand.url;
    if (simTitle) simTitle.textContent = `${brand.brand} · ${angle.title}`;
    if (simModel) simModel.textContent = `${angle.model} · ${angle.format}`;
    if (simPrompt) simPrompt.textContent = angle.prompt;

    if (simMediaStage) {
      if (angle.isVideo) {
        simMediaStage.innerHTML = `
          <video class="sim-video" src="${angle.media}" autoplay loop muted playsinline></video>
        `;
      } else {
        simMediaStage.innerHTML = `
          <img class="sim-video" src="${angle.media}" alt="${angle.title}">
        `;
      }
    }

    if (simLaunchBtn) {
      simLaunchBtn.href = `/app#view_${angle.isVideo ? "video" : "image"}`;
    }
  }

  brandChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      brandChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeBrandKey = chip.dataset.brand;
      renderSimulator();
    });
  });

  angleCards.forEach((card) => {
    card.addEventListener("click", () => {
      angleCards.forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      activeAngleKey = card.dataset.angle;
      renderSimulator();
    });
  });

  renderSimulator();

  // 5. Billing Period Toggle (Monthly vs Yearly)
  const billingToggle = document.getElementById("billing_toggle");
  const priceStarter = document.getElementById("price_starter");
  const pricePro = document.getElementById("price_pro");
  const priceStudio = document.getElementById("price_studio");

  if (billingToggle) {
    billingToggle.addEventListener("change", () => {
      const isAnnual = billingToggle.checked;
      if (priceStarter) priceStarter.textContent = isAnnual ? "$15" : "$19";
      if (pricePro) pricePro.textContent = isAnnual ? "$39" : "$49";
      if (priceStudio) priceStudio.textContent = isAnnual ? "$119" : "$149";
    });
  }

  // 6. Connect "Sign in" & "Create account" to the Supabase modal
  const authTriggers = document.querySelectorAll("[data-auth-modal]");
  authTriggers.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const tab = btn.dataset.authModal || "signin";
      if (typeof window.openAuthDialog === "function") {
        window.openAuthDialog(tab);
      } else {
        window.location.href = "/app";
      }
    });
  });
});
