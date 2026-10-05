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
    initStudioDragAndDrop();
    initImageStudioDragAndDrop();
    checkSelfHostedStatus();
  });
} else {
  initAPIKeysPersistence();
  initStudioDragAndDrop();
  initImageStudioDragAndDrop();
  checkSelfHostedStatus();
}

/* ============================================================
   GOOGLE FLOW — AI VIDEO STUDIO JAVASCRIPT CONTROLLER
   ============================================================ */

// Main View Switcher (Video Studio vs Image Studio vs Ad Campaign vs MoneyPrinter Turbo)
function switchMainView(view) {
  const studioTab = document.getElementById("nav_tab_studio");
  const imageTab = document.getElementById("nav_tab_image");
  const campaignTab = document.getElementById("nav_tab_campaign");
  const mptTab = document.getElementById("nav_tab_moneyprinter");
  const studioView = document.getElementById("view_video_studio");
  const imageView = document.getElementById("view_image_studio");
  const campaignView = document.getElementById("view_ad_campaign");
  const mptView = document.getElementById("view_moneyprinter");
  
  [studioTab, imageTab, campaignTab, mptTab].forEach(t => t && t.classList.remove("active"));
  [studioView, imageView, campaignView, mptView].forEach(v => v && (v.style.display = "none"));
  
  if (view === "studio") {
    if (studioTab) studioTab.classList.add("active");
    if (studioView) studioView.style.display = "block";
  } else if (view === "image") {
    if (imageTab) imageTab.classList.add("active");
    if (imageView) imageView.style.display = "block";
    loadImageStudioHistory();
  } else if (view === "moneyprinter") {
    if (mptTab) mptTab.classList.add("active");
    if (mptView) mptView.style.display = "block";
  } else {
    if (campaignTab) campaignTab.classList.add("active");
    if (campaignView) campaignView.style.display = "block";
  }
}

// Studio State
const studioState = {
  engine: "minimax",
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

// Set Video Engine (MiniMax-H3 vs Omni Flash)
function setStudioEngine(engine) {
  studioState.engine = engine;
  document.querySelectorAll("#studio_engine_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.engine === engine);
  });
  const generateBtn = document.getElementById("studio_generate_btn");
  if (generateBtn) {
    if (engine === "minimax") {
      generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video (MiniMax-H3)</span>';
    } else {
      generateBtn.innerHTML = '<i class="fa-solid fa-play"></i><span>Generate Video with Omni Flash 1.1</span>';
    }
  }
}

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

// Reference Image Slots Handling (3 slots: Character, Product, Style)
let activeSlotIndex = 0;

function triggerRefUpload(index) {
  activeSlotIndex = index;
  const input = document.getElementById("studio_ref_input_hidden");
  if (input) input.click();
}

function handleSingleSlotUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  studioState.referenceImages[activeSlotIndex] = file;
  
  const imgEl = document.getElementById(`slot_img_${activeSlotIndex}`);
  const emptyEl = document.getElementById(`slot_empty_${activeSlotIndex}`);
  const delBtn = document.getElementById(`slot_del_${activeSlotIndex}`);
  
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
  studioState.referenceImages[index] = null;
  
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
  const count = studioState.referenceImages.filter(Boolean).length;
  const badge = document.getElementById("ref_count_badge");
  if (badge) badge.textContent = `${count} / 3`;
}

// Handle Keyframe Uploads (First & Last frame)
function handleKeyframeUpload(e, position) {
  const file = e.target.files[0];
  if (!file) return;
  
  if (position === "first") {
    studioState.firstFrame = file;
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("keyframe_body_first");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    if (preview) { preview.src = URL.createObjectURL(file); preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "flex";
  } else {
    studioState.lastFrame = file;
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
    studioState.firstFrame = null;
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("keyframe_body_first");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    const input = document.getElementById("studio_first_frame_input");
    if (preview) { preview.src = ""; preview.style.display = "none"; }
    if (emptyState) emptyState.style.display = "flex";
    if (clearBtn) clearBtn.style.display = "none";
    if (input) input.value = "";
  } else {
    studioState.lastFrame = null;
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
  if (emptyState) emptyState.style.display = "flex";
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
  const videoKey = localStorage.getItem("self_hosted_video_key") || "";
  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  if (videoKey) headers["x-video-api-key"] = videoKey;
  
  const activeEngine = studioState.engine || "minimax";
  formData.append("generator", activeEngine);

  const engineTitle = activeEngine === "minimax" ? "MiniMax-H3 (Self-Hosted)" : "Omni Flash 1.1";

  // UI Loading State
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.innerHTML = `<div class="mini-spinner"></div><span>Rendering with ${engineTitle}...</span>`;
  }
  if (emptyState) emptyState.style.display = "none";
  if (videoPlayer) videoPlayer.style.display = "none";
  if (actionsBar) actionsBar.style.display = "none";
  if (loadingOverlay) loadingOverlay.style.display = "flex";
  if (loadingTitle) loadingTitle.textContent = `Synthesizing Video with ${engineTitle}`;
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
              downloadBtn.download = `${activeEngine}_video_${studioState.resolution}_${Date.now()}.mp4`;
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
              generateBtn.innerHTML = activeEngine === 'minimax' 
                ? '<i class="fa-solid fa-play"></i><span>Generate Video (MiniMax-H3)</span>' 
                : '<i class="fa-solid fa-play"></i><span>Generate Video with Omni Flash 1.1</span>';
            }
          }, 600);
          
        } else if (jobData.status === "failed") {
          clearInterval(pollInterval);
          throw new Error(jobData.error || `${engineTitle} video generation failed on server`);
        }
      } catch (pollErr) {
        clearInterval(pollInterval);
        console.error("Polling error:", pollErr);
        alert("Generation failed: " + pollErr.message);
        if (loadingOverlay) loadingOverlay.style.display = "none";
        if (emptyState) emptyState.style.display = "flex";
        if (generateBtn) {
          generateBtn.disabled = false;
          generateBtn.innerHTML = activeEngine === 'minimax' 
            ? '<i class="fa-solid fa-play"></i><span>Generate Video (MiniMax-H3)</span>' 
            : '<i class="fa-solid fa-play"></i><span>Generate Video with Omni Flash 1.1</span>';
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
      generateBtn.innerHTML = activeEngine === 'minimax' 
        ? '<i class="fa-solid fa-play"></i><span>Generate Video (MiniMax-H3)</span>' 
        : '<i class="fa-solid fa-play"></i><span>Generate Video with Omni Flash 1.1</span>';
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
   AI IMAGE ADS STUDIO JAVASCRIPT CONTROLLER (QWEN-IMAGE-2.1)
   ============================================================ */

const imageStudioState = {
  mode: "text", // "text" or "product"
  aspectRatio: "1:1",
  stylePreset: "luxury_podium",
  engine: "qwen", // "qwen" or "gemini"
  steps: 35,
  seed: null,
  productFile: null,
  currentImageUrl: null,
  currentPrompt: "",
  history: []
};

// Set Creation Mode: "text" vs "product"
function setImageStudioMode(mode) {
  imageStudioState.mode = mode;
  const btnText = document.getElementById("btn_img_mode_text");
  const btnProduct = document.getElementById("btn_img_mode_product");
  const uploadPane = document.getElementById("image_product_upload_pane");
  const promptInput = document.getElementById("img_studio_prompt");
  
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

// Set Aspect Ratio
function setImageStudioAspectRatio(ratio) {
  imageStudioState.aspectRatio = ratio;
  document.querySelectorAll("#img_aspect_ratio_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.ratio === ratio);
  });
  
  const viewport = document.getElementById("img_stage_viewport");
  if (viewport) {
    viewport.classList.remove("ratio-9-16", "ratio-16-9", "ratio-1-1", "ratio-4-5");
    viewport.classList.add(`ratio-${ratio.replace(":", "-")}`);
  }
  updateImageStudioMetaBadges();
}

// Set Engine
function setImageStudioEngine(engine) {
  imageStudioState.engine = engine;
  document.querySelectorAll("#img_engine_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.engine === engine);
  });
  
  const btn = document.getElementById("img_studio_generate_btn");
  if (btn) {
    if (engine === "qwen") {
      btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span>Generate Image Ad (Qwen-Image-2.1)</span>';
    } else {
      btn.innerHTML = '<i class="fa-solid fa-bolt"></i><span>Generate Image Ad (Gemini Nano Banana Pro)</span>';
    }
  }
  updateImageStudioMetaBadges();
}

// Set Steps
function setImageStudioSteps(steps) {
  imageStudioState.steps = steps;
  document.querySelectorAll("#img_steps_selector .pill-btn").forEach(btn => {
    btn.classList.toggle("active", parseInt(btn.dataset.steps) === steps);
  });
}

// Set Style Preset
function setImageStudioPreset(presetKey) {
  imageStudioState.stylePreset = presetKey;
  document.querySelectorAll("#img_style_presets_grid .preset-card-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.preset === presetKey);
  });
  updateImageStudioMetaBadges();
}

function updateImageStudioMetaBadges() {
  const resBadge = document.getElementById("img_player_res_badge");
  const presetBadge = document.getElementById("img_player_preset_badge");
  const engineBadge = document.getElementById("img_player_engine_badge");
  
  const ratioLabels = {
    "1:1": "1:1 Square · 1024x1024",
    "9:16": "9:16 Story · 1024x1792",
    "16:9": "16:9 Banner · 1792x1024",
    "4:5": "4:5 Portrait · 1024x1280"
  };
  if (resBadge) resBadge.textContent = ratioLabels[imageStudioState.aspectRatio] || imageStudioState.aspectRatio;
  
  const presetLabels = {
    "luxury_podium": "Luxury Podium",
    "ugc_lifestyle": "UGC Lifestyle",
    "neon_cyber": "Cyber Neon",
    "nature_botanical": "Botanical",
    "dramatic_splash": "Dynamic Splash",
    "minimal_dtc": "Minimal DTC"
  };
  if (presetBadge) presetBadge.textContent = presetLabels[imageStudioState.stylePreset] || (imageStudioState.stylePreset ? imageStudioState.stylePreset : "Custom Style");
  
  if (engineBadge) {
    if (imageStudioState.engine === "qwen") {
      engineBadge.innerHTML = '<i class="fa-solid fa-microchip"></i> Qwen-Image-2.1';
    } else {
      engineBadge.innerHTML = '<i class="fa-solid fa-bolt"></i> Nano Banana Pro';
    }
  }
}

// Append visual booster to prompt
function appendImagePromptBooster(phrase) {
  const textarea = document.getElementById("img_studio_prompt");
  if (!textarea) return;
  const current = textarea.value.trim();
  if (!current) {
    textarea.value = phrase;
  } else {
    textarea.value = current.endsWith(",") ? `${current} ${phrase}` : `${current}, ${phrase}`;
  }
  textarea.focus();
}

// Product Image upload handling
function handleProductImageUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  
  imageStudioState.productFile = file;
  const preview = document.getElementById("img_product_preview");
  const emptyState = document.getElementById("img_dropzone_empty");
  const previewWrap = document.getElementById("img_dropzone_preview_wrap");
  
  if (preview) {
    preview.src = URL.createObjectURL(file);
  }
  if (emptyState) emptyState.style.display = "none";
  if (previewWrap) previewWrap.style.display = "flex";
}

function clearProductImage() {
  imageStudioState.productFile = null;
  const fileInput = document.getElementById("img_studio_product_file");
  if (fileInput) fileInput.value = "";
  
  const preview = document.getElementById("img_product_preview");
  const emptyState = document.getElementById("img_dropzone_empty");
  const previewWrap = document.getElementById("img_dropzone_preview_wrap");
  
  if (preview) preview.src = "";
  if (emptyState) emptyState.style.display = "flex";
  if (previewWrap) previewWrap.style.display = "none";
}

// Drag & drop setup for Image Studio dropzone
function initImageStudioDragAndDrop() {
  const dropzone = document.getElementById("img_studio_dropzone");
  if (!dropzone) return;
  
  ["dragenter", "dragover"].forEach(ev => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.add("drag-over"); });
  });
  ["dragleave", "drop"].forEach(ev => {
    dropzone.addEventListener(ev, (e) => { e.preventDefault(); dropzone.classList.remove("drag-over"); });
  });
  dropzone.addEventListener("drop", (e) => {
    const file = Array.from(e.dataTransfer.files).find(f => f.type.startsWith("image/"));
    if (file) {
      handleProductImageUpload({ target: { files: [file] } });
    }
  });
}

// Generate Image Ad API call
let imgElapsedInterval = null;

async function generateImageAd() {
  const promptInput = document.getElementById("img_studio_prompt");
  const negInput = document.getElementById("img_studio_negative_prompt");
  const seedInput = document.getElementById("img_studio_seed");
  const generateBtn = document.getElementById("img_studio_generate_btn");
  
  const emptyState = document.getElementById("img_empty_state");
  const loadingOverlay = document.getElementById("img_loading_state");
  const imgDisplay = document.getElementById("img_ad_display");
  const actionsBar = document.getElementById("img_player_actions");
  const downloadBtn = document.getElementById("btn_download_image_ad");
  const loadingTitle = document.getElementById("img_loading_title");
  const loadingSub = document.getElementById("img_loading_sub");
  const progressBar = document.getElementById("img_progress_bar");
  const timerEl = document.getElementById("img_elapsed_timer");
  
  const prompt = promptInput ? promptInput.value.trim() : "";
  if (!prompt) {
    alert("Please enter a scene prompt or ad concept.");
    if (promptInput) promptInput.focus();
    return;
  }
  
  if (imageStudioState.mode === "product" && !imageStudioState.productFile) {
    alert("Please upload a tangible product image to remix or switch to 'Text-to-Ad Creative'.");
    return;
  }
  
  const formData = new FormData();
  formData.append("prompt", prompt);
  formData.append("aspect_ratio", imageStudioState.aspectRatio);
  formData.append("style_preset", imageStudioState.stylePreset || "");
  formData.append("engine", imageStudioState.engine);
  formData.append("steps", imageStudioState.steps);
  
  if (seedInput && seedInput.value.trim()) {
    formData.append("seed", parseInt(seedInput.value.trim()));
  }
  if (negInput && negInput.value.trim()) {
    formData.append("negative_prompt", negInput.value.trim());
  }
  if (imageStudioState.mode === "product" && imageStudioState.productFile) {
    formData.append("product_image", imageStudioState.productFile);
  }
  
  const apiKey = document.getElementById("api_key_input") ? document.getElementById("api_key_input").value.trim() : "";
  const imageKey = localStorage.getItem("self_hosted_image_key") || "";
  const headers = {};
  if (apiKey) headers["x-api-key"] = apiKey;
  if (imageKey) headers["x-image-api-key"] = imageKey;
  
  // Show Loading state
  if (emptyState) emptyState.style.display = "none";
  if (imgDisplay) imgDisplay.style.display = "none";
  if (actionsBar) actionsBar.style.display = "none";
  if (loadingOverlay) loadingOverlay.style.display = "flex";
  if (generateBtn) generateBtn.disabled = true;
  
  const engineTitle = imageStudioState.engine === "qwen" ? "Qwen-Image-2.1 (Self-Hosted)" : "Gemini Nano Banana Pro";
  if (loadingTitle) loadingTitle.textContent = `Synthesizing with ${engineTitle}`;
  if (loadingSub) loadingSub.textContent = "Running diffusion steps (approx 60-90s on GPU)...";
  
  // Progress animation & timer
  let elapsed = 0;
  if (timerEl) timerEl.textContent = "0s elapsed";
  if (progressBar) progressBar.style.width = "5%";
  
  if (imgElapsedInterval) clearInterval(imgElapsedInterval);
  imgElapsedInterval = setInterval(() => {
    elapsed++;
    if (timerEl) timerEl.textContent = `${elapsed}s elapsed`;
    
    // Simulate gradual progress bar up to 90%
    if (progressBar) {
      const pct = Math.min(90, Math.floor(5 + (elapsed / 70) * 85));
      progressBar.style.width = `${pct}%`;
    }
    
    if (elapsed === 15 && loadingSub) {
      loadingSub.textContent = "Evaluating layout and denoising latent features...";
    } else if (elapsed === 40 && loadingSub) {
      loadingSub.textContent = "Rendering high-frequency textures and studio lighting...";
    } else if (elapsed === 70 && loadingSub) {
      loadingSub.textContent = "Finalizing 2K upscaling and color balancing...";
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
    
    // Cache current output
    imageStudioState.currentImageUrl = data.image_url;
    imageStudioState.currentPrompt = prompt;
    
    // Render image
    if (imgDisplay) {
      imgDisplay.src = data.image_url;
      imgDisplay.style.display = "block";
    }
    if (downloadBtn) {
      downloadBtn.href = data.image_url;
      downloadBtn.download = data.filename || "ai_image_ad.png";
    }
    if (actionsBar) actionsBar.style.display = "flex";
    
    // Add to history
    imageStudioState.history.unshift(data);
    renderImageStudioHistory();
    
  } catch (err) {
    console.error("Image generation failed:", err);
    alert(`Image generation failed:\n${err.message}`);
    if (emptyState) emptyState.style.display = "flex";
  } finally {
    if (imgElapsedInterval) clearInterval(imgElapsedInterval);
    if (loadingOverlay) loadingOverlay.style.display = "none";
    if (generateBtn) generateBtn.disabled = false;
  }
}

// Bridge function: Animate current image ad in Video Studio
async function animateCurrentImageAd() {
  if (!imageStudioState.currentImageUrl) return;
  const imgUrl = imageStudioState.currentImageUrl;
  const prompt = imageStudioState.currentPrompt;
  
  // 1. Switch to Video Studio view
  switchMainView("studio");
  
  // 2. Set mode to start & end frame
  setStudioMode("first_last_frame");
  
  // 3. Convert image url to Blob & File for studioState.firstFrame
  try {
    const res = await fetch(imgUrl);
    const blob = await res.blob();
    const file = new File([blob], "image_ad_keyframe.png", { type: blob.type || "image/png" });
    studioState.firstFrame = file;
    
    const preview = document.getElementById("preview_first_frame");
    const emptyState = document.getElementById("keyframe_body_first");
    const clearBtn = document.getElementById("clear_first_frame_btn");
    if (preview) { preview.src = imgUrl; preview.style.display = "block"; }
    if (emptyState) emptyState.style.display = "none";
    if (clearBtn) clearBtn.style.display = "flex";
  } catch (e) {
    console.warn("Could not set image as first frame blob:", e);
  }
  
  // 4. Autofill scene prompt for video motion
  const promptInput = document.getElementById("studio_prompt");
  if (promptInput) {
    promptInput.value = prompt ? `Cinematic dynamic ad animation starting from this scene: ${prompt}` : "Cinematic commercial animation, smooth camera motion revealing the product with dynamic lighting and atmospheric depth";
  }
}

// Load and render history from server
async function loadImageStudioHistory() {
  try {
    const res = await fetch("/api/image-studio/history");
    if (res.ok) {
      const data = await res.json();
      if (data.images && data.images.length > 0) {
        // Merge with session history
        const existingUrls = new Set(imageStudioState.history.map(h => h.image_url));
        data.images.forEach(img => {
          if (!existingUrls.has(img.url)) {
            imageStudioState.history.push({
              image_url: img.url,
              filename: img.filename,
              aspect_ratio: "1:1",
              model_used: "Qwen-Image-2.1"
            });
          }
        });
        renderImageStudioHistory();
      }
    }
  } catch (e) {
    console.warn("Failed to load image history:", e);
  }
}

function renderImageStudioHistory() {
  const reel = document.getElementById("img_studio_history_reel");
  const countEl = document.getElementById("img_history_count");
  if (!reel) return;
  
  if (imageStudioState.history.length === 0) {
    reel.innerHTML = '<div class="history-empty" id="img_history_empty_msg">Generated image ads will appear here for instant preview, download, and video animation.</div>';
    if (countEl) countEl.textContent = "0 images";
    return;
  }
  
  if (countEl) countEl.textContent = `${imageStudioState.history.length} image${imageStudioState.history.length > 1 ? "s" : ""}`;
  
  reel.innerHTML = imageStudioState.history.map((item, idx) => `
    <div class="history-item image-ad-item ${item.image_url === imageStudioState.currentImageUrl ? 'active' : ''}" onclick="selectHistoryImageAd(${idx})">
      <img src="${item.image_url}" alt="Ad history ${idx + 1}" loading="lazy">
      <span class="history-item-badge">#${idx + 1}</span>
    </div>
  `).join('');
}

function selectHistoryImageAd(index) {
  const item = imageStudioState.history[index];
  if (!item) return;
  
  imageStudioState.currentImageUrl = item.image_url;
  imageStudioState.currentPrompt = item.prompt || "";
  
  const emptyState = document.getElementById("img_empty_state");
  const imgDisplay = document.getElementById("img_ad_display");
  const actionsBar = document.getElementById("img_player_actions");
  const downloadBtn = document.getElementById("btn_download_image_ad");
  
  if (emptyState) emptyState.style.display = "none";
  if (imgDisplay) {
    imgDisplay.src = item.image_url;
    imgDisplay.style.display = "block";
  }
  if (downloadBtn) {
    downloadBtn.href = item.image_url;
    downloadBtn.download = item.filename || "ai_image_ad.png";
  }
  if (actionsBar) actionsBar.style.display = "flex";
  
  renderImageStudioHistory();
}



