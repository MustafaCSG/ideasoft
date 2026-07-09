// Global App State
let leadsData = [];
let filteredLeads = [];
let currentPage = 1;
const itemsPerPage = 12;

// Auto-Save timeout helper
let saveTimeout = null;

// DOM Elements
const tbody = document.getElementById("leads-table-body");
const searchInput = document.getElementById("lead-search");
const filterDesign = document.getElementById("filter-design");
const filterStatus = document.getElementById("filter-status");
const refreshBtn = document.getElementById("btn-refresh-leads");
const drawer = document.getElementById("detail-drawer");
const drawerOverlay = document.getElementById("drawer-overlay");
const drawerCloseBtn = document.getElementById("btn-close-drawer");
const drawerContent = document.getElementById("drawer-body-content");
const paginationContainer = document.getElementById("pagination-controls");
const tableInfo = document.getElementById("table-info-text");

// Stats DOM Elements
const statTotal = document.getElementById("stat-total-leads");
const statBakir = document.getElementById("stat-bakir-leads");
const statCalled = document.getElementById("stat-called-leads");
const statCalledPercent = document.getElementById("stat-called-percent");
const statSuccess = document.getElementById("stat-success-leads");

// Load Initial Data
document.addEventListener("DOMContentLoaded", () => {
    fetchLeads();
    fetchStats();
    
    // Bind Event Listeners
    searchInput.addEventListener("input", handleFiltersChange);
    filterDesign.addEventListener("change", handleFiltersChange);
    filterStatus.addEventListener("change", handleFiltersChange);
    refreshBtn.addEventListener("click", () => {
        fetchLeads();
        fetchStats();
    });
    
    drawerCloseBtn.addEventListener("click", closeDrawer);
    drawerOverlay.addEventListener("click", closeDrawer);

    // Mobile Sidebar Toggles
    const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
    const btnCloseSidebar = document.getElementById("btn-close-sidebar");
    const appSidebar = document.getElementById("app-sidebar");

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
});

// Fetch all leads from API
async function fetchLeads() {
    tbody.innerHTML = `<tr><td colspan="7" class="table-loading"><i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor...</td></tr>`;
    try {
        const res = await fetch("/api/leads");
        if (res.ok) {
            leadsData = await res.json();
            applyFilters();
        } else {
            tbody.innerHTML = `<tr><td colspan="7" class="table-empty"><i class="fa-solid fa-triangle-exclamation"></i> Veriler alınamadı! (HTTP ${res.status})</td></tr>`;
        }
    } catch (err) {
        console.error("Fetch error:", err);
        tbody.innerHTML = `<tr><td colspan="7" class="table-empty"><i class="fa-solid fa-triangle-exclamation"></i> Hata: Sunucuya bağlanılamadı.</td></tr>`;
    }
}

// Fetch stats counters from API
async function fetchStats() {
    try {
        const res = await fetch("/api/stats");
        if (res.ok) {
            const stats = await res.json();
            statTotal.innerText = stats.total_leads;
            statBakir.innerText = stats.design_breakdown["BAKIR / YAPIM ASAMASINDA"] || 0;
            statCalled.innerText = stats.total_called;
            statSuccess.innerText = stats.status_breakdown["OLUMLU"] || 0;
            
            // Calculate call rate percentage
            if (stats.total_leads > 0) {
                const percent = Math.round((stats.total_called / stats.total_leads) * 100);
                statCalledPercent.innerText = `Arama oranı: %${percent}`;
            } else {
                statCalledPercent.innerText = `Arama oranı: %0`;
            }
        }
    } catch (err) {
        console.error("Stats error:", err);
    }
}

// Filter logic based on UI controls
function handleFiltersChange() {
    currentPage = 1;
    applyFilters();
}

function applyFilters() {
    const searchVal = searchInput.value.toLowerCase().trim();
    const designFilter = filterDesign.value;
    const statusFilter = filterStatus.value;
    
    filteredLeads = leadsData.filter(lead => {
        // 1. Search Query Filter
        const matchesSearch = 
            lead.domain.toLowerCase().includes(searchVal) ||
            lead.company_name.toLowerCase().includes(searchVal) ||
            lead.phone.toLowerCase().includes(searchVal) ||
            lead.email.toLowerCase().includes(searchVal) ||
            lead.tags.toLowerCase().includes(searchVal) ||
            lead.address.toLowerCase().includes(searchVal);
            
        // 2. Design Status Filter
        let matchesDesign = true;
        if (designFilter === "BAKIR") {
            matchesDesign = lead.design_status.includes("BAKIR");
        } else if (designFilter === "AKTIF") {
            matchesDesign = lead.design_status.includes("AKTIF");
        }
        
        // 3. Call Status Filter
        let matchesStatus = true;
        if (statusFilter !== "ALL") {
            matchesStatus = lead.call_status === statusFilter;
        }
        
        return matchesSearch && matchesDesign && matchesStatus;
    });
    
    renderLeadsTable();
}

// Render the leads inside the table body
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

function renderLeadsTable() {
    if (filteredLeads.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="table-empty"><i class="fa-solid fa-folder-open"></i> Eşleşen kayıt bulunamadı.</td></tr>`;
        tableInfo.innerText = "Gösterilen kayıt: 0 / 0";
        paginationContainer.innerHTML = "";
        return;
    }
    
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredLeads.length);
    const paginatedLeads = filteredLeads.slice(startIndex, endIndex);
    
    tbody.innerHTML = "";
    
    paginatedLeads.forEach(lead => {
        const tr = document.createElement("tr");
        tr.addEventListener("click", () => openLeadDrawer(lead));
        
        // Design Status Badge
        let designClass = "badge-design-unknown";
        let designText = "Belirsiz";
        if (lead.design_status.includes("BAKIR")) {
            designClass = "badge-design-bakir";
            designText = "BAKIR (Boş)";
        } else if (lead.design_status.includes("AKTIF")) {
            designClass = "badge-design-aktif";
            designText = "AKTİF";
        }
        
        // Status Badge Class
        let statusClass = "badge-status-yeni";
        let statusText = "Yeni";
        
        switch (lead.call_status) {
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
            contactPills += `<span class="contact-pill active" title="${lead.phone}"><i class="fa-solid fa-phone"></i> ${phonesCount} adet</span>`;
        }
        if (lead.email) {
            const emailsCount = lead.email.split(",").length;
            contactPills += `<span class="contact-pill active" title="${lead.email}"><i class="fa-solid fa-envelope"></i> ${emailsCount} adet</span>`;
        }
        
        if (!contactPills) {
            contactPills = `<span class="contact-pill"><i class="fa-solid fa-circle-minus"></i> Bulunamadı</span>`;
        }
        
        let todayBadge = "";
        if (isToday(lead.scraped_at)) {
            todayBadge = `<span class="badge-today-pulse">BUGÜN</span>`;
        }
        
        let tagBadges = "";
        if (lead.tags) {
            lead.tags.split(",").forEach(t => {
                const cleanedTag = t.trim();
                if (cleanedTag) {
                    tagBadges += `<span class="badge-tag">${cleanedTag}</span>`;
                }
            });
        }
        
        const formattedDate = formatDate(lead.scraped_at);
        
        tr.innerHTML = `
            <td>
                <div class="domain-cell-container">
                    <div class="domain-cell-top">
                        <span class="domain-name" title="${lead.domain}">${lead.domain}</span>
                        ${todayBadge}
                        ${tagBadges}
                    </div>
                    <div class="domain-actions">
                        <a href="https://${lead.domain}" target="_blank" onclick="event.stopPropagation();" class="domain-action-btn" title="Ana Sayfayı Aç">
                            <i class="fa-solid fa-globe"></i> Ana Sayfa
                        </a>
                        <a href="https://${lead.domain}/iletisim" target="_blank" onclick="event.stopPropagation();" class="domain-action-btn contact-btn" title="İletişim Sayfasını Aç">
                            <i class="fa-solid fa-address-book"></i> İletişim
                        </a>
                    </div>
                </div>
            </td>
            <td>
                <div>${lead.company_name}</div>
                ${lead.authorized_person ? `<small style="color:var(--color-text-muted); font-size:11px; display:inline-flex; align-items:center; gap:4px; margin-top:2px;"><i class="fa-solid fa-user-tie"></i> ${lead.authorized_person}</small>` : ''}
            </td>
            <td>
                <div class="date-cell" style="font-size: 13px; color: var(--color-text-secondary);">${formattedDate}</div>
            </td>
            <td><span class="badge ${designClass}">${designText}</span></td>
            <td><span class="badge ${statusClass}">${statusText}</span></td>
            <td><div class="contacts-summary">${contactPills}</div></td>
            <td>
                <button class="btn-action-edit" title="Detayları Görüntüle / Düzenle">
                    <i class="fa-solid fa-pen-to-square"></i> Detay
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
    
    tableInfo.innerText = `Gösterilen kayıt: ${startIndex + 1} - ${endIndex} / ${filteredLeads.length}`;
    renderPagination();
}

// Generate pagination controls
function renderPagination() {
    const totalPages = Math.ceil(filteredLeads.length / itemsPerPage);
    paginationContainer.innerHTML = "";
    
    if (totalPages <= 1) return;
    
    // Previous Button
    const prevBtn = document.createElement("button");
    prevBtn.className = "btn-page";
    prevBtn.innerHTML = `<i class="fa-solid fa-chevron-left"></i>`;
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            renderLeadsTable();
        }
    });
    paginationContainer.appendChild(prevBtn);
    
    // Page Numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
            const pageBtn = document.createElement("button");
            pageBtn.className = `btn-page ${i === currentPage ? "active" : ""}`;
            pageBtn.innerText = i;
            pageBtn.addEventListener("click", () => {
                currentPage = i;
                renderLeadsTable();
            });
            paginationContainer.appendChild(pageBtn);
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            const dots = document.createElement("span");
            dots.innerText = "...";
            dots.style.alignSelf = "center";
            dots.style.margin = "0 4px";
            paginationContainer.appendChild(dots);
        }
    }
    
    // Next Button
    const nextBtn = document.createElement("button");
    nextBtn.className = "btn-page";
    nextBtn.innerHTML = `<i class="fa-solid fa-chevron-right"></i>`;
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener("click", () => {
        if (currentPage < totalPages) {
            currentPage++;
            renderLeadsTable();
        }
    });
    paginationContainer.appendChild(nextBtn);
}

// Open Detail Drawer
function openLeadDrawer(lead) {
    drawer.classList.add("open");
    drawerOverlay.classList.add("active");
    
    // Prepare contact details list UI
    let contactHTML = "";
    if (lead.phone) {
        lead.phone.split(",").forEach(p => {
            contactHTML += `
                <div class="detail-contact-row">
                    <i class="fa-solid fa-phone"></i>
                    <span>${p.trim()}</span>
                    <a href="tel:${p.trim()}" class="btn-action-edit" title="Ara" style="margin-left:auto;"><i class="fa-solid fa-phone-flip"></i></a>
                </div>`;
        });
    }
    if (lead.email) {
        lead.email.split(",").forEach(e => {
            contactHTML += `
                <div class="detail-contact-row">
                    <i class="fa-solid fa-envelope"></i>
                    <span>${e.trim()}</span>
                    <a href="mailto:${e.trim()}" class="btn-action-edit" title="E-posta gönder" style="margin-left:auto;"><i class="fa-solid fa-paper-plane"></i></a>
                </div>`;
        });
    }
    
    if (!contactHTML) {
        contactHTML = `<div class="detail-val-text" style="color:var(--color-text-muted);">İletişim bilgisi bulunamadı.</div>`;
    }
    
    drawerContent.innerHTML = `
        <div class="detail-sec">
            <div class="detail-label">Alan Adı (Domain)</div>
            <div class="detail-val-domain">${lead.domain}</div>
            <a href="https://${lead.domain}" target="_blank" class="detail-val-text" style="color:var(--primary-hover); text-decoration:none;">
                <i class="fa-solid fa-link"></i> Web sitesini aç
            </a>
        </div>
        
        <div class="detail-sec">
            <div class="detail-label">Şirket Adı / Ticari Ünvanı</div>
            <input type="text" class="form-input" id="drawer-company-name" value="${lead.company_name}" placeholder="Şirket adını girin...">
        </div>
        
        <div class="detail-sec">
            <div class="detail-label">Firma Yetkilisi</div>
            <input type="text" class="form-input" id="drawer-authorized-person" value="${lead.authorized_person}" placeholder="Yetkili adını soyadını girin...">
        </div>
        
        <div class="detail-sec">
            <div class="detail-label">Tasarım Altyapı Durumu</div>
            <div class="detail-val-text" style="font-weight:600; color: #fff;">
                ${lead.design_status}
            </div>
        </div>
        
        <div class="detail-sec">
            <div class="detail-label">İletişim Bilgileri</div>
            <div class="detail-contacts-list">${contactHTML}</div>
        </div>
        
        <div class="detail-sec">
            <div class="detail-label">Adres Bilgisi</div>
            <div class="detail-val-text">${lead.address || "Bulunamadı"}</div>
        </div>
        
        <div style="border-top:1px solid var(--border-color); margin: 10px 0;"></div>
        
        <div class="detail-sec">
            <div class="detail-label">Arama Aşaması (Call Status)</div>
            <select class="form-select" id="drawer-call-status">
                <option value="YENI" ${lead.call_status === "YENI" ? "selected" : ""}>Yeni Yakalanan</option>
                <option value="ARANACAK" ${lead.call_status === "ARANACAK" ? "selected" : ""}>Aranacak</option>
                <option value="ULASILAMADI" ${lead.call_status === "ULASILAMADI" ? "selected" : ""}>Ulaşılamadı</option>
                <option value="TEKLIF_BEKLIYOR" ${lead.call_status === "TEKLIF_BEKLIYOR" ? "selected" : ""}>Teklif Bekliyor</option>
                <option value="OLUMLU" ${lead.call_status === "OLUMLU" ? "selected" : ""}>Olumlu (Satış)</option>
                <option value="OLUMSUZ" ${lead.call_status === "OLUMSUZ" ? "selected" : ""}>Olumsuz</option>
            </select>
        </div>
        
        <div class="detail-sec">
            <div class="detail-label">Arama / Görüşme Notları</div>
            <textarea class="form-textarea" id="drawer-notes" placeholder="Müşteri görüşmesi hakkında notlar yazın... (Örn: Fiyat yüksek dedi, haftaya aranacak)">${lead.notes}</textarea>
        </div>
        
        <div class="save-status-container">
            <span class="save-status" id="drawer-save-status"></span>
        </div>
    `;
    
    // Bind change/input events for auto-save
    const statusSelect = document.getElementById("drawer-call-status");
    const notesTextarea = document.getElementById("drawer-notes");
    const companyInput = document.getElementById("drawer-company-name");
    const authorizedInput = document.getElementById("drawer-authorized-person");
    
    statusSelect.addEventListener("change", () => {
        saveLeadChanges(lead.domain, statusSelect.value, notesTextarea.value, authorizedInput.value, companyInput.value);
    });
    
    notesTextarea.addEventListener("input", () => {
        showSaveStatus("saving", "Kaydediliyor...");
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            saveLeadChanges(lead.domain, statusSelect.value, notesTextarea.value, authorizedInput.value, companyInput.value);
        }, 1200);
    });
    
    companyInput.addEventListener("input", () => {
        showSaveStatus("saving", "Kaydediliyor...");
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            saveLeadChanges(lead.domain, statusSelect.value, notesTextarea.value, authorizedInput.value, companyInput.value);
        }, 1200);
    });
    
    authorizedInput.addEventListener("input", () => {
        showSaveStatus("saving", "Kaydediliyor...");
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(() => {
            saveLeadChanges(lead.domain, statusSelect.value, notesTextarea.value, authorizedInput.value, companyInput.value);
        }, 1200);
    });
}

// Close Drawer Helper
function closeDrawer() {
    drawer.classList.remove("open");
    drawerOverlay.classList.remove("active");
    clearTimeout(saveTimeout);
}

// Auto-save function
async function saveLeadChanges(domain, status, notes, authorizedPerson, companyName) {
    showSaveStatus("saving", "Kaydediliyor...");
    try {
        const res = await fetch(`/api/leads/${domain}`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                call_status: status,
                notes: notes,
                authorized_person: authorizedPerson,
                company_name: companyName
            })
        });
        
        if (res.ok) {
            showSaveStatus("saved", '<i class="fa-solid fa-circle-check"></i> Kaydedildi!');
            
            // Update local memory data
            const leadIndex = leadsData.findIndex(l => l.domain === domain);
            if (leadIndex !== -1) {
                leadsData[leadIndex].call_status = status;
                leadsData[leadIndex].notes = notes;
                leadsData[leadIndex].authorized_person = authorizedPerson;
                leadsData[leadIndex].company_name = companyName;
            }
            
            // Re-apply filters quietly
            applyFilters();
            fetchStats();
        } else {
            showSaveStatus("error", "Kayıt Başarısız!");
        }
    } catch (err) {
        console.error("Save error:", err);
        showSaveStatus("error", "Bağlantı Hatası!");
    }
}

// Show/Hide save status label in sidebar
function showSaveStatus(type, html) {
    const label = document.getElementById("drawer-save-status");
    if (!label) return;
    
    label.className = `save-status status-${type} visible`;
    label.innerHTML = html;
    
    // If saved, fade it out after 3 seconds
    if (type === "saved") {
        setTimeout(() => {
            if (label.classList.contains("status-saved")) {
                label.classList.remove("visible");
            }
        }, 3000);
    }
}
