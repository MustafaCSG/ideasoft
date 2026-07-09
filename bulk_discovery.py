import asyncio
import aiohttp
import sqlite3
import dns.asyncresolver
import sys
import os

# Force UTF-8 output
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

DB_FILE = "ideahunter.db"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/agmmnn/tr-domains/master/data_nodoc/"
LIST_FILES = [
    "com.tr.txt",
    "net.tr.txt",
    "org.tr.txt",
    "info.tr.txt",
    "biz.tr.txt",
    "web.tr.txt"
]

# Initialize Database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS checked_domains (
        domain TEXT PRIMARY KEY,
        checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_ideasoft INTEGER,
        status TEXT
    )
    """)
    conn.commit()
    conn.close()

def log_discovered_domain(domain, is_ideasoft):
    """Saves discovered domain status to database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    status = "DISCOVERED" if is_ideasoft else "NON_IDEASOFT"
    cursor.execute(
        "INSERT OR IGNORE INTO checked_domains (domain, is_ideasoft, status) VALUES (?, ?, ?)",
        (domain, 1 if is_ideasoft else 0, status)
    )
    conn.commit()
    conn.close()

async def download_domain_list(session, filename):
    """Downloads a raw domain list from agmmnn/tr-domains GitHub repo."""
    url = f"{GITHUB_RAW_BASE}{filename}"
    print(f"[+] '{filename}' listesi indiriliyor: {url}")
    try:
        async with session.get(url, timeout=15) as res:
            if res.status == 200:
                text = await res.text()
                domains = text.splitlines()
                print(f"  |-> Başarıyla indirildi. {len(domains)} adet domain yüklendi.")
                return domains
            else:
                print(f"  |-> İndirme hatası: HTTP {res.status}")
    except Exception as e:
        print(f"  |-> Hata: {e}")
    return []

async def check_domain_ns(domain, semaphore, resolver):
    """Checks if a domain's NS records point to myideasoft.com."""
    async with semaphore:
        try:
            # Query NS records
            answers = await resolver.resolve(domain, 'NS')
            ns_list = [str(rdata.target).lower() for rdata in answers]
            
            is_ideasoft = any("myideasoft.com" in ns for ns in ns_list)
            if is_ideasoft:
                # Log to DB immediately
                log_discovered_domain(domain, True)
                return domain, True
        except Exception:
            # Domain does not resolve or query fails
            pass
        return domain, False

async def main(limit=None):
    init_db()
    
    print("=" * 60)
    print("       IdeaHunter - Toplu Domain Keşif Aracı (DNS Scanner)")
    print("=" * 60)
    
    all_domains = []
    
    # Step 1: Download lists
    async with aiohttp.ClientSession() as session:
        for filename in LIST_FILES:
            domains = await download_domain_list(session, filename)
            all_domains.extend(domains)
            
    # Remove duplicates and clean
    all_domains = list(set([d.strip().lower() for d in all_domains if d.strip()]))
    total_loaded = len(all_domains)
    
    print(f"\n[+] Toplam yüklenebilecek benzersiz domain sayısı: {total_loaded}")
    
    if limit:
        all_domains = all_domains[:limit]
        print(f"[!] Test modu aktif. Sadece ilk {len(all_domains)} domain taranacak.")
        
    print("[+] Tarama başlatılıyor (Eşzamanlı limit: 500 DNS sorgusu)...")
    
    # Step 2: Configure Resolver & Semaphore
    semaphore = asyncio.Semaphore(500) # Limit concurrent queries to prevent local resource depletion
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 2
    resolver.lifetime = 3
    # Use public DNS resolvers for maximum performance
    resolver.nameservers = ['1.1.1.1', '8.8.8.8', '9.9.9.9']
    
    tasks = [check_domain_ns(domain, semaphore, resolver) for domain in all_domains]
    
    # Step 3: Run queries and track progress
    found_count = 0
    processed = 0
    total_tasks = len(tasks)
    
    # We execute in chunks or gather
    for chunk_idx in range(0, total_tasks, 2000):
        chunk = tasks[chunk_idx:chunk_idx+2000]
        results = await asyncio.gather(*chunk)
        processed += len(results)
        
        chunk_found = sum(1 for _, matched in results if matched)
        found_count += chunk_found
        
        sys.stdout.write(f"\rİlerleme: %{processed*100/total_tasks:.2f} ({processed}/{total_tasks}) | Bulunan IdeaSoft Mağazası: {found_count}")
        sys.stdout.flush()
        
    print(f"\n\n[✓] Tarama tamamlandı!")
    print(f"Toplam taranan domain: {processed}")
    print(f"Bulunan IdeaSoft mağazası: {found_count}")
    print("Bulunan tüm alan adları 'ideahunter.db' veritabanına kaydedildi.")
    print("=" * 60)

if __name__ == "__main__":
    # If ran directly, run with first 5000 domains for test. To scan all, call with main()
    # Let's check command line arguments
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        asyncio.run(main())
    else:
        print("[!] Varsayılan olarak test amaçlı ilk 5000 alan adı taranacaktır.")
        print("[!] Tüm domainleri taramak için: python bulk_discovery.py --all")
        print("-" * 60)
        asyncio.run(main(limit=5000))
