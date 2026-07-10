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
const PAGE_SIZE = 50;

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

function designBadge(status) {
  const s = (status || '').toUpperCase();
  if (s === 'BAKIR') return '<span class="badge badge-design-bakir"><i class="fa-solid fa-paintbrush-pencil"></i> Bakır</span>';
  if (s === 'AKTIF') return '<span class="badge badge-design-aktif"><i class="fa-solid fa-check"></i> Aktif</span>';
  return '<span class="badge badge-design-unknown">—</span>';
}

function statusBadge(status) {
  const s = (status || 'YENI').toUpperCase();
  const map = {
    'YENI'          : 'yeni',
    'ARANACAK'      : 'aranacak',
    'ULASILAMADI'   : 'ulasilamadi',
    'TEKLIF_BEKLIYOR': 'teklif',
    'OLUMLU'        : 'olumlu',
    'OLUMSUZ'       : 'olumsuz',
  };
  const cls = map[s] || 'yeni';
  const labels = {
    'YENI'           : 'Yeni',
    'ARANACAK'       : 'Aranacak',
    'ULASILAMADI'    : 'Ulaşılamadı',
    'TEKLIF_BEKLIYOR': 'Teklif Bekliyor',
    'OLUMLU'         : 'Olumlu',
    'OLUMSUZ'        : 'Olumsuz',
  };
  return `<span class="badge badge-status-${cls}">${labels[s] || s}</span>`;
}

function esc(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatDate(isoStr) {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('tr-TR', { day:'2-digit', month:'short', year:'numeric' });
  } catch { return isoStr; }
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
  const query  = (el('lead-search').value || '').toLowerCase();
  const design = el('filter-design').value;
  const status = el('filter-status').value;

  filteredLeads = allLeads.filter(l => {
    const matchQuery = !query || [
      l.domain, l.company_name, l.phone, l.email, l.address, l.authorized_person
    ].some(v => (v || '').toLowerCase().includes(query));

    const matchDesign = design === 'ALL' || (l.design_status || '').toUpperCase() === design;
    const matchStatus = status === 'ALL' || (l.crm_status || 'YENI').toUpperCase() === status;

    return matchQuery && matchDesign && matchStatus;
  });

  currentPage = 1;
  renderTable();
}

function renderTable() {
  const tbody = el('leads-table-body');
  const start = (currentPage - 1) * PAGE_SIZE;
  const page  = filteredLeads.slice(start, start + PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(filteredLeads.length / PAGE_SIZE));

  if (filteredLeads.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="table-empty"><i class="fa-solid fa-magnifying-glass"></i><br>Sonuç bulunamadı</td></tr>';
    el('table-info-text').textContent = '0 sonuç';
    el('pagination-controls').innerHTML = '';
    return;
  }

  tbody.innerHTML = page.map((lead, i) => {
    const hasPhone = lead.phone && lead.phone.trim();
    const hasEmail = lead.email && lead.email.trim();
    const idx      = allLeads.indexOf(lead);

    return `
    <tr onclick="openDrawer(${idx})">
      <td>
        <div class="domain-cell">
          <span>${esc(lead.domain)}</span>
          <a href="${esc(lead.url || 'https://' + lead.domain)}" target="_blank" onclick="event.stopPropagation()" title="Siteyi aç">
            <i class="fa-solid fa-arrow-up-right-from-square"></i>
          </a>
        </div>
        <div style="font-size:11px;color:var(--color-text-muted);margin-top:2px;">${esc(lead.company_name || '—')}</div>
      </td>
      <td>
        <div style="font-weight:600;font-size:13px;">${esc(lead.company_name || '—')}</div>
        <div style="font-size:11px;color:var(--color-text-muted);margin-top:2px;">${esc(lead.authorized_person || '—')}</div>
      </td>
      <td>${designBadge(lead.design_status)}</td>
      <td>${statusBadge(lead.crm_status)}</td>
      <td>
        <div class="contacts-summary">
          <span class="contact-pill ${hasPhone ? 'active' : ''}">
            <i class="fa-solid fa-phone"></i> ${hasPhone ? esc(lead.phone) : 'Yok'}
          </span>
          <span class="contact-pill ${hasEmail ? 'active' : ''}">
            <i class="fa-solid fa-envelope"></i> ${hasEmail ? esc(lead.email) : 'Yok'}
          </span>
        </div>
      </td>
      <td>
        <button class="btn-action-edit" title="Detayı aç" onclick="event.stopPropagation(); openDrawer(${idx})">
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </td>
    </tr>`;
  }).join('');

  // Footer info
  const from = start + 1;
  const to   = Math.min(start + PAGE_SIZE, filteredLeads.length);
  el('table-info-text').textContent = `${from}–${to} / ${filteredLeads.length} sonuç gösteriliyor`;

  // Pagination
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

    const now = new Date().toLocaleTimeString('tr-TR');
    el('last-updated-badge').textContent = `Son yükleme: ${now}`;

    updateStats();
    applyFilters();
  } catch (err) {
    el('leads-table-body').innerHTML = `<tr><td colspan="6" class="table-empty">
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
      ${designBadge(lead.design_status)}
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
      <div class="detail-label">Notlar</div>
      <textarea class="form-textarea" id="drawer-notes" placeholder="Bu firma hakkında notlar..."
        oninput="handleNotesChange(${idx}, this.value)">${esc(lead.notes || '')}</textarea>
    </div>

    <div class="save-status-container">
      <span class="save-status" id="drawer-save-status"></span>
    </div>

    <div class="detail-sec" style="font-size:11px;color:var(--color-text-muted);">
      <div>Keşfedilme: ${formatDate(lead.discovered_at)}</div>
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
      saveStatus.textContent = '⚠ GitHub ayarları eksik';
      saveStatus.className = 'save-status visible status-error';
    }
    el('global-save-indicator').textContent = '⚠ Ayarlar eksik — yerel değişiklikler kaydedilmedi';
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
    // Reset SHA so it's re-fetched on next attempt (might be a conflict)
    fileSha = null;
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

  // Reset SHA so we re-fetch with new credentials
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

  // Show token prompt if not configured
  const { token } = getGHConfig();
  if (!token) {
    el('global-save-indicator').textContent = '⚠ GitHub Token eksik (Konsoldan openSettings() çalıştırın)';
    el('global-save-indicator').style.color = 'var(--status-teklif-color)';
  }
});
