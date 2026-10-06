import re
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🌐 Güncel Tarayıcı Header Yapısı (Engellemeleri aşmak için)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}
TIMEOUT = 4
MAX_WORKERS = 30

# 🔗 Yalnızca Türk Ulusal ve Dünya Geneli Müzik/Klip Kaynakları
SOURCES = {
    # Özel Türk M3U Kaynağınız
    "Türk Ulusal": "https://onureroz.com/indirmeler/turk/index.m3u",
    
    # Türkiye Geneli Açık Kaynak Liste (Genişletilmiş Ulusal Yayınlar)
    "Türk Yayınları (IPTV-Org)": "https://iptv-org.github.io/iptv/countries/tr.m3u",
    
    # Tüm Dünyadan Canlı Müzik ve Klip Kanalları
    "Müzik & Klip (Global)": "https://iptv-org.github.io/iptv/categories/music.m3u"
}

# 🚫 Filtrelenecek Yerel / İstenmeyen Kelimeler Listesi
EXCLUDE_KEYWORDS = [
    "yerel", "local", "fatsa", "ordu", "bursa", "ege", "adana", "rize", "trabzon",
    "antakya", "denizli", "kayseri", "konya", "tv41", "tv19", "kanal26", "kanal3",
    "edirne", "afyon", "sivas", "malatya", "eskişehir", "samsun", "mersin", "gaziantep",
    "balıkesir", "isparta", "tokat", "elazığ", "kocaeli", "çorum", "manisa"
]

def is_local_or_unwanted(name):
    name_lower = name.lower()
    return any(keyword in name_lower for keyword in EXCLUDE_KEYWORDS)

def verify_link(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=True)
        return url if res.status_code == 200 else None
    except:
        return None

def threaded_verify_links(entries):
    valid_results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(verify_link, link): (name, group, link)
            for name, group, link in entries
        }
        for future in as_completed(future_map):
            name, group, link = future_map[future]
            if future.result():
                valid_results.append((name, group, link))
    return valid_results

def parse_m3u(url, default_label):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        print(f"[{default_label}] HTTP Yanıt Kodu: {res.status_code}")
        
        if res.status_code != 200:
            print(f"[{default_label}] Kaynağa erişilemedi ({res.status_code}), bu kaynak atlanıyor.")
            return []

        lines = res.text.splitlines()
        entries = []
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_info = lines[i]
                
                # Grup Adı Yakalama
                group_match = re.search(r'group-title="([^"]+)"', line_info)
                group = group_match.group(1) if group_match else default_label
                
                name = line_info.split(",")[-1].strip()
                
                # Yerel kanal kontrolü
                if is_local_or_unwanted(name):
                    continue

                if i + 1 < len(lines):
                    link = lines[i + 1].strip()
                    if link.startswith("http"):
                        entries.append((name, group, link))
        
        print(f"[{default_label}] {len(entries)} potansiyel kanal bulundu, doğrulanıyor...")
        return threaded_verify_links(entries)
    except Exception as e:
        print(f"[{default_label}] Hata oluştu: {e}")
        return []

def main():
    print(f"--- Güncelleme Başlatıldı (main1): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    all_channels = []
    
    for label, url in SOURCES.items():
        all_channels += parse_m3u(url, label)
        
    # M3U Dosyası Oluşturma
    with open("channels1.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("# Otomatik Oluşturulan Playlist - Türk Ulusal & Global Müzik\n")
        for name, group, url in all_channels:
            f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')
            
    print(f"--- İşlem Tamamlandı: {len(all_channels)} çalışan kanal channels1.m3u dosyasına kaydedildi. ---")

if __name__ == "__main__":
    main()
