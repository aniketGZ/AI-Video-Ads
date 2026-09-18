// Application State
let state = {
  campaignData: null,
  selectedAdGroupIndex: 0,
  selectedVideoIndex: 0,
  uploadedFiles: [],
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
      <button class="btn btn-primary" onclick="openStudio(${vIdx})">
        <i class="fa-solid fa-clapperboard"></i> Open Creator Studio
      </button>
    `;
    
    grid.appendChild(card);
  });
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
  
  if (state.generatedStoryboards[key]) {
    // Already generated storyboard
    storyboardPlaceholder.style.display = "none";
    storyboardImg.src = state.generatedStoryboards[key];
    storyboardImg.style.display = "block";
    
    generateStoryboardBtn.textContent = "Regenerate Storyboard";
    generateVideoBtn.disabled = false;
    generateVideoBtn.style.opacity = "1";
    setVideoPlaceholderText("Ready to Animate Videos");
  } else {
    storyboardPlaceholder.style.display = "flex";
    storyboardImg.style.display = "none";
    storyboardImg.src = "";
    
    generateStoryboardBtn.textContent = "Generate Storyboard (Nano Banana Pro)";
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
  
  const statusEl = document.getElementById("storyboard_status");
  statusEl.className = "generator-status working";
  statusEl.style.display = "flex";
  statusEl.querySelector("span").textContent = "Drafting 9:16 layout using Nano Banana Pro...";
  
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
    product_image_paths: state.campaignData.product_image_paths || []
  };
  
  const apiKey = document.getElementById("api_key_input").value;
  const headers = { "Content-Type": "application/json" };
  if (apiKey) {
    headers["x-api-key"] = apiKey;
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
    
    statusEl.className = "generator-status success";
    statusEl.querySelector("span").textContent = "Storyboard Generated Successfully!";
    generateBtn.textContent = "Regenerate Storyboard";
    
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
  
  if (generator === "seedance" && !kieKey) {
    alert("Please enter a Kie AI API Key in the header to use Seedance 2 Mini.");
    return;
  }
  
  const statusEl = document.getElementById("video_status");
  statusEl.className = "generator-status working";
  statusEl.style.display = "flex";
  
  statusEl.querySelector("span").textContent = `Generating both 9:16 and 16:9 videos using ${generator === "seedance" ? "Seedance 2 Mini" : "Omni Flash"}...`;
  
  const animateBtn = document.getElementById("generate_video_btn");
  animateBtn.disabled = true;
  
  const apiKey = document.getElementById("api_key_input").value;
  const headers = { "Content-Type": "application/json" };
  if (apiKey) headers["x-api-key"] = apiKey;
  if (kieKey) headers["x-kie-key"] = kieKey;
  
  // Create base request body
  const baseReq = {
    storyboard_image_url: storyboardUrl,
    product_image_paths: state.campaignData.product_image_paths || [],
    generator: generator
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
      ? `Create a 10s vertical 9:16 advertising video from this storyboard grid. Hook is: "${video.hook_line}". Visual description: ${video.visual_directions}. Follow the 4 panels left-to-right, top-to-bottom as reference frames.`
      : `Create a 10s landscape 16:9 advertising video from this storyboard grid. Hook is: "${video.hook_line}". Visual description: ${video.visual_directions}. Follow the 4 panels left-to-right, top-to-bottom as reference frames.`;
      
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
        if (isVertical) {
          videoPlaceholder_9_16.querySelector("p").textContent = `Generating 9:16... (attempt ${pollAttempts})`;
        } else {
          videoPlaceholder_16_9.querySelector("p").textContent = `Generating 16:9... (attempt ${pollAttempts})`;
        }
      }
    }
    
    if (!finished) {
      throw new Error(`${ratio} video generation timed out`);
    }
  }
  
  try {
    const [res_9_16, res_16_9] = await Promise.all([
      generateRatio("9:16"),
      generateRatio("16:9")
    ]);
    
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
  if (model === "seedance") {
    generateBtn.innerHTML = '<i class="fa-solid fa-play"></i> Animate Videos (Seedance 2 Mini)';
  } else {
    generateBtn.innerHTML = '<i class="fa-solid fa-play"></i> Animate Videos (Omni Flash)';
  }
}

// LocalStorage API Key Persistence
function initAPIKeysPersistence() {
  const apiKeyEl = document.getElementById("api_key_input");
  const kieKeyEl = document.getElementById("kie_key_input");
  
  if (apiKeyEl) {
    const savedApiKey = localStorage.getItem("gemini_api_key");
    if (savedApiKey) apiKeyEl.value = savedApiKey;
    
    apiKeyEl.addEventListener("input", (e) => {
      localStorage.setItem("gemini_api_key", e.target.value.trim());
    });
  }
  
  if (kieKeyEl) {
    const savedKieKey = localStorage.getItem("kie_api_key");
    if (savedKieKey) kieKeyEl.value = savedKieKey;
    
    kieKeyEl.addEventListener("input", (e) => {
      localStorage.setItem("kie_api_key", e.target.value.trim());
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initAPIKeysPersistence();
    initStudioDragAndDrop();
  });
} else {
  initAPIKeysPersistence();
  initStudioDragAndDrop();
}

/* ============================================================
   GOOGLE FLOW — AI VIDEO STUDIO JAVASCRIPT CONTROLLER
   ============================================================ */

// Main View Switcher (Video Studio vs Ad Campaign)
function switchMainView(view) {
  const studioTab = document.getElementById("nav_tab_studio");
  const campaignTab = document.getElementById("nav_tab_campaign");
  const studioView = document.getElementById("view_video_studio");
  const campaignView = document.getElementById("view_ad_campaign");
  
  if (view === "studio") {
    if (studioTab) studioTab.classList.add("active");
    if (campaignTab) campaignTab.classList.remove("active");
    if (studioView) studioView.style.display = "block";
    if (campaignView) campaignView.style.display = "none";
  } else {
    if (campaignTab) campaignTab.classList.add("active");
    if (studioTab) studioTab.classList.remove("active");
    if (studioView) studioView.style.display = "none";
    if (campaignView) campaignView.style.display = "block";
  }
}

// Studio State
const studioState = {
  mode: "prompt_images",
  aspectRatio: "9:16",
  resolution: "720p",
  duration: 6,
  referenceImages: [], // Up to 3
  firstFrame: null,
  lastFrame: null,
  sourceVideo: null,
  history: []
};

// Set Generation Mode
function setStudioMode(mode) {
  studioState.mode = mode;
  
  // Update mode buttons
  document.querySelectorAll(".mode-tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
  
  // Update mode panels
  const panePrompt = document.getElementById("pane_prompt_images");
  const paneKeyframes = document.getElementById("pane_first_last_frame");
  const paneVideo = document.getElementById("pane_edit_video");
  const promptLabel = document.getElementById("prompt_label_text");
  const promptInput = document.getElementById("studio_prompt");
  
  if (panePrompt) panePrompt.style.display = mode === "prompt_images" ? "block" : "none";
  if (paneKeyframes) paneKeyframes.style.display = mode === "first_last_frame" ? "block" : "none";
  if (paneVideo) paneVideo.style.display = mode === "edit_video" ? "block" : "none";
  
  // Update prompt placeholders based on mode
  if (mode === "first_last_frame") {
    if (promptLabel) promptLabel.textContent = "Motion & Transition Instructions";
    if (promptInput) promptInput.placeholder = "Describe the motion and scene evolution that bridges the start frame to the end frame...";
  } else if (mode === "edit_video") {
    if (promptLabel) promptLabel.textContent = "Video Edit Instructions & Modifications";
    if (promptInput) promptInput.placeholder = "Describe what to modify (e.g. change the backdrop to a futuristic neon city, make lighting golden-hour, change wardrobe to a red leather jacket)...";
  } else {
    if (promptLabel) promptLabel.textContent = "Scene Prompt & Motion Directions";
    if (promptInput) promptInput.placeholder = "Describe the scene, lighting, action, and style in rich detail...";
  }
}

// Set Aspect Ratio
function setStudioAspectRatio(ratio) {
  studioState.aspectRatio = ratio;
  
  document.querySelectorAll("#aspect_ratio_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.ratio === ratio);
  });
  
  const viewport = document.getElementById("player_viewport");
  if (viewport) {
    viewport.classList.remove("ratio-9-16", "ratio-16-9", "ratio-1-1");
    viewport.classList.add(`ratio-${ratio.replace(":", "-")}`);
  }
  
  updateStudioMetaBadges();
}

// Set Resolution
function setStudioResolution(res) {
  studioState.resolution = res;
  
  document.querySelectorAll("#resolution_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.res === res);
  });
  
  updateStudioMetaBadges();
}

// Set Duration
function setStudioDuration(dur) {
  studioState.duration = dur;
  
  document.querySelectorAll("#duration_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.dur) === dur);
  });
  
  updateStudioMetaBadges();
}

function updateStudioMetaBadges() {
  const resBadge = document.getElementById("player_res_badge");
  const durBadge = document.getElementById("player_dur_badge");
  
  let ratioName = "9:16 Vertical";
  if (studioState.aspectRatio === "16:9") ratioName = "16:9 Landscape";
  else if (studioState.aspectRatio === "1:1") ratioName = "1:1 Square";
  
  if (resBadge) resBadge.textContent = `${ratioName} · ${studioState.resolution}`;
  if (durBadge) durBadge.textContent = `${studioState.duration}s`;
}

// Append Camera Preset Keyword to Prompt
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

// Handle Reference Images Upload (up to 3)
function handleStudioRefImages(e) {
  const files = Array.from(e.target.files);
  if (!files.length) return;
  
  const remainingSlots = 3 - studioState.referenceImages.length;
  if (remainingSlots <= 0) {
    alert("Maximum 3 reference images allowed for Gemini Omni Flash 1.1.");
    return;
  }
  
  const toAdd = files.slice(0, remainingSlots);
  studioState.referenceImages = studioState.referenceImages.concat(toAdd);
  renderStudioRefThumbnails();
}

function renderStudioRefThumbnails() {
  const container = document.getElementById("studio_ref_thumbnails");
  const badge = document.getElementById("ref_count_badge");
  if (!container) return;
  
  container.innerHTML = "";
  if (badge) badge.textContent = `${studioState.referenceImages.length} / 3 selected`;
  
  studioState.referenceImages.forEach((file, index) => {
    const item = document.createElement("div");
    item.className = "ref-thumb-item";
    
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    img.alt = `Ref ${index + 1}`;
    
    const removeBtn = document.createElement("button");
    removeBtn.className = "ref-thumb-remove";
    removeBtn.type = "button";
    removeBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
    removeBtn.title = "Remove image";
    removeBtn.onclick = (e) => {
      e.stopPropagation();
      removeStudioRefImage(index);
    };
    
    item.appendChild(img);
    item.appendChild(removeBtn);
    container.appendChild(item);
  });
}

function removeStudioRefImage(index) {
  studioState.referenceImages.splice(index, 1);
  renderStudioRefThumbnails();
}

// Handle Keyframe Uploads (First & Last frame)
function handleKeyframeUpload(e, position) {
  const file = e.target.files[0];
  if (!file) return;
  
  if (position === "first") {
    studioState.firstFrame = file;
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("empty_first_frame");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "block";
  } else {
    studioState.lastFrame = file;
    const preview = document.getElementById("preview_last_frame");
    const emptyState = document.getElementById("empty_last_frame");
    const clearBtn = document.getElementById("clear_last_frame_btn");
    if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "block";
  }
}

function clearKeyframe(position) {
  if (position === "first") {
    studioState.firstFrame = null;
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("empty_first_frame");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    const input = document.getElementById("studio_first_frame_input");
    if (preview) { preview.src = ""; preview.style.display = "none"; }
    if (emptyState) emptyState.style.display = "flex";
    if (clearBtn) clearBtn.style.display = "none";
    if (input) input.value = "";
  } else {
    studioState.lastFrame = null;
    const preview = document.getElementById("preview_last_frame");
    const emptyState = document.getElementById("empty_last_frame");
    const clearBtn = document.getElementById("clear_last_frame_btn");
    const input = document.getElementById("studio_last_frame_input");
    if (preview) { preview.src = ""; preview.style.display = "none"; }
    if (emptyState) emptyState.style.display = "flex";
    if (clearBtn) clearBtn.style.display = "none";
    if (input) input.value = "";
  }
}

// Handle Source Video Upload for Video-to-Video Editing
function handleSourceVideoUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  studioState.sourceVideo = file;
  const previewContainer = document.getElementById("video_preview_container");
  const emptyState = document.getElementById("video_empty_state");
  const videoPlayer = document.getElementById("preview_source_video");
  
  if (videoPlayer) videoPlayer.src = URL.createObjectURL(file);
  if (emptyState) emptyState.style.display = "none";
  if (previewContainer) previewContainer.style.display = "flex";
}

function clearSourceVideo() {
  studioState.sourceVideo = null;
  const previewContainer = document.getElementById("video_preview_container");
  const emptyState = document.getElementById("video_empty_state");
  const videoPlayer = document.getElementById("preview_source_video");
  const input = document.getElementById("studio_video_input");
  
  if (videoPlayer) videoPlayer.src = "";
  if (previewContainer) previewContainer.style.display = "none";
  if (emptyState) emptyState.style.display = "block";
  if (input) input.value = "";
}

// Drag & Drop Listeners Setup
function initStudioDragAndDrop() {
  const dropzoneRef = document.getElementById("dropzone_reference");
  const dropzoneFirst = document.getElementById("dropzone_first_frame");
  const dropzoneLast = document.getElementById("dropzone_last_frame");
  const dropzoneVideo = document.getElementById("dropzone_source_video");
  
  const setupDrop = (zone, onFile) => {
    if (!zone) return;
    zone.addEventListener("dragover", (e) => { e.preventDefault(); zone.classList.add("drag-over"); });
    zone.addEventListener("dragleave", (e) => { e.preventDefault(); zone.classList.remove("drag-over"); });
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      zone.classList.remove("drag-over");
      onFile(e.dataTransfer.files);
    });
  };
  
  setupDrop(dropzoneRef, (files) => {
    const remainingSlots = 3 - studioState.referenceImages.length;
    if (remainingSlots <= 0) return alert("Maximum 3 reference images allowed.");
    const toAdd = Array.from(files).filter(f => f.type.startsWith("image/")).slice(0, remainingSlots);
    studioState.referenceImages = studioState.referenceImages.concat(toAdd);
    renderStudioRefThumbnails();
  });
  
  setupDrop(dropzoneFirst, (files) => {
    const f = Array.from(files).find(f => f.type.startsWith("image/"));
    if (f) handleKeyframeUpload({ target: { files: [f] } }, "first");
  });
  
  setupDrop(dropzoneLast, (files) => {
    const f = Array.from(files).find(f => f.type.startsWith("image/"));
    if (f) handleKeyframeUpload({ target: { files: [f] } }, "last");
  });
  
  setupDrop(dropzoneVideo, (files) => {
    const f = Array.from(files).find(f => f.type.startsWith("video/"));
    if (f) handleSourceVideoUpload({ target: { files: [f] } });
  });
}

// Submit Studio Video Generation
async function submitStudioVideo() {
  const promptInput = document.getElementById("studio_prompt");
  const negInput = document.getElementById("studio_negative_prompt");
  const generateBtn = document.getElementById("studio_generate_btn");
  const emptyState = document.getElementById("player_empty_state");
  const loadingOverlay = document.getElementById("player_loading_state");
  const videoPlayer = document.getElementById("studio_video_player");
  const actionsBar = document.getElementById("player_actions");
  const downloadBtn = document.getElementById("download_video_btn");
  const loadingTitle = document.getElementById("studio_loading_title");
  const loadingSub = document.getElementById("studio_loading_sub");
  const progressBar = document.getElementById("studio_progress_bar");
  
  const prompt = promptInput ? promptInput.value.trim() : "";
  if (!prompt) {
    alert("Please enter a scene prompt or motion directions.");
    if (promptInput) promptInput.focus();
    return;
  }
  
  if (studioState.mode === "edit_video" && !studioState.sourceVideo) {
    alert("Please upload a source video to edit.");
    return;
  }
  
  const formData = new FormData();
  formData.append("mode", studioState.mode);
  formData.append("prompt", prompt);
  if (negInput && negInput.value.trim()) {
    formData.append("negative_prompt", negInput.value.trim());
  }
  formData.append("aspect_ratio", studioState.aspectRatio);
  formData.append("resolution", studioState.resolution);
  formData.append("duration", studioState.duration);
  
  // Attach mode-specific files
  if (studioState.mode === "prompt_images" && studioState.referenceImages.length > 0) {
    studioState.referenceImages.forEach(img => {
      formData.append("reference_images", img);
    });
  } else if (studioState.mode === "first_last_frame") {
    if (studioState.firstFrame) formData.append("first_frame", studioState.firstFrame);
    if (studioState.lastFrame) formData.append("last_frame", studioState.lastFrame);
  } else if (studioState.mode === "edit_video" && studioState.sourceVideo) {
    formData.append("source_video", studioState.sourceVideo);
  }
  
  const apiKey = document.getElementById("api_key_input") ? document.getElementById("api_key_input").value.trim() : "";
  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  
  // UI Loading State
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<div class="mini-spinner"></div><span>Rendering with Omni Flash 1.1...</span>';
  }
  if (emptyState) emptyState.style.display = "none";
  if (videoPlayer) videoPlayer.style.display = "none";
  if (actionsBar) actionsBar.style.display = "none";
  if (loadingOverlay) loadingOverlay.style.display = "flex";
  if (loadingTitle) loadingTitle.textContent = "Synthesizing Video with Omni Flash 1.1";
  if (loadingSub) loadingSub.textContent = `Targeting ${studioState.resolution} · ${studioState.aspectRatio} · ${studioState.duration}s...`;
  if (progressBar) progressBar.style.width = "25%";
  
  try {
    const res = await fetch("/api/studio/generate-video", {
      method: "POST",
      headers: headers,
      body: formData
    });
    
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to dispatch video generation job");
    }
    
    const data = await res.json();
    const jobId = data.job_id;
    
    // Poll for status
    let progress = 35;
    const pollInterval = setInterval(async () => {
      try {
        progress = Math.min(progress + 8, 92);
        if (progressBar) progressBar.style.width = `${progress}%`;
        
        const statusRes = await fetch(`/api/video-status/${jobId}`);
        if (!statusRes.ok) return;
        const jobData = await statusRes.json();
        
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
              downloadBtn.download = `omni_flash_${studioState.resolution}_${Date.now()}.mp4`;
            }
            
            // Add to session history
            const historyEntry = {
              id: jobId,
              url: jobData.video_url,
              prompt: prompt,
              aspectRatio: studioState.aspectRatio,
              resolution: studioState.resolution,
              duration: studioState.duration,
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            };
            studioState.history.unshift(historyEntry);
            renderStudioHistory();
            
            // Reset generate button
            if (generateBtn) {
              generateBtn.disabled = false;
              generateBtn.innerHTML = '<i class="fa-solid fa-sparkles"></i><span>Generate with Omni Flash 1.1</span>';
            }
          }, 600);
          
        } else if (jobData.status === "failed") {
          clearInterval(pollInterval);
          throw new Error(jobData.error || "Omni Flash video generation failed on server");
        }
      } catch (pollErr) {
        clearInterval(pollInterval);
        console.error("Polling error:", pollErr);
        alert("Generation failed: " + pollErr.message);
        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (emptyState) emptyState.style.display = "flex";
        if (generateBtn) {
          generateBtn.disabled = false;
          generateBtn.innerHTML = '<i class="fa-solid fa-sparkles"></i><span>Generate with Omni Flash 1.1</span>';
        }
      }
    }, 3000);
    
  } catch (err) {
    console.error("Submit error:", err);
    alert("Generation failed: " + err.message);
    if (loadingOverlay) loadingOverlay.style.display = "none";
    if (emptyState) emptyState.style.display = "flex";
    if (generateBtn) {
      generateBtn.disabled = false;
      generateBtn.innerHTML = '<i class="fa-solid fa-sparkles"></i><span>Generate with Omni Flash 1.1</span>';
    }
  }
}

// Render Session Generations Reel
function renderStudioHistory() {
  const reel = document.getElementById("studio_history_reel");
  const countBadge = document.getElementById("history_count");
  if (!reel) return;
  
  if (countBadge) countBadge.textContent = `${studioState.history.length} video${studioState.history.length === 1 ? '' : 's'}`;
  reel.innerHTML = "";
  
  if (studioState.history.length === 0) {
    reel.innerHTML = '<div class="history-empty">Generated videos in this session will appear here for instant replay and comparison.</div>';
    return;
  }
  
  studioState.history.forEach((item, idx) => {
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
      document.querySelectorAll(".history-item").forEach(c => c.classList.remove("active"));
      card.classList.add("active");
      
      const player = document.getElementById("studio_video_player");
      const emptyState = document.getElementById("player_empty_state");
      const actionsBar = document.getElementById("player_actions");
      const downloadBtn = document.getElementById("download_video_btn");
      
      if (emptyState) emptyState.style.display = "none";
      if (player) {
        player.src = item.url;
        player.style.display = "block";
        player.play().catch(() => {});
      }
      if (actionsBar) actionsBar.style.display = "flex";
      if (downloadBtn) downloadBtn.href = item.url;
      
      setStudioAspectRatio(item.aspectRatio);
    };
    
    reel.appendChild(card);
  });
}

