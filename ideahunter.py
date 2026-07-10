import asyncio
import aiohttp
import sqlite3
import re
import sys
import argparse
import json
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Configure UTF-8 stdout encoding for Windows compatibility
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("IdeaHunter")

DB_FILE = "ideahunter.db"

# =====================================================================
# DATABASE SETUP
# =====================================================================

def init_db():
    """Initializes the SQLite database tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Table to track checked domains to avoid double scanning
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checked_domains (
        domain TEXT PRIMARY KEY,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_ideasoft INTEGER,
        status TEXT
    )
    """)
    
    # Table to store scraped leads
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scraped_leads (
        domain TEXT PRIMARY KEY,
        company_name TEXT,
        authorized_person TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        url TEXT,
        call_status TEXT DEFAULT 'YENI',
        notes TEXT,
        updated_at TIMESTAMP,
        tags TEXT DEFAULT ''
    )
    """)
    
    # Run migrations for existing databases
    try:
        cursor.execute("ALTER TABLE scraped_leads ADD COLUMN authorized_person TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE scraped_leads ADD COLUMN call_status TEXT DEFAULT 'YENI'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE scraped_leads ADD COLUMN notes TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE scraped_leads ADD COLUMN updated_at TIMESTAMP")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE scraped_leads ADD COLUMN tags TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

def is_domain_checked(domain):
    """Checks if a domain has already been scanned."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM checked_domains WHERE domain = ?", (domain,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def log_checked_domain(domain, is_ideasoft, status):
    """Logs domain check results."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO checked_domains (domain, is_ideasoft, status) VALUES (?, ?, ?)",
        (domain, 1 if is_ideasoft else 0, status)
    )
    conn.commit()
    conn.close()

def save_lead(domain, company_name, authorized_person, phone, email, address, url, design_status="AKTIF / TASARLANMIS", tags=""):
    """Saves a verified and scraped lead. Updates both SQLite and docs/leads.json, preserving CRM notes/statuses and tags."""
    import os
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT call_status, notes, tags FROM scraped_leads WHERE domain = ?", (domain,))
    row = cursor.fetchone()
    call_status = "YENI"
    notes = ""
    existing_tags = ""
    
    if row:
        call_status = row[0] or "YENI"
        notes = row[1] or ""
        existing_tags = row[2] or ""
        
        # Merge tags if a new tag is provided
        final_tags = existing_tags
        if tags:
            tag_list = [t.strip() for t in existing_tags.split(",") if t.strip()]
            new_tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            for nt in new_tag_list:
                if nt not in tag_list:
                    tag_list.append(nt)
            final_tags = ", ".join(tag_list)
            
        cursor.execute(
            """UPDATE scraped_leads 
               SET company_name = ?, authorized_person = ?, phone = ?, email = ?, address = ?, url = ?, tags = ? 
               WHERE domain = ?""",
            (company_name, authorized_person, phone, email, address, url, final_tags, domain)
        )
    else:
        cursor.execute(
            """INSERT INTO scraped_leads 
               (domain, company_name, authorized_person, phone, email, address, url, call_status, tags, scraped_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, 'YENI', ?, ?)""",
            (domain, company_name, authorized_person, phone, email, address, url, tags, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        final_tags = tags
        
    conn.commit()
    conn.close()

    # Sync with docs/leads.json
    os.makedirs("docs", exist_ok=True)
    json_path = os.path.join("docs", "leads.json")
    leads = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                leads = json.load(f)
        except Exception:
            leads = []
            
    found = False
    for l in leads:
        if l.get("domain") == domain:
            l["company_name"] = company_name
            l["authorized_person"] = authorized_person
            l["phone"] = phone
            l["email"] = email
            l["address"] = address
            l["url"] = url
            l["call_status"] = call_status
            l["crm_status"] = call_status
            l["notes"] = notes
            l["design_status"] = design_status
            l["tags"] = final_tags
            l["scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            found = True
            break
            
    if not found:
        leads.append({
            "domain": domain,
            "company_name": company_name,
            "authorized_person": authorized_person,
            "phone": phone,
            "email": email,
            "address": address,
            "url": url,
            "call_status": "YENI",
            "crm_status": "YENI",
            "notes": "",
            "design_status": design_status,
            "tags": final_tags,
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to write leads to JSON: {e}")

def get_all_leads():
    """Retrieves all leads from the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT domain, company_name, authorized_person, phone, email, address, scraped_at FROM scraped_leads ORDER BY scraped_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows
    return rows

# =====================================================================
# VALIDATION ENGINE (DNS & HTTP HEADERS)
# =====================================================================

async def check_nameservers(session, domain):
    """
    Queries Cloudflare DNS-over-HTTPS (DoH) API to find the Nameservers (NS) of a domain.
    """
    url = "https://cloudflare-dns.com/dns-query"
    params = {"name": domain, "type": "NS"}
    headers = {"Accept": "application/dns-json"}
    
    try:
        async with session.get(url, params=params, headers=headers, timeout=5) as res:
            if res.status == 200:
                data = await res.json()
                answers = data.get("Answer", [])
                ns_records = []
                for ans in answers:
                    if ans.get("type") == 2: # NS record type
                        ns_data = ans.get("data", "").lower().strip(".")
                        ns_records.append(ns_data)
                return ns_records
    except Exception as e:
        logger.debug(f"DoH error for {domain}: {e}")
    return []

async def verify_infrastructure(session, domain):
    """
    Checks if a domain uses IdeaSoft via Nameservers or HTTP headers.
    Returns (is_ideasoft, html_content, status_code).
    """
    # Step 1: DNS NS check
    ns_records = await check_nameservers(session, domain)
    is_ideasoft_ns = any("myideasoft.com" in ns for ns in ns_records)
    
    # Step 2: HTTP Connection & Headers Check
    url = f"https://{domain}"
    try:
        # We perform a GET request instead of HEAD because we need the HTML signature if headers are stripped/behind proxy
        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=7, allow_redirects=True) as res:
            html = await res.text()
            status_code = res.status
            
            # Check for header footprint
            headers = res.headers
            is_ideasoft_header = (
                'ideasoft' in str(headers.get('X-Powered-By', '')).lower() or
                'ideasoft' in str(headers.get('Powered-By', '')).lower() or
                'x-idea-cluster' in headers
            )
            
            # Check for HTML footprint (copyright meta, socialconnector etc.)
            is_ideasoft_html = (
                "Programlama IdeaSoft Akıllı E-Ticaret" in html or
                "socialconnector.eticaret.com" in html or
                "anticsrf" in html or
                "myideasoft.com" in html
            )
            
            is_ideasoft = is_ideasoft_ns or is_ideasoft_header or is_ideasoft_html
            return is_ideasoft, html, status_code
            
    except Exception as e:
        logger.debug(f"HTTP verification failed for {domain}: {e}")
        # If HTTPS fails, try HTTP fallback
        try:
            async with session.get(f"http://{domain}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=5, allow_redirects=True) as res:
                html = await res.text()
                status_code = res.status
                headers = res.headers
                is_ideasoft_header = (
                    'ideasoft' in str(headers.get('X-Powered-By', '')).lower() or
                    'ideasoft' in str(headers.get('Powered-By', '')).lower() or
                    'x-idea-cluster' in headers
                )
                is_ideasoft_html = (
                    "Programlama IdeaSoft Akıllı E-Ticaret" in html or
                    "socialconnector.eticaret.com" in html or
                    "anticsrf" in html
                )
                is_ideasoft = is_ideasoft_ns or is_ideasoft_header or is_ideasoft_html
                return is_ideasoft, html, status_code
        except Exception:
            pass
            
    # If DNS matches, but HTTP timed out/failed
    if is_ideasoft_ns:
        return True, "", 0
        
    return False, "", 0

# =====================================================================
# CLASSIFICATION & SCRAPING ENGINE
# =====================================================================

def classify_site_status(html_content, status_code):
    """
    Classifies the IdeaSoft website status (BAKIR / YAPIM ASAMASINDA or AKTIF).
    """
    if not html_content:
        if status_code == 503 or status_code == 0:
            return "BAKIR / YAPIM ASAMASINDA"
        return "AKTIF / TASARLANMIS"
        
    soup = BeautifulSoup(html_content, "html.parser")
    body_text = soup.body.get_text(strip=True) if soup.body else ""
    title_text = soup.title.string.strip().lower() if soup.title and soup.title.string else ""
    
    # Key default phrases or signatures indicating under construction / bare site
    is_construction = (
        "geçici olarak servis dışıdır" in body_text.lower() or
        "yapım aşamasında" in body_text.lower() or
        "sitemiz yapım aşamasındadır" in body_text.lower() or
        "service unavailable" in body_text.lower() or
        "yapım aşamasında" in title_text or
        "yapim asamasinda" in title_text
    )
    
    if is_construction:
        return "BAKIR / YAPIM ASAMASINDA"
    return "AKTIF / TASARLANMIS"

def clean_phone(phone_str):
    """Cleans phone numbers and verifies if they match Turkish formatting rules."""
    cleaned = re.sub(r'\D', '', phone_str)
    # Match standard Turkish mobile/landline digit count
    # E.g. 5321234567 (10 digits) or starting with 0 (05321234567 -> 11 digits)
    if len(cleaned) == 10 and cleaned.startswith(('2', '3', '4', '5', '8')):
        return f"0{cleaned}"
    elif len(cleaned) == 11 and cleaned.startswith('0'):
        return cleaned
    elif len(cleaned) == 12 and cleaned.startswith('90'):
        return f"0{cleaned[2:]}"
    elif len(cleaned) == 13 and cleaned.startswith('+90'):
        return f"0{cleaned[3:]}"
    return None

def extract_contacts_from_html(html, base_url):
    """Parses contact numbers, emails, company names, and addresses from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Email Extraction
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}'
    all_emails = re.findall(email_pattern, html)
    emails = []
    for email in all_emails:
        email_lower = email.lower()
        # Filter out obvious template placeholders
        if not any(placeholder in email_lower for placeholder in ["myideasoft.com", "ideasoft.com.tr", "example.com", "test.com", "domain.com"]):
            if email not in emails:
                emails.append(email)
                
    # 2. Phone Extraction (Regex covers 05xx..., 02xx... etc.)
    phone_pattern = r'(?:\+?90|0)?\s*\(?[1-9]\d{2}\)?\s*\d{3}\s*[\s-]*\d{2}\s*[\s-]*\d{2}'
    raw_phones = re.findall(phone_pattern, html)
    phones = []
    for p in raw_phones:
        cleaned = clean_phone(p)
        if cleaned and cleaned not in phones:
            phones.append(cleaned)
            
    # 3. Company Name
    company_name = ""
    copyright_meta = soup.find("meta", {"name": "copyright"})
    if copyright_meta and copyright_meta.get("content"):
        content = copyright_meta.get("content")
        # If the copyright contains the default IdeaSoft signature, we treat it as empty to find the real name
        if "IdeaSoft" not in content and len(content) < 80:
            company_name = content.replace("Copyright ©", "").replace("Copyright", "").strip()
            
    # Try finding full commercial name in body text (with A.Ş., LTD, Şti etc.)
    body_text = soup.body.get_text() if soup.body else ""
    collapsed_text = re.sub(r'\s+', ' ', body_text).strip()
    
    if not company_name or "IdeaSoft" in company_name:
        title_match = re.search(
            r'(?:Ticari\s+)?(?:Ünvan|Unvan)(?:ı|ı:)?\s*([A-Za-z0-9ıİğĞüşŞöÖçÇ\s.,/-]{3,80}?(?:Şti|Şirket|LTD|A\.Ş\.|AŞ|Anonim|Limited)[A-Za-z0-9ıİğĞüşŞöÖçÇ\s.,/-]*)', 
            collapsed_text, 
            re.IGNORECASE
        )
        if title_match:
            company_name = title_match.group(1).strip()
            company_name = re.sub(r'\s+', ' ', company_name).strip(" .,:-")
            
    if not company_name or "IdeaSoft" in company_name:
        title_tag = soup.find("title")
        if title_tag and title_tag.text:
            title_text = title_tag.text.strip()
            if title_text and not any(kw in title_text.lower() for kw in ["e-ticaret", "alışveriş", "yapım aşamasında"]):
                company_name = title_text.split("-")[0].strip()
                
    if not company_name or "IdeaSoft" in company_name:
        # Fallback to domain name base
        domain_name = urlparse(base_url).netloc or base_url
        company_name = domain_name.replace("www.", "").split(".")[0].capitalize()

    # 4. Authorized Person (Yetkili Kişi)
    authorized_person = ""
    yetkili_match = re.search(
        r'(?:Yetkili\s+Kişi|Yetkili|Firma\s+Yetkilisi|Şirket\s+Müdürü|Yetkili\s+Müdür|Temsilci)(?:\s*:\s*|\s+)([A-ZÇĞİÖŞÜa-zçğıöşü]+(?:\s+[A-ZÇĞİÖŞÜa-zçğıöşü]+){1,3})', 
        collapsed_text,
        re.IGNORECASE
    )
    if yetkili_match:
        name = yetkili_match.group(1).strip()
        # Clean trailing label words if they got captured
        for word in ['Ticari', 'Adres', 'Telefon', 'Tel', 'Email', 'E-posta', 'Şirket', 'Ünvan', 'Unvan']:
            if name.endswith(word):
                name = name[:-len(word)].strip()
        authorized_person = name
        
    # 5. Address Extraction
    address = ""
    address_elem = soup.find(string=re.compile(r'Adres:', re.IGNORECASE))
    if address_elem:
        parent = address_elem.parent
        address_text = parent.get_text().replace("Adres:", "").strip()
        if len(address_text) > 10 and len(address_text) < 200:
            address = address_text
            
    if not address:
        addr_tag = soup.find("address")
        if addr_tag:
            address = addr_tag.get_text(strip=True)
            
    # Try finding typical address strings in body if empty (excluding sentence separators)
    if not address:
        match = re.search(
            r'([^.!?]{1,100}(mahallesi|bulvarı|bulv\.|cadde|caddesi|cad\.|sokak|sok\.|köyü)[^.!?]{1,100})',
            collapsed_text,
            re.IGNORECASE
        )
        if match:
            address = match.group(0).strip()
            # Clean trailing email/phone patterns often merged in footer text
            address = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+(?:\.[a-zA-Z]{2,4})?', '', address)
            address = re.sub(r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}', '', address)
            address = re.sub(r'\d{8,}', '', address)
            
            # Clean leading/trailing noise (like "com Adres" or "Vergi No")
            address = re.sub(r'^(?:com\s+)?Adres\s+', '', address, flags=re.IGNORECASE)
            address = re.sub(r'(?:Vergi\s+No|Vergi\s+Dairesi|Ülke).*$', '', address, flags=re.IGNORECASE)
            address = re.sub(r'\s+', ' ', address).strip(" .,-")

    return {
        "emails": emails,
        "phones": phones,
        "company_name": company_name,
        "authorized_person": authorized_person,
        "address": address
    }

async def scrape_site_contacts(session, domain, homepage_html):
    """
    Navigates to the contact page (if available) and extracts all contact details.
    """
    # Start with homepage extraction
    contacts = extract_contacts_from_html(homepage_html, f"https://{domain}")
    
    # Look for contact page link
    soup = BeautifulSoup(homepage_html, "html.parser")
    contact_url = None
    
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(kw in href for kw in ["iletisim", "contact", "iletisim-bilgileri"]):
            contact_url = urljoin(f"https://{domain}", a["href"])
            break
            
    # If no contact page link found, try default fallback paths
    if not contact_url:
        for path in ["/iletisim", "/iletisim-bilgileri", "/contact", "/contact-us"]:
            contact_url = f"https://{domain}{path}"
            # Test if page exists via a quick head/get
            try:
                async with session.get(contact_url, timeout=4) as test_res:
                    if test_res.status == 200:
                        break
            except Exception:
                pass
            contact_url = None
            
    if contact_url:
        logger.info(f"  |-> İletişim sayfası taranıyor: {contact_url}")
        try:
            async with session.get(contact_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5) as res:
                if res.status == 200:
                    contact_html = await res.text()
                    c_contacts = extract_contacts_from_html(contact_html, contact_url)
                    
                    # Merge lists and details
                    contacts["emails"] = list(set(contacts["emails"] + c_contacts["emails"]))
                    contacts["phones"] = list(set(contacts["phones"] + c_contacts["phones"]))
                    if c_contacts["company_name"] and not contacts["company_name"]:
                        contacts["company_name"] = c_contacts["company_name"]
                    if c_contacts["authorized_person"] and not contacts["authorized_person"]:
                        contacts["authorized_person"] = c_contacts["authorized_person"]
                    if c_contacts["address"] and not contacts["address"]:
                        contacts["address"] = c_contacts["address"]
        except Exception as e:
            logger.debug(f"Failed to fetch contact page {contact_url}: {e}")
            
    return contacts

# =====================================================================
# MAIN PIPELINE FOR PROCESSING DOMAINS
# =====================================================================

async def process_domain(session, domain, tags=""):
    """Processes a single domain: checks if checked, verifies, classifies, and scrapes."""
    if is_domain_checked(domain):
        return None
        
    logger.info(f"[+] Domain İnceleniyor: {domain}")
    is_ideasoft, html, status_code = await verify_infrastructure(session, domain)
    
    if not is_ideasoft:
        log_checked_domain(domain, False, "NON_IDEASOFT")
        logger.info(f"  |-> IdeaSoft altyapısı algılanmadı.")
        return None
        
    status = classify_site_status(html, status_code)
    log_checked_domain(domain, True, status)
    logger.info(f"  |-> [✓] IdeaSoft Altyapısı Doğrulandı! Durum: {status}")
    
    # If the site is a lead candidate
    contacts = await scrape_site_contacts(session, domain, html)
    
    email = ", ".join(contacts["emails"]) if contacts["emails"] else ""
    phone = ", ".join(contacts["phones"]) if contacts["phones"] else ""
    address = contacts["address"] if contacts["address"] else ""
    company_name = contacts["company_name"] if contacts["company_name"] else ""
    authorized_person = contacts["authorized_person"] if contacts["authorized_person"] else ""
    
    if not company_name:
        company_name = domain.split(".")[0].capitalize()
        
    save_lead(domain, company_name, authorized_person, phone, email, address, f"https://{domain}", design_status=status, tags=tags)
    
    logger.info(f"  |-> [FİRM] Ünvan: {company_name}")
    logger.info(f"  |-> [YETK] Yetkili: {authorized_person if authorized_person else 'Yok'}")
    logger.info(f"  |-> [TEL]  Telefon: {phone if phone else 'Yok'}")
    logger.info(f"  |-> [MAIL] E-posta: {email if email else 'Yok'}")
    logger.info(f"  |-> [ADR]  Adres: {address if address else 'Yok'}")
    logger.info(f"  |-> [DB]   Veritabanına kaydedildi.")
    
    return {
        "domain": domain,
        "company_name": company_name,
        "authorized_person": authorized_person,
        "phone": phone,
        "email": email,
        "address": address,
        "status": status
    }

# =====================================================================
# CERTSTREAM MONITORING ENGINE (LIVE DISCOVERY)
# =====================================================================

async def run_live_monitor():
    """Runs a real-time monitor connecting to Certstream and filtering domains."""
    url = "wss://certstream.calidog.io/"
    logger.info("=" * 60)
    logger.info("        IdeaHunter - Canlı İzleme Modu (Certstream)")
    logger.info("=" * 60)
    
    retry_delay = 5
    while True:
        logger.info(f"Certstream sunucusuna bağlanılıyor: {url}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(url, timeout=10, heartbeat=20) as ws:
                    logger.info("Bağlantı kuruldu! Canlı akış dinleniyor...")
                    retry_delay = 5 # Reset delay on success
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("message_type") == "certificate_update":
                                leaf_cert = data.get("data", {}).get("leaf_cert", {})
                                all_domains = leaf_cert.get("all_domains", [])
                                
                                for domain in all_domains:
                                    # Clean wildcards
                                    if domain.startswith("*."):
                                        domain = domain[2:]
                                        
                                    # Filter: Only .tr domains or domains with specific keywords
                                    is_tr = domain.endswith((".tr", ".com.tr", ".net.tr", ".org.tr"))
                                    contains_keywords = any(kw in domain.lower() for kw in ["ideasoft", "eticaret", "e-ticaret"])
                                    
                                    if is_tr or contains_keywords:
                                        # Process asynchronously
                                        asyncio.create_task(process_domain(session, domain))
                                        
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            logger.warning("Bağlantı sunucu tarafından kapatıldı.")
                            break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error("Bağlantı hatası oluştu.")
                            break
        except Exception as e:
            logger.error(f"Bağlantı kurulamadı: {e}")
            
        logger.info(f"{retry_delay} saniye sonra tekrar denenecek...")
        await asyncio.sleep(retry_delay)
        retry_delay = min(retry_delay * 2, 60) # Exponential backoff

# =====================================================================
# AD-HOC SCANNING INTERFACE
# =====================================================================

async def scan_domain_list(domains):
    """Scans a hardcoded list or file list of domains."""
    logger.info("=" * 60)
    logger.info(f"        IdeaHunter - Liste Tarama Modu ({len(domains)} Domain)")
    logger.info("=" * 60)
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for d in domains:
            d = d.strip()
            if d:
                tasks.append(process_domain(session, d))
        await asyncio.gather(*tasks)

# =====================================================================
# ENTRY POINT
# =====================================================================

async def search_duckduckgo(session, query, region="tr-tr"):
    """
    Scrapes DuckDuckGo HTML search for a query and a region code (kl).
    """
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "tr,en-US;q=0.7,en;q=0.3"
    }
    domains = set()
    try:
        async with session.post(url, data={"q": query, "kl": region}, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                links = soup.find_all("a", class_="result__url")
                for link in links:
                    href = link.get("href", "")
                    if "uddg=" in href:
                        from urllib.parse import parse_qs
                        parsed_href = urlparse(href)
                        query_params = parse_qs(parsed_href.query)
                        actual_url = query_params.get("uddg", [""])[0]
                    else:
                        actual_url = href
                    
                    if actual_url:
                        netloc = urlparse(actual_url).netloc.replace("www.", "").lower().strip()
                        if netloc and "." in netloc:
                            domains.add(netloc)
            elif resp.status == 429:
                logger.debug(f"[DDG] Rate limited (429) for query: {query}")
    except Exception as e:
        logger.debug(f"[DDG] Error for query '{query}': {e}")
    return domains


async def search_bing(session, query, cc="TR", lang="tr", page=0):
    """
    Scrapes Bing search results for a query and a country code (cc).
    """
    url = "https://www.bing.com/search"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": f"{lang},en-US;q=0.7,en;q=0.3"
    }
    domains = set()
    try:
        params = {"q": query, "cc": cc, "setlang": lang, "first": page * 10 + 1}
        async with session.get(url, params=params, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                links = soup.select(".b_algo h2 a")
                for link in links:
                    href = link.get("href", "")
                    if href and href.startswith("http"):
                        netloc = urlparse(href).netloc.replace("www.", "").lower().strip()
                        if netloc and "." in netloc:
                            domains.add(netloc)
            elif resp.status == 429:
                logger.debug(f"[Bing] Rate limited (429) for query: {query}")
    except Exception as e:
        logger.debug(f"[Bing] Error for query '{query}': {e}")
    return domains


async def search_yandex(session, query, region_id=11508, page=0):
    """
    Scrapes Yandex search results for a query and a region ID (lr).
    """
    url = "https://yandex.com.tr/search/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "tr,en-US;q=0.7,en;q=0.3"
    }
    domains = set()
    try:
        params = {"text": query, "lr": region_id, "p": page}
        async with session.get(url, params=params, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                links = soup.select(".organic__url, a.Link, h2.organic__title a")
                for link in links:
                    href = link.get("href", "")
                    if href and href.startswith("http") and "yandex" not in href:
                        netloc = urlparse(href).netloc.replace("www.", "").lower().strip()
                        if netloc and "." in netloc:
                            domains.add(netloc)
            elif resp.status == 429:
                logger.debug(f"[Yandex] Rate limited (429) for query: {query}")
    except Exception as e:
        logger.debug(f"[Yandex] Error for query '{query}': {e}")
    return domains


async def search_searxng(session, instance, query):
    """
    Queries a specific SearXNG instance for a query and returns discovered domains.
    """
    url = f"{instance}/search"
    params = {"q": query, "format": "json", "pageno": 1}
    domains = set()
    try:
        async with session.get(url, params=params, timeout=12) as res:
            if res.status == 200:
                data = await res.json(content_type=None)
                results = data.get("results", [])
                for r in results:
                    result_url = r.get("url", "")
                    if result_url:
                        netloc = urlparse(result_url).netloc.replace("www.", "").lower().strip()
                        if netloc and "." in netloc:
                            domains.add(netloc)
                return domains, True
    except Exception as e:
        logger.debug(f"[SearXNG] {instance} error: {e}")
    return domains, False


async def search_footprints():
    """
    Discovers IdeaSoft domains via SearXNG public instances, DuckDuckGo, Bing, and Yandex.
    Returns a set of new discovered domains.
    """
    SEARX_INSTANCES = [
        "https://search.privacyguides.net",
        "https://searx.be",
        "https://searx.tiekoetter.com",
        "https://search.bus-hit.me",
        "https://searxng.site",
        "https://searx.space",
        "https://priv.au"
    ]
    
    FOOTPRINT_QUERIES = [
        'site:myideasoft.com',
        '"Programlama IdeaSoft Akıllı E-Ticaret"',
        '"Programlama IdeaSoft"',
        '"socialconnector.eticaret.com"',
        '"E-Ticaret Paketi Tarafından Hazırlanmıştır"',
        '"Altyapı: IdeaSoft"',
        '"ile hazırlandı" ideasoft'
    ]
    
    found_domains = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for query in FOOTPRINT_QUERIES:
            logger.info(f"[Footprint] '{query}' sorgusu çalıştırılıyor...")
            
            # 1. DuckDuckGo (Default Turkey)
            ddg_results = await search_duckduckgo(session, query, region="tr-tr")
            found_domains.update(ddg_results)
            logger.info(f"  |-> DuckDuckGo: {len(ddg_results)} domain buldu.")
            
            # 2. Bing (Default Turkey)
            bing_results = await search_bing(session, query, cc="TR", lang="tr")
            found_domains.update(bing_results)
            logger.info(f"  |-> Bing: {len(bing_results)} domain buldu.")
            
            # 3. Yandex (Default Turkey)
            yandex_results = await search_yandex(session, query, region_id=11508)
            found_domains.update(yandex_results)
            logger.info(f"  |-> Yandex: {len(yandex_results)} domain buldu.")
            
            # 4. SearXNG
            searx_success = False
            for instance in SEARX_INSTANCES:
                searx_results, success = await search_searxng(session, instance, query)
                if success:
                    found_domains.update(searx_results)
                    logger.info(f"  |-> SearXNG ({instance}): {len(searx_results)} domain buldu.")
                    searx_success = True
                    break
            if not searx_success:
                logger.warning(f"  |-> SearXNG: Hiçbir SearXNG örneği yanıt vermedi.")
                
            # Random delay between queries to avoid getting blocked
            import random
            await asyncio.sleep(random.uniform(1.5, 3.0))
            
    # Filter out known non-ideasoft domains
    EXCLUDE = {"google.com", "youtube.com", "facebook.com", "twitter.com", "wikipedia.org", 
               "github.com", "linkedin.com", "instagram.com", "ideasoft.com.tr", "myideasoft.com"}
    found_domains -= EXCLUDE
    
    logger.info(f"[Footprint] Toplam benzersiz domain bulundu: {len(found_domains)}")
    return found_domains


async def run_regional_search():
    """
    Performs regional footprint searches rotating through search engine parameters
    (DuckDuckGo regions, Bing country codes, and Yandex city IDs).
    Automatically verifies and scrapes each discovered domain.
    """
    import random
    
    FOOTPRINT_QUERIES = [
        'site:myideasoft.com',
        '"Programlama IdeaSoft Akıllı E-Ticaret"',
        '"Programlama IdeaSoft"',
        '"socialconnector.eticaret.com"',
        '"E-Ticaret Paketi Tarafından Hazırlanmıştır"',
        '"Altyapı: IdeaSoft"',
        '"ile hazırlandı" ideasoft'
    ]
    
    # DuckDuckGo region codes (kl)
    DDG_REGIONS = ["tr-tr", "us-en", "uk-en", "de-de", "fr-fr", "ru-ru", "es-es"]
    
    # Bing country codes (cc) and languages
    BING_REGIONS = [
        {"cc": "TR", "lang": "tr"},
        {"cc": "US", "lang": "en"},
        {"cc": "GB", "lang": "en"},
        {"cc": "DE", "lang": "de"},
        {"cc": "FR", "lang": "fr"}
    ]
    
    # Yandex Turkey region ID + Yandex Turkish cities region IDs (lr)
    YANDEX_REGIONS = [
        {"lr": 11508, "name": "Türkiye"},
        {"lr": 10590, "name": "İstanbul"},
        {"lr": 10693, "name": "Ankara"},
        {"lr": 10697, "name": "İzmir"},
        {"lr": 10694, "name": "Bursa"},
        {"lr": 10695, "name": "Antalya"},
        {"lr": 10704, "name": "Kocaeli"},
        {"lr": 10692, "name": "Adana"},
        {"lr": 10705, "name": "Konya"},
        {"lr": 10699, "name": "Gaziantep"}
    ]
    
    logger.info("=" * 60)
    logger.info("    IdeaHunter - Gelişmiş Bölgesel Parametrik Arama Başlıyor")
    logger.info("=" * 60)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/120.0.0.0"
    }
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        for q_idx, query in enumerate(FOOTPRINT_QUERIES):
            logger.info(f"\n[Sorgu {q_idx+1}/{len(FOOTPRINT_QUERIES)}] Footprint sorgulanıyor: {query}")
            
            logger.info("  |-> DuckDuckGo Bölgesel Sorgular (kl parametresi)...")
            for region in DDG_REGIONS:
                logger.info(f"    |-> DDG Bölge Filtresi: {region}")
                ddg_res = await search_duckduckgo(session, query, region=region)
                
                new_domains = [d for d in ddg_res if not is_domain_checked(d)]
                if new_domains:
                    logger.info(f"      |-> {len(new_domains)} yeni domain doğrulama aşamasına gönderiliyor...")
                    for d in new_domains:
                        try:
                            await process_domain(session, d)
                        except Exception as e:
                            logger.debug(f"Hata ({d}): {e}")
                        await asyncio.sleep(random.uniform(0.5, 1.2))
                else:
                    logger.info("      |-> Yeni domain bulunamadı.")
                await asyncio.sleep(random.uniform(1.5, 3.0))
                
            logger.info("  |-> Bing Bölgesel Sorgular (cc parametresi, 3 sayfa)...")
            for region in BING_REGIONS:
                cc = region["cc"]
                lang = region["lang"]
                for page in range(3):
                    logger.info(f"    |-> Bing Bölge Filtresi: {cc} ({lang}) | Sayfa: {page+1}")
                    bing_res = await search_bing(session, query, cc=cc, lang=lang, page=page)
                    
                    new_domains = [d for d in bing_res if not is_domain_checked(d)]
                    if new_domains:
                        logger.info(f"      |-> {len(new_domains)} yeni domain doğrulama aşamasına gönderiliyor...")
                        for d in new_domains:
                            try:
                                await process_domain(session, d)
                            except Exception as e:
                                logger.debug(f"Hata ({d}): {e}")
                            await asyncio.sleep(random.uniform(0.5, 1.2))
                    else:
                        logger.info("      |-> Yeni domain bulunamadı.")
                    await asyncio.sleep(random.uniform(1.5, 3.0))
                
            logger.info("  |-> Yandex Bölgesel Sorgular (lr parametresi, 3 sayfa)...")
            for region in YANDEX_REGIONS:
                lr = region["lr"]
                name = region["name"]
                for page in range(3):
                    logger.info(f"    |-> Yandex Bölge Filtresi: {name} (lr={lr}) | Sayfa: {page+1}")
                    yandex_res = await search_yandex(session, query, region_id=lr, page=page)
                    
                    new_domains = [d for d in yandex_res if not is_domain_checked(d)]
                    if new_domains:
                        logger.info(f"      |-> {len(new_domains)} yeni domain doğrulama aşamasına gönderiliyor...")
                        for d in new_domains:
                            try:
                                await process_domain(session, d)
                            except Exception as e:
                                logger.debug(f"Hata ({d}): {e}")
                            await asyncio.sleep(random.uniform(0.5, 1.2))
                    else:
                        logger.info("      |-> Yeni domain bulunamadı.")
                    await asyncio.sleep(random.uniform(1.5, 3.0))


async def process_discovered_domains():
    """Processes all newly discovered domains in the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT domain FROM checked_domains WHERE is_ideasoft = 1 AND status = 'DISCOVERED'")
    rows = cursor.fetchall()
    conn.close()
    
    domains = [row[0] for row in rows]
    if not domains:
        logger.info("[!] İşlenecek yeni keşfedilmiş domain bulunamadı. Lütfen önce bulk_discovery.py dosyasını çalıştırın.")
        return
        
    logger.info("=" * 60)
    logger.info(f"    IdeaHunter - Keşfedilmiş Mağazaları Taramaya Başlama ({len(domains)} Mağaza)")
    logger.info("=" * 60)
    
    semaphore = asyncio.Semaphore(15) # Concurrency limit for HTTP requests
    
    async def sem_process(session, domain):
        async with semaphore:
            # Temporarily delete check status to bypass cache check in process_domain
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM checked_domains WHERE domain = ?", (domain,))
            conn.commit()
            conn.close()
            try:
                await process_domain(session, domain)
            except Exception as e:
                logger.error(f"Hata ({domain}): {e}")
                
    async with aiohttp.ClientSession() as session:
        tasks = [sem_process(session, d) for d in domains]
        await asyncio.gather(*tasks)


async def run_all_sources():
    """Runs discovery from all available sources: DNS zone + SearXNG footprints."""
    logger.info("=" * 60)
    logger.info("    IdeaHunter - Çoklu Kaynak Tarama Başlıyor")
    logger.info("=" * 60)
    
    # Phase 1: Footprint search
    logger.info("[Phase 1] Arama motoru footprint taraması...")
    footprint_domains = await search_footprints()
    
    # Phase 2: Process footprint candidates
    if footprint_domains:
        logger.info(f"[Phase 2] {len(footprint_domains)} footprint domain scraping'e gönderiliyor...")
        semaphore = asyncio.Semaphore(10)
        
        async def sem_process(session, domain):
            async with semaphore:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM checked_domains WHERE domain = ?", (domain,))
                if cursor.fetchone():
                    conn.close()
                    return
                conn.close()
                try:
                    await process_domain(session, domain)
                except Exception as e:
                    logger.debug(f"Footprint domain hata ({domain}): {e}")
        
        async with aiohttp.ClientSession() as session:
            tasks = [sem_process(session, d) for d in footprint_domains]
            await asyncio.gather(*tasks)
    
    logger.info("[Tamamlandı] Çoklu kaynak taraması bitti.")


class ProgressCounter:
    def __init__(self, total):
        self.count = 0
        self.total = total
        self.lock = asyncio.Lock()

    async def increment(self):
        async with self.lock:
            self.count += 1
            return self.count


async def process_domain_semaphore(semaphore, counter, prefix, session, domain, tags):
    async with semaphore:
        try:
            await process_domain(session, domain, tags=tags)
        except Exception as e:
            logger.debug(f"Hata ({domain}): {e}")
        current = await counter.increment()
        if current % 50 == 0 or current == counter.total:
            logger.info(f"[{prefix} Progress] {current}/{counter.total} ({int(current/counter.total*100)}%) domain kontrol edildi.")


async def scan_kayseri_osm():
    """
    Queries OpenStreetMap's Overpass API to find all businesses in Kayseri
    with website tags, and runs search engine sector sweeps to discover even more domains.
    Checks if they use IdeaSoft infrastructure and tags them as 'kayseri'.
    """
    import random
    # Overpass API endpoint
    url = "https://overpass-api.de/api/interpreter"
    
    # Overpass query to find nodes/ways with website/url/contact:website tag in Kayseri
    query = """
    [out:json][timeout:30];
    area["ISO3166-2"="TR-38"]->.searchArea;
    (
      node["website"](area.searchArea);
      node["contact:website"](area.searchArea);
      node["url"](area.searchArea);
      way["website"](area.searchArea);
      way["contact:website"](area.searchArea);
      way["url"](area.searchArea);
    );
    out tags;
    """
    
    logger.info("=" * 60)
    logger.info("[OSM] Kayseri esnaflarının web siteleri Overpass API ile taranıyor...")
    logger.info("=" * 60)
    
    headers = {
        "User-Agent": "IdeaHunter OSM Kayseri Scanner/1.0"
    }
    
    found_websites = set()
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, data={"data": query}, timeout=95) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    elements = data.get("elements", [])
                    for elem in elements:
                        tags = elem.get("tags", {})
                        web = tags.get("website") or tags.get("contact:website") or tags.get("url")
                        if web:
                            found_websites.add(web)
                    logger.info(f"[OSM] Kayseri OSM verisinde {len(found_websites)} web sitesi bulundu.")
                else:
                    logger.warning(f"[OSM] Overpass API hatası: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"[OSM] Overpass API bağlantı hatası: {e}")
        
    # Clean domains
    domains = set()
    for web in found_websites:
        try:
            # Clean protocol and www
            netloc = urlparse(web).netloc.replace("www.", "").lower().strip()
            if not netloc and web: # In case the website tag has no http protocol
                netloc = urlparse("http://" + web).netloc.replace("www.", "").lower().strip()
            # Clean trailing paths
            netloc = netloc.split("/")[0].split(":")[0]
            if netloc and "." in netloc:
                domains.add(netloc)
        except Exception:
            pass

    # 2. Deep Footprint + Kayseri Lokasyon Kombinasyonu Arama
    logger.info("[OSM] Arama motorları üzerinden derin IdeaSoft footprint + Kayseri konum taraması başlatılıyor...")
    
    # Kayseri districts grouped by size/commercial activity
    CENTRAL_LOCATIONS = ["Kayseri", "Melikgazi", "Kocasinan", "Talas"]
    OUTER_LOCATIONS = ["Develi", "Yahyalı", "Bünyan", "İncesu", "Hacılar", "Pınarbaşı", "Tomarza", "Yeşilhisar", "Sarıoğlan"]
    
    FOOTPRINTS = [
        '"Programlama IdeaSoft Akıllı E-Ticaret"',
        '"Programlama IdeaSoft"',
        '"Altyapı: IdeaSoft"',
        '"E-Ticaret Paketi Tarafından Hazırlanmıştır"',
        '"socialconnector.eticaret.com"',
        '"ile hazırlandı" ideasoft',
        'site:myideasoft.com',
        '"IdeaSoft Akıllı E-Ticaret"'
    ]
    
    SEARX_INSTANCES = [
        "https://search.privacyguides.net",
        "https://searx.be",
        "https://searx.tiekoetter.com",
        "https://search.bus-hit.me",
        "https://searxng.site",
        "https://searx.space",
        "https://priv.au"
    ]
    
    # 2.1 Central Districts - 5 Pages Deep
    central_queries = []
    for loc in CENTRAL_LOCATIONS:
        for fp in FOOTPRINTS:
            central_queries.append((f'{fp} "{loc}"', 5)) # (query, page_depth)
            
    # 2.2 Outer Districts - 3 Pages Deep
    outer_queries = []
    for loc in OUTER_LOCATIONS:
        # Use top 5 footprints for outer districts to keep query count reasonable
        for fp in FOOTPRINTS[:5]:
            outer_queries.append((f'{fp} "{loc}"', 3))
            
    all_queries = central_queries + outer_queries
    random.shuffle(all_queries)
    selected_queries = all_queries[:15]
    
    logger.info(f"[OSM] Toplam {len(all_queries)} adet derin tarama sorgusu oluşturuldu. Seçilen {len(selected_queries)} sorgu çalıştırılacak.")
    
    search_engine_domains = set()
    async with aiohttp.ClientSession(headers=headers) as session:
        for idx, (query, depth) in enumerate(selected_queries):
            logger.info(f"  |-> [Sorgu {idx+1}/{len(selected_queries)}] Sorgulanıyor: {query} (Derinlik: {depth} sayfa)")
            
            # Query SearXNG for Google index integration
            searx_success = False
            for instance in SEARX_INSTANCES:
                searx_results, success = await search_searxng(session, instance, query)
                if success:
                    search_engine_domains.update(searx_results)
                    searx_success = True
                    break
            
            for page in range(depth):
                # Yandex search (Kayseri region id: 10698)
                yandex_res = await search_yandex(session, query, region_id=10698, page=page)
                search_engine_domains.update(yandex_res)
                
                # Bing search
                bing_res = await search_bing(session, query, cc="TR", lang="tr", page=page)
                search_engine_domains.update(bing_res)
                
                # DuckDuckGo search (TR-TR region)
                ddg_res = await search_duckduckgo(session, query, region="tr-tr")
                search_engine_domains.update(ddg_res)
                
                await asyncio.sleep(random.uniform(1.0, 2.5))
            
    logger.info(f"[OSM] Arama motorlarından toplam {len(search_engine_domains)} adet potansiyel domain toplandı.")
    domains.update(search_engine_domains)
            
    # Filter out already checked domains and non-ideasoft candidates
    EXCLUDE = {"google.com", "youtube.com", "facebook.com", "twitter.com", "wikipedia.org", 
               "github.com", "linkedin.com", "instagram.com", "ideasoft.com.tr", "myideasoft.com"}
    domains -= EXCLUDE
    
    new_domains = [d for d in domains if not is_domain_checked(d)]
    logger.info(f"[OSM] Kayseri için taranacak toplam {len(new_domains)} yeni domain ayrıştırıldı.")
    
    if not new_domains:
        logger.info("[OSM] Kayseri için yeni taranacak domain bulunamadı.")
        return
        
    # Process domains and verify IdeaSoft
    semaphore = asyncio.Semaphore(30)
    counter = ProgressCounter(len(new_domains))
    logger.info(f"[OSM Kayseri] {len(new_domains)} domain icin paralel tarama baslatiliyor (Eszamanlilik limiti: 30)...")
    async with aiohttp.ClientSession() as session:
        tasks = [process_domain_semaphore(semaphore, counter, "OSM Kayseri", session, d, tags="kayseri") for d in new_domains]
        await asyncio.gather(*tasks)


async def scan_istanbul_osm():
    """
    Queries OpenStreetMap's Overpass API to find all businesses in Istanbul
    with website tags, and runs deep search engine sweeps to discover even more domains.
    Checks if they use IdeaSoft infrastructure and saves them as normal leads (no tags).
    """
    import random
    # Overpass API endpoint
    url = "https://overpass-api.de/api/interpreter"
    
    # Overpass query to find nodes/ways with website/url/contact:website tag in Istanbul
    query = """
    [out:json][timeout:60];
    area["ISO3166-2"="TR-34"]->.searchArea;
    (
      node["website"](area.searchArea);
      node["contact:website"](area.searchArea);
      node["url"](area.searchArea);
      way["website"](area.searchArea);
      way["contact:website"](area.searchArea);
      way["url"](area.searchArea);
    );
    out tags;
    """
    
    logger.info("=" * 60)
    logger.info("[OSM] İstanbul esnaflarının web siteleri Overpass API ile taranıyor...")
    logger.info("=" * 60)
    
    headers = {
        "User-Agent": "IdeaHunter OSM Istanbul Scanner/1.0"
    }
    
    found_websites = set()
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, data={"data": query}, timeout=120) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    elements = data.get("elements", [])
                    for elem in elements:
                        tags = elem.get("tags", {})
                        web = tags.get("website") or tags.get("contact:website") or tags.get("url")
                        if web:
                            found_websites.add(web)
                    logger.info(f"[OSM] İstanbul OSM verisinde {len(found_websites)} web sitesi bulundu.")
                else:
                    logger.warning(f"[OSM] Overpass API hatası: HTTP {resp.status}")
    except Exception as e:
        logger.error(f"[OSM] Overpass API bağlantı hatası: {e}")
        
    # Clean domains
    domains = set()
    for web in found_websites:
        try:
            # Clean protocol and www
            netloc = urlparse(web).netloc.replace("www.", "").lower().strip()
            if not netloc and web: # In case the website tag has no http protocol
                netloc = urlparse("http://" + web).netloc.replace("www.", "").lower().strip()
            # Clean trailing paths
            netloc = netloc.split("/")[0].split(":")[0]
            if netloc and "." in netloc:
                domains.add(netloc)
        except Exception:
            pass

    # 2. Deep Footprint + İstanbul Lokasyon Kombinasyonu Arama
    logger.info("[OSM] Arama motorları üzerinden derin IdeaSoft footprint + İstanbul konum taraması başlatılıyor...")
    
    # Istanbul districts grouped by commercial density
    CENTRAL_LOCATIONS = ["İstanbul", "Fatih", "Kadıköy", "Şişli", "Beşiktaş", "Üsküdar", "Ümraniye", "Esenyurt", "Bakırköy"]
    OUTER_LOCATIONS = [
        "Ataşehir", "Maltepe", "Kartal", "Pendik", "Sarıyer", "Beyoğlu", "Kağıthane", 
        "Zeytinburnu", "Bahçelievler", "Bağcılar", "Bayrampaşa", "Küçükçekmece", 
        "Büyükçekmece", "Avcılar", "Beylikdüzü", "Başakşehir", "Silivri", "Beykoz", 
        "Çekmeköy", "Sancaktepe", "Sultanbeyli"
    ]
    
    FOOTPRINTS = [
        '"Programlama IdeaSoft Akıllı E-Ticaret"',
        '"Programlama IdeaSoft"',
        '"Altyapı: IdeaSoft"',
        '"E-Ticaret Paketi Tarafından Hazırlanmıştır"',
        '"socialconnector.eticaret.com"',
        '"ile hazırlandı" ideasoft',
        'site:myideasoft.com',
        '"IdeaSoft Akıllı E-Ticaret"'
    ]
    
    SEARX_INSTANCES = [
        "https://search.privacyguides.net",
        "https://searx.be",
        "https://searx.tiekoetter.com",
        "https://search.bus-hit.me",
        "https://searxng.site",
        "https://searx.space",
        "https://priv.au"
    ]
    
    # 2.1 Central Districts - 5 Pages Deep
    central_queries = []
    for loc in CENTRAL_LOCATIONS:
        for fp in FOOTPRINTS:
            central_queries.append((f'{fp} "{loc}"', 5)) # (query, page_depth)
            
    # 2.2 Outer Districts - 3 Pages Deep
    outer_queries = []
    for loc in OUTER_LOCATIONS:
        # Use top 5 footprints for outer districts to keep query count reasonable
        for fp in FOOTPRINTS[:5]:
            outer_queries.append((f'{fp} "{loc}"', 3))
            
    all_queries = central_queries + outer_queries
    random.shuffle(all_queries)
    selected_queries = all_queries[:15]
    
    logger.info(f"[OSM] Toplam {len(all_queries)} adet derin tarama sorgusu oluşturuldu. Seçilen {len(selected_queries)} sorgu çalıştırılacak.")
    
    search_engine_domains = set()
    async with aiohttp.ClientSession(headers=headers) as session:
        for idx, (query, depth) in enumerate(selected_queries):
            logger.info(f"  |-> [Sorgu {idx+1}/{len(selected_queries)}] Sorgulanıyor: {query} (Derinlik: {depth} sayfa)")
            
            # Query SearXNG for Google index integration
            searx_success = False
            for instance in SEARX_INSTANCES:
                searx_results, success = await search_searxng(session, instance, query)
                if success:
                    search_engine_domains.update(searx_results)
                    searx_success = True
                    break
            
            for page in range(depth):
                # Yandex search (Istanbul region id: 213)
                yandex_res = await search_yandex(session, query, region_id=213, page=page)
                search_engine_domains.update(yandex_res)
                
                # Bing search
                bing_res = await search_bing(session, query, cc="TR", lang="tr", page=page)
                search_engine_domains.update(bing_res)
                
                # DuckDuckGo search (TR-TR region)
                ddg_res = await search_duckduckgo(session, query, region="tr-tr")
                search_engine_domains.update(ddg_res)
                
                await asyncio.sleep(random.uniform(1.0, 2.5))
            
    logger.info(f"[OSM] Arama motorlarından toplam {len(search_engine_domains)} adet potansiyel domain toplandı.")
    domains.update(search_engine_domains)
            
    # Filter out already checked domains and non-ideasoft candidates
    EXCLUDE = {"google.com", "youtube.com", "facebook.com", "twitter.com", "wikipedia.org", 
               "github.com", "linkedin.com", "instagram.com", "ideasoft.com.tr", "myideasoft.com"}
    domains -= EXCLUDE
    
    new_domains = [d for d in domains if not is_domain_checked(d)]
    logger.info(f"[OSM] İstanbul için taranacak toplam {len(new_domains)} yeni domain ayrıştırıldı.")
    
    if not new_domains:
        logger.info("[OSM] İstanbul için yeni taranacak domain bulunamadı.")
        return
        
    # Process domains and verify IdeaSoft (no tags passed as requested)
    semaphore = asyncio.Semaphore(30)
    counter = ProgressCounter(len(new_domains))
    logger.info(f"[OSM İstanbul] {len(new_domains)} domain icin paralel tarama baslatiliyor (Eszamanlilik limiti: 30)...")
    async with aiohttp.ClientSession() as session:
        tasks = [process_domain_semaphore(semaphore, counter, "OSM Istanbul", session, d, tags="") for d in new_domains]
        await asyncio.gather(*tasks)


def main():
    init_db()
    
    parser = argparse.ArgumentParser(description="IdeaHunter: Auto IdeaSoft Store Finder")
    parser.add_argument("--scan", help="Scan a single domain (e.g. --scan example.com)")
    parser.add_argument("--file", help="Scan a list of domains from a text file")
    parser.add_argument("--live", action="store_true", help="Start the real-time Certstream monitor")
    parser.add_argument("--view", action="store_true", help="Display all scraped leads in the database")
    parser.add_argument("--hunt", action="store_true", help="Process and scrape all domains discovered via bulk_discovery.py")
    parser.add_argument("--footprint", action="store_true", help="Discover domains via SearXNG search engine footprints")
    parser.add_argument("--regional", action="store_true", help="Discover and process domains via 81 Turkish cities regional footprint search")
    parser.add_argument("--all-sources", action="store_true", help="Run all discovery sources: bulk DNS + SearXNG footprints")
    parser.add_argument("--osm-kayseri", action="store_true", help="Discover Kayseri shop domains via OpenStreetMap Overpass and analyze infrastructure")
    parser.add_argument("--osm-istanbul", action="store_true", help="Discover Istanbul shop domains via OpenStreetMap Overpass and footprint sweeps")
    
    args = parser.parse_args()
    
    if args.view:
        leads = get_all_leads()
        print("=" * 90)
        print(f"%-25s | %-20s | %-15s | %-20s" % ("Domain", "Firma Adı", "Telefon", "E-posta"))
        print("=" * 90)
        for row in leads:
            print(f"%-25s | %-20s | %-15s | %-20s" % (row[0], (row[1] or "")[:20], (row[3] or "")[:15], (row[4] or "")[:20]))
        print("=" * 90)
        print(f"Toplam kayıtlı lead sayısı: {len(leads)}")
        return
        
    if args.scan:
        asyncio.run(scan_domain_list([args.scan]))
    elif args.file:
        try:
            with open(args.file, "r") as f:
                domains = f.read().splitlines()
            asyncio.run(scan_domain_list(domains))
        except FileNotFoundError:
            logger.error(f"Dosya bulunamadı: {args.file}")
    elif args.live:
        try:
            asyncio.run(run_live_monitor())
        except KeyboardInterrupt:
            logger.info("Canlı izleme sonlandırıldı.")
    elif args.hunt:
        try:
            asyncio.run(process_discovered_domains())
        except KeyboardInterrupt:
            logger.info("Tarama sonlandırıldı.")
    elif args.footprint:
        try:
            asyncio.run(search_footprints())
        except KeyboardInterrupt:
            logger.info("Footprint taraması sonlandırıldı.")
    elif getattr(args, "regional", False):
        try:
            asyncio.run(run_regional_search())
        except KeyboardInterrupt:
            logger.info("Bölgesel tarama sonlandırıldı.")
    elif getattr(args, "all_sources", False):
        try:
            asyncio.run(run_all_sources())
        except KeyboardInterrupt:
            logger.info("Çoklu kaynak taraması sonlandırıldı.")
    elif getattr(args, "osm_kayseri", False):
        try:
            asyncio.run(scan_kayseri_osm())
        except KeyboardInterrupt:
            logger.info("OSM Kayseri taraması sonlandırıldı.")
    elif getattr(args, "osm_istanbul", False):
        try:
            asyncio.run(scan_istanbul_osm())
        except KeyboardInterrupt:
            logger.info("OSM İstanbul taraması sonlandırıldı.")
    else:
        print("IdeaSoft Mağaza Avcısı - IdeaHunter")
        print("Kullanım:")
        print("  python ideahunter.py --live             -> Canlı Certstream akışını başlatır")
        print("  python ideahunter.py --scan [site]      -> Tek bir siteyi sorgular")
        print("  python ideahunter.py --file [dosya]     -> Dosyadaki domainleri toplu tarar")
        print("  python ideahunter.py --view             -> Veritabanındaki leadleri listeler")
        print("  python ideahunter.py --hunt             -> Keşfedilen tüm domainleri işler")
        print("  python ideahunter.py --footprint        -> SearXNG arama motoru footprint keşfi")
        print("  python ideahunter.py --regional         -> 81 il ile bölgesel footprint keşfi ve taraması")
        print("  python ideahunter.py --all-sources      -> Tüm kaynakları çalıştır")
        print("  python ideahunter.py --osm-kayseri      -> Kayseri esnaflarını OSM ile tarar ve analiz eder")
        print("  python ideahunter.py --osm-istanbul     -> İstanbul esnaflarını OSM ile tarar ve analiz eder")

if __name__ == "__main__":
    main()
