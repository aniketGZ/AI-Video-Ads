// Application State
let state = {
  campaignData: null,
  selectedAdGroupIndex: 0,
  selectedVideoIndex: 0,
  uploadedFiles: [],
  storyboardEngine: "banana", // "banana" (Nano Banana Pro) or "qwen" (Qwen-Image-2.1)
  generatedStoryboards: {}, // Key: "adGroup_video" -> storyboard URL
  generatedVideos: {}      // Key: "adGroup_video" -> video URL
};

// Toggle tangible product upload zone
function toggleTangibleProduct() {
  const checkbox = document.getElementById("is_tangible");
  checkbox.checked = !checkbox.checked;
  
  const checkboxUi = document.getElementById("checkbox_ui");
  const uploadZone = document.getElementById("upload_zone");
  
  if (checkbox.checked) {
    uploadZone.style.display = "block";
    uploadZone.classList.add("active");
  } else {
    uploadZone.style.display = "none";
    uploadZone.classList.remove("active");
    // Clear uploaded files
    state.uploadedFiles = [];
    document.getElementById("upload_thumbnails").innerHTML = "";
    document.getElementById("product_images").value = "";
  }
}

// Handle multiple file upload selections
function handleFileSelect(e) {
  const files = e.target.files;
  const thumbnailContainer = document.getElementById("upload_thumbnails");
  thumbnailContainer.innerHTML = "";
  state.uploadedFiles = [];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    state.uploadedFiles.push(file);
    
    const reader = new FileReader();
    reader.onload = function(event) {
      const wrapper = document.createElement("div");
      wrapper.className = "thumbnail-wrapper";
      
      const img = document.createElement("img");
      img.src = event.target.result;
      
      wrapper.appendChild(img);
      thumbnailContainer.appendChild(wrapper);
    };
    reader.readAsDataURL(file);
  }
}

// Quick fill examples
function quickFill(url) {
  document.getElementById("brand_url").value = url;
}

// Wizard loader simulator
function setLoaderStep(stepId, status) {
  const stepEl = document.getElementById(stepId);
  if (!stepEl) return;
  
  stepEl.classList.remove("active", "completed");
  if (status === "active") {
    stepEl.classList.add("active");
  } else if (status === "completed") {
    stepEl.classList.add("completed");
  }
}

// Start campaign generation API call
async function startCampaignAnalysis() {
  const urlInput = document.getElementById("brand_url").value;
  if (!urlInput) return;
  
  // Show loader, hide dashboard and configurator inputs
  const loader = document.getElementById("loader_overlay");
  const dashboard = document.getElementById("dashboard_container");
  
  loader.style.display = "flex";
  dashboard.style.display = "none";
  
  // Reset loader steps
  setLoaderStep("step_scrape", "active");
  setLoaderStep("step_ground", "");
  setLoaderStep("step_adgroups", "");
  setLoaderStep("step_scripts", "");
  
  // Simulate steps progression
  setTimeout(() => setLoaderStep("step_scrape", "completed"), 3000);
  setTimeout(() => setLoaderStep("step_ground", "active"), 3200);
  setTimeout(() => setLoaderStep("step_ground", "completed"), 8000);
  setTimeout(() => setLoaderStep("step_adgroups", "active"), 8200);
  setTimeout(() => setLoaderStep("step_adgroups", "completed"), 14000);
  setTimeout(() => setLoaderStep("step_scripts", "active"), 14200);

  const formData = new FormData();
  formData.append("url", urlInput);
  formData.append("is_tangible", document.getElementById("is_tangible").checked);
  
  // Append product images if any
  state.uploadedFiles.forEach(file => {
    formData.append("images", file);
  });
  
  const apiKey = document.getElementById("api_key_input").value;
  const headers = {};
  if (apiKey) {
    headers["x-api-key"] = apiKey;
  }
  
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: headers,
      body: formData
    });
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Failed to analyze URL");
    }
    
    const data = await response.json();
    state.campaignData = data;
    
    // Complete the final step
    setLoaderStep("step_scripts", "completed");
    
    setTimeout(() => {
      // Hide loader, render and show dashboard
      loader.style.display = "none";
      renderDashboard();
    }, 1000);
    
  } catch (error) {
    console.error(error);
    alert("Generation failed: " + error.message);
    loader.style.display = "none";
  }
}

// Render generated campaign inside dashboard
function renderDashboard() {
  const data = state.campaignData;
  if (!data) return;
  
  // Fill Brand DNA Card
  document.getElementById("dna_brand_name").textContent = data.brand_name;
  document.getElementById("dna_product_name").textContent = data.product_name;
  document.getElementById("dna_category").textContent = data.product_category;
  document.getElementById("dna_audience").textContent = data.target_audience_persona;
  const talent = data.on_screen_talent || "";
  const firstSentence = talent.split(/[.!?]/)[0] + ".";
  const dnaTalentEl = document.getElementById("dna_talent");
  if (dnaTalentEl) {
    dnaTalentEl.textContent = firstSentence;
    dnaTalentEl.title = talent;
  }
  document.getElementById("dna_visual_style").textContent = data.visual_style;
  document.getElementById("dna_logo_text").textContent = data.logo_text;
  document.getElementById("dna_description").textContent = data.product_visual_description;
  
  // Mood Chips
  const moodContainer = document.getElementById("dna_mood_chips");
  moodContainer.innerHTML = "";
  if (data.mood_keywords) {
    const moods = data.mood_keywords.split("·").map(m => m.trim());
    moods.forEach(mood => {
      const chip = document.createElement("span");
      chip.className = "tag-chip";
      chip.textContent = mood;
      moodContainer.appendChild(chip);
    });
  }
  
  // Color Palette Chips
  const paletteContainer = document.getElementById("dna_palette_chips");
  paletteContainer.innerHTML = "";
  if (data.color_palette) {
    const colors = data.color_palette.split(",").map(c => c.trim());
    colors.forEach(color => {
      const chip = document.createElement("span");
      chip.className = "tag-chip";
      
      const dot = document.createElement("span");
      dot.className = "palette-color";
      // Deduce hex color or leave border style
      dot.style.backgroundColor = color.toLowerCase();
      
      chip.appendChild(dot);
      chip.appendChild(document.createTextNode(color));
      paletteContainer.appendChild(chip);
    });
  }
  
  // Render Tabs
  const tabsContainer = document.getElementById("ad_group_tabs");
  tabsContainer.innerHTML = "";
  
  data.ad_groups.forEach((ag, idx) => {
    const btn = document.createElement("button");
    btn.className = `tab-btn ${idx === 0 ? 'active' : ''}`;
    btn.textContent = ag.name;
    btn.onclick = () => selectAdGroup(idx);
    tabsContainer.appendChild(btn);
  });
  
  // Select first ad group
  selectAdGroup(0);

  // Initialize Meta Image Ad Creative Studio
  if (typeof initMetaAdStudio === "function") {
    initMetaAdStudio();
  }
  
  // Show dashboard
  document.getElementById("dashboard_container").style.display = "flex";
  // Smooth scroll to dashboard
  document.getElementById("dashboard_container").scrollIntoView({ behavior: 'smooth' });
}

// Escape untrusted text before injecting into HTML
function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Helper to format Voiceover field with dialogue/voiceover badges
function formatVoiceover(text) {
  if (!text) return "";

  // Replace brackets like [Dialogue: "spoken text"] or [Voiceover: "narrated text"]
  const segmentRegex = /\[(Dialogue|Voiceover):\s*["']?([^\]"']+)["']?\]/gi;
  if (segmentRegex.test(text)) {
    segmentRegex.lastIndex = 0; // reset
    return text.replace(segmentRegex, (match, type, content) => {
      const isDialogue = type.toLowerCase() === "dialogue";
      const cls = isDialogue ? "dialogue" : "voiceover";
      const label = isDialogue ? "🗣️ Dialogue · Lipsync" : "🎙️ Voiceover · Narration";
      return `<div class="audio-segment ${cls}"><span class="audio-tag">${label}</span>"${escapeHtml(content.trim())}"</div>`;
    });
  }

  return escapeHtml(text);
}

// Select active ad group tab
function selectAdGroup(index) {
  state.selectedAdGroupIndex = index;
  
  // Set active tab styling
  const tabs = document.querySelectorAll("#ad_group_tabs .tab-btn");
  tabs.forEach((tab, idx) => {
    if (idx === index) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });
  
  const ag = state.campaignData.ad_groups[index];
  document.getElementById("current_ad_group_title").textContent = ag.name;
  document.getElementById("current_ad_group_angle").textContent = ag.angle;
  
  // Render video script cards
  const grid = document.getElementById("scripts_grid");
  grid.innerHTML = "";
  
  ag.videos.forEach((video, vIdx) => {
    const card = document.createElement("div");
    card.className = "script-card";
    
    card.innerHTML = `
      <div style="flex-grow: 1;">
        <div class="script-header">
          <span class="script-type"><i class="fa-solid fa-film"></i> Video ${vIdx + 1} · ${escapeHtml(video.video_style_type)}</span>
        </div>
        <div class="script-detail-grid">
          <div class="script-field">
            <div class="script-field-title">Script Hook</div>
            <div class="script-field-value">"${escapeHtml(video.hook_line)}"</div>
          </div>
          <div class="script-field">
            <div class="script-field-title">Voiceover / Audio</div>
            <div class="script-field-value">${formatVoiceover(video.voiceover)}</div>
          </div>
          <div class="script-field">
            <div class="script-field-title">Visual Directions</div>
            <div class="script-field-value">${escapeHtml(video.visual_directions)}</div>
          </div>
          <div class="script-field">
            <div class="script-field-title">Call To Action</div>
            <div class="script-field-value">"${escapeHtml(video.cta_line)}"</div>
          </div>
        </div>
      </div>
      <div class="script-card-footer">
        <button class="btn btn-primary btn-sm script-open-btn" onclick="openStudio(${vIdx})">
          <i class="fa-solid fa-clapperboard"></i> Creator Studio · 10s Video &amp; Storyboard
        </button>
        <div class="script-image-ad-strip">
          <span class="script-img-ad-label"><i class="fa-brands fa-meta"></i> Meta Image Ad:</span>
          <div class="script-img-ad-chips">
            <button class="chip-btn-engine" onclick="createMetaAdForScript(${vIdx}, 'qwen')" title="Create Meta Image Ad with Qwen-Image-2.1 (Self-Hosted GPU)">
              <i class="fa-solid fa-server"></i> Qwen 2.1
            </button>
            <button class="chip-btn-engine" onclick="createMetaAdForScript(${vIdx}, 'banana')" title="Create Meta Image Ad with Nano Banana Pro (Gemini)">
              <i class="fa-solid fa-bolt"></i> Nano Banana
            </button>
          </div>
        </div>
      </div>
    `;
    
    grid.appendChild(card);
  });
}

// Switch storyboard engine in Creator Studio (Nano Banana Pro vs Qwen-Image-2.1)
function setStoryboardEngine(engine) {
  state.storyboardEngine = engine;
  const btnBanana = document.getElementById("sb_engine_banana");
  const btnQwen = document.getElementById("sb_engine_qwen");
  if (btnBanana) btnBanana.classList.toggle("active", engine === "banana");
  if (btnQwen) btnQwen.classList.toggle("active", engine === "qwen");

  const generateStoryboardBtn = document.getElementById("generate_storyboard_btn");
  if (generateStoryboardBtn) {
    const key = `${state.selectedAdGroupIndex}_${state.selectedVideoIndex}`;
    const engineLabel = engine === "qwen" ? "Qwen-Image-2.1" : "Nano Banana Pro";
    if (state.generatedStoryboards[key]) {
      generateStoryboardBtn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Regenerate Storyboard (${engineLabel})`;
    } else {
      generateStoryboardBtn.innerHTML = `<i class="fa-solid fa-image"></i> Generate Storyboard (${engineLabel})`;
    }
  }
}

// Open Studio Overlay modal for a specific video
function openStudio(videoIndex) {
  state.selectedVideoIndex = videoIndex;
  
  const ag = state.campaignData.ad_groups[state.selectedAdGroupIndex];
  const video = ag.videos[videoIndex];
  
  // Set details
  document.getElementById("studio_video_title").textContent = `${ag.name} — Video #${videoIndex + 1}`;
  document.getElementById("studio_video_style").textContent = `Format: ${video.video_style_type} Vertical Ad`;
  
  const key = `${state.selectedAdGroupIndex}_${videoIndex}`;
  
  // Sync storyboard engine toggle & label
  setStoryboardEngine(state.storyboardEngine || "banana");

  // Storyboard pane setup
  const storyboardBox = document.getElementById("storyboard_preview_box");
  const storyboardPlaceholder = document.getElementById("storyboard_placeholder");
  const storyboardImg = document.getElementById("storyboard_img");
  const generateStoryboardBtn = document.getElementById("generate_storyboard_btn");
  
  // Video panes setup
  const videoPlaceholder_9_16 = document.getElementById("video_placeholder_9_16");
  const videoEl_9_16 = document.getElementById("ad_video_9_16");
  const downloadBtn_9_16 = document.getElementById("download_video_btn_9_16");
  
  const videoPlaceholder_16_9 = document.getElementById("video_placeholder_16_9");
  const videoEl_16_9 = document.getElementById("ad_video_16_9");
  const downloadBtn_16_9 = document.getElementById("download_video_btn_16_9");
  
  const generateVideoBtn = document.getElementById("generate_video_btn");
  
  // Reset statuses
  document.getElementById("storyboard_status").style.display = "none";
  document.getElementById("video_status").style.display = "none";
  
  const setVideoPlaceholderText = (txt) => {
    videoPlaceholder_9_16.querySelector("p").textContent = txt;
    videoPlaceholder_16_9.querySelector("p").textContent = txt;
  };
  
  const engineLabel = (state.storyboardEngine === "qwen") ? "Qwen-Image-2.1" : "Nano Banana Pro";

  if (state.generatedStoryboards[key]) {
    // Already generated storyboard
    storyboardPlaceholder.style.display = "none";
    storyboardImg.src = state.generatedStoryboards[key];
    storyboardImg.style.display = "block";
    
    generateStoryboardBtn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Regenerate Storyboard (${engineLabel})`;
    generateVideoBtn.disabled = false;
    generateVideoBtn.style.opacity = "1";
    setVideoPlaceholderText("Ready to Animate Videos");
  } else {
    storyboardPlaceholder.style.display = "flex";
    storyboardImg.style.display = "none";
    storyboardImg.src = "";
    
    generateStoryboardBtn.innerHTML = `<i class="fa-solid fa-image"></i> Generate Storyboard (${engineLabel})`;
    generateVideoBtn.disabled = true;
    generateVideoBtn.style.opacity = "0.5";
    setVideoPlaceholderText("Generate Storyboard First");
  }
  
  const key_9_16 = `${key}_9_16`;
  const key_16_9 = `${key}_16_9`;
  
  // 9:16 Video Setup
  if (state.generatedVideos[key_9_16]) {
    videoPlaceholder_9_16.style.display = "none";
    videoEl_9_16.src = state.generatedVideos[key_9_16];
    videoEl_9_16.style.display = "block";
    downloadBtn_9_16.href = state.generatedVideos[key_9_16];
    downloadBtn_9_16.style.display = "flex";
  } else {
    videoPlaceholder_9_16.style.display = "flex";
    videoEl_9_16.style.display = "none";
    videoEl_9_16.src = "";
    downloadBtn_9_16.style.display = "none";
  }
  
  // 16:9 Video Setup
  if (state.generatedVideos[key_16_9]) {
    videoPlaceholder_16_9.style.display = "none";
    videoEl_16_9.src = state.generatedVideos[key_16_9];
    videoEl_16_9.style.display = "block";
    downloadBtn_16_9.href = state.generatedVideos[key_16_9];
    downloadBtn_16_9.style.display = "flex";
  } else {
    videoPlaceholder_16_9.style.display = "flex";
    videoEl_16_9.style.display = "none";
    videoEl_16_9.src = "";
    downloadBtn_16_9.style.display = "none";
  }
  
  // Show overlay modal
  document.getElementById("studio_overlay").style.display = "flex";
}

// Close studio overlay
function closeStudio() {
  document.getElementById("studio_overlay").style.display = "none";
  
  // Pause any running preview video
  const videoEl_9_16 = document.getElementById("ad_video_9_16");
  const videoEl_16_9 = document.getElementById("ad_video_16_9");
  if (videoEl_9_16) videoEl_9_16.pause();
  if (videoEl_16_9) videoEl_16_9.pause();
}

// Generate Storyboard image using Backend
async function generateStoryboard() {
  const ag = state.campaignData.ad_groups[state.selectedAdGroupIndex];
  const video = ag.videos[state.selectedVideoIndex];
  const engine = state.storyboardEngine || "banana";
  const isQwen = (engine === "qwen");
  const engineLabel = isQwen ? "Qwen-Image-2.1 (Self-Hosted GPU)" : "Nano Banana Pro";
  
  const statusEl = document.getElementById("storyboard_status");
  statusEl.className = "generator-status working";
  statusEl.style.display = "flex";
  statusEl.querySelector("span").textContent = isQwen
    ? "Synthesizing 9:16 layout using Qwen-Image-2.1 on GPU (approx 60-90s)..."
    : "Drafting 9:16 layout using Nano Banana Pro...";
  
  const generateBtn = document.getElementById("generate_storyboard_btn");
  generateBtn.disabled = true;
  
  const reqBody = {
    brand_name: state.campaignData.brand_name,
    product_name: state.campaignData.product_name,
    product_category: state.campaignData.product_category,
    product_visual_description: state.campaignData.product_visual_description,
    product_hero_angle: state.campaignData.product_hero_angle,
    target_audience_persona: state.campaignData.target_audience_persona,
    on_screen_talent: state.campaignData.on_screen_talent,
    setting: state.campaignData.setting,
    mood_keywords: state.campaignData.mood_keywords,
    color_palette: state.campaignData.color_palette,
    visual_style: state.campaignData.visual_style,
    logo_text: state.campaignData.logo_text,
    key_benefits: state.campaignData.key_benefits,
    video_style_type: video.video_style_type,
    hook_line: video.hook_line,
    cta_line: video.cta_line,
    shot_1: video.shot_1,
    shot_2: video.shot_2,
    shot_3: video.shot_3,
    shot_4: video.shot_4,
    product_image_paths: state.campaignData.product_image_paths || [],
    use_self_hosted: isQwen
  };
  
  const apiKey = document.getElementById("api_key_input").value;
  const imageKey = localStorage.getItem("self_hosted_image_key") || "";
  const headers = { "Content-Type": "application/json" };
  if (apiKey) {
    headers["x-api-key"] = apiKey;
  }
  if (imageKey) {
    headers["x-image-api-key"] = imageKey;
  }
  
  try {
    const response = await fetch("/api/generate-storyboard", {
      method: "POST",
      headers: headers,
      body: JSON.stringify(reqBody)
    });
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Storyboard generation failed");
    }
    
    const data = await response.json();
    const key = `${state.selectedAdGroupIndex}_${state.selectedVideoIndex}`;
    
    state.generatedStoryboards[key] = data.storyboard_image_url;
    
    // Render image
    document.getElementById("storyboard_placeholder").style.display = "none";
    const imgEl = document.getElementById("storyboard_img");
    imgEl.src = data.storyboard_image_url;
    imgEl.style.display = "block";
    
    // Enable animate button
    const animBtn = document.getElementById("generate_video_btn");
    animBtn.disabled = false;
    animBtn.style.opacity = "1";
    
    document.getElementById("video_placeholder_9_16").querySelector("p").textContent = "Ready to Animate Videos";
    document.getElementById("video_placeholder_16_9").querySelector("p").textContent = "Ready to Animate Videos";
    
    const modelLabel = data.model_used ? ` (${data.model_used})` : "";
    statusEl.className = "generator-status success";
    statusEl.querySelector("span").textContent = `Storyboard Generated Successfully${modelLabel}!`;
    generateBtn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Regenerate Storyboard (${isQwen ? "Qwen-Image-2.1" : "Nano Banana Pro"})`;
    
  } catch (error) {
    console.error(error);
    statusEl.className = "generator-status error";
    statusEl.querySelector("span").textContent = "Error: " + error.message;
  } finally {
    generateBtn.disabled = false;
  }
}

// Animate Storyboard using Omni Flash or Seedance 2 Mini
async function animateVideo() {
  const key = `${state.selectedAdGroupIndex}_${state.selectedVideoIndex}`;
  const storyboardUrl = state.generatedStoryboards[key];
  if (!storyboardUrl) return;
  
  const ag = state.campaignData.ad_groups[state.selectedAdGroupIndex];
  const video = ag.videos[state.selectedVideoIndex];
  
  const generator = document.getElementById("video_generator_select").value;
  const kieKey = document.getElementById("kie_key_input").value;
  const mptServiceUrl = document.getElementById("mpt_service_url_input") ? document.getElementById("mpt_service_url_input").value.trim() : "";
  
  if (generator === "seedance" && !kieKey) {
    alert("Please enter a Kie AI API Key in the header to use Seedance 2 Mini.");
    return;
  }
  
  if (generator === "moneyprinter" && !mptServiceUrl) {
    alert("Please enter your MoneyPrinter Service Link (e.g. https://your-service.onrender.com) in the top bar.");
    return;
  }
  
  const statusEl = document.getElementById("video_status");
  statusEl.className = "generator-status working";
  statusEl.style.display = "flex";
  
  const engineName = generator === "minimax" ? "MiniMax-H3 (Self-Hosted)" : (generator === "seedance" ? "Seedance 2 Mini" : (generator === "moneyprinter" ? "MoneyPrinter Turbo" : "Omni Flash"));
  statusEl.querySelector("span").textContent = `Generating videos using ${engineName}...`;
  
  const animateBtn = document.getElementById("generate_video_btn");
  animateBtn.disabled = true;
  
  const apiKey = document.getElementById("api_key_input").value;
  const videoKey = localStorage.getItem("self_hosted_video_key") || "";
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["x-api-key"] = apiKey;
  if (kieKey) headers["x-kie-key"] = kieKey;
  if (videoKey) headers["x-video-api-key"] = videoKey;
  
  // Create base request body
  const baseReq = {
    storyboard_image_url: storyboardUrl,
    product_image_paths: state.campaignData.product_image_paths || [],
    generator: generator,
    mpt_service_url: mptServiceUrl,
    hook_line: video.hook_line || "",
    voice_script: video.voiceover || ""
  };
  
  const videoPlaceholder_9_16 = document.getElementById("video_placeholder_9_16");
  const videoEl_9_16 = document.getElementById("ad_video_9_16");
  const downloadBtn_9_16 = document.getElementById("download_video_btn_9_16");
  
  const videoPlaceholder_16_9 = document.getElementById("video_placeholder_16_9");
  const videoEl_16_9 = document.getElementById("ad_video_16_9");
  const downloadBtn_16_9 = document.getElementById("download_video_btn_16_9");
  
  // Hide current videos and show placeholders/spinners while loading
  videoPlaceholder_9_16.style.display = "flex";
  videoPlaceholder_9_16.querySelector("p").textContent = "Generating 9:16 video...";
  videoEl_9_16.style.display = "none";
  downloadBtn_9_16.style.display = "none";
  
  videoPlaceholder_16_9.style.display = "flex";
  videoPlaceholder_16_9.querySelector("p").textContent = "Generating 16:9 video...";
  videoEl_16_9.style.display = "none";
  downloadBtn_16_9.style.display = "none";

  async function generateRatio(ratio) {
    const isVertical = ratio === "9:16";
    const prompt = isVertical 
      ? `Create a vertical 9:16 advertising video from this storyboard. Hook is: "${video.hook_line}". Visual description: ${video.visual_directions}. Follow the 4 panels left-to-right, top-to-bottom as reference frames.`
      : `Create a landscape 16:9 advertising video from this storyboard. Hook is: "${video.hook_line}". Visual description: ${video.visual_directions}. Follow the 4 panels left-to-right, top-to-bottom as reference frames.`;
      
    const res = await fetch("/api/generate-video", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        ...baseReq,
        video_prompt: prompt,
        aspect_ratio: ratio
      })
    });
    
    if (!res.ok) {
      const err = await res.json();
      throw new Error(`${ratio} generation failed to start: ${err.detail || "Video animation failed"}`);
    }
    
    const triggerRes = await res.json();
    const jobId = triggerRes.job_id;
    
    let finished = false;
    let pollAttempts = 0;
    const maxPollAttempts = 450; // 450 attempts * 2 seconds = 900 seconds (15 minutes)
    
    while (!finished && pollAttempts < maxPollAttempts) {
      pollAttempts++;
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const statusRes = await fetch(`/api/video-status/${jobId}`);
      if (!statusRes.ok) {
        throw new Error(`Failed to check ${ratio} video status`);
      }
      
      const jobData = await statusRes.json();
      if (jobData.status === "success") {
        finished = true;
        return jobData;
      } else if (jobData.status === "failed") {
        finished = true;
        throw new Error(`${ratio} generation failed: ${jobData.error || "Video animation failed on the server"}`);
      } else {
        // Still processing
        const msg = jobData.progress_msg || (isVertical ? `Generating 9:16... (attempt ${pollAttempts})` : `Generating 16:9... (attempt ${pollAttempts})`);
        if (isVertical) {
          videoPlaceholder_9_16.querySelector("p").textContent = msg;
        } else {
          videoPlaceholder_16_9.querySelector("p").textContent = msg;
        }
      }
    }
    
    if (!finished) {
      throw new Error(`${ratio} video generation timed out`);
    }
  }
  
  try {
    let res_9_16, res_16_9;
    if (generator === "minimax") {
      videoPlaceholder_9_16.querySelector("p").textContent = "Processing 9:16 on MiniMax-H3 GPU...";
      videoPlaceholder_16_9.querySelector("p").textContent = "Queued (will process after 9:16)...";
      res_9_16 = await generateRatio("9:16");

      videoPlaceholder_9_16.style.display = "none";
      videoEl_9_16.src = res_9_16.video_url;
      videoEl_9_16.style.display = "block";
      downloadBtn_9_16.href = res_9_16.video_url;
      downloadBtn_9_16.style.display = "flex";

      videoPlaceholder_16_9.querySelector("p").textContent = "Now processing 16:9 on MiniMax-H3 GPU...";
      res_16_9 = await generateRatio("16:9");
    } else {
      [res_9_16, res_16_9] = await Promise.all([
        generateRatio("9:16"),
        generateRatio("16:9")
      ]);
    }
    
    // Store in state
    state.generatedVideos[`${key}_9_16`] = res_9_16.video_url;
    state.generatedVideos[`${key}_16_9`] = res_16_9.video_url;
    
    // Display 9:16
    videoPlaceholder_9_16.style.display = "none";
    videoEl_9_16.src = res_9_16.video_url;
    videoEl_9_16.style.display = "block";
    downloadBtn_9_16.href = res_9_16.video_url;
    downloadBtn_9_16.style.display = "flex";
    
    // Display 16:9
    videoPlaceholder_16_9.style.display = "none";
    videoEl_16_9.src = res_16_9.video_url;
    videoEl_16_9.style.display = "block";
    downloadBtn_16_9.href = res_16_9.video_url;
    downloadBtn_16_9.style.display = "flex";
    
    statusEl.className = "generator-status success";
    statusEl.querySelector("span").textContent = "Both Videos Animated Successfully!";
  } catch (error) {
    console.error(error);
    statusEl.className = "generator-status error";
    statusEl.querySelector("span").textContent = "Error: " + error.message;
    
    videoPlaceholder_9_16.querySelector("p").textContent = "Generation failed.";
    videoPlaceholder_16_9.querySelector("p").textContent = "Generation failed.";
  } finally {
    animateBtn.disabled = false;
  }
}

function updateGeneratorModelText() {
  const model = document.getElementById("video_generator_select").value;
  const generateBtn = document.getElementById("generate_video_btn");
  if (model === "minimax") {
    generateBtn.innerHTML = '<i class="fa-solid fa-play"></i> Animate Videos (MiniMax-H3)';
  } else if (model === "seedance") {
    generateBtn.innerHTML = '<i class="fa-solid fa-play"></i> Animate Videos (Seedance 2 Mini)';
  } else if (model === "moneyprinter") {
    generateBtn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Videos (MoneyPrinter Turbo)';
  } else {
    generateBtn.innerHTML = '<i class="fa-solid fa-play"></i> Animate Videos (Omni Flash)';
  }
}

// LocalStorage API Key Persistence
function initAPIKeysPersistence() {
  const apiKeyEl = document.getElementById("api_key_input");
  const kieKeyEl = document.getElementById("kie_key_input");
  const mptKeyEl = document.getElementById("mpt_service_url_input");
  
  if (apiKeyEl) {
    const savedApiKey = localStorage.getItem("gemini_api_key");
    if (savedApiKey) apiKeyEl.value = savedApiKey;
    
    apiKeyEl.addEventListener("input", (e) => {
      localStorage.setItem("gemini_api_key", e.target.value.trim());
      updateKeysStatusBadge();
    });
  }
  
  if (kieKeyEl) {
    const savedKieKey = localStorage.getItem("kie_api_key");
    if (savedKieKey) kieKeyEl.value = savedKieKey;
    
    kieKeyEl.addEventListener("input", (e) => {
      localStorage.setItem("kie_api_key", e.target.value.trim());
    });
  }

  const pixKeyEl = document.getElementById("pixabay_key_input");
  const mptPixKey = document.getElementById("mpt_pixabay_key");

  if (pixKeyEl) {
    const savedPixKey = localStorage.getItem("pixabay_api_key");
    if (savedPixKey) {
      pixKeyEl.value = savedPixKey;
      if (mptPixKey) mptPixKey.value = savedPixKey;
    }

    pixKeyEl.addEventListener("input", (e) => {
      localStorage.setItem("pixabay_api_key", e.target.value.trim());
      if (mptPixKey) mptPixKey.value = e.target.value.trim();
    });
  }

  if (mptPixKey) {
    const savedPixKey = localStorage.getItem("pixabay_api_key");
    if (savedPixKey) mptPixKey.value = savedPixKey;

    mptPixKey.addEventListener("input", (e) => {
      localStorage.setItem("pixabay_api_key", e.target.value.trim());
      if (pixKeyEl) pixKeyEl.value = e.target.value.trim();
    });
  }

  // Self-hosted Image & Video Keys
  const imgKeyModal = document.getElementById("modal_image_key");
  const vidKeyModal = document.getElementById("modal_video_key");
  if (imgKeyModal) {
    const savedImgKey = localStorage.getItem("self_hosted_image_key");
    if (savedImgKey) imgKeyModal.value = savedImgKey;
    imgKeyModal.addEventListener("input", (e) => {
      localStorage.setItem("self_hosted_image_key", e.target.value.trim());
    });
  }
  if (vidKeyModal) {
    const savedVidKey = localStorage.getItem("self_hosted_video_key");
    if (savedVidKey) vidKeyModal.value = savedVidKey;
    vidKeyModal.addEventListener("input", (e) => {
      localStorage.setItem("self_hosted_video_key", e.target.value.trim());
    });
  }

  updateKeysStatusBadge();
}

// ------------------------------------------------------------
// Antigravity API Keys & Credentials Modal Controller
// ------------------------------------------------------------

function openApiKeysModal() {
  const modal = document.getElementById("api_keys_modal");
  if (modal) {
    modal.style.display = "flex";
    const apiKeyEl = document.getElementById("api_key_input");
    const kieKeyEl = document.getElementById("kie_key_input");
    const pixKeyEl = document.getElementById("pixabay_key_input");

    if (apiKeyEl) apiKeyEl.value = localStorage.getItem("gemini_api_key") || "";
    if (kieKeyEl) kieKeyEl.value = localStorage.getItem("kie_api_key") || "";
    if (pixKeyEl) pixKeyEl.value = localStorage.getItem("pixabay_api_key") || "";

    updateKeysStatusBadge();
  }
}

function closeApiKeysModal() {
  const modal = document.getElementById("api_keys_modal");
  if (modal) modal.style.display = "none";
}

function saveApiKeysFromModal() {
  const apiKeyEl = document.getElementById("api_key_input");
  const kieKeyEl = document.getElementById("kie_key_input");
  const pixKeyEl = document.getElementById("pixabay_key_input");

  if (apiKeyEl) localStorage.setItem("gemini_api_key", apiKeyEl.value.trim());
  if (kieKeyEl) localStorage.setItem("kie_api_key", kieKeyEl.value.trim());
  if (pixKeyEl) {
    localStorage.setItem("pixabay_api_key", pixKeyEl.value.trim());
    const mptPixKey = document.getElementById("mpt_pixabay_key");
    if (mptPixKey) mptPixKey.value = pixKeyEl.value.trim();
  }

  updateKeysStatusBadge();
  closeApiKeysModal();
  alert("Credentials successfully saved in browser LocalStorage!");
}

function toggleKeyMask(inputId, btnEl) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isPass = input.type === "password";
  input.type = isPass ? "text" : "password";
  if (btnEl) {
    btnEl.innerHTML = isPass ? '<i class="fa-regular fa-eye-slash"></i>' : '<i class="fa-regular fa-eye"></i>';
  }
}

function updateKeysStatusBadge() {
  const badge = document.getElementById("keys_status_badge");
  if (!badge) return;
  const geminiKey = localStorage.getItem("gemini_api_key") || (document.getElementById("api_key_input") ? document.getElementById("api_key_input").value : "");
  if (geminiKey && geminiKey.trim().length > 5) {
    badge.className = "keys-status-indicator configured";
    badge.textContent = "Active";
  } else {
    badge.className = "keys-status-indicator";
    badge.textContent = "Configure";
  }
}

// ------------------------------------------------------------
// Self-Hosted GPU Modal & Diagnostics Controller
// ------------------------------------------------------------
let currentPublicIp = "";

function openSelfHostedModal() {
  const modal = document.getElementById("self_hosted_modal");
  if (modal) {
    modal.style.display = "flex";
    const imgKeyInput = document.getElementById("modal_image_key");
    const vidKeyInput = document.getElementById("modal_video_key");
    if (imgKeyInput) imgKeyInput.value = localStorage.getItem("self_hosted_image_key") || "";
    if (vidKeyInput) vidKeyInput.value = localStorage.getItem("self_hosted_video_key") || "";
    checkSelfHostedStatus();
  }
}

function closeSelfHostedModal() {
  const modal = document.getElementById("self_hosted_modal");
  if (modal) modal.style.display = "none";
}

async function checkSelfHostedStatus(showToast = false) {
  try {
    const res = await fetch("/api/self-hosted/status");
    if (!res.ok) return;
    const diag = await res.json();

    currentPublicIp = diag.public_ip || "";
    const ipEl = document.getElementById("user_public_ip");
    if (ipEl) ipEl.textContent = currentPublicIp;

    const imgServer = diag.image_server || {};
    const vidServer = diag.video_server || {};

    // Update Image Server card
    const imgBadge = document.getElementById("badge_image_status");
    const imgUrl = document.getElementById("node_image_url");
    const imgHint = document.getElementById("node_image_hint");
    if (imgUrl && imgServer.url) imgUrl.textContent = imgServer.url;
    if (imgBadge) {
      if (imgServer.online && imgServer.loaded) {
        imgBadge.className = "node-badge online";
        imgBadge.textContent = "Online";
      } else if (imgServer.online && !imgServer.loaded) {
        imgBadge.className = "node-badge loading";
        imgBadge.textContent = "Loading Model";
      } else {
        imgBadge.className = "node-badge offline";
        imgBadge.textContent = "Offline / Stopped";
      }
    }
    if (imgHint && imgServer.detail) {
      imgHint.textContent = imgServer.detail;
    }

    // Update Video Server card
    const vidBadge = document.getElementById("badge_video_status");
    const vidUrl = document.getElementById("node_video_url");
    const vidHint = document.getElementById("node_video_hint");
    if (vidUrl && vidServer.url) vidUrl.textContent = vidServer.url;
    if (vidBadge) {
      if (vidServer.online && vidServer.loaded) {
        vidBadge.className = "node-badge online";
        vidBadge.textContent = "Online";
      } else if (vidServer.online && !vidServer.loaded) {
        vidBadge.className = "node-badge loading";
        vidBadge.textContent = "Loading Model";
      } else {
        vidBadge.className = "node-badge offline";
        vidBadge.textContent = "Offline / Stopped";
      }
    }
    if (vidHint && vidServer.detail) {
      vidHint.textContent = vidServer.detail;
    }

    // Update Header Status Pill
    const statusDot = document.getElementById("gpu_status_dot");
    const statusText = document.getElementById("gpu_status_text");
    if (statusDot && statusText) {
      if (imgServer.online && vidServer.online) {
        statusDot.className = "gpu-pulse-dot online";
        statusText.textContent = "GPU: Online";
      } else if (imgServer.online || vidServer.online) {
        statusDot.className = "gpu-pulse-dot loading";
        statusText.textContent = "GPU: Partial";
      } else {
        statusDot.className = "gpu-pulse-dot offline";
        statusText.textContent = "GPU: Offline";
      }
    }

    if (showToast) {
      alert("Self-hosted servers health check refreshed!");
    }
  } catch (err) {
    console.error("Failed to check self-hosted status:", err);
  }
}

async function saveSelfHostedSettings() {
  const imgKeyInput = document.getElementById("modal_image_key");
  const vidKeyInput = document.getElementById("modal_video_key");
  const imgKey = imgKeyInput ? imgKeyInput.value.trim() : "";
  const vidKey = vidKeyInput ? vidKeyInput.value.trim() : "";

  localStorage.setItem("self_hosted_image_key", imgKey);
  localStorage.setItem("self_hosted_video_key", vidKey);

  try {
    await fetch("/api/self-hosted/configure", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_api_key: imgKey,
        video_api_key: vidKey,
        use_self_hosted: true
      })
    });
    alert("API keys saved and applied successfully!");
    checkSelfHostedStatus();
  } catch (e) {
    alert("Saved in browser: " + e.message);
  }
}

function copyPublicIp() {
  const ipText = currentPublicIp || (document.getElementById("user_public_ip") ? document.getElementById("user_public_ip").textContent : "");
  if (ipText && ipText !== "Detecting...") {
    navigator.clipboard.writeText(ipText).then(() => {
      alert(`Copied IP: ${ipText}\nShare this with the server owner to allowlist on GCP firewall.`);
    }).catch(() => {
      prompt("Copy your IP:", ipText);
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initAPIKeysPersistence();
    initMinimaxDragAndDrop();
    initOmniDragAndDrop();
    initQwenDragAndDrop();
    initBananaDragAndDrop();
    checkSelfHostedStatus();
  });
} else {
  initAPIKeysPersistence();
  initMinimaxDragAndDrop();
  initOmniDragAndDrop();
  initQwenDragAndDrop();
  initBananaDragAndDrop();
  checkSelfHostedStatus();
}

/* ============================================================
   VIEW SWITCHER (MiniMax vs Omni Flash vs Qwen vs Nano Banana vs Campaign vs MPT)
   ============================================================ */

function switchMainView(view) {
  const mmTab = document.getElementById("nav_tab_minimax");
  const omniTab = document.getElementById("nav_tab_omniflash");
  const qwenTab = document.getElementById("nav_tab_qwen") || document.getElementById("nav_tab_image");
  const bananaTab = document.getElementById("nav_tab_banana");
  const campaignTab = document.getElementById("nav_tab_campaign");
  const mptTab = document.getElementById("nav_tab_moneyprinter");

  const mmView = document.getElementById("view_minimax_studio");
  const omniView = document.getElementById("view_omniflash_studio");
  const qwenView = document.getElementById("view_qwen_studio") || document.getElementById("view_image_studio");
  const bananaView = document.getElementById("view_banana_studio");
  const campaignView = document.getElementById("view_ad_campaign");
  const mptView = document.getElementById("view_moneyprinter");

  [mmTab, omniTab, qwenTab, bananaTab, campaignTab, mptTab].forEach(t => t && t.classList.remove("active"));
  [mmView, omniView, qwenView, bananaView, campaignView, mptView].forEach(v => v && (v.style.display = "none"));

  if (view === "minimax" || view === "studio") {
    if (mmTab) mmTab.classList.add("active");
    if (mmView) mmView.style.display = "block";
  } else if (view === "omniflash") {
    if (omniTab) omniTab.classList.add("active");
    if (omniView) omniView.style.display = "block";
  } else if (view === "qwen" || view === "image") {
    if (qwenTab) qwenTab.classList.add("active");
    if (qwenView) qwenView.style.display = "block";
    loadQwenHistory();
  } else if (view === "banana" || view === "nanobanana") {
    if (bananaTab) bananaTab.classList.add("active");
    if (bananaView) bananaView.style.display = "block";
    loadBananaHistory();
  } else if (view === "moneyprinter") {
    if (mptTab) mptTab.classList.add("active");
    if (mptView) mptView.style.display = "block";
  } else {
    if (campaignTab) campaignTab.classList.add("active");
    if (campaignView) campaignView.style.display = "block";
  }
}

/* ============================================================
   FLOW 1: MINIMAX-H3 VIDEO STUDIO (SELF-HOSTED GPU ENGINE)
   ============================================================ */

const minimaxState = {
  mode: "t2va", // "t2va", "fl2va_single", "fl2va_dual"
  aspectRatio: "9:16", // "9:16", "16:9", "auto"
  shortEdge: 768, // 480, 768, 1344
  duration: 5, // 4 to 15
  steps: 30, // 20, 30, 40, 50
  singleFrame: null,
  firstFrame: null,
  lastFrame: null,
  history: []
};

function setMinimaxMode(mode) {
  minimaxState.mode = mode;

  const btnT2va = document.getElementById("btn_mm_mode_t2va");
  const btnSingle = document.getElementById("btn_mm_mode_single");
  const btnDual = document.getElementById("btn_mm_mode_dual");

  if (btnT2va) btnT2va.classList.toggle("active", mode === "t2va");
  if (btnSingle) btnSingle.classList.toggle("active", mode === "fl2va_single");
  if (btnDual) btnDual.classList.toggle("active", mode === "fl2va_dual");

  const paneSingle = document.getElementById("pane_mm_single_frame");
  const paneDual = document.getElementById("pane_mm_dual_frame");
  const promptLabel = document.getElementById("minimax_prompt_label");
  const promptInput = document.getElementById("minimax_prompt");

  if (paneSingle) paneSingle.style.display = mode === "fl2va_single" ? "block" : "none";
  if (paneDual) paneDual.style.display = mode === "fl2va_dual" ? "block" : "none";

  if (mode === "fl2va_single") {
    if (promptLabel) promptLabel.textContent = "Motion & Animation Directions";
    if (promptInput) promptInput.placeholder = "Describe how this picture should animate, camera motion, atmosphere, action, and sound...";
  } else if (mode === "fl2va_dual") {
    if (promptLabel) promptLabel.textContent = "Frame Transition & Interpolation Prompt";
    if (promptInput) promptInput.placeholder = "Describe the evolution that bridges Frame 0 into Frame -1, camera motion, and sound...";
  } else {
    if (promptLabel) promptLabel.textContent = "Scene Prompt & Motion Directions";
    if (promptInput) promptInput.placeholder = "Describe the scene action, motion dynamics, visual atmosphere, and audio style in detail...";
  }
}

function setMinimaxAspectRatio(ratio) {
  minimaxState.aspectRatio = ratio;
  document.querySelectorAll("#minimax_aspect_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.ratio === ratio);
  });

  const viewport = document.getElementById("minimax_viewport");
  if (viewport) {
    viewport.classList.remove("ratio-9-16", "ratio-16-9", "ratio-auto");
    viewport.classList.add(ratio === "auto" ? "ratio-16-9" : `ratio-${ratio.replace(":", "-")}`);
  }
  updateMinimaxMetaBadges();
}

function setMinimaxResolution(edge) {
  minimaxState.shortEdge = parseInt(edge, 10);
  document.querySelectorAll("#minimax_res_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.edge, 10) === minimaxState.shortEdge);
  });
  updateMinimaxMetaBadges();
}

function setMinimaxDuration(dur) {
  minimaxState.duration = parseInt(dur, 10);
  document.querySelectorAll("#minimax_dur_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.dur, 10) === minimaxState.duration);
  });
  updateMinimaxMetaBadges();
}

function setMinimaxSteps(steps) {
  minimaxState.steps = parseInt(steps, 10);
  document.querySelectorAll("#minimax_steps_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.steps, 10) === minimaxState.steps);
  });
}

function updateMinimaxMetaBadges() {
  const resBadge = document.getElementById("minimax_meta_res");
  const durBadge = document.getElementById("minimax_meta_dur");
  let ratioName = "9:16 Vertical";
  if (minimaxState.aspectRatio === "16:9") ratioName = "16:9 Wide";
  else if (minimaxState.aspectRatio === "auto") ratioName = "Auto Aspect";

  if (resBadge) resBadge.textContent = `${ratioName} · ${minimaxState.shortEdge}p`;
  if (durBadge) durBadge.textContent = `${minimaxState.duration}s`;
}

function appendMinimaxKeyword(keyword) {
  const textarea = document.getElementById("minimax_prompt");
  if (!textarea) return;
  const current = textarea.value.trim();
  if (!current) {
    textarea.value = keyword;
  } else {
    textarea.value = current.endsWith(",") ? `${current} ${keyword}` : `${current}, ${keyword}`;
  }
  textarea.focus();
}

// Single Frame (Image-to-Video) handlers
function handleMinimaxSingleUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  minimaxState.singleFrame = file;

  const preview = document.getElementById("preview_mm_single_frame");
  const emptyState = document.getElementById("body_mm_single");
  const clearBtn = document.getElementById("clear_mm_single_btn");

  if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
  if (emptyState) emptyState.style.display = "none";
  if (clearBtn) clearBtn.style.display = "inline-flex";
}

function clearMinimaxSingleFrame() {
  minimaxState.singleFrame = null;
  const preview = document.getElementById("preview_mm_single_frame");
  const emptyState = document.getElementById("body_mm_single");
  const clearBtn = document.getElementById("clear_mm_single_btn");
  const input = document.getElementById("input_mm_single_frame");

  if (preview) { preview.src = ""; preview.style.display = "none"; }
  if (emptyState) emptyState.style.display = "flex";
  if (clearBtn) clearBtn.style.display = "none";
  if (input) input.value = "";
}

// Dual Keyframes (Start & End Frame) handlers
function handleMinimaxDualUpload(e, position) {
  const file = e.target.files[0];
  if (!file) return;

  if (position === "first") {
    minimaxState.firstFrame = file;
    const preview = document.getElementById("preview_mm_first_frame");
    const emptyState = document.getElementById("body_mm_first");
    const clearBtn = document.getElementById("clear_mm_first_btn");
    if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "inline-flex";
  } else {
    minimaxState.lastFrame = file;
    const preview = document.getElementById("preview_mm_last_frame");
    const emptyState = document.getElementById("body_mm_last");
    const clearBtn = document.getElementById("clear_mm_last_btn");
    if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "inline-flex";
  }
}

function clearMinimaxDualFrame(position) {
  if (position === "first") {
    minimaxState.firstFrame = null;
    const preview = document.getElementById("preview_mm_first_frame");
    const emptyState = document.getElementById("body_mm_first");
    const clearBtn = document.getElementById("clear_mm_first_btn");
    const input = document.getElementById("input_mm_first_frame");
    if (preview) { preview.src = ""; preview.style.display = "none"; }
    if (emptyState) emptyState.style.display = "flex";
    if (clearBtn) clearBtn.style.display = "none";
    if (input) input.value = "";
  } else {
    minimaxState.lastFrame = null;
    const preview = document.getElementById("preview_mm_last_frame");
    const emptyState = document.getElementById("body_mm_last");
    const clearBtn = document.getElementById("clear_mm_last_btn");
    const input = document.getElementById("input_mm_last_frame");
    if (preview) { preview.src = ""; preview.style.display = "none"; }
    if (emptyState) emptyState.style.display = "flex";
    if (clearBtn) clearBtn.style.display = "none";
    if (input) input.value = "";
  }
}

// Drag & Drop for MiniMax
function initMinimaxDragAndDrop() {
  const dropSingle = document.getElementById("dropzone_mm_single");
  const dropFirst = document.getElementById("dropzone_mm_first");
  const dropLast = document.getElementById("dropzone_mm_last");

  const setupDrop = (zone, onFile) => {
    if (!zone) return;
    zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", (e) => { e.preventDefault(); zone.classList.remove("drag-over"); });
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      const f = Array.from(e.dataTransfer.files).find(file => file.type.startsWith("image/"));
      if (f) onFile(f);
    });
  };

  setupDrop(dropSingle, (file) => handleMinimaxSingleUpload({ target: { files: [file] } }));
  setupDrop(dropFirst, (file) => handleMinimaxDualUpload({ target: { files: [file] } }, "first"));
  setupDrop(dropLast, (file) => handleMinimaxDualUpload({ target: { files: [file] } }, "last"));
}

let mmElapsedInterval = null;

async function submitMiniMaxStudioVideo() {
  const promptInput = document.getElementById("minimax_prompt");
  const generateBtn = document.getElementById("minimax_generate_btn");
  const emptyState = document.getElementById("minimax_empty_state");
  const loadingOverlay = document.getElementById("minimax_loading_state");
  const videoPlayer = document.getElementById("minimax_video_player");
  const actionsBar = document.getElementById("minimax_player_actions");
  const downloadBtn = document.getElementById("download_minimax_btn");
  const loadingTitle = document.getElementById("minimax_loading_title");
  const loadingSub = document.getElementById("minimax_loading_sub");
  const progressBar = document.getElementById("minimax_progress_bar");
  const elapsedTimer = document.getElementById("minimax_elapsed_timer");

  const prompt = promptInput ? promptInput.value.trim() : "";
  if (!prompt) {
    alert("Please enter a scene prompt or motion directions for MiniMax-H3.");
    if (promptInput) promptInput.focus();
    return;
  }

  if (minimaxState.mode === "fl2va_single" && !minimaxState.singleFrame) {
    alert("Please upload a starting frame to animate with MiniMax-H3.");
    return;
  }

  if (minimaxState.mode === "fl2va_dual" && (!minimaxState.firstFrame || !minimaxState.lastFrame)) {
    alert("Please upload both start frame (Frame 0) and end frame (Frame -1) for boundary generation.");
    return;
  }

  const formData = new FormData();
  formData.append("mode", minimaxState.mode);
  formData.append("prompt", prompt);
  formData.append("generator", "minimax");
  formData.append("aspect_ratio", minimaxState.aspectRatio);
  formData.append("resolution", `${minimaxState.shortEdge}p`);
  formData.append("short_edge", minimaxState.shortEdge);
  formData.append("duration", minimaxState.duration);
  formData.append("steps", minimaxState.steps);

  const seedInput = document.getElementById("minimax_seed");
  if (seedInput && seedInput.value.trim()) {
    const s = parseInt(seedInput.value.trim(), 10);
    if (!isNaN(s)) formData.append("seed", s);
  }

  if (minimaxState.mode === "fl2va_single" && minimaxState.singleFrame) {
    formData.append("first_frame", minimaxState.singleFrame);
  } else if (minimaxState.mode === "fl2va_dual") {
    if (minimaxState.firstFrame) formData.append("first_frame", minimaxState.firstFrame);
    if (minimaxState.lastFrame) formData.append("last_frame", minimaxState.lastFrame);
  }

  const apiKey = document.getElementById("api_key_input") ? document.getElementById("api_key_input").value.trim() : "";
  const videoKey = localStorage.getItem("self_hosted_video_key") || "";
  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  if (videoKey) headers["x-video-api-key"] = videoKey;

  // UI state
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<div class="mini-spinner"></div><span>Synthesizing with MiniMax-H3 (GPU)...</span>';
  }
  if (emptyState) emptyState.style.display = "none";
  if (videoPlayer) videoPlayer.style.display = "none";
  if (actionsBar) actionsBar.style.display = "none";
  if (loadingOverlay) loadingOverlay.style.display = "flex";
  if (loadingTitle) loadingTitle.textContent = "Synthesizing with MiniMax-H3";
  if (loadingSub) loadingSub.textContent = `Queueing job on GPU server (${minimaxState.shortEdge}p, ${minimaxState.duration}s, steps=${minimaxState.steps})...`;
  if (progressBar) progressBar.style.width = "10%";

  let elapsedSec = 0;
  if (mmElapsedInterval) clearInterval(mmElapsedInterval);
  if (elapsedTimer) elapsedTimer.textContent = "0s elapsed · Submitting job...";
  mmElapsedInterval = setInterval(() => {
    elapsedSec += 1;
    if (elapsedTimer) {
      elapsedTimer.textContent = `${elapsedSec}s elapsed · Polling MiniMax-H3 GPU server...`;
    }
  }, 1000);

  try {
    const res = await fetch("/api/studio/generate-video", {
      method: "POST",
      headers: headers,
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to dispatch MiniMax video job");
    }

    const data = await res.json();
    const jobId = data.job_id;

    // Polling status
    let progress = 15;
    const pollInterval = setInterval(async () => {
      try {
        progress = Math.min(progress + 5, 92);
        if (progressBar) progressBar.style.width = `${progress}%`;

        const statusRes = await fetch(`/api/video-status/${jobId}`);
        if (!statusRes.ok) return;
        const jobData = await statusRes.json();

        if (jobData.progress_msg && loadingSub) {
          loadingSub.textContent = jobData.progress_msg;
        }

        if (jobData.status === "success") {
          clearInterval(pollInterval);
          if (mmElapsedInterval) clearInterval(mmElapsedInterval);
          if (progressBar) progressBar.style.width = "100%";

          setTimeout(() => {
            if (loadingOverlay) loadingOverlay.style.display = "none";
            if (videoPlayer) {
              videoPlayer.src = jobData.video_url;
              videoPlayer.style.display = "block";
              videoPlayer.play().catch(e => console.log("Autoplay caught:", e));
            }
            if (actionsBar) actionsBar.style.display = "flex";
            if (downloadBtn) {
              downloadBtn.href = jobData.video_url;
              downloadBtn.download = `minimax_video_${minimaxState.shortEdge}p_${minimaxState.duration}s_${Date.now()}.mp4`;
            }

            // History entry
            const historyEntry = {
              id: jobId,
              url: jobData.video_url,
              prompt: prompt,
              aspectRatio: minimaxState.aspectRatio,
              shortEdge: minimaxState.shortEdge,
              duration: minimaxState.duration,
              steps: minimaxState.steps,
              hasAudio: true,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            minimaxState.history.unshift(historyEntry);
            renderMiniMaxHistory();

            if (generateBtn) {
              generateBtn.disabled = false;
              generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video + Audio (MiniMax-H3)</span>';
            }
          }, 600);

        } else if (jobData.status === "failed") {
          clearInterval(pollInterval);
          if (mmElapsedInterval) clearInterval(mmElapsedInterval);
          throw new Error(jobData.error || "MiniMax-H3 video generation failed on server");
        }
      } catch (pollErr) {
        clearInterval(pollInterval);
        if (mmElapsedInterval) clearInterval(mmElapsedInterval);
        console.error("MiniMax polling error:", pollErr);
        alert("Generation failed: " + pollErr.message);
        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (emptyState) emptyState.style.display = "flex";
        if (generateBtn) {
          generateBtn.disabled = false;
          generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video + Audio (MiniMax-H3)</span>';
        }
      }
    }, 4000);

  } catch (err) {
    if (mmElapsedInterval) clearInterval(mmElapsedInterval);
    console.error("MiniMax submit error:", err);
    alert("MiniMax generation failed: " + err.message);
    if (loadingOverlay) loadingOverlay.style.display = "none";
    if (emptyState) emptyState.style.display = "flex";
    if (generateBtn) {
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video + Audio (MiniMax-H3)</span>';
    }
  }
}

function renderMiniMaxHistory() {
  const reel = document.getElementById("minimax_history_reel");
  const countBadge = document.getElementById("minimax_history_count");
  if (!reel) return;

  if (countBadge) {
    countBadge.textContent = `${minimaxState.history.length} video${minimaxState.history.length === 1 ? '' : 's'}`;
  }
  reel.innerHTML = "";

  if (minimaxState.history.length === 0) {
    reel.innerHTML = '<div class="history-empty" id="minimax_history_empty_msg">MiniMax video clips in this session will appear here for instant replay and comparison.</div>';
    return;
  }

  minimaxState.history.forEach((item, idx) => {
    const card = document.createElement("div");
    card.className = `history-item ${idx === 0 ? 'active' : ''}`;
    card.title = `${item.prompt} (${item.shortEdge || 768}p · ${item.duration}s)`;

    const vid = document.createElement("video");
    vid.src = item.url;
    vid.muted = true;
    vid.playsInline = true;
    vid.onmouseover = () => vid.play().catch(() => {});
    vid.onmouseout = () => vid.pause();

    const badge = document.createElement("span");
    badge.className = "history-item-badge";
    badge.innerHTML = `<i class="fa-solid fa-volume-high" style="margin-right:2px;"></i> ${item.shortEdge || 768}p · ${item.duration}s`;

    card.appendChild(vid);
    card.appendChild(badge);

    card.onclick = () => {
      document.querySelectorAll("#minimax_history_reel .history-item").forEach(c => c.classList.remove("active"));
      card.classList.add("active");

      const player = document.getElementById("minimax_video_player");
      const emptyState = document.getElementById("minimax_empty_state");
      const actionsBar = document.getElementById("minimax_player_actions");
      const downloadBtn = document.getElementById("download_minimax_btn");

      if (emptyState) emptyState.style.display = "none";
      if (player) {
        player.src = item.url;
        player.style.display = "block";
        player.play().catch(() => {});
      }
      if (actionsBar) actionsBar.style.display = "flex";
      if (downloadBtn) {
        downloadBtn.href = item.url;
        downloadBtn.download = `minimax_${item.shortEdge || 768}p_${item.duration}s_${Date.now()}.mp4`;
      }

      setMinimaxAspectRatio(item.aspectRatio || "9:16");
    };

    reel.appendChild(card);
  });
}

/* ============================================================
   FLOW 2: GEMINI OMNI FLASH 1.1 STUDIO
   ============================================================ */

const omniState = {
  mode: "prompt_images", // "prompt_images", "first_last_frame", "edit_video"
  aspectRatio: "9:16",
  resolution: "720p",
  duration: 6,
  referenceImages: [], // Up to 3
  firstFrame: null,
  lastFrame: null,
  sourceVideo: null,
  history: []
};

// Mode switcher
function setStudioMode(mode) {
  setOmniMode(mode);
}

function setOmniMode(mode) {
  omniState.mode = mode;

  document.querySelectorAll("#view_omniflash_studio .mode-tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });

  const panePrompt = document.getElementById("pane_prompt_images");
  const paneKeyframes = document.getElementById("pane_first_last_frame");
  const paneVideo = document.getElementById("pane_edit_video");
  const promptLabel = document.getElementById("prompt_label_text");
  const promptInput = document.getElementById("studio_prompt");

  if (panePrompt) panePrompt.style.display = mode === "prompt_images" ? "block" : "none";
  if (paneKeyframes) paneKeyframes.style.display = mode === "first_last_frame" ? "block" : "none";
  if (paneVideo) paneVideo.style.display = mode === "edit_video" ? "block" : "none";

  if (mode === "first_last_frame") {
    if (promptLabel) promptLabel.textContent = "Motion & Transition Instructions";
    if (promptInput) promptInput.placeholder = "Describe the motion and scene evolution that bridges the start frame to the end frame...";
  } else if (mode === "edit_video") {
    if (promptLabel) promptLabel.textContent = "Video Edit Instructions & Modifications";
    if (promptInput) promptInput.placeholder = "Describe what to modify (e.g. change backdrop to neon city, golden-hour lighting)...";
  } else {
    if (promptLabel) promptLabel.textContent = "Scene Prompt & Motion Directions";
    if (promptInput) promptInput.placeholder = "Describe the scene, lighting, action, and style in rich detail...";
  }
}

function setStudioAspectRatio(ratio) { setOmniAspectRatio(ratio); }
function setOmniAspectRatio(ratio) {
  omniState.aspectRatio = ratio;
  document.querySelectorAll("#omni_aspect_ratio_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.ratio === ratio);
  });
  const viewport = document.getElementById("omni_player_viewport");
  if (viewport) {
    viewport.classList.remove("ratio-9-16", "ratio-16-9", "ratio-1-1");
    viewport.classList.add(`ratio-${ratio.replace(":", "-")}`);
  }
  updateOmniMetaBadges();
}

function setStudioResolution(res) { setOmniResolution(res); }
function setOmniResolution(res) {
  omniState.resolution = res;
  document.querySelectorAll("#omni_resolution_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.res === res);
  });
  updateOmniMetaBadges();
}

function setStudioDuration(dur) { setOmniDuration(dur); }
function setOmniDuration(dur) {
  omniState.duration = parseInt(dur, 10);
  document.querySelectorAll("#omni_duration_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.dur, 10) === omniState.duration);
  });
  updateOmniMetaBadges();
}

function updateOmniMetaBadges() {
  const resBadge = document.getElementById("omni_player_res_badge");
  const durBadge = document.getElementById("omni_player_dur_badge");
  let ratioName = "9:16 Vertical";
  if (omniState.aspectRatio === "16:9") ratioName = "16:9 Landscape";
  else if (omniState.aspectRatio === "1:1") ratioName = "1:1 Square";

  if (resBadge) resBadge.textContent = `${ratioName} · ${omniState.resolution}`;
  if (durBadge) durBadge.textContent = `${omniState.duration}s`;
}

function appendPromptKeyword(keyword) {
  const textarea = document.getElementById("studio_prompt");
  if (!textarea) return;
  const current = textarea.value.trim();
  if (!current) {
    textarea.value = keyword;
  } else {
    textarea.value = current.endsWith(",") ? `${current} ${keyword}` : `${current}, ${keyword}`;
  }
  textarea.focus();
}

// Omni Flash Reference Image Slots
let omniActiveSlotIndex = 0;
function triggerRefUpload(index) {
  omniActiveSlotIndex = index;
  const input = document.getElementById("studio_ref_input_hidden");
  if (input) input.click();
}

function handleSingleSlotUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  omniState.referenceImages[omniActiveSlotIndex] = file;
  const imgEl = document.getElementById(`slot_img_${omniActiveSlotIndex}`);
  const emptyEl = document.getElementById(`slot_empty_${omniActiveSlotIndex}`);
  const delBtn = document.getElementById(`slot_del_${omniActiveSlotIndex}`);

  if (imgEl) {
    imgEl.src = URL.createObjectURL(file);
    imgEl.style.display = "block";
  }
  if (emptyEl) emptyEl.style.display = "none";
  if (delBtn) delBtn.style.display = "flex";

  updateRefCountBadge();
  e.target.value = "";
}

function removeSlotRef(index) {
  omniState.referenceImages[index] = null;
  const imgEl = document.getElementById(`slot_img_${index}`);
  const emptyEl = document.getElementById(`slot_empty_${index}`);
  const delBtn = document.getElementById(`slot_del_${index}`);

  if (imgEl) {
    imgEl.src = "";
    imgEl.style.display = "none";
  }
  if (emptyEl) emptyEl.style.display = "flex";
  if (delBtn) delBtn.style.display = "none";

  updateRefCountBadge();
}

function updateRefCountBadge() {
  const count = omniState.referenceImages.filter(Boolean).length;
  const badge = document.getElementById("ref_count_badge");
  if (badge) badge.textContent = `${count} / 3`;
}

// Keyframes
function handleKeyframeUpload(e, position) {
  const file = e.target.files[0];
  if (!file) return;

  if (position === "first") {
    omniState.firstFrame = file;
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("keyframe_body_first");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "flex";
  } else {
    omniState.lastFrame = file;
    const preview = document.getElementById("preview_last_frame");
    const emptyState = document.getElementById("keyframe_body_last");
    const clearBtn = document.getElementById("clear_last_frame_btn");
    if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "flex";
  }
}

function clearKeyframe(position) {
  if (position === "first") {
    omniState.firstFrame = null;
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("keyframe_body_first");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    const input = document.getElementById("studio_first_frame_input");
    if (preview) { preview.src = ""; preview.style.display = "none"; }
    if (emptyState) emptyState.style.display = "flex";
    if (clearBtn) clearBtn.style.display = "none";
    if (input) input.value = "";
  } else {
    omniState.lastFrame = null;
    const preview = document.getElementById("preview_last_frame");
    const emptyState = document.getElementById("keyframe_body_last");
    const clearBtn = document.getElementById("clear_last_frame_btn");
    const input = document.getElementById("studio_last_frame_input");
    if (preview) { preview.src = ""; preview.style.display = "none"; }
    if (emptyState) emptyState.style.display = "flex";
    if (clearBtn) clearBtn.style.display = "none";
    if (input) input.value = "";
  }
}

// Source Video
function handleSourceVideoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;

  omniState.sourceVideo = file;
  const previewContainer = document.getElementById("video_preview_container");
  const emptyState = document.getElementById("video_empty_state");
  const videoPlayer = document.getElementById("preview_source_video");

  if (videoPlayer) videoPlayer.src = URL.createObjectURL(file);
  if (emptyState) emptyState.style.display = "none";
  if (previewContainer) previewContainer.style.display = "flex";
}

function clearSourceVideo() {
  omniState.sourceVideo = null;
  const previewContainer = document.getElementById("video_preview_container");
  const emptyState = document.getElementById("video_empty_state");
  const videoPlayer = document.getElementById("preview_source_video");
  const input = document.getElementById("studio_video_input");

  if (videoPlayer) videoPlayer.src = "";
  if (previewContainer) previewContainer.style.display = "none";
  if (emptyState) emptyState.style.display = "flex";
  if (input) input.value = "";
}

function initOmniDragAndDrop() {
  const firstCard = document.querySelector(".keyframe-compact-card:nth-child(1)");
  const lastCard = document.querySelector(".keyframe-compact-card:nth-child(3)");
  const videoBox = document.querySelector(".video-compact-box");

  const setupDrop = (el, onFile) => {
    if (!el) return;
    el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("drag-over"); });
    el.addEventListener("dragleave", (e) => { e.preventDefault(); el.classList.remove("drag-over"); });
    el.addEventListener("drop", (e) => {
      e.preventDefault();
      el.classList.remove("drag-over");
      const f = Array.from(e.dataTransfer.files).find(onFile.filter || (() => true));
      if (f) onFile.handler(f);
    });
  };

  if (firstCard) setupDrop(firstCard, { filter: f => f.type.startsWith("image/"), handler: f => handleKeyframeUpload({ target: { files: [f] } }, "first") });
  if (lastCard) setupDrop(lastCard, { filter: f => f.type.startsWith("image/"), handler: f => handleKeyframeUpload({ target: { files: [f] } }, "last") });
  if (videoBox) setupDrop(videoBox, { filter: f => f.type.startsWith("video/"), handler: f => handleSourceVideoUpload({ target: { files: [f] } }) });
}

async function submitOmniStudioVideo() {
  const promptInput = document.getElementById("studio_prompt");
  const negInput = document.getElementById("omni_negative_prompt");
  const generateBtn = document.getElementById("omni_generate_btn");
  const emptyState = document.getElementById("omni_player_empty_state");
  const loadingOverlay = document.getElementById("omni_player_loading_state");
  const videoPlayer = document.getElementById("omni_video_player");
  const actionsBar = document.getElementById("omni_player_actions");
  const downloadBtn = document.getElementById("download_omni_video_btn");
  const loadingTitle = document.getElementById("omni_loading_title");
  const loadingSub = document.getElementById("omni_loading_sub");
  const progressBar = document.getElementById("omni_progress_bar");

  const prompt = promptInput ? promptInput.value.trim() : "";
  if (!prompt) {
    alert("Please enter a scene prompt or motion directions.");
    if (promptInput) promptInput.focus();
    return;
  }

  if (omniState.mode === "edit_video" && !omniState.sourceVideo) {
    alert("Please upload a source video to edit.");
    return;
  }

  const formData = new FormData();
  formData.append("mode", omniState.mode);
  formData.append("prompt", prompt);
  formData.append("generator", "omni-flash");
  if (negInput && negInput.value.trim()) {
    formData.append("negative_prompt", negInput.value.trim());
  }
  formData.append("aspect_ratio", omniState.aspectRatio);
  formData.append("resolution", omniState.resolution);
  formData.append("duration", omniState.duration);

  // Attach mode-specific files
  const activeRefs = omniState.referenceImages.filter(Boolean);
  if (omniState.mode === "prompt_images" && activeRefs.length > 0) {
    activeRefs.forEach(img => formData.append("reference_images", img));
  } else if (omniState.mode === "first_last_frame") {
    if (omniState.firstFrame) formData.append("first_frame", omniState.firstFrame);
    if (omniState.lastFrame) formData.append("last_frame", omniState.lastFrame);
  } else if (omniState.mode === "edit_video" && omniState.sourceVideo) {
    formData.append("source_video", omniState.sourceVideo);
  }

  const apiKey = document.getElementById("api_key_input") ? document.getElementById("api_key_input").value.trim() : "";
  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;

  // UI state
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<div class="mini-spinner"></div><span>Rendering with Omni Flash 1.1...</span>';
  }
  if (emptyState) emptyState.style.display = "none";
  if (videoPlayer) videoPlayer.style.display = "none";
  if (actionsBar) actionsBar.style.display = "none";
  if (loadingOverlay) loadingOverlay.style.display = "flex";
  if (loadingTitle) loadingTitle.textContent = "Synthesizing with Omni Flash 1.1";
  if (loadingSub) loadingSub.textContent = `Targeting ${omniState.resolution} · ${omniState.aspectRatio} · ${omniState.duration}s...`;
  if (progressBar) progressBar.style.width = "25%";

  try {
    const res = await fetch("/api/studio/generate-video", {
      method: "POST",
      headers: headers,
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to dispatch Omni Flash job");
    }

    const data = await res.json();
    const jobId = data.job_id;

    let progress = 35;
    const pollInterval = setInterval(async () => {
      try {
        progress = Math.min(progress + 7, 92);
        if (progressBar) progressBar.style.width = `${progress}%`;

        const statusRes = await fetch(`/api/video-status/${jobId}`);
        if (!statusRes.ok) return;
        const jobData = await statusRes.json();

        if (jobData.progress_msg && loadingSub) {
          loadingSub.textContent = jobData.progress_msg;
        }

        if (jobData.status === "success") {
          clearInterval(pollInterval);
          if (progressBar) progressBar.style.width = "100%";

          setTimeout(() => {
            if (loadingOverlay) loadingOverlay.style.display = "none";
            if (videoPlayer) {
              videoPlayer.src = jobData.video_url;
              videoPlayer.style.display = "block";
              videoPlayer.play().catch(e => console.log("Autoplay caught:", e));
            }
            if (actionsBar) actionsBar.style.display = "flex";
            if (downloadBtn) {
              downloadBtn.href = jobData.video_url;
              downloadBtn.download = `omniflash_video_${omniState.resolution}_${Date.now()}.mp4`;
            }

            const historyEntry = {
              id: jobId,
              url: jobData.video_url,
              prompt: prompt,
              aspectRatio: omniState.aspectRatio,
              resolution: omniState.resolution,
              duration: omniState.duration,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            omniState.history.unshift(historyEntry);
            renderOmniHistory();

            if (generateBtn) {
              generateBtn.disabled = false;
              generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video with Omni Flash 1.1</span>';
            }
          }, 600);

        } else if (jobData.status === "failed") {
          clearInterval(pollInterval);
          throw new Error(jobData.error || "Omni Flash video generation failed on server");
        }
      } catch (pollErr) {
        clearInterval(pollInterval);
        console.error("Omni Flash polling error:", pollErr);
        alert("Generation failed: " + pollErr.message);
        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (emptyState) emptyState.style.display = "flex";
        if (generateBtn) {
          generateBtn.disabled = false;
          generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video with Omni Flash 1.1</span>';
        }
      }
    }, 3000);

  } catch (err) {
    console.error("Omni submit error:", err);
    alert("Generation failed: " + err.message);
    if (loadingOverlay) loadingOverlay.style.display = "none";
    if (emptyState) emptyState.style.display = "flex";
    if (generateBtn) {
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video with Omni Flash 1.1</span>';
    }
  }
}

function renderOmniHistory() {
  const reel = document.getElementById("omni_history_reel");
  const countBadge = document.getElementById("omni_history_count");
  if (!reel) return;

  if (countBadge) {
    countBadge.textContent = `${omniState.history.length} video${omniState.history.length === 1 ? '' : 's'}`;
  }
  reel.innerHTML = "";

  if (omniState.history.length === 0) {
    reel.innerHTML = '<div class="history-empty" id="omni_history_empty_msg">Generated clips in this session will appear here for instant replay and comparison.</div>';
    return;
  }

  omniState.history.forEach((item, idx) => {
    const card = document.createElement("div");
    card.className = `history-item ${idx === 0 ? 'active' : ''}`;
    card.title = `${item.prompt} (${item.resolution})`;

    const vid = document.createElement("video");
    vid.src = item.url;
    vid.muted = true;
    vid.playsInline = true;
    vid.onmouseover = () => vid.play().catch(() => {});
    vid.onmouseout = () => vid.pause();

    const badge = document.createElement("span");
    badge.className = "history-item-badge";
    badge.textContent = `${item.resolution}`;

    card.appendChild(vid);
    card.appendChild(badge);

    card.onclick = () => {
      document.querySelectorAll("#omni_history_reel .history-item").forEach(c => c.classList.remove("active"));
      card.classList.add("active");

      const player = document.getElementById("omni_video_player");
      const emptyState = document.getElementById("omni_player_empty_state");
      const actionsBar = document.getElementById("omni_player_actions");
      const downloadBtn = document.getElementById("download_omni_video_btn");

      if (emptyState) emptyState.style.display = "none";
      if (player) {
        player.src = item.url;
        player.style.display = "block";
        player.play().catch(() => {});
      }
      if (actionsBar) actionsBar.style.display = "flex";
      if (downloadBtn) downloadBtn.href = item.url;

      setOmniAspectRatio(item.aspectRatio);
    };

    reel.appendChild(card);
  });
}

// Backward compatibility aliases
const studioState = omniState;
const submitStudioVideo = submitOmniStudioVideo;
const renderStudioHistory = renderOmniHistory;
function setStudioEngine() {}

/* ============================================================
   FLOW 3: MONEYPRINTER TURBO JAVASCRIPT CONTROLLER
   ============================================================ */

async function generateMoneyPrinterVideo() {
  const subjectInput = document.getElementById("mpt_subject_input");
  const subject = subjectInput ? subjectInput.value.trim() : "";
  if (!subject) {
    alert("Please enter a Video Topic or Ad Angle.");
    if (subjectInput) subjectInput.focus();
    return;
  }

  const customScript = document.getElementById("mpt_custom_script_input") ? document.getElementById("mpt_custom_script_input").value.trim() : "";
  const aspectSelect = document.getElementById("mpt_aspect_select");
  const aspectRatio = aspectSelect ? aspectSelect.value : "9:16";
  const voiceSelect = document.getElementById("mpt_voice_select");
  const voiceName = voiceSelect ? voiceSelect.value : "en-US-ChristopherNeural";
  const burnSubtitles = document.getElementById("mpt_subtitles_toggle") ? document.getElementById("mpt_subtitles_toggle").checked : true;
  
  const pixabayKey = (document.getElementById("mpt_pixabay_key") ? document.getElementById("mpt_pixabay_key").value.trim() : "") ||
                     (document.getElementById("pixabay_key_input") ? document.getElementById("pixabay_key_input").value.trim() : "");
                     
  const apiKey = document.getElementById("api_key_input") ? document.getElementById("api_key_input").value.trim() : "";

  const generateBtn = document.getElementById("mpt_generate_btn");
  const statusEl = document.getElementById("mpt_status");
  const statusText = document.getElementById("mpt_status_text");
  
  const videoPlaceholder = document.getElementById("mpt_video_placeholder");
  const videoEl = document.getElementById("mpt_ad_video");
  const downloadBtn = document.getElementById("mpt_download_btn");
  const detailsCard = document.getElementById("mpt_details_card");
  const scriptPreview = document.getElementById("mpt_script_preview");
  const keywordsWrap = document.getElementById("mpt_keywords_wrap");

  generateBtn.disabled = true;
  statusEl.className = "generator-status working";
  statusEl.style.display = "flex";
  statusText.textContent = "1/4: Analyzing topic & generating viral script...";

  videoPlaceholder.style.display = "flex";
  videoPlaceholder.querySelector("p").textContent = "Generating your video...";
  videoEl.style.display = "none";
  downloadBtn.style.display = "none";
  if (detailsCard) detailsCard.style.display = "none";

  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["x-api-key"] = apiKey;

  try {
    const res = await fetch("/api/moneyprinter/generate", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({
        subject: subject,
        custom_script: customScript,
        aspect_ratio: aspectRatio,
        voice_name: voiceName,
        pixabay_key: pixabayKey,
        burn_subtitles: burnSubtitles
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to start MoneyPrinter generation");
    }

    const { job_id } = await res.json();
    let finished = false;
    let pollAttempts = 0;
    let consecutiveErrors = 0;
    const maxPolls = 60;

    while (!finished && pollAttempts < maxPolls) {
      pollAttempts++;
      await new Promise(r => setTimeout(r, 2000));

      let statusRes;
      try {
        statusRes = await fetch(`/api/video-status/${job_id}`);
      } catch (netErr) {
        consecutiveErrors++;
        if (consecutiveErrors > 4) {
          throw new Error("Network connection lost. Please check your connection.");
        }
        continue;
      }

      if (!statusRes.ok) {
        consecutiveErrors++;
        if (consecutiveErrors > 3) {
          let msg = "Job interrupted on server (server may have restarted). Please click Generate again.";
          try {
            const errData = await statusRes.json();
            if (errData.detail) msg = errData.detail;
          } catch(e) {}
          throw new Error(msg);
        }
        continue;
      }
      consecutiveErrors = 0;

      const jobData = await statusRes.json();
      if (jobData.status === "success") {
        finished = true;
        
        // Show video
        videoPlaceholder.style.display = "none";
        videoEl.src = jobData.video_url;
        videoEl.style.display = "block";
        downloadBtn.href = jobData.video_url;
        downloadBtn.style.display = "flex";

        // Show details
        if (detailsCard && jobData.script) {
          detailsCard.style.display = "block";
          if (scriptPreview) scriptPreview.textContent = jobData.script;
          if (keywordsWrap && jobData.keywords) {
            keywordsWrap.innerHTML = jobData.keywords.map(kw => 
              `<span class="engine-badge" style="background: rgba(139,92,246,0.15); border-color: rgba(139,92,246,0.3); color: var(--accent-light);"><i class="fa-solid fa-tag"></i> ${kw}</span>`
            ).join("");
          }
        }

        statusEl.className = "generator-status success";
        statusText.textContent = "Video generated successfully!";
        return;
      } else if (jobData.status === "failed") {
        finished = true;
        throw new Error(jobData.error || "Video rendering failed on the server.");
      } else {
        // Progress update
        if (jobData.progress_msg) {
          statusText.textContent = `${jobData.progress_step || ""} ${jobData.progress_msg}`;
        }
      }
    }

    if (!finished) {
      throw new Error("Video generation took too long. Please try again.");
    }
  } catch (err) {
    console.error(err);
    statusEl.className = "generator-status error";
    statusText.textContent = "Error: " + err.message;
    videoPlaceholder.querySelector("p").textContent = "Generation failed.";
  } finally {
    generateBtn.disabled = false;
  }
}

/* ============================================================
   FLOW 3: QWEN-IMAGE-2.1 STUDIO CONTROLLER (SELF-HOSTED GPU)
   ============================================================ */

const qwenStudioState = {
  mode: "text", // "text" or "product"
  aspectRatio: "1:1",
  stylePreset: "luxury_podium",
  steps: 35,
  seed: null,
  productFile: null,
  currentImageUrl: null,
  currentPrompt: "",
  history: []
};

function setQwenMode(mode) {
  qwenStudioState.mode = mode;
  const btnText = document.getElementById("btn_qwen_mode_text");
  const btnProduct = document.getElementById("btn_qwen_mode_product");
  const uploadPane = document.getElementById("qwen_product_upload_pane");
  const promptInput = document.getElementById("qwen_prompt");
  
  if (btnText) btnText.classList.toggle("active", mode === "text");
  if (btnProduct) btnProduct.classList.toggle("active", mode === "product");
  if (uploadPane) uploadPane.style.display = mode === "product" ? "block" : "none";
  
  if (promptInput && !promptInput.value.trim()) {
    if (mode === "product") {
      promptInput.placeholder = "Describe where to place your product: e.g. Place this luxury bottle on a sleek black marble pedestal with soft morning window light...";
    } else {
      promptInput.placeholder = "Describe the ad creative: product appearance, background setting, lighting, atmosphere, colors...";
    }
  }
}

function setQwenAspectRatio(ratio) {
  qwenStudioState.aspectRatio = ratio;
  document.querySelectorAll("#qwen_aspect_ratio_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.ratio === ratio);
  });
  
  const viewport = document.getElementById("qwen_stage_viewport");
  if (viewport) {
    viewport.classList.remove("ratio-9-16", "ratio-16-9", "ratio-1-1", "ratio-4-5");
    viewport.classList.add(`ratio-${ratio.replace(":", "-")}`);
  }
  updateQwenMetaBadges();
}

function setQwenSteps(steps) {
  qwenStudioState.steps = steps;
  document.querySelectorAll("#qwen_steps_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.steps) === steps);
  });
}

function setQwenPreset(presetKey) {
  qwenStudioState.stylePreset = presetKey;
  document.querySelectorAll("#qwen_presets_grid .preset-card-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.preset === presetKey);
  });
  updateQwenMetaBadges();
}

function updateQwenMetaBadges() {
  const resBadge = document.getElementById("qwen_player_res_badge");
  const presetBadge = document.getElementById("qwen_player_preset_badge");
  
  const ratioLabels = {
    "1:1": "1:1 Square · 1024x1024",
    "9:16": "9:16 Story · 1024x1792",
    "16:9": "16:9 Banner · 1792x1024",
    "4:5": "4:5 Portrait · 1024x1280"
  };
  if (resBadge) resBadge.textContent = ratioLabels[qwenStudioState.aspectRatio] || qwenStudioState.aspectRatio;
  
  const presetLabels = {
    "luxury_podium": "Luxury Podium",
    "ugc_lifestyle": "UGC Lifestyle",
    "neon_cyber": "Cyber Neon",
    "nature_botanical": "Botanical",
    "dramatic_splash": "Dynamic Splash",
    "minimal_dtc": "Minimal DTC"
  };
  if (presetBadge) presetBadge.textContent = presetLabels[qwenStudioState.stylePreset] || (qwenStudioState.stylePreset ? qwenStudioState.stylePreset : "Custom Style");
}

function appendQwenPromptBooster(phrase) {
  const textarea = document.getElementById("qwen_prompt");
  if (!textarea) return;
  const current = textarea.value.trim();
  if (!current) {
    textarea.value = phrase;
  } else {
    textarea.value = current.endsWith(",") ? `${current} ${phrase}` : `${current}, ${phrase}`;
  }
  textarea.focus();
}

function handleQwenProductUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  qwenStudioState.productFile = file;
  const preview = document.getElementById("qwen_product_preview");
  const emptyState = document.getElementById("qwen_dropzone_empty");
  const previewWrap = document.getElementById("qwen_dropzone_preview_wrap");
  
  if (preview) preview.src = URL.createObjectURL(file);
  if (emptyState) emptyState.style.display = "none";
  if (previewWrap) previewWrap.style.display = "flex";
}

function clearQwenProductImage() {
  qwenStudioState.productFile = null;
  const fileInput = document.getElementById("qwen_product_file");
  if (fileInput) fileInput.value = "";
  
  const preview = document.getElementById("qwen_product_preview");
  const emptyState = document.getElementById("qwen_dropzone_empty");
  const previewWrap = document.getElementById("qwen_dropzone_preview_wrap");
  
  if (preview) preview.src = "";
  if (emptyState) emptyState.style.display = "flex";
  if (previewWrap) previewWrap.style.display = "none";
}

function initQwenDragAndDrop() {
  const dropzone = document.getElementById("qwen_dropzone");
  if (!dropzone) return;
  
  ["dragenter", "dragover"].forEach(ev => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag-over"); });
  });
  ["dragleave", "drop"].forEach(ev => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag-over"); });
  });
  dropzone.addEventListener("drop", (e) => {
    const file = Array.from(e.dataTransfer.files).find(f => f.type.startsWith("image/"));
    if (file) handleQwenProductUpload({ target: { files: [file] } });
  });
}

let qwenElapsedInterval = null;

async function generateQwenImageAd() {
  const promptInput = document.getElementById("qwen_prompt");
  const negInput = document.getElementById("qwen_negative_prompt");
  const seedInput = document.getElementById("qwen_seed");
  const generateBtn = document.getElementById("qwen_generate_btn");
  
  const emptyState = document.getElementById("qwen_empty_state");
  const loadingOverlay = document.getElementById("qwen_loading_state");
  const imgDisplay = document.getElementById("qwen_ad_display");
  const actionsBar = document.getElementById("qwen_player_actions");
  const downloadBtn = document.getElementById("btn_download_qwen_ad");
  const loadingTitle = document.getElementById("qwen_loading_title");
  const loadingSub = document.getElementById("qwen_loading_sub");
  const progressBar = document.getElementById("qwen_progress_bar");
  const timerEl = document.getElementById("qwen_elapsed_timer");
  
  const prompt = promptInput ? promptInput.value.trim() : "";
  if (!prompt) {
    alert("Please enter a scene prompt or ad concept.");
    if (promptInput) promptInput.focus();
    return;
  }
  
  if (qwenStudioState.mode === "product" && !qwenStudioState.productFile) {
    alert("Please upload a tangible product image to remix or switch to 'Text-to-Ad'.");
    return;
  }
  
  const formData = new FormData();
  formData.append("prompt", prompt);
  formData.append("aspect_ratio", qwenStudioState.aspectRatio);
  formData.append("style_preset", qwenStudioState.stylePreset || "");
  formData.append("engine", "qwen");
  formData.append("steps", qwenStudioState.steps);
  
  if (seedInput && seedInput.value.trim()) {
    formData.append("seed", parseInt(seedInput.value.trim()));
  }
  if (negInput && negInput.value.trim()) {
    formData.append("negative_prompt", negInput.value.trim());
  }
  if (qwenStudioState.mode === "product" && qwenStudioState.productFile) {
    formData.append("product_image", qwenStudioState.productFile);
  }
  
  const apiKey = document.getElementById("api_key_input") ? document.getElementById("api_key_input").value.trim() : "";
  const imageKey = localStorage.getItem("self_hosted_image_key") || "";
  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  if (imageKey) headers["x-image-api-key"] = imageKey;
  
  if (emptyState) emptyState.style.display = "none";
  if (imgDisplay) imgDisplay.style.display = "none";
  if (actionsBar) actionsBar.style.display = "none";
  if (loadingOverlay) loadingOverlay.style.display = "flex";
  if (generateBtn) generateBtn.disabled = true;
  
  if (loadingTitle) loadingTitle.textContent = "Synthesizing with Qwen-Image-2.1";
  if (loadingSub) loadingSub.textContent = "Running diffusion steps on GCP GPU (approx 60-90s)...";
  
  let elapsed = 0;
  if (timerEl) timerEl.textContent = "0s elapsed";
  if (progressBar) progressBar.style.width = "5%";
  
  if (qwenElapsedInterval) clearInterval(qwenElapsedInterval);
  qwenElapsedInterval = setInterval(() => {
    elapsed++;
    if (timerEl) timerEl.textContent = `${elapsed}s elapsed`;
    if (progressBar) {
      const pct = Math.min(90, Math.floor(5 + (elapsed / 70) * 85));
      progressBar.style.width = `${pct}%`;
    }
  }, 1000);
  
  try {
    const res = await fetch("/api/image-studio/generate", {
      method: "POST",
      headers: headers,
      body: formData
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `Image generation failed with status ${res.status}`);
    }
    
    const data = await res.json();
    if (progressBar) progressBar.style.width = "100%";
    
    qwenStudioState.currentImageUrl = data.image_url;
    qwenStudioState.currentPrompt = prompt;
    
    if (imgDisplay) {
      imgDisplay.src = data.image_url;
      imgDisplay.style.display = "block";
    }
    if (downloadBtn) {
      downloadBtn.href = data.image_url;
      downloadBtn.download = data.filename || "qwen_image_ad.png";
    }
    if (actionsBar) actionsBar.style.display = "flex";
    
    qwenStudioState.history.unshift(data);
    renderQwenHistory();
    
  } catch (err) {
    console.error("Qwen image generation failed:", err);
    alert(`Qwen generation failed:\n${err.message}`);
    if (emptyState) emptyState.style.display = "flex";
  } finally {
    if (qwenElapsedInterval) clearInterval(qwenElapsedInterval);
    if (loadingOverlay) loadingOverlay.style.display = "none";
    if (generateBtn) generateBtn.disabled = false;
  }
}

async function animateQwenImageAd() {
  if (!qwenStudioState.currentImageUrl) return;
  const imgUrl = qwenStudioState.currentImageUrl;
  const prompt = qwenStudioState.currentPrompt;
  
  switchMainView("minimax");
  setMinimaxMode("fl2va_single");
  
  try {
    const res = await fetch(imgUrl);
    const blob = await res.blob();
    const file = new File([blob], "qwen_ad_start_frame.png", { type: blob.type || "image/png" });
    minimaxState.singleFrame = file;
    
    const preview = document.getElementById("preview_mm_single_frame");
    const emptyState = document.getElementById("body_mm_single");
    const clearBtn = document.getElementById("clear_mm_single_btn");
    if (preview) { preview.src = imgUrl; preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "inline-flex";
  } catch (e) {
    console.warn("Could not set image as start frame blob:", e);
  }
  
  const promptInput = document.getElementById("minimax_prompt");
  if (promptInput) {
    promptInput.value = prompt 
      ? `Cinematic commercial animation starting from this scene: ${prompt}` 
      : "Cinematic commercial animation, smooth camera motion revealing the product with dynamic lighting and synchronized stereo ambiance";
  }
}

async function loadQwenHistory() {
  try {
    const res = await fetch("/api/image-studio/history?engine=qwen");
    if (res.ok) {
      const data = await res.json();
      if (data.images && data.images.length > 0) {
        const existingUrls = new Set(qwenStudioState.history.map(h => h.image_url));
        data.images.forEach(img => {
          if (!existingUrls.has(img.url)) {
            qwenStudioState.history.push({
              image_url: img.url,
              filename: img.filename,
              aspect_ratio: "1:1",
              model_used: "Qwen-Image-2.1"
            });
          }
        });
        renderQwenHistory();
      }
    }
  } catch (e) {
    console.warn("Failed to load Qwen history:", e);
  }
}

function renderQwenHistory() {
  const reel = document.getElementById("qwen_history_reel");
  const countEl = document.getElementById("qwen_history_count");
  if (!reel) return;
  
  if (qwenStudioState.history.length === 0) {
    reel.innerHTML = '<div class="history-empty" id="qwen_history_empty_msg">Qwen image ads in this session will appear here for instant preview, download, and video animation.</div>';
    if (countEl) countEl.textContent = "0 images";
    return;
  }
  
  if (countEl) countEl.textContent = `${qwenStudioState.history.length} image${qwenStudioState.history.length > 1 ? "s" : ""}`;
  
  reel.innerHTML = qwenStudioState.history.map((item, idx) => `
    <div class="history-item image-ad-item ${item.image_url === qwenStudioState.currentImageUrl ? 'active' : ''}" onclick="selectQwenHistoryItem(${idx})">
      <img src="${item.image_url}" alt="Qwen ad ${idx + 1}" loading="lazy">
      <span class="history-item-badge">#${idx + 1}</span>
    </div>
  `).join('');
}

function selectQwenHistoryItem(index) {
  const item = qwenStudioState.history[index];
  if (!item) return;
  
  qwenStudioState.currentImageUrl = item.image_url;
  qwenStudioState.currentPrompt = item.prompt || "";
  
  const emptyState = document.getElementById("qwen_empty_state");
  const imgDisplay = document.getElementById("qwen_ad_display");
  const actionsBar = document.getElementById("qwen_player_actions");
  const downloadBtn = document.getElementById("btn_download_qwen_ad");
  
  if (emptyState) emptyState.style.display = "none";
  if (imgDisplay) {
    imgDisplay.src = item.image_url;
    imgDisplay.style.display = "block";
  }
  if (downloadBtn) {
    downloadBtn.href = item.image_url;
    downloadBtn.download = item.filename || "qwen_image_ad.png";
  }
  if (actionsBar) actionsBar.style.display = "flex";
  
  renderQwenHistory();
}

/* ============================================================
   FLOW 4: GEMINI NANO BANANA PRO STUDIO CONTROLLER
   ============================================================ */

const bananaStudioState = {
  mode: "text", // "text" or "product"
  aspectRatio: "1:1",
  stylePreset: "luxury_podium",
  productFile: null,
  currentImageUrl: null,
  currentPrompt: "",
  history: []
};

function setBananaMode(mode) {
  bananaStudioState.mode = mode;
  const btnText = document.getElementById("btn_banana_mode_text");
  const btnProduct = document.getElementById("btn_banana_mode_product");
  const uploadPane = document.getElementById("banana_product_upload_pane");
  const promptInput = document.getElementById("banana_prompt");
  
  if (btnText) btnText.classList.toggle("active", mode === "text");
  if (btnProduct) btnProduct.classList.toggle("active", mode === "product");
  if (uploadPane) uploadPane.style.display = mode === "product" ? "block" : "none";
  
  if (promptInput && !promptInput.value.trim()) {
    if (mode === "product") {
      promptInput.placeholder = "Describe how to feature your product with Gemini multimodal consistency...";
    } else {
      promptInput.placeholder = "Describe the ad creative: product appearance, background setting, lighting, atmosphere, colors...";
    }
  }
}

function setBananaAspectRatio(ratio) {
  bananaStudioState.aspectRatio = ratio;
  document.querySelectorAll("#banana_aspect_ratio_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.ratio === ratio);
  });
  
  const viewport = document.getElementById("banana_stage_viewport");
  if (viewport) {
    viewport.classList.remove("ratio-9-16", "ratio-16-9", "ratio-1-1", "ratio-4-5");
    viewport.classList.add(`ratio-${ratio.replace(":", "-")}`);
  }
  updateBananaMetaBadges();
}

function setBananaPreset(presetKey) {
  bananaStudioState.stylePreset = presetKey;
  document.querySelectorAll("#banana_presets_grid .preset-card-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.preset === presetKey);
  });
  updateBananaMetaBadges();
}

function updateBananaMetaBadges() {
  const resBadge = document.getElementById("banana_player_res_badge");
  const presetBadge = document.getElementById("banana_player_preset_badge");
  
  const ratioLabels = {
    "1:1": "1:1 Square",
    "9:16": "9:16 Story",
    "16:9": "16:9 Banner",
    "4:5": "4:5 Portrait"
  };
  if (resBadge) resBadge.textContent = ratioLabels[bananaStudioState.aspectRatio] || bananaStudioState.aspectRatio;
  
  const presetLabels = {
    "luxury_podium": "Luxury Podium",
    "ugc_lifestyle": "UGC Lifestyle",
    "neon_cyber": "Cyber Neon",
    "nature_botanical": "Botanical",
    "dramatic_splash": "Dynamic Splash",
    "minimal_dtc": "Minimal DTC"
  };
  if (presetBadge) presetBadge.textContent = presetLabels[bananaStudioState.stylePreset] || (bananaStudioState.stylePreset ? bananaStudioState.stylePreset : "Custom Style");
}

function appendBananaPromptBooster(phrase) {
  const textarea = document.getElementById("banana_prompt");
  if (!textarea) return;
  const current = textarea.value.trim();
  if (!current) {
    textarea.value = phrase;
  } else {
    textarea.value = current.endsWith(",") ? `${current} ${phrase}` : `${current}, ${phrase}`;
  }
  textarea.focus();
}

function handleBananaProductUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  bananaStudioState.productFile = file;
  const preview = document.getElementById("banana_product_preview");
  const emptyState = document.getElementById("banana_dropzone_empty");
  const previewWrap = document.getElementById("banana_dropzone_preview_wrap");
  
  if (preview) preview.src = URL.createObjectURL(file);
  if (emptyState) emptyState.style.display = "none";
  if (previewWrap) previewWrap.style.display = "flex";
}

function clearBananaProductImage() {
  bananaStudioState.productFile = null;
  const fileInput = document.getElementById("banana_product_file");
  if (fileInput) fileInput.value = "";
  
  const preview = document.getElementById("banana_product_preview");
  const emptyState = document.getElementById("banana_dropzone_empty");
  const previewWrap = document.getElementById("banana_dropzone_preview_wrap");
  
  if (preview) preview.src = "";
  if (emptyState) emptyState.style.display = "flex";
  if (previewWrap) previewWrap.style.display = "none";
}

function initBananaDragAndDrop() {
  const dropzone = document.getElementById("banana_dropzone");
  if (!dropzone) return;
  
  ["dragenter", "dragover"].forEach(ev => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag-over"); });
  });
  ["dragleave", "drop"].forEach(ev => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag-over"); });
  });
  dropzone.addEventListener("drop", (e) => {
    const file = Array.from(e.dataTransfer.files).find(f => f.type.startsWith("image/"));
    if (file) handleBananaProductUpload({ target: { files: [file] } });
  });
}

let bananaElapsedInterval = null;

async function generateBananaImageAd() {
  const promptInput = document.getElementById("banana_prompt");
  const negInput = document.getElementById("banana_negative_prompt");
  const generateBtn = document.getElementById("banana_generate_btn");
  
  const emptyState = document.getElementById("banana_empty_state");
  const loadingOverlay = document.getElementById("banana_loading_state");
  const imgDisplay = document.getElementById("banana_ad_display");
  const actionsBar = document.getElementById("banana_player_actions");
  const downloadBtn = document.getElementById("btn_download_banana_ad");
  const loadingTitle = document.getElementById("banana_loading_title");
  const loadingSub = document.getElementById("banana_loading_sub");
  const progressBar = document.getElementById("banana_progress_bar");
  const timerEl = document.getElementById("banana_elapsed_timer");
  
  const prompt = promptInput ? promptInput.value.trim() : "";
  if (!prompt) {
    alert("Please enter a scene prompt or ad concept.");
    if (promptInput) promptInput.focus();
    return;
  }
  
  if (bananaStudioState.mode === "product" && !bananaStudioState.productFile) {
    alert("Please upload a product consistency reference image or switch to 'Text-to-Ad'.");
    return;
  }
  
  const formData = new FormData();
  formData.append("prompt", prompt);
  formData.append("aspect_ratio", bananaStudioState.aspectRatio);
  formData.append("style_preset", bananaStudioState.stylePreset || "");
  formData.append("engine", "banana");
  
  if (negInput && negInput.value.trim()) {
    formData.append("negative_prompt", negInput.value.trim());
  }
  if (bananaStudioState.mode === "product" && bananaStudioState.productFile) {
    formData.append("product_image", bananaStudioState.productFile);
  }
  
  const apiKey = document.getElementById("api_key_input") ? document.getElementById("api_key_input").value.trim() : "";
  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  
  if (emptyState) emptyState.style.display = "none";
  if (imgDisplay) imgDisplay.style.display = "none";
  if (actionsBar) actionsBar.style.display = "none";
  if (loadingOverlay) loadingOverlay.style.display = "flex";
  if (generateBtn) generateBtn.disabled = true;
  
  if (loadingTitle) loadingTitle.textContent = "Synthesizing with Nano Banana Pro";
  if (loadingSub) loadingSub.textContent = "Rendering with Gemini multimodal vision...";
  
  let elapsed = 0;
  if (timerEl) timerEl.textContent = "0s elapsed";
  if (progressBar) progressBar.style.width = "10%";
  
  if (bananaElapsedInterval) clearInterval(bananaElapsedInterval);
  bananaElapsedInterval = setInterval(() => {
    elapsed++;
    if (timerEl) timerEl.textContent = `${elapsed}s elapsed`;
    if (progressBar) {
      const pct = Math.min(92, Math.floor(10 + (elapsed / 25) * 80));
      progressBar.style.width = `${pct}%`;
    }
  }, 1000);
  
  try {
    const res = await fetch("/api/image-studio/generate", {
      method: "POST",
      headers: headers,
      body: formData
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      throw new Error(err.detail || `Nano Banana Pro failed with status ${res.status}`);
    }
    
    const data = await res.json();
    if (progressBar) progressBar.style.width = "100%";
    
    bananaStudioState.currentImageUrl = data.image_url;
    bananaStudioState.currentPrompt = prompt;
    
    if (imgDisplay) {
      imgDisplay.src = data.image_url;
      imgDisplay.style.display = "block";
    }
    if (downloadBtn) {
      downloadBtn.href = data.image_url;
      downloadBtn.download = data.filename || "banana_image_ad.png";
    }
    if (actionsBar) actionsBar.style.display = "flex";
    
    bananaStudioState.history.unshift(data);
    renderBananaHistory();
    
  } catch (err) {
    console.error("Banana Pro image generation failed:", err);
    alert(`Nano Banana Pro generation failed:\n${err.message}`);
    if (emptyState) emptyState.style.display = "flex";
  } finally {
    if (bananaElapsedInterval) clearInterval(bananaElapsedInterval);
    if (loadingOverlay) loadingOverlay.style.display = "none";
    if (generateBtn) generateBtn.disabled = false;
  }
}

async function animateBananaImageAd() {
  if (!bananaStudioState.currentImageUrl) return;
  const imgUrl = bananaStudioState.currentImageUrl;
  const prompt = bananaStudioState.currentPrompt;
  
  switchMainView("omniflash");
  setOmniMode("first_last_frame");
  
  try {
    const res = await fetch(imgUrl);
    const blob = await res.blob();
    const file = new File([blob], "banana_ad_start_frame.png", { type: blob.type || "image/png" });
    omniState.firstFrame = file;
    
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("keyframe_body_first");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    if (preview) { preview.src = imgUrl; preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "flex";
  } catch (e) {
    console.warn("Could not set banana image as first frame blob:", e);
  }
  
  const promptInput = document.getElementById("studio_prompt");
  if (promptInput) {
    promptInput.value = prompt 
      ? `Cinematic smooth video motion starting from this ad scene: ${prompt}` 
      : "Cinematic commercial animation, fluid motion with rich lighting and atmosphere";
  }
}

async function loadBananaHistory() {
  try {
    const res = await fetch("/api/image-studio/history?engine=banana");
    if (res.ok) {
      const data = await res.json();
      if (data.images && data.images.length > 0) {
        const existingUrls = new Set(bananaStudioState.history.map(h => h.image_url));
        data.images.forEach(img => {
          if (!existingUrls.has(img.url)) {
            bananaStudioState.history.push({
              image_url: img.url,
              filename: img.filename,
              aspect_ratio: "1:1",
              model_used: "nano-banana-pro-preview"
            });
          }
        });
        renderBananaHistory();
      }
    }
  } catch (e) {
    console.warn("Failed to load Banana Pro history:", e);
  }
}

function renderBananaHistory() {
  const reel = document.getElementById("banana_history_reel");
  const countEl = document.getElementById("banana_history_count");
  if (!reel) return;
  
  if (bananaStudioState.history.length === 0) {
    reel.innerHTML = '<div class="history-empty" id="banana_history_empty_msg">Nano Banana image ads in this session will appear here for instant preview, download, and video animation.</div>';
    if (countEl) countEl.textContent = "0 images";
    return;
  }
  
  if (countEl) countEl.textContent = `${bananaStudioState.history.length} image${bananaStudioState.history.length > 1 ? "s" : ""}`;
  
  reel.innerHTML = bananaStudioState.history.map((item, idx) => `
    <div class="history-item image-ad-item ${item.image_url === bananaStudioState.currentImageUrl ? 'active' : ''}" onclick="selectBananaHistoryItem(${idx})">
      <img src="${item.image_url}" alt="Banana ad ${idx + 1}" loading="lazy">
      <span class="history-item-badge">#${idx + 1}</span>
    </div>
  `).join('');
}

function selectBananaHistoryItem(index) {
  const item = bananaStudioState.history[index];
  if (!item) return;
  
  bananaStudioState.currentImageUrl = item.image_url;
  bananaStudioState.currentPrompt = item.prompt || "";
  
  const emptyState = document.getElementById("banana_empty_state");
  const imgDisplay = document.getElementById("banana_ad_display");
  const actionsBar = document.getElementById("banana_player_actions");
  const downloadBtn = document.getElementById("btn_download_banana_ad");
  
  if (emptyState) emptyState.style.display = "none";
  if (imgDisplay) {
    imgDisplay.src = item.image_url;
    imgDisplay.style.display = "block";
  }
  if (downloadBtn) {
    downloadBtn.href = item.image_url;
    downloadBtn.download = item.filename || "banana_image_ad.png";
  }
  if (actionsBar) actionsBar.style.display = "flex";
  
  renderBananaHistory();
}

// Backward-compatibility aliases
const imageStudioState = qwenStudioState;
const setImageStudioMode = setQwenMode;
const setImageStudioAspectRatio = setQwenAspectRatio;
const setImageStudioSteps = setQwenSteps;
const setImageStudioPreset = setQwenPreset;
const appendImagePromptBooster = appendQwenPromptBooster;
const handleProductImageUpload = handleQwenProductUpload;
const clearProductImage = clearQwenProductImage;
const initImageStudioDragAndDrop = initQwenDragAndDrop;
const generateImageAd = generateQwenImageAd;
const animateCurrentImageAd = animateQwenImageAd;
const loadImageStudioHistory = loadQwenHistory;
const renderImageStudioHistory = renderQwenHistory;
const selectHistoryImageAd = selectQwenHistoryItem;
function setImageStudioEngine() {}

/* ============================================================
   FLOW 4: META IMAGE AD CREATIVE STUDIO (Instagram & Facebook)
   ============================================================ */

const metaAdState = {
  aspectRatio: "4:5",
  engine: "qwen",
  selectedAngleIndex: 0,
  selectedProductPath: null,
  customProductFile: null,
  platform: "ig",
  currentAd: null,
  history: []
};

function initMetaAdStudio() {
  const data = state.campaignData;
  if (!data) return;

  // 1. Audience Pill
  const audPill = document.getElementById("meta_pill_audience_text");
  if (audPill) {
    const rawAud = data.target_audience_persona || "Analyzed Audience";
    const shortAud = rawAud.length > 55 ? rawAud.slice(0, 52) + "..." : rawAud;
    audPill.textContent = shortAud;
    audPill.title = rawAud;
  }

  // 2. Populate Angles from Campaign Ad Groups
  const angleSelect = document.getElementById("meta_angle_select");
  if (angleSelect) {
    angleSelect.innerHTML = "";
    if (data.ad_groups && data.ad_groups.length > 0) {
      data.ad_groups.forEach((ag, idx) => {
        const opt = document.createElement("option");
        opt.value = idx;
        opt.textContent = `Angle ${idx + 1}: ${ag.name} — "${ag.angle}"`;
        angleSelect.appendChild(opt);
      });
      angleSelect.value = "0";
      metaAdState.selectedAngleIndex = 0;
      updateMetaAngleHint(0);
    }
  }

  // 3. Populate Product Photo Picker
  renderMetaProductPicker();

  // 4. Default Mockup Text & Info
  const brandName = data.brand_name || "Brand Name";
  const previewBrand = document.getElementById("meta_preview_brand");
  const previewAvatar = document.getElementById("meta_preview_avatar");
  const previewDomain = document.getElementById("meta_preview_domain");
  const previewHeadline = document.getElementById("meta_preview_headline");
  const previewPrimary = document.getElementById("meta_preview_primary_text");

  if (previewBrand) previewBrand.textContent = brandName;
  if (previewAvatar) previewAvatar.textContent = brandName.charAt(0).toUpperCase() || "B";
  if (previewDomain) previewDomain.textContent = `WWW.${brandName.toUpperCase().replace(/[^A-Z0-9]/g, "") || "BRAND"}.COM`;
  if (previewHeadline) previewHeadline.textContent = `Elevate Your Routine · ${data.product_name || "Shop Now"}`;
  if (previewPrimary && !metaAdState.currentAd) {
    previewPrimary.textContent = `Click "Generate Meta Creative & Ad Copy" to produce high-converting copy and photorealistic imagery tailored for ${data.target_audience_persona ? data.target_audience_persona.split(".")[0] : "your target audience"}.`;
  }

  // 5. Load past meta ads history
  loadMetaAdsHistory();
}

function updateMetaAngleHint(index) {
  const data = state.campaignData;
  const hintEl = document.getElementById("meta_angle_hint");
  if (!hintEl || !data || !data.ad_groups || !data.ad_groups[index]) return;
  const ag = data.ad_groups[index];
  hintEl.innerHTML = `<strong>Focus:</strong> ${escapeHtml(ag.angle || "")} · <em>Target Emotion: ${escapeHtml(ag.target_emotion || "Desire & Urgency")}</em>`;
}

function onMetaAngleChange() {
  const sel = document.getElementById("meta_angle_select");
  if (!sel) return;
  const idx = parseInt(sel.value, 10);
  metaAdState.selectedAngleIndex = idx;
  updateMetaAngleHint(idx);
}

function renderMetaProductPicker() {
  const picker = document.getElementById("meta_product_picker");
  const badge = document.getElementById("meta_product_count_badge");
  if (!picker) return;

  picker.innerHTML = "";
  const paths = (state.campaignData && state.campaignData.product_image_paths) || [];

  if (paths.length === 0 && !metaAdState.customProductFile) {
    picker.innerHTML = `
      <div class="meta-picker-empty" id="meta_picker_empty">
        <i class="fa-regular fa-image"></i>
        <span>No product photos attached yet. Upload one below or generate creative without reference.</span>
      </div>
    `;
    if (badge) badge.textContent = "0 photos attached";
    metaAdState.selectedProductPath = null;
    return;
  }

  const totalCount = paths.length + (metaAdState.customProductFile ? 1 : 0);
  if (badge) badge.textContent = `${totalCount} photo${totalCount > 1 ? "s" : ""} available`;

  // Render campaign uploaded photos
  paths.forEach((p, idx) => {
    const isSelected = !metaAdState.customProductFile && (metaAdState.selectedProductPath === p || (!metaAdState.selectedProductPath && idx === 0));
    const thumb = document.createElement("div");
    thumb.className = `meta-product-thumb ${isSelected ? "active" : ""}`;
    thumb.title = `Product Photo #${idx + 1}`;
    thumb.innerHTML = `<img src="${p}" alt="Product ${idx + 1}" />`;
    thumb.onclick = () => {
      metaAdState.selectedProductPath = p;
      metaAdState.customProductFile = null;
      document.querySelectorAll(".meta-product-thumb").forEach(t => t.classList.remove("active"));
      thumb.classList.add("active");
      const note = document.getElementById("meta_custom_product_note");
      if (note) note.textContent = `Using product photo #${idx + 1}`;
    };
    picker.appendChild(thumb);
    if (!metaAdState.selectedProductPath && idx === 0 && !metaAdState.customProductFile) {
      metaAdState.selectedProductPath = p;
    }
  });

  // Render custom uploaded photo if present
  if (metaAdState.customProductFile) {
    const thumb = document.createElement("div");
    thumb.className = "meta-product-thumb active";
    thumb.title = "Custom Uploaded Photo";
    const objUrl = URL.createObjectURL(metaAdState.customProductFile);
    thumb.innerHTML = `<img src="${objUrl}" alt="Custom Upload" />`;
    thumb.onclick = () => {
      metaAdState.selectedProductPath = null;
      document.querySelectorAll(".meta-product-thumb").forEach(t => t.classList.remove("active"));
      thumb.classList.add("active");
    };
    picker.appendChild(thumb);
  }
}

function handleMetaCustomProductUpload(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  metaAdState.customProductFile = file;
  metaAdState.selectedProductPath = null;
  const note = document.getElementById("meta_custom_product_note");
  if (note) note.textContent = `Custom: ${file.name}`;
  renderMetaProductPicker();
}

function setMetaRatio(ratio) {
  metaAdState.aspectRatio = ratio;
  document.querySelectorAll("#meta_ratio_group .meta-pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.ratio === ratio);
  });
  const frame = document.getElementById("meta_media_frame");
  if (frame) {
    frame.classList.remove("ratio-1-1", "ratio-4-5", "ratio-9-16");
    frame.classList.add(`ratio-${ratio.replace(":", "-")}`);
  }
}

function setMetaEngine(engine) {
  metaAdState.engine = engine;
  document.querySelectorAll("#meta_engine_group .meta-pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.engine === engine);
  });
}

function setMockupPlatform(plat) {
  metaAdState.platform = plat;
  const igTab = document.getElementById("tab_mockup_ig");
  const fbTab = document.getElementById("tab_mockup_fb");
  if (igTab) igTab.classList.toggle("active", plat === "ig");
  if (fbTab) fbTab.classList.toggle("active", plat === "fb");
}

async function generateMetaCreative() {
  const data = state.campaignData;
  if (!data) {
    alert("Please enter a Brand URL and analyze the campaign first.");
    return;
  }

  const btn = document.getElementById("btn_generate_meta_ad");
  const mediaLoader = document.getElementById("meta_media_loader");
  const mediaPlaceholder = document.getElementById("meta_media_placeholder");
  const previewImg = document.getElementById("meta_preview_image");
  const loaderStatus = document.getElementById("meta_loader_status");

  // Get active ad group angle
  let angleName = "Problem-Solution";
  let angleDesc = "";
  if (data.ad_groups && data.ad_groups[metaAdState.selectedAngleIndex]) {
    const ag = data.ad_groups[metaAdState.selectedAngleIndex];
    angleName = ag.name || "Angle";
    angleDesc = ag.angle || "";
  }

  const customDirective = (document.getElementById("meta_custom_directive") ? document.getElementById("meta_custom_directive").value.trim() : "");
  const apiKey = document.getElementById("api_key_input").value;
  const imageKey = localStorage.getItem("self_hosted_image_key") || "";

  // Prepare FormData
  const formData = new FormData();
  formData.append("brand_name", data.brand_name || "");
  formData.append("product_name", data.product_name || "");
  formData.append("product_category", data.product_category || "");
  formData.append("target_audience_persona", data.target_audience_persona || "");
  formData.append("visual_style", data.visual_style || "");
  formData.append("product_visual_description", data.product_visual_description || "");
  formData.append("angle_name", angleName);
  formData.append("angle_description", angleDesc);
  formData.append("aspect_ratio", metaAdState.aspectRatio);
  formData.append("engine", metaAdState.engine);
  if (customDirective) formData.append("custom_directive", customDirective);

  // Attach product photo
  if (metaAdState.customProductFile) {
    formData.append("product_image", metaAdState.customProductFile);
  } else if (metaAdState.selectedProductPath) {
    formData.append("product_image_path", metaAdState.selectedProductPath);
  }

  // Show UI loading
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;margin-right:8px;"></div> Synthesizing Meta Creative...';
  }
  if (mediaPlaceholder) mediaPlaceholder.style.display = "none";
  if (previewImg) previewImg.style.display = "none";
  if (mediaLoader) mediaLoader.style.display = "flex";
  if (loaderStatus) {
    loaderStatus.textContent = metaAdState.engine === "qwen" 
      ? "Synthesizing with Qwen-Image-2.1 on GPU..."
      : "Synthesizing with Gemini Nano Banana Pro...";
  }

  // Progress update interval
  let elapsed = 0;
  const timer = setInterval(() => {
    elapsed += 5;
    if (loaderStatus) {
      if (metaAdState.engine === "qwen") {
        loaderStatus.textContent = `Synthesizing creative on GCP GPU (${elapsed}s elapsed)...`;
      } else {
        loaderStatus.textContent = `Synthesizing creative & Meta copy (${elapsed}s elapsed)...`;
      }
    }
  }, 5000);

  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  if (imageKey) headers["x-image-api-key"] = imageKey;

  try {
    const res = await fetch("/api/campaign/generate-meta-ad", {
      method: "POST",
      headers: headers,
      body: formData
    });

    if (!res.ok) {
      let msg = "Generation failed";
      try {
        const err = await res.json();
        if (err.detail) msg = err.detail;
      } catch (e) {}
      throw new Error(msg);
    }

    const result = await res.json();
    metaAdState.currentAd = result;
    metaAdState.history.unshift(result);

    // Update Live Mockup & Gallery
    applyMetaAdToMockup(result);
    renderMetaGallery();

  } catch (err) {
    console.error("Meta ad generation error:", err);
    alert("Meta Creative Generation failed: " + err.message);
    if (!metaAdState.currentAd && mediaPlaceholder) {
      mediaPlaceholder.style.display = "flex";
    }
  } finally {
    clearInterval(timer);
    if (mediaLoader) mediaLoader.style.display = "none";
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-brands fa-meta"></i> Generate Meta Creative &amp; Ad Copy';
    }
  }
}

function applyMetaAdToMockup(ad) {
  if (!ad) return;

  const previewImg = document.getElementById("meta_preview_image");
  const mediaPlaceholder = document.getElementById("meta_media_placeholder");
  const primaryText = document.getElementById("meta_preview_primary_text");
  const headline = document.getElementById("meta_preview_headline");
  const ctaBtn = document.getElementById("meta_preview_cta");
  const brandTitle = document.getElementById("meta_preview_brand");
  const avatar = document.getElementById("meta_preview_avatar");
  const domain = document.getElementById("meta_preview_domain");

  if (previewImg) {
    previewImg.src = ad.image_url;
    previewImg.style.display = "block";
  }
  if (mediaPlaceholder) mediaPlaceholder.style.display = "none";

  if (primaryText) primaryText.textContent = ad.primary_text || "";
  if (headline) headline.textContent = ad.headline || "";
  if (ctaBtn) ctaBtn.textContent = ad.cta || "Shop Now";
  if (brandTitle && ad.brand_name) brandTitle.textContent = ad.brand_name;
  if (avatar && ad.brand_name) avatar.textContent = ad.brand_name.charAt(0).toUpperCase() || "B";
  if (domain && ad.brand_name) domain.textContent = `WWW.${ad.brand_name.toUpperCase().replace(/[^A-Z0-9]/g, "")}.COM`;

  if (ad.aspect_ratio) {
    setMetaRatio(ad.aspect_ratio);
  }
}

function copyCurrentMetaCopy() {
  const ad = metaAdState.currentAd;
  let textToCopy = "";
  if (ad) {
    textToCopy = `${ad.primary_text}\n\nHeadline: ${ad.headline}\nCTA Button: ${ad.cta}`;
  } else {
    const primary = document.getElementById("meta_preview_primary_text") ? document.getElementById("meta_preview_primary_text").textContent : "";
    const headline = document.getElementById("meta_preview_headline") ? document.getElementById("meta_preview_headline").textContent : "";
    const cta = document.getElementById("meta_preview_cta") ? document.getElementById("meta_preview_cta").textContent : "Shop Now";
    textToCopy = `${primary}\n\nHeadline: ${headline}\nCTA Button: ${cta}`;
  }

  navigator.clipboard.writeText(textToCopy).then(() => {
    alert("Meta Ad Copy copied to clipboard!\n\nReady to paste directly into Meta Ads Manager.");
  }).catch(() => {
    prompt("Copy ad copy:", textToCopy);
  });
}

function downloadCurrentMetaImage() {
  const ad = metaAdState.currentAd;
  if (!ad || !ad.image_url) {
    alert("Please generate a creative first.");
    return;
  }
  const link = document.createElement("a");
  link.href = ad.image_url;
  link.download = ad.filename || `meta_ad_${Date.now()}.png`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function bridgeToMiniMaxFromMeta() {
  const ad = metaAdState.currentAd;
  if (!ad || !ad.image_url) {
    alert("Please generate a creative first before animating.");
    return;
  }

  // Switch to MiniMax Video Studio
  switchMainView("minimax");
  setMinimaxMode("fl2va_single");

  // Pre-fill prompt
  const mmPrompt = document.getElementById("minimax_prompt");
  if (mmPrompt) {
    mmPrompt.value = `Cinematic video commercial starting from this ad scene: ${ad.visual_prompt || ad.headline || "Smooth dynamic camera motion showcasing product"}`;
  }

  // Fetch image and set as single frame
  fetch(ad.image_url)
    .then(res => res.blob())
    .then(blob => {
      const file = new File([blob], ad.filename || "meta_creative.png", { type: blob.type || "image/png" });
      minimaxState.singleFrame = file;
      const preview = document.getElementById("preview_mm_single_frame");
      const emptyState = document.getElementById("body_mm_single");
      const clearBtn = document.getElementById("clear_mm_single_btn");
      if (preview) { preview.src = ad.image_url; preview.style.display = "block"; }
      if (emptyState) emptyState.style.display = "none";
      if (clearBtn) clearBtn.style.display = "inline-flex";
    })
    .catch(err => console.warn("Failed to bridge image to MiniMax:", err));
}

function bridgeToOmniFromMeta() {
  const ad = metaAdState.currentAd;
  if (!ad || !ad.image_url) {
    alert("Please generate a creative first before animating.");
    return;
  }

  // Switch to Omni Flash Video Studio
  switchMainView("omniflash");
  setOmniMode("first_last_frame");

  // Pre-fill prompt
  const omniPrompt = document.getElementById("studio_prompt");
  if (omniPrompt) {
    omniPrompt.value = `Cinematic video ad motion starting from this creative: ${ad.visual_prompt || ad.headline || "Fluid motion with atmospheric lighting"}`;
  }

  // Fetch image and set as first frame
  fetch(ad.image_url)
    .then(res => res.blob())
    .then(blob => {
      const file = new File([blob], ad.filename || "meta_creative.png", { type: blob.type || "image/png" });
      omniState.firstFrame = file;
      const preview = document.getElementById("preview_first_frame");
      const emptyState = document.getElementById("keyframe_body_first");
      const clearBtn = document.getElementById("clear_first_frame_btn");
      if (preview) { preview.src = ad.image_url; preview.style.display = "block"; }
      if (emptyState) emptyState.style.display = "none";
      if (clearBtn) clearBtn.style.display = "flex";
    })
    .catch(err => console.warn("Failed to bridge image to Omni Flash:", err));
}

function createMetaAdForScript(videoIndex, engine) {
  const ag = state.campaignData && state.campaignData.ad_groups[state.selectedAdGroupIndex];
  if (!ag) return;
  const video = ag.videos[videoIndex];

  // Set chosen image engine if provided
  if (engine) {
    setMetaEngine(engine);
  }

  // Ensure campaign view is showing image studio
  setCampaignViewFilter("all");

  // Set angle selector
  const angleSel = document.getElementById("meta_angle_select");
  if (angleSel) {
    angleSel.value = String(state.selectedAdGroupIndex);
    onMetaAngleChange();
  }

  // Pre-fill directive with video hook and visual directions
  const directiveInput = document.getElementById("meta_custom_directive");
  if (directiveInput && video) {
    directiveInput.value = `${video.hook_line}. Style: ${video.visual_directions.slice(0, 100)}`;
  }

  // Scroll to Meta Ad Studio card and add attention glow
  const metaCard = document.getElementById("meta_ad_studio_card");
  if (metaCard) {
    metaCard.style.display = "block";
    metaCard.scrollIntoView({ behavior: "smooth" });
    metaCard.classList.add("card-highlight-pulse");
    setTimeout(() => metaCard.classList.remove("card-highlight-pulse"), 2500);
  }
}

function createMetaAdFromStudio() {
  const vIdx = state.selectedVideoIndex || 0;
  const engine = state.storyboardEngine || "banana";
  closeStudio();
  createMetaAdForScript(vIdx, engine);
}

function setCampaignViewFilter(filter) {
  const metaCard = document.getElementById("meta_ad_studio_card");
  const adGroupsCard = document.querySelector(".ad-groups-card");
  const brandDnaCard = document.querySelector(".brand-dna-card");

  document.querySelectorAll("#campaign_view_pills .format-pill").forEach(p => {
    p.classList.toggle("active", p.dataset.filter === filter);
  });

  if (filter === "image_ads") {
    if (brandDnaCard) brandDnaCard.style.display = "block";
    if (metaCard) {
      metaCard.style.display = "block";
      metaCard.scrollIntoView({ behavior: "smooth" });
    }
    if (adGroupsCard) adGroupsCard.style.display = "none";
  } else if (filter === "video_ads") {
    if (brandDnaCard) brandDnaCard.style.display = "block";
    if (metaCard) metaCard.style.display = "none";
    if (adGroupsCard) {
      adGroupsCard.style.display = "block";
      adGroupsCard.scrollIntoView({ behavior: "smooth" });
    }
  } else { // 'all'
    if (brandDnaCard) brandDnaCard.style.display = "block";
    if (metaCard) metaCard.style.display = "block";
    if (adGroupsCard) adGroupsCard.style.display = "block";
  }
}

function scrollToMetaImageStudio() {
  setCampaignViewFilter("all");
  const metaCard = document.getElementById("meta_ad_studio_card");
  if (metaCard) {
    metaCard.scrollIntoView({ behavior: "smooth" });
    metaCard.classList.add("card-highlight-pulse");
    setTimeout(() => metaCard.classList.remove("card-highlight-pulse"), 2500);
  }
}

function renderMetaGallery() {
  const section = document.getElementById("meta_gallery_section");
  const grid = document.getElementById("meta_gallery_grid");
  const countBadge = document.getElementById("meta_gallery_count");
  if (!section || !grid) return;

  if (metaAdState.history.length === 0) {
    section.style.display = "none";
    return;
  }

  section.style.display = "block";
  if (countBadge) countBadge.textContent = metaAdState.history.length;

  grid.innerHTML = metaAdState.history.map((item, idx) => `
    <div class="meta-gallery-card ${item.image_url === (metaAdState.currentAd && metaAdState.currentAd.image_url) ? "active" : ""}" onclick="selectMetaGalleryItem(${idx})">
      <img src="${item.image_url}" alt="Meta Ad ${idx + 1}" loading="lazy" />
      <span class="meta-gallery-badge">${escapeHtml(item.angle || item.headline || `#${idx + 1}`)}</span>
    </div>
  `).join("");
}

function selectMetaGalleryItem(idx) {
  const item = metaAdState.history[idx];
  if (!item) return;
  metaAdState.currentAd = item;
  applyMetaAdToMockup(item);
  renderMetaGallery();
}

async function loadMetaAdsHistory() {
  try {
    const res = await fetch("/api/campaign/meta-ads");
    if (res.ok) {
      const data = await res.json();
      if (data.meta_ads && data.meta_ads.length > 0) {
        data.meta_ads.forEach(item => {
          if (!metaAdState.history.some(h => h.image_url === item.url)) {
            metaAdState.history.push({
              image_url: item.url,
              filename: item.filename,
              headline: "Saved Meta Creative",
              primary_text: "High-converting Meta creative generated in previous session.",
              cta: "Shop Now",
              aspect_ratio: "4:5"
            });
          }
        });
        renderMetaGallery();
      }
    }
  } catch (e) {
    console.warn("Could not load meta ads history:", e);
  }
}
