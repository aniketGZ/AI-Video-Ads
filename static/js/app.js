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

// Helper to format Voiceover field with dialogue/voiceover badges
function formatVoiceover(text) {
  if (!text) return "";
  
  // Replace brackets like [Dialogue: "spoken text"] or [Voiceover: "narrated text"]
  const segmentRegex = /\[(Dialogue|Voiceover):\s*["']?([^\]"']+)["']?\]/gi;
  if (segmentRegex.test(text)) {
    segmentRegex.lastIndex = 0; // reset
    return text.replace(segmentRegex, (match, type, content) => {
      const isDialogue = type.toLowerCase() === "dialogue";
      const bg = isDialogue ? "rgba(0, 168, 204, 0.15)" : "rgba(255, 255, 255, 0.05)";
      const border = isDialogue ? "var(--accent-light)" : "var(--border-color)";
      const label = isDialogue ? "🗣️ Spoken Dialogue (Lipsync)" : "🎙️ Voiceover Narration (No Lipsync)";
      const labelColor = isDialogue ? "var(--accent-light)" : "rgba(255, 255, 255, 0.7)";
      return `<div class="audio-segment" style="margin-bottom: 0.4rem; padding: 0.35rem 0.5rem; background: ${bg}; border-left: 3px solid ${border}; border-radius: 0 4px 4px 0;"><span style="font-weight: 700; font-size: 0.75rem; text-transform: uppercase; color: ${labelColor}; display: block; margin-bottom: 0.1rem;">${label}</span>"${content.trim()}"</div>`;
    });
  }
  
  return text;
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
          <span class="script-type">Video #${vIdx + 1}: ${video.video_style_type}</span>
        </div>
        <div class="script-detail-grid">
          <div class="script-field">
            <div class="script-field-title">Script Hook</div>
            <div class="script-field-value">"${video.hook_line}"</div>
          </div>
          <div class="script-field">
            <div class="script-field-title">Voiceover / Audio</div>
            <div class="script-field-value">${formatVoiceover(video.voiceover)}</div>
          </div>
          <div class="script-field">
            <div class="script-field-title">Visual Directions</div>
            <div class="script-field-value">${video.visual_directions}</div>
          </div>
          <div class="script-field" style="margin-bottom: 1.5rem;">
            <div class="script-field-title">Call To Action</div>
            <div class="script-field-value">"${video.cta_line}"</div>
          </div>
        </div>
      </div>
      <button class="btn" style="width: 100%; justify-content: center;" onclick="openStudio(${vIdx})">
        <i class="fa-solid fa-clapperboard"></i> Creator Studio
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
    storyboardPlaceholder.style.display = "block";
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
    videoPlaceholder_9_16.style.display = "block";
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
    videoPlaceholder_16_9.style.display = "block";
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
    shot_5: video.shot_5,
    shot_6: video.shot_6,
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
