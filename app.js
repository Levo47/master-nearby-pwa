// --- PWA install button ---
let deferredPrompt = null;

function ensureInstallBtn() {
  let btn = document.getElementById("installBtn");
  if (btn) return btn;

  btn = document.createElement("button");
  btn.id = "installBtn";
  btn.textContent = "Установить";
  btn.style.marginLeft = "8px";
  btn.style.borderRadius = "12px";
  btn.style.padding = "10px 12px";
  btn.style.border = "1px solid var(--border)";
  btn.style.background = "#0b1224";
  btn.style.color = "var(--text)";
  btn.style.cursor = "pointer";
  btn.hidden = true;

  // вставим кнопку рядом с заголовком (вверх страницы)
  const wrap = document.querySelector(".wrap");
  const h1 = wrap?.querySelector("h1");
  if (h1 && h1.parentNode) h1.parentNode.insertBefore(btn, h1.nextSibling);

  btn.addEventListener("click", async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    deferredPrompt = null;
    btn.hidden = true;
  });

  return btn;
}

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = ensureInstallBtn();
  btn.hidden = false;
});

// --- Service Worker registration ---
if ("serviceWorker" in navigator) {
  window.addEventListener("load", async () => {
    try {
      await navigator.serviceWorker.register("/sw.js");
      // console.log("SW registered");
    } catch (err) {
      console.warn("SW registration failed:", err);
    }
  });
}

// --- App logic (geo + search) ---
const geoBtn = document.getElementById("geoBtn");
const searchBtn = document.getElementById("searchBtn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");
const serviceSelect = document.getElementById("serviceSelect");
const radiusSelect = document.getElementById("radiusSelect");
const verifiedOnlyEl = document.getElementById("verifiedOnly");

let userPos = null;

function setStatus(msg) {
  statusEl.textContent = msg || "";
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
  }[c]));
}

geoBtn.addEventListener("click", () => {
  if (!("geolocation" in navigator)) {
    setStatus("Геолокация не поддерживается этим браузером.");
    return;
  }

  setStatus("Определяю местоположение…");
  searchBtn.disabled = true;

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      userPos = { lat: pos.coords.latitude, lng: pos.coords.longitude };
      setStatus(`Готово ✅\nШирота: ${userPos.lat}\nДолгота: ${userPos.lng}`);
      searchBtn.disabled = false;
    },
    (err) => {
      console.log(err);
      setStatus("Не удалось получить геолокацию. Проверь разрешения в браузере.");
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
  );
});

searchBtn.addEventListener("click", async () => {
  if (!userPos) return;

  const service = serviceSelect.value;
  const radiusKm = Number(radiusSelect.value);
  const verifiedOnly = !!verifiedOnlyEl?.checked;

  setStatus("Ищу мастеров рядом…");
  resultsEl.innerHTML = "";

  const masters = await fetchMasters(service, radiusKm, userPos, verifiedOnly);

  if (!masters.length) {
    setStatus("Пока нет мастеров в этом радиусе.");
    return;
  }

  setStatus(`Нашёл: ${masters.length} (показано до 5)`);
  renderMasters(masters);
});

function renderMasters(list) {
  resultsEl.innerHTML = "";
  list.forEach((m) => {
    const div = document.createElement("div");
    div.className = "item";

    div.innerHTML = `
      <div class="top">
        <strong>${escapeHtml(m.name)}</strong>
        <span class="badge">⭐ ${m.rating.toFixed(1)} · ${m.jobs} заказов</span>
      </div>
      <div class="muted">${escapeHtml(m.tagline)}</div>
      <div class="muted">≈ ${m.distanceKm.toFixed(1)} км · от ${m.priceFrom} ₽</div>
      <div class="actions">
        <a class="action" href="tel:${m.phone}">Позвонить</a>
        <a class="action" href="sms:${m.phone}">SMS</a>
      </div>
    `;
    resultsEl.appendChild(div);
  });
}

function mockMasters(service) {
  const all = [
    { name: "Игорь, сантехник", phone: "+491234567890", rating: 4.8, jobs: 132, priceFrom: 50, tagline: "Приезжаю быстро, без навязываний", distanceKm: 0.8, service: "plumber" },
    { name: "Марина, сантехник", phone: "+491111222333", rating: 4.7, jobs: 64,  priceFrom: 45, tagline: "Чисто, аккуратно, по делу", distanceKm: 1.9, service: "plumber" },

    { name: "Алина, электрик", phone: "+492222333444", rating: 4.9, jobs: 98,  priceFrom: 60, tagline: "Аккуратно, с гарантией", distanceKm: 1.6, service: "electrician" },
    { name: "Павел, электрик", phone: "+493333444555", rating: 4.6, jobs: 51,  priceFrom: 55, tagline: "Розетки/свет/автоматы", distanceKm: 2.6, service: "electrician" },

    { name: "Сергей, сборка мебели", phone: "+494444555666", rating: 4.7, jobs: 210, priceFrom: 40, tagline: "IKEA/кухни/шкафы", distanceKm: 2.4, service: "furniture" },
    { name: "Денис, сборка мебели", phone: "+495555666777", rating: 4.8, jobs: 88,  priceFrom: 45, tagline: "Быстро и ровно 🙂", distanceKm: 1.1, service: "furniture" },

    { name: "Кирилл, мастер на час", phone: "+496666777888", rating: 4.6, jobs: 175, priceFrom: 35, tagline: "Полки, карнизы, мелкий ремонт", distanceKm: 1.2, service: "handyman" },
    { name: "Олег, мастер на час", phone: "+497777888999", rating: 4.5, jobs: 73,  priceFrom: 30, tagline: "Домашние задачи без лишних слов", distanceKm: 2.9, service: "handyman" }
  ];

  return all.filter(m => m.service === service);
}

async function fetchMasters(service, radiusKm, pos) {
  const url = `/api/masters?service=${encodeURIComponent(service)}&radius_km=${encodeURIComponent(radiusKm)}&lat=${encodeURIComponent(pos.lat)}&lng=${encodeURIComponent(pos.lng)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return (data.items || []).slice(0, 5);
}
