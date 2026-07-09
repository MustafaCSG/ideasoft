import requests
from bs4 import BeautifulSoup
import sys

def main():
    # Force UTF-8 stdout encoding for Windows compatibility
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    print("=" * 60)
    print("       IdeaHunter - IdeaSoft Canlı Doğrulama Testi (PoC)")
    print("=" * 60)
    
    fallback_domains = [
        "sweetbaby.myideasoft.com", # Bakir / Kapalı şablon
        "senetsepet.com",           # Aktif / Tasarlanmış
        "hariboshop.com",           # Aktif / Tasarlanmış
        "istikbal.com.tr",          # Aktif / Tasarlanmış
        "nonexistent-ideasoft-site.myideasoft.com" # Erişilemeyen / Boş
    ]
    
    url = "https://crt.sh/?q=%.myideasoft.com&output=json"
    print("[1] crt.sh üzerinden son sertifika kayıtları sorgulanıyor...")
    
    unique_domains = []
    try:
        # Request with a 15s timeout
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            data_sorted = sorted(data, key=lambda x: x.get('entry_timestamp', ''), reverse=True)
            for entry in data_sorted:
                domain = entry.get('common_name')
                if domain and domain not in unique_domains and not domain.startswith("*."):
                    unique_domains.append(domain)
                    if len(unique_domains) >= 10:
                        break
            print(f"[+] crt.sh'tan en güncel {len(unique_domains)} benzersiz site başarıyla çekildi.")
        else:
            print(f"[-] crt.sh API HTTP hatası (Status: {response.status_code}). Fallback moduna geçiliyor.")
            unique_domains = fallback_domains
    except Exception as e:
        print(f"[-] crt.sh sorgusu zaman aşımına uğradı veya hata verdi: {e}")
        print("[!] Canlı testi tamamlamak için önceden tanımlanmış test listesi (Fallback) kullanılıyor...")
        unique_domains = fallback_domains
        
    print("-" * 60)
    print(f"Test edilecek domainler: {', '.join(unique_domains)}")
    print("-" * 60)
    
    # 2. Her alan adını canlı kontrol et
    poc_results = []
    for idx, domain in enumerate(unique_domains):
        site_url = f"https://{domain}"
        print(f"[{idx+1}/{len(unique_domains)}] Kontrol ediliyor: {site_url}")
        
        try:
            res = requests.get(site_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            
            headers = res.headers
            is_ideasoft = 'ideasoft' in str(headers.get('X-Powered-By', '')).lower() or \
                          'ideasoft' in str(headers.get('Powered-By', '')).lower() or \
                          'x-idea-cluster' in headers
            
            if is_ideasoft:
                html_content = res.text
                soup = BeautifulSoup(html_content, 'html.parser')
                body_text = soup.body.get_text(strip=True) if soup.body else ""
                
                status = "AKTIF / TASARLANMIS"
                if "geçici olarak servis dışıdır" in body_text.lower() or "yapım aşamasında" in body_text.lower():
                    status = "BAKIR / YAPIM ASAMASINDA"
                
                print(f"   |-> [OK] IdeaSoft Sitenin Durumu: {status}")
                poc_results.append({
                    "domain": domain,
                    "status": status,
                    "url": site_url
                })
            else:
                print("   |-> [-] IdeaSoft imzası bulunamadı.")
        except requests.exceptions.RequestException as e:
            print(f"   |-> [FAIL] Siteye erişilemedi (Bağlantı hatası).")
            
    # 3. Sonuçları listele ve dosyaya kaydet
    print("\n" + "=" * 60)
    print("                 TEST SONUÇLARI ÖZETİ")
    print("=" * 60)
    
    with open("poc_sonuclari.txt", "w", encoding="utf-8") as f:
        f.write("=== IdeaHunter PoC Sonuçları ===\n\n")
        for item in poc_results:
            line = f"- Domain: {item['domain']} | Durum: {item['status']} | Link: {item['url']}\n"
            print(line.strip())
            f.write(line)
            
    print("-" * 60)
    print("[OK] Sonuçlar 'poc_sonuclari.txt' dosyasına kaydedildi.")

if __name__ == "__main__":
    main()
