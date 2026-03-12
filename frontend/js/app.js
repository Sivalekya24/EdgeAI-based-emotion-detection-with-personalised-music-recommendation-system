"use strict";

/* ═══════════════════════════════════════════════════════════════
   MoodWave — app.js
   Camera state machine: IDLE → LIVE → CAPTURED → detect → IDLE
═══════════════════════════════════════════════════════════════ */

const CAM = { IDLE: "idle", LIVE: "live", CAPTURED: "captured" };

/* ── Emotion metadata ── */
const EMOTION_META = {
  happy:    { emoji: "😊", desc: "You're glowing with happiness! Let's find some upbeat tracks to match your mood." },
  sad:      { emoji: "😢", desc: "It's okay to feel blue. Music will wrap you up warmly and gently lift your spirit." },
  angry:    { emoji: "😠", desc: "Channel that energy! Here's something powerful and cathartic just for you." },
  fear:     { emoji: "😨", desc: "Take a breath — let some calming melodies ease your mind and soothe your nerves." },
  disgust:  { emoji: "🤢", desc: "Let's flip the mood completely with positive, uplifting tracks to refresh your state." },
  surprise: { emoji: "😲", desc: "What a moment! Celebrate the unexpected with high-energy, exciting music." },
  neutral:  { emoji: "😐", desc: "Feeling chill and balanced? Let's keep the vibe smooth and perfectly relaxed." },
};

/* ── Language options ── */
const LANGUAGES = [
  { id: "english",  name: "English",  native: "English", flag: "🇬🇧" },
  { id: "hindi",    name: "Hindi",    native: "हिंदी",    flag: "🇮🇳" },
  { id: "telugu",   name: "Telugu",   native: "తెలుగు",   flag: "🇮🇳" },
  { id: "tamil",    name: "Tamil",    native: "தமிழ்",    flag: "🇮🇳" },
  { id: "punjabi",  name: "Punjabi",  native: "ਪੰਜਾਬੀ",   flag: "🇮🇳" },
  { id: "korean",   name: "Korean",   native: "한국어",    flag: "🇰🇷" },
  { id: "japanese", name: "Japanese", native: "日本語",    flag: "🇯🇵" },
  { id: "spanish",  name: "Spanish",  native: "Español",  flag: "🇪🇸" },
];

/* ── State ── */
let camState        = CAM.IDLE;
let liveStream      = null;
let capturedB64     = null;
let detectedEmotion = null;
let selectedLang    = null;

/* ── DOM helpers ── */
const $        = id  => document.getElementById(id);
const show     = el  => { if (el) el.style.display = "block"; };
const hide     = el  => { if (el) el.style.display = "none"; };
const showFlex = el  => { if (el) el.style.display = "flex"; };

/* ════════════════════════════════════════
   TOAST
════════════════════════════════════════ */
function toast(msg, type = "inf", ms = 3500) {
  const el = $("toast");
  const icons = { ok: "✅", err: "❌", inf: "💡" };
  el.innerHTML  = `${icons[type] || "💡"} ${msg}`;
  el.className  = `toast t-${type} show`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), ms);
}

/* ════════════════════════════════════════
   CAMERA STATE MACHINE
════════════════════════════════════════ */
function setCamState(state) {
  camState = state;

  const p     = $("camPlaceholder");
  const vid   = $("videoEl");
  const img   = $("capturedImg");
  const badge = $("frozenBadge");
  const scan  = $("scanLayer");
  const led   = $("camLed");
  const stxt  = $("camStatusTxt");
  const bs    = $("btnStart");
  const bd    = $("btnDetect");

  if (state === CAM.IDLE) {
    showFlex(p); hide(vid); hide(img); hide(badge);
    scan.classList.remove("active");
    led.classList.remove("on");
    stxt.textContent   = "Off";
    bs.innerHTML       = `<span>📷</span> Start Camera`;
    bs.disabled        = false;
    bd.disabled        = true;
    bd.innerHTML       = `<span>🎯</span> Detect Emotion`;

  } else if (state === CAM.LIVE) {
    hide(p); show(vid); hide(img); hide(badge);
    scan.classList.add("active");
    led.classList.add("on");
    stxt.textContent   = "Live — Click to Capture";
    bs.innerHTML       = `<span>📸</span> Capture Photo`;
    bs.disabled        = false;
    bd.disabled        = true;
    bd.innerHTML       = `<span>🎯</span> Detect Emotion`;

  } else if (state === CAM.CAPTURED) {
    hide(p); hide(vid); show(img); show(badge);
    scan.classList.remove("active");
    led.classList.remove("on");
    stxt.textContent   = "Photo Captured";
    bs.innerHTML       = `<span>🔄</span> Retake Photo`;
    bs.disabled        = false;
    bd.disabled        = false;
    bd.innerHTML       = `<span>🎯</span> Detect Emotion`;
  }
}

function stopStream() {
  if (liveStream) { liveStream.getTracks().forEach(t => t.stop()); liveStream = null; }
  const vid = $("videoEl");
  if (vid) vid.srcObject = null;
}

async function handleStartBtn() {
  if (camState === CAM.IDLE || camState === CAM.CAPTURED) {
    await openCamera();
  } else {
    capturePhoto();
  }
}

async function openCamera() {
  capturedB64 = null;
  stopStream();
  const bs = $("btnStart");
  bs.disabled  = true;
  bs.innerHTML = `<span style="display:inline-block;width:14px;height:14px;border:2px solid rgba(255,255,255,.3);border-top-color:var(--teal);border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;"></span> Starting…`;
  try {
    liveStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 480 }, height: { ideal: 360 }, facingMode: "user" }
    });
    const vid = $("videoEl");
    vid.srcObject = liveStream;
    await vid.play();
    setCamState(CAM.LIVE);
    toast("Camera live — position your face then click 'Capture Photo'", "ok");
  } catch (e) {
    setCamState(CAM.IDLE);
    const msg =
      e.name === "NotAllowedError" ? "Camera permission denied. Please allow camera access." :
      e.name === "NotFoundError"   ? "No camera found on this device." :
      "Camera error: " + e.message;
    toast(msg, "err", 5000);
  }
}

function capturePhoto() {
  const vid = $("videoEl");
  if (!vid || vid.readyState < 2) { toast("Camera not ready yet.", "err"); return; }
  const canvas = $("canvasEl");
  canvas.width  = vid.videoWidth  || 480;
  canvas.height = vid.videoHeight || 360;
  const ctx = canvas.getContext("2d");
  // Mirror-correct: draw un-flipped for server, display flipped for user (CSS)
  ctx.save();
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(vid, 0, 0, canvas.width, canvas.height);
  ctx.restore();
  capturedB64 = canvas.toDataURL("image/jpeg", 0.82);
  $("capturedImg").src = capturedB64;
  stopStream();
  setCamState(CAM.CAPTURED);
  toast("📸 Photo captured! Click 'Detect Emotion' to analyse.", "ok");
}

/* ════════════════════════════════════════
   DETECT EMOTION
════════════════════════════════════════ */
async function detectEmotion() {
  if (camState !== CAM.CAPTURED || !capturedB64) {
    toast("Please capture a photo first.", "err");
    return;
  }
  const bd = $("btnDetect");
  const bs = $("btnStart");
  const overlay = $("camStatusMsg");
  bd.disabled = bs.disabled = true;
  bd.innerHTML = `<span style="display:inline-block;width:15px;height:15px;border:2px solid rgba(255,255,255,.3);border-top-color:var(--violet);border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;"></span> Analysing…`;
  if (overlay) { overlay.textContent = "🧠 Analysing your expression…"; overlay.classList.add("visible"); }

  try {
    const res  = await fetch("/detect-emotion", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ image: capturedB64 }),
    });
    const data = await res.json();
    if (overlay) overlay.classList.remove("visible");

    if (!res.ok || !data.success) {
      bd.disabled = bs.disabled = false;
      bd.innerHTML = `<span>🎯</span> Detect Emotion`;
      toast(`⚠️ ${data.error || "Detection failed — try retaking the photo."}`, "err", 5500);
      return;
    }

    capturedB64     = null;
    detectedEmotion = data.emotion.toLowerCase();
    selectedLang    = null;

    setCamState(CAM.IDLE);
    renderResult(data);
    const meta = EMOTION_META[detectedEmotion] || EMOTION_META.neutral;
    toast(`Detected: ${meta.emoji} ${detectedEmotion.charAt(0).toUpperCase() + detectedEmotion.slice(1)}`, "ok");
    setTimeout(() => $("resultSection").scrollIntoView({ behavior: "smooth", block: "start" }), 150);

  } catch (e) {
    if (overlay) overlay.classList.remove("visible");
    $("btnDetect").disabled = $("btnStart").disabled = false;
    $("btnDetect").innerHTML = `<span>🎯</span> Detect Emotion`;
    toast("Network error: " + e.message, "err");
  }
}

/* ════════════════════════════════════════
   RENDER RESULT
════════════════════════════════════════ */
function renderResult(data) {
  const { emotion, confidence, all_emotions } = data;
  const meta = EMOTION_META[emotion] || EMOTION_META.neutral;
  const pct  = Math.round((confidence || 0) * 100);

  show($("resultSection"));

  // Emoji + name
  $("resEmoji").textContent   = meta.emoji;
  $("resName").textContent    = emotion.charAt(0).toUpperCase() + emotion.slice(1);
  $("resNameInline").textContent = emotion.charAt(0).toUpperCase() + emotion.slice(1);
  $("resDesc").textContent    = meta.desc;
  $("resConfVal").textContent = `${pct}%`;

  // Animated SVG confidence ring (circumference = 2π × 50 ≈ 314)
  const fill = $("confRingFill");
  if (fill) {
    const offset = 314 - (pct / 100) * 314;
    // Use teal→violet gradient
    if (!document.getElementById("mwGrad")) {
      const svg  = fill.closest("svg");
      const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      defs.innerHTML = `<linearGradient id="mwGrad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%"   stop-color="#00e5c8"/>
        <stop offset="100%" stop-color="#a855f7"/>
      </linearGradient>`;
      svg.prepend(defs);
      fill.setAttribute("stroke", "url(#mwGrad)");
    }
    requestAnimationFrame(() => requestAnimationFrame(() => {
      fill.style.strokeDashoffset = offset;
    }));
  }

  // 7-emotion probability grid (2-column layout)
  const order = ["happy", "neutral", "sad", "angry", "fear", "disgust", "surprise"];
  const grid  = $("emotionGrid");
  grid.innerHTML = order.map(lbl => {
    const v   = all_emotions ? (all_emotions[lbl] || 0) : 0;
    const p   = Math.round(v * 100);
    const top = lbl === emotion;
    return `
      <div class="em-prob-row">
        <div class="em-prob-top-row">
          <span class="em-prob-name${top ? " em-top-label" : ""}">${lbl.charAt(0).toUpperCase() + lbl.slice(1)}</span>
          <span class="em-prob-pct${top ? " em-top-pct"   : ""}">${p}%</span>
        </div>
        <div class="em-prob-bar">
          <div class="em-prob-fill${top ? " em-top-fill" : ""}" data-w="${p}%" style="width:0%;"></div>
        </div>
      </div>`;
  }).join("");

  // Animate bars after paint
  requestAnimationFrame(() => requestAnimationFrame(() => {
    grid.querySelectorAll(".em-prob-fill").forEach(el => { el.style.width = el.dataset.w; });
  }));

  // Show language picker, hide music
  buildLangGrid();
  show($("langSection"));
  hide($("musicSection"));
  $("btnGetMusic").disabled = true;
}

/* ════════════════════════════════════════
   LANGUAGE SELECTION
════════════════════════════════════════ */
function buildLangGrid() {
  $("langGrid").innerHTML = LANGUAGES.map(l => `
    <div class="lang-card" data-lang="${l.id}" onclick="selectLang('${l.id}')">
      <span class="lang-flag">${l.flag}</span>
      <span class="lang-name">${l.name}</span>
      <span class="lang-native">${l.native}</span>
    </div>`).join("");
}

function selectLang(id) {
  selectedLang = id;
  document.querySelectorAll(".lang-card").forEach(c => {
    c.classList.toggle("selected", c.dataset.lang === id);
  });
  $("btnGetMusic").disabled = false;
  const lang = LANGUAGES.find(l => l.id === id);
  toast(`${lang?.flag || ""} ${lang?.name || id} selected`, "inf", 1800);
}

/* ════════════════════════════════════════
   FETCH MUSIC
════════════════════════════════════════ */
async function fetchMusic() {
  if (!detectedEmotion) { toast("Please detect your emotion first.", "err"); return; }
  if (!selectedLang)    { toast("Please select a language first.",  "err"); return; }

  const btn = $("btnGetMusic");
  const ms  = $("musicSection");
  const sp  = $("musicSpinner");

  btn.disabled = true;
  btn.innerHTML = `<span style="display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,.3);border-top-color:var(--teal);border-radius:50%;animation:spin .6s linear infinite;vertical-align:middle;"></span> Loading…`;

  show(ms);
  sp.classList.add("active");
  $("songsGrid").innerHTML = "";
  setTimeout(() => ms.scrollIntoView({ behavior: "smooth", block: "start" }), 100);

  try {
    const res  = await fetch(`/recommend-music?emotion=${detectedEmotion}&language=${selectedLang}`);
    const data = await res.json();
    sp.classList.remove("active");
    if (!res.ok || !data.success) throw new Error(data.error || "Music fetch failed.");
    renderPlaylist(data);
  } catch (e) {
    sp.classList.remove("active");
    toast("Music error: " + e.message, "err");
  } finally {
    btn.disabled  = false;
    btn.innerHTML = `<span>🎵</span> Get My Playlist`;
  }
}

/* ════════════════════════════════════════
   RENDER PLAYLIST
════════════════════════════════════════ */
function renderPlaylist(data) {
  const { emotion, language, songs } = data;
  const meta  = EMOTION_META[emotion] || EMOTION_META.neutral;
  const lname = LANGUAGES.find(l => l.id === language)?.name || language;

  $("playlistTitle").innerHTML =
    `${meta.emoji} ${emotion.charAt(0).toUpperCase() + emotion.slice(1)} Playlist &nbsp;·&nbsp; <span class="g-text">${lname}</span>`;
  $("playlistCount").textContent = `${songs.length} tracks`;

  const mb = $("playlistMetaBar");
  if (mb) mb.style.display = "flex";

  const grid = $("songsGrid");
  if (!songs?.length) {
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:60px;color:var(--text-2);">
        <div style="font-size:40px;margin-bottom:12px;">🎵</div>
        <p>No songs found for this combination. Try another language.</p>
      </div>`;
    return;
  }

  grid.innerHTML = songs.map((s, i) => {
    const name   = s.name   || s.song_name    || "Unknown";
    const artist = s.artist || s.artist_name  || "Unknown Artist";
    const album  = s.album  || s.movie_name   || "";
    const url    = s.spotify_url || s.full_song_url || "";
    const img    = s.album_image || "";
    return `
      <div class="song-card" style="animation-delay:${i * 0.05}s;">
        <div class="song-img-wrap">
          ${img
            ? `<img class="song-img" src="${esc(img)}" alt="${esc(album)}" loading="lazy"
                    onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">`
            : ""}
          <div class="song-img-fallback"${img ? ' style="display:none;"' : ""}>🎵</div>
        </div>
        <div class="song-info">
          <div class="song-name"   title="${esc(name)}">${esc(name)}</div>
          <div class="song-artist">${esc(artist)}</div>
          ${album ? `<div class="song-album">${esc(album)}</div>` : ""}
          ${url
            ? `<a class="btn-spotify" href="${esc(url)}" target="_blank" rel="noopener">${spotifySvg()} Play on Spotify</a>`
            : `<span class="btn-spotify btn-spotify-disabled">Not available</span>`}
        </div>
      </div>`;
  }).join("");
}

/* ════════════════════════════════════════
   UTILITIES
════════════════════════════════════════ */
function esc(str) {
  const d = document.createElement("div");
  d.textContent = str || "";
  return d.innerHTML;
}

function spotifySvg() {
  return `<svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
  </svg>`;
}

function submitContact(e) {
  e.preventDefault();
  toast("Message sent! We'll be in touch 🎵", "ok");
  e.target.reset();
}

/* ════════════════════════════════════════
   INIT
════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  // Wire up buttons
  $("btnStart").addEventListener("click", handleStartBtn);
  $("btnDetect").addEventListener("click", detectEmotion);
  $("btnGetMusic").addEventListener("click", fetchMusic);
  const form = $("contactForm");
  if (form) form.addEventListener("submit", submitContact);

  // Initialise camera state
  setCamState(CAM.IDLE);

  // Scroll-reveal animation for cards
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting) {
        en.target.style.opacity   = "1";
        en.target.style.transform = "translateY(0)";
        io.unobserve(en.target);
      }
    });
  }, { threshold: 0.08 });

  document.querySelectorAll(".feat-card, .app-card, .hsw-step, .tip-img-card").forEach(el => {
    el.style.opacity    = "0";
    el.style.transform  = "translateY(20px)";
    el.style.transition = "opacity .5s ease, transform .5s ease";
    io.observe(el);
  });

  // Hero emoji cycler
  const heroEl  = $("heroEmoji");
  const emojis  = ["😊", "😢", "😠", "😨", "😲", "🤢", "😐"];
  let ei = 0;
  if (heroEl) {
    heroEl.style.transition = "opacity .3s ease";
    setInterval(() => {
      ei = (ei + 1) % emojis.length;
      heroEl.style.opacity = "0";
      setTimeout(() => {
        heroEl.textContent   = emojis[ei];
        heroEl.style.opacity = "1";
      }, 300);
    }, 2400);
  }

  console.log("🎵 MoodWave ready");
});