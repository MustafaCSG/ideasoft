/**
 * IdeaHunter CRM — GitHub Pages Edition
 * Reads leads.json locally (when served), then syncs changes back
 * to GitHub via the REST API using a PAT stored in localStorage.
 */

/* ─── Config ─────────────────────────────────────────── */
const LEADS_JSON_PATH   = './leads.json';
const GITHUB_API_BASE   = 'https://api.github.com';
const GITHUB_FILE_PATH  = 'docs/leads.json'; // path inside repo

/* ─── State ──────────────────────────────────────────── */
let allLeads    = [];
let filteredLeads = [];
let currentPage = 1;
const PAGE_SIZE = 12; // Matches itemsPerPage from local server

let saveTimer   = null;
let fileSha     = null;  // GitHub blob SHA, needed for updates

/* ─── GitHub Config (Locked to MustafaCSG/ideasoft) ─── */
function getGHConfig() {
  return {
    owner : 'MustafaCSG',
    repo  : 'ideasoft',
    token : localStorage.getItem('gh_token') || '',
  };
}

/* ─── Helpers ────────────────────────────────────────── */
function el(id) { return document.getElementById(id); }

function esc(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function isToday(dateString) {
  if (!dateString) return false;
  const datePart = dateString.substring(0, 10);
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  const todayStr = `${year}-${month}-${day}`;
  return datePart === todayStr;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const parts = dateStr.split(" ");
  if (parts.length >= 1) {
    const dateParts = parts[0].split("-");
    if (dateParts.length === 3) {
      const formattedDate = `${dateParts[2]}.${dateParts[1]}.${dateParts[0]}`;
      if (parts.length > 1) {
        const timeParts = parts[1].split(":");
        return `${formattedDate} ${timeParts[0]}:${timeParts[1]}`;
      }
      return formattedDate;
    }
  }
  return dateStr;
}

/* ─── Stats ──────────────────────────────────────────── */
function updateStats() {
  const total   = allLeads.length;
  const bakir   = allLeads.filter(l => (l.design_status || '').toUpperCase() === 'BAKIR').length;
  const called  = allLeads.filter(l => l.crm_status && l.crm_status !== 'YENI').length;
  const success = allLeads.filter(l => (l.crm_status || '').toUpperCase() === 'OLUMLU').length;

  el('stat-total-leads').textContent  = total;
  el('stat-bakir-leads').textContent  = bakir;
  el('stat-called-leads').textContent = called;
  el('stat-success-leads').textContent = success;
  el('stat-called-percent').textContent =
    total > 0 ? `Arama oranı: %${Math.round(called / total * 100)}` : 'Arama oranı: %0';
}

/* ─── Table rendering ────────────────────────────────── */
function applyFilters() {
  const query  = (el('lead-search').value || '').toLowerCase().trim();
  const design = el('filter-design').value;
  const status = el('filter-status').value;

  filteredLeads = allLeads.filter(l => {
    const matchesSearch = !query || [
      l.domain, l.company_name, l.phone, l.email, l.address, l.authorized_person,
      (Array.isArray(l.tags) ? l.tags.join(', ') : (l.tags || ''))
    ].some(v => (v || '').toLowerCase().includes(query));

    let matchesDesign = true;
    if (design === "BAKIR") {
      matchesDesign = (l.design_status || '').toUpperCase().includes("BAKIR");
    } else if (design === "AKTIF") {
      matchesDesign = (l.design_status || '').toUpperCase().includes("AKTIF");
    }

    let matchesStatus = true;
    if (status !== "ALL") {
      matchesStatus = (l.crm_status || 'YENI').toUpperCase() === status;
    }

    return matchesSearch && matchesDesign && matchesStatus;
  });

  currentPage = 1;
  renderTable();
}

function renderTable() {
  const tbody = el('leads-table-body');
  if (filteredLeads.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="table-empty"><i class="fa-solid fa-folder-open"></i> Eşleşen kayıt bulunamadı.</td></tr>';
    el('table-info-text').textContent = 'Gösterilen kayıt: 0 / 0';
    el('pagination-controls').innerHTML = '';
    return;
  }

  const start = (currentPage - 1) * PAGE_SIZE;
  const end   = Math.min(start + PAGE_SIZE, filteredLeads.length);
  const page  = filteredLeads.slice(start, end);
  const totalPages = Math.max(1, Math.ceil(filteredLeads.length / PAGE_SIZE));

  tbody.innerHTML = page.map(lead => {
    const idx = allLeads.indexOf(lead);
    
    // Design Status Badge
    let designClass = "badge-design-unknown";
    let designText = "Belirsiz";
    if ((lead.design_status || '').toUpperCase().includes("BAKIR")) {
      designClass = "badge-design-bakir";
      designText = "BAKIR (Boş)";
    } else if ((lead.design_status || '').toUpperCase().includes("AKTIF")) {
      designClass = "badge-design-aktif";
      designText = "AKTİF";
    }

    // Status Badge Class
    let statusClass = "badge-status-yeni";
    let statusText = "Yeni";
    switch (lead.crm_status) {
      case "ARANACAK":
        statusClass = "badge-status-aranacak";
        statusText = "Aranacak";
        break;
      case "ULASILAMADI":
        statusClass = "badge-status-ulasilamadi";
        statusText = "Ulaşılamadı";
        break;
      case "TEKLIF_BEKLIYOR":
        statusClass = "badge-status-teklif";
        statusText = "Teklif";
        break;
      case "OLUMLU":
        statusClass = "badge-status-olumlu";
        statusText = "Olumlu";
        break;
      case "OLUMSUZ":
        statusClass = "badge-status-olumsuz";
        statusText = "Olumsuz";
        break;
    }

    // Generate contacts info summary
    let contactPills = "";
    if (lead.phone) {
      const phonesCount = lead.phone.split(",").length;
      contactPills += `<span class="contact-pill active" title="${esc(lead.phone)}"><i class="fa-solid fa-phone"></i> ${phonesCount} adet</span>`;
    }
    if (lead.email) {
      const emailsCount = lead.email.split(",").length;
      contactPills += `<span class="contact-pill active" title="${esc(lead.email)}"><i class="fa-solid fa-envelope"></i> ${emailsCount} adet</span>`;
    }
    if (!contactPills) {
      contactPills = `<span class="contact-pill"><i class="fa-solid fa-circle-minus"></i> Bulunamadı</span>`;
    }

    let todayBadge = "";
    if (isToday(lead.scraped_at)) {
      todayBadge = `<span class="badge-today-pulse">BUGÜN</span>`;
    }

    let tagBadges = "";
    if (Array.isArray(lead.tags)) {
      lead.tags.forEach(t => {
        const cleanedTag = t.trim();
        if (cleanedTag) {
          tagBadges += `<span class="badge-tag">${esc(cleanedTag)}</span>`;
        }
      });
    } else if (lead.tags) {
      lead.tags.split(",").forEach(t => {
        const cleanedTag = t.trim();
        if (cleanedTag) {
          tagBadges += `<span class="badge-tag">${esc(cleanedTag)}</span>`;
        }
      });
    }

    const formattedDate = formatDate(lead.scraped_at);

    return `
      <tr onclick="openDrawer(${idx})">
        <td>
          <div class="domain-cell-container">
            <div class="domain-cell-top">
              <span class="domain-name" title="${esc(lead.domain)}">${esc(lead.domain)}</span>
              ${todayBadge}
              ${tagBadges}
            </div>
            <div class="domain-actions">
              <a href="https://${esc(lead.domain)}" target="_blank" onclick="event.stopPropagation();" class="domain-action-btn" title="Ana Sayfayı Aç">
                <i class="fa-solid fa-globe"></i> Ana Sayfa
              </a>
              <a href="https://${esc(lead.domain)}/iletisim" target="_blank" onclick="event.stopPropagation();" class="domain-action-btn contact-btn" title="İletişim Sayfasını Aç">
                <i class="fa-solid fa-address-book"></i> İletişim
              </a>
            </div>
          </div>
        </td>
        <td>
          <div>${esc(lead.company_name || 'Bilinmiyor')}</div>
          ${lead.authorized_person ? `<small style="color:var(--color-text-muted); font-size:11px; display:inline-flex; align-items:center; gap:4px; margin-top:2px;"><i class="fa-solid fa-user-tie"></i> ${esc(lead.authorized_person)}</small>` : ''}
        </td>
        <td>
          <div class="date-cell" style="font-size: 13px; color: var(--color-text-secondary);">${esc(formattedDate)}</div>
        </td>
        <td><span class="badge ${designClass}">${designText}</span></td>
        <td><span class="badge ${statusClass}">${statusText}</span></td>
        <td><div class="contacts-summary">${contactPills}</div></td>
        <td>
          <button class="btn-action-edit" title="Detayları Görüntüle / Düzenle" onclick="event.stopPropagation(); openDrawer(${idx})">
            <i class="fa-solid fa-pen-to-square"></i> Detay
          </button>
        </td>
      </tr>`;
  }).join('');

  el('table-info-text').textContent = `Gösterilen kayıt: ${start + 1} - ${end} / ${filteredLeads.length}`;
  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  const pagCtrl = el('pagination-controls');
  let pagHTML = `<button class="btn-page" onclick="goPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
    <i class="fa-solid fa-chevron-left"></i>
  </button>`;

  const windowSize = 5;
  let startP = Math.max(1, currentPage - Math.floor(windowSize / 2));
  let endP   = Math.min(totalPages, startP + windowSize - 1);
  if (endP - startP < windowSize - 1) startP = Math.max(1, endP - windowSize + 1);

  for (let p = startP; p <= endP; p++) {
    pagHTML += `<button class="btn-page ${p === currentPage ? 'active' : ''}" onclick="goPage(${p})">${p}</button>`;
  }

  pagHTML += `<button class="btn-page" onclick="goPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>
    <i class="fa-solid fa-chevron-right"></i>
  </button>`;

  pagCtrl.innerHTML = pagHTML;
}

function goPage(n) {
  const totalPages = Math.max(1, Math.ceil(filteredLeads.length / PAGE_SIZE));
  if (n < 1 || n > totalPages) return;
  currentPage = n;
  renderTable();
}

/* ─── Lead Loading ───────────────────────────────────── */
async function loadLeads() {
  try {
    const res  = await fetch(`${LEADS_JSON_PATH}?t=${Date.now()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allLeads = Array.isArray(data) ? data : Object.values(data);

    // Normalize status fields
    allLeads.forEach(l => {
      if (!l.crm_status && l.call_status) {
        l.crm_status = l.call_status;
      }
    });

    const now = new Date().toLocaleTimeString('tr-TR');
    el('last-updated-badge').textContent = `Son yükleme: ${now}`;

    updateStats();
    applyFilters();
  } catch (err) {
    el('leads-table-body').innerHTML = `<tr><td colspan="7" class="table-empty">
      <i class="fa-solid fa-circle-exclamation" style="color:#f87171;"></i><br>
      <strong>leads.json yüklenemedi.</strong><br>
      <small style="color:var(--color-text-muted);">${err.message}</small>
    </td></tr>`;
    console.error('loadLeads error:', err);
  }
}

/* ─── Detail Drawer ──────────────────────────────────── */
function openDrawer(idx) {
  const lead = allLeads[idx];
  if (!lead) return;

  const tagList = Array.isArray(lead.tags) ? lead.tags.join(', ') : (lead.tags || '');

  const content = `
    <div class="detail-sec">
      <div class="detail-label">Domain</div>
      <div class="detail-val-domain">
        ${esc(lead.domain)}
        <a href="${esc(lead.url || 'https://' + lead.domain)}" target="_blank" style="font-size:14px;color:var(--color-text-muted);margin-left:8px;">
          <i class="fa-solid fa-arrow-up-right-from-square"></i>
        </a>
      </div>
    </div>

    <div class="detail-sec">
      <div class="detail-label">Şirket Bilgileri</div>
      <div class="detail-contacts-list">
        <div class="detail-contact-row">
          <i class="fa-solid fa-building"></i>
          <span>${esc(lead.company_name || '—')}</span>
        </div>
        <div class="detail-contact-row">
          <i class="fa-solid fa-user-tie"></i>
          <span>${esc(lead.authorized_person || '—')}</span>
        </div>
        <div class="detail-contact-row">
          <i class="fa-solid fa-phone"></i>
          <span>${esc(lead.phone || '—')}</span>
        </div>
        <div class="detail-contact-row">
          <i class="fa-solid fa-envelope"></i>
          <span>${esc(lead.email || '—')}</span>
        </div>
        <div class="detail-contact-row">
          <i class="fa-solid fa-location-dot"></i>
          <span>${esc(lead.address || '—')}</span>
        </div>
      </div>
    </div>

    <div class="detail-sec">
      <div class="detail-label">Tasarım Durumu</div>
      <select class="form-select" id="drawer-design-status" onchange="handleDesignStatusChange(${idx}, this.value)">
        <option value="BAKIR" ${(lead.design_status||'').toUpperCase().includes('BAKIR')?'selected':''}>BAKIR (Boş Mağaza)</option>
        <option value="AKTIF" ${(lead.design_status||'').toUpperCase().includes('AKTIF')?'selected':''}>AKTİF (Tasarımı Var)</option>
      </select>
    </div>

    <div class="detail-sec">
      <div class="detail-label">CRM Durumu</div>
      <select class="form-select" id="drawer-crm-status" onchange="handleStatusChange(${idx}, this.value)">
        <option value="YENI"           ${(lead.crm_status||'YENI')==='YENI'?'selected':''}>Yeni</option>
        <option value="ARANACAK"       ${lead.crm_status==='ARANACAK'?'selected':''}>Aranacak</option>
        <option value="ULASILAMADI"    ${lead.crm_status==='ULASILAMADI'?'selected':''}>Ulaşılamadı</option>
        <option value="TEKLIF_BEKLIYOR"${lead.crm_status==='TEKLIF_BEKLIYOR'?'selected':''}>Teklif Bekliyor</option>
        <option value="OLUMLU"         ${lead.crm_status==='OLUMLU'?'selected':''}>Olumlu</option>
        <option value="OLUMSUZ"        ${lead.crm_status==='OLUMSUZ'?'selected':''}>Olumsuz</option>
      </select>
    </div>

    <div class="detail-sec">
      <div class="detail-label">Etiketler</div>
      <div style="font-size: 13px; font-weight: 500; color: var(--color-text-secondary); background: rgba(255,255,255,0.03); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border-color);">${esc(tagList || '—')}</div>
    </div>

    <div class="detail-sec">
      <div class="detail-label">Notlar</div>
      <textarea class="form-textarea" id="drawer-notes" placeholder="Bu firma hakkında notlar..."
        oninput="handleNotesChange(${idx}, this.value)">${esc(lead.notes || '')}</textarea>
    </div>

    <div class="save-status-container">
      <span class="save-status" id="drawer-save-status"></span>
    </div>

    <div class="detail-sec" style="font-size:11px;color:var(--color-text-muted);">
      <div>Keşfedilme: ${formatDate(lead.scraped_at)}</div>
      <div>Son güncelleme: ${formatDate(lead.updated_at)}</div>
    </div>
  `;

  el('drawer-body-content').innerHTML = content;
  el('detail-drawer').classList.add('open');
  el('drawer-overlay').classList.add('active');
}

function closeDrawer() {
  el('detail-drawer').classList.remove('open');
  el('drawer-overlay').classList.remove('active');
}

/* ─── CRM Edits ──────────────────────────────────────── */
function handleStatusChange(idx, value) {
  allLeads[idx].crm_status = value;
  allLeads[idx].call_status = value; // keep both synced
  allLeads[idx].updated_at = new Date().toISOString();
  scheduleSave(idx);
  updateStats();
  renderTable();
}

function handleDesignStatusChange(idx, value) {
  allLeads[idx].design_status = value;
  allLeads[idx].updated_at = new Date().toISOString();
  scheduleSave(idx);
  updateStats();
  renderTable();
}

function handleNotesChange(idx, value) {
  allLeads[idx].notes = value;
  allLeads[idx].updated_at = new Date().toISOString();
  scheduleSave(idx);
}

function scheduleSave(idx) {
  const saveStatus = el('drawer-save-status');
  if (saveStatus) {
    saveStatus.textContent = '● Kaydediliyor...';
    saveStatus.className = 'save-status visible status-saving';
  }

  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => commitToGitHub(), 2000); // 2s debounce
}

/* ─── GitHub Commit ──────────────────────────────────── */
async function fetchFileSha() {
  const { owner, repo, token } = getGHConfig();
  if (!owner || !repo || !token) return null;

  try {
    const res = await fetch(`${GITHUB_API_BASE}/repos/${owner}/${repo}/contents/${GITHUB_FILE_PATH}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept': 'application/vnd.github+json',
      }
    });
    if (res.ok) {
      const data = await res.json();
      return data.sha;
    }
  } catch (e) { console.error('fetchFileSha:', e); }
  return null;
}

async function commitToGitHub() {
  const { owner, repo, token } = getGHConfig();
  if (!owner || !repo || !token) {
    const saveStatus = el('drawer-save-status');
    if (saveStatus) {
      saveStatus.textContent = '⚠ GitHub Token eksik (Konsoldan openSettings() çalıştırın)';
      saveStatus.className = 'save-status visible status-error';
    }
    el('global-save-indicator').textContent = '⚠ Token eksik — yerel değişiklikler kaydedilmedi';
    return;
  }

  try {
    const saveStatus = el('drawer-save-status');

    // Get current SHA if we don't have it
    if (!fileSha) {
      fileSha = await fetchFileSha();
    }

    const content   = JSON.stringify(allLeads, null, 2);
    const encoded   = btoa(unescape(encodeURIComponent(content)));
    const now       = new Date().toLocaleString('tr-TR');

    const body = {
      message: `CRM güncellendi: ${now}`,
      content : encoded,
      ...(fileSha ? { sha: fileSha } : {})
    };

    const res = await fetch(`${GITHUB_API_BASE}/repos/${owner}/${repo}/contents/${GITHUB_FILE_PATH}`, {
      method : 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Accept'       : 'application/vnd.github+json',
        'Content-Type' : 'application/json',
      },
      body: JSON.stringify(body)
    });

    if (res.ok) {
      const data = await res.json();
      fileSha = data.content.sha;
      if (saveStatus) {
        saveStatus.textContent = '✓ GitHub\'a kaydedildi';
        saveStatus.className = 'save-status visible status-saved';
        setTimeout(() => { saveStatus.classList.remove('visible'); }, 3000);
      }
      el('global-save-indicator').textContent = `✓ ${now} kaydedildi`;
    } else {
      const err = await res.json();
      throw new Error(err.message || `HTTP ${res.status}`);
    }
  } catch (err) {
    console.error('commitToGitHub:', err);
    const saveStatus = el('drawer-save-status');
    if (saveStatus) {
      saveStatus.textContent = `✗ Hata: ${err.message}`;
      saveStatus.className = 'save-status visible status-error';
    }
    el('global-save-indicator').textContent = `✗ Kayıt hatası: ${err.message}`;
    fileSha = null; // reset SHA on error to re-fetch
  }
}

/* ─── Settings Modal ─────────────────────────────────── */
function openSettings() {
  const cfg = getGHConfig();
  el('cfg-owner').value = cfg.owner;
  el('cfg-repo').value  = cfg.repo;
  el('cfg-token').value = cfg.token;
  el('settings-status').textContent = '';
  el('settings-overlay').style.display = 'flex';
}

function closeSettings() {
  el('settings-overlay').style.display = 'none';
}

function saveSettings() {
  const owner = el('cfg-owner').value.trim();
  const repo  = el('cfg-repo').value.trim();
  const token = el('cfg-token').value.trim();

  if (!owner || !repo || !token) {
    el('settings-status').textContent = '⚠ Tüm alanlar zorunludur.';
    el('settings-status').style.color = 'var(--status-ulasilamadi-color)';
    return;
  }

  localStorage.setItem('gh_owner', owner);
  localStorage.setItem('gh_repo',  repo);
  localStorage.setItem('gh_token', token);

  fileSha = null;

  el('settings-status').textContent = '✓ Kaydedildi!';
  el('settings-status').style.color = 'var(--status-olumlu-color)';
  setTimeout(closeSettings, 1200);
}

/* ─── Event Listeners & Init ─────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  loadLeads();

  el('btn-refresh-leads').addEventListener('click', loadLeads);
  el('btn-close-drawer').addEventListener('click', closeDrawer);
  el('drawer-overlay').addEventListener('click', closeDrawer);
  el('lead-search').addEventListener('input', applyFilters);
  el('filter-design').addEventListener('change', applyFilters);
  el('filter-status').addEventListener('change', applyFilters);

  // Close settings on overlay click
  el('settings-overlay').addEventListener('click', (e) => {
    if (e.target === el('settings-overlay')) closeSettings();
  });

  // Mobile Sidebar Toggles
  const btnToggleSidebar = el("btn-toggle-sidebar");
  const btnCloseSidebar = el("btn-close-sidebar");
  const appSidebar = el("app-sidebar");

  if (btnToggleSidebar && appSidebar) {
    btnToggleSidebar.addEventListener("click", () => {
      appSidebar.classList.add("open");
    });
  }

  if (btnCloseSidebar && appSidebar) {
    btnCloseSidebar.addEventListener("click", () => {
      appSidebar.classList.remove("open");
    });
  }

  document.querySelectorAll(".sidebar-menu .menu-item").forEach(item => {
    item.addEventListener("click", () => {
      if (appSidebar) {
        appSidebar.classList.remove("open");
      }
    });
  });

  // Show token prompt if not configured
  const { token } = getGHConfig();
  if (!token) {
    el('global-save-indicator').textContent = '⚠ GitHub Token eksik (Konsoldan openSettings() çalıştırın)';
    el('global-save-indicator').style.color = 'var(--status-teklif-color)';
  }
});
