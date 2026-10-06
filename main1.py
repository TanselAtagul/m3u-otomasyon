import re
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🌐 Güncel Tarayıcı Header Yapısı
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

# 🇹🇷 Korunacak Ulusal Kanallar Beyaz Listesi (Kanal D, Kanal 7, TRT 1 vb. istisnalar)
NATIONAL_WHITELIST = [
    "TRT 1", "KANAL D", "SHOW TV", "STAR TV", "NOW TV", "TV8", "KANAL 7", 
    "BEYAZ TV", "TEVE2", "TV360", "TV4", "TRT TURK", "TRT AVAZ", "TRT WORLD", 
    "TRT ARABI", "TRT KURDI", "TRT 4K", "KANAL 7 AVRUPA", "EURO D", "FOX TV",
    "HABERTURK", "NTV", "CNN TURK", "TRT HABER", "HALK TV", "A HABER", "TGRT HABER"
]

# 🚫 Filtrelenecek Yerel / İstenmeyen Şehir ve Kelimeler Listesi
EXCLUDE_KEYWORDS = [
    "yerel", "local", "fatsa", "ordu", "bursa", "ege", "adana", "rize", "trabzon",
    "antakya", "denizli", "kayseri", "konya", "edirne", "afyon", "sivas", "malatya", 
    "eskişehir", "samsun", "mersin", "gaziantep", "balıkesir", "isparta", "tokat", 
    "elazığ", "kocaeli", "çorum", "manisa", "antalya", "bodrum", "çanakkale", "kahramanmaraş"
]

def is_local_or_unwanted(name, group=""):
    name_upper = name.strip().upper()
    group_upper = group.strip().upper()

    # 1. BEYAZ LİSTE KONTROLÜ: Doğrudan bilinen ulusal kanalsa (Kanal D, Kanal 7 vb.) ASLA eleme!
    for national in NATIONAL_WHITELIST:
        if national in name_upper:
            return False

    # 2. NUMARALI YEREL KANAL KONTROLÜ (Regex):
    # Beyaz listede olmayan "Kanal 15", "Kanal 32", "TV 41", "Tivi 6" vb. numaralı kanalları eler.
    if re.search(r"(KANAL|TIVI|TV)\s*\d+", name_upper):
        return True

    # 3. KELİME FİLTRESİ KONTROLÜ: Şehir isimleri veya "yerel" geçen kanalları eler.
    name_lower = name.lower()
    if any(keyword in name_lower for keyword in EXCLUDE_KEYWORDS):
        return True

    return False

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
                
                # Yerel ve İstenmeyen Kanal Kontrolü
                if is_local_or_unwanted(name, group):
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
    raw_channels = []
    
    for label, url in SOURCES.items():
        raw_channels += parse_m3u(url, label)
        
    # 🧹 MÜKERRER ELENMESİ VE KATEGORİ STANDARTLAŞTIRILMASI
    seen_urls = set()
    seen_names = set()
    cleaned_channels = []

    for name, group, url in raw_channels:
        name_clean = name.strip()
        
        # 1. Aynı akış URL'si daha önce eklendiyse atla
        if url in seen_urls:
            continue
            
        # 2. Aynı kanal adı daha önce eklendiyse (isteğe bağlı mükerrer isim engeli) atla
        if name_clean.upper() in seen_names:
            continue

        seen_urls.add(url)
        seen_names.add(name_clean.upper())

        # Ulusal Türk kanallarının grup başlığını standartlaştır
        final_group = group
        if any(nat in name_clean.upper() for nat in NATIONAL_WHITELIST):
            final_group = "Ulusal"

        cleaned_channels.append((name_clean, final_group, url))

    # M3U Dosyası Oluşturma
    with open("channels1.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("# Otomatik Oluşturulan Playlist - Türk Ulusal & Global Müzik\n")
        for name, group, url in cleaned_channels:
            f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')
            
    print(f"--- İşlem Tamamlandı: {len(cleaned_channels)} temizlenmiş kanal channels1.m3u dosyasına kaydedildi. ---")

if __name__ == "__main__":
    main()
