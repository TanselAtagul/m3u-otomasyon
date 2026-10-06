import re
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}
TIMEOUT = 4
MAX_WORKERS = 30

SOURCES = {
    "Türk Ulusal": "https://onureroz.com/indirmeler/turk/index.m3u",
    "Türk Yayınları (IPTV-Org)": "https://iptv-org.github.io/iptv/countries/tr.m3u",
    "Müzik TV (Global)": "https://iptv-org.github.io/iptv/categories/music.m3u"
}

# 🇹🇷 Sadece Kabul Edilecek Temel Ulusal TV Kanalları
NATIONAL_WHITELIST = [
    "TRT 1", "KANAL D", "SHOW TV", "STAR TV", "NOW TV", "TV8", "KANAL 7", 
    "BEYAZ TV", "TEVE2", "TV360", "TV4", "TRT TURK", "TRT AVAZ", "TRT WORLD", 
    "TRT ARABI", "TRT KURDI", "TRT 4K", "KANAL 7 AVRUPA", "EURO D", "FOX TV",
    "HABERTURK", "NTV", "CNN TURK", "TRT HABER", "HALK TV", "A HABER", "TGRT HABER",
    "HABER GLOBAL", "24 TV", "EKOL TV", "TELE1", "ULKE TV", "TV 8.5"
]

# 🚫 Engellenecek Şehir / Bölge / Yerel Kelimeler
EXCLUDE_KEYWORDS = [
    "yerel", "local", "fatsa", "ordu", "bursa", "ege", "adana", "rize", "trabzon",
    "antakya", "denizli", "kayseri", "konya", "edirne", "afyon", "sivas", "malatya", 
    "eskişehir", "samsun", "mersin", "gaziantep", "balıkesir", "isparta", "tokat", 
    "elazığ", "kocaeli", "çorum", "manisa", "antalya", "bodrum", "çanakkale", "kahramanmaraş",
    "anadolu", "karadeniz", "akdeniz", "doğu", "güneydoğu", "trakya", "rumeli"
]

# 📻 RADYO FİLTRESİ: İsmi veya grubu radyoyu çağrıştıran yayınları engeller
RADIO_KEYWORDS = ["RADYO", "RADIO", " FM ", "FM1", "FM2", "AUDIO", "RJD", "POWER FM", "SUPER FM", "PAL FM", "SLOW TURK"]

def is_radio(name, group=""):
    """Yayın isminde veya grubunda radyo ibaresi olup olmadığını kontrol eder."""
    text_to_check = f"{name} {group}".upper()
    
    # İsmin içinde açıkça radyo / fm geçiyorsa
    for key in RADIO_KEYWORDS:
        if key in text_to_check:
            return True
            
    # Kelime sonunda .FM bitişleri (örneğin "Virgin.FM", "MetroFM")
    if re.search(r'\b\w+FM\b', text_to_check):
        return True
        
    return False

def normalize_channel_name(name):
    """Kanal ismindeki çözünürlük ve ek bilgileri temizler."""
    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name)
    clean = re.sub(r'\b(HD|FHD|SD|UHD|4K|1080P|720P|CANLI|LIVE|TR|TURK|TURKEY)\b', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip().upper()
    return clean

def is_local_or_unwanted(name, group=""):
    name_upper = name.strip().upper()

    # 1. RADYO KONTROLÜ (Açıksa doğrudan engelle)
    if is_radio(name, group):
        return True

    # 2. Ulusal TV kanalı beyaz listesindeyse izin ver
    for national in NATIONAL_WHITELIST:
        if national in name_upper:
            return False

    # 3. Numaralı yerel TV kanallarını engelle (Kanal 15, TV 41 vb.)
    if re.search(r"(KANAL|TIVI|TV)\s*\d+", name_upper):
        return True

    # 4. Şehir ve bölge kelimelerini engelle
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
        if res.status_code != 200:
            return []

        lines = res.text.splitlines()
        entries = []
        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_info = lines[i]
                group_match = re.search(r'group-title="([^"]+)"', line_info)
                group = group_match.group(1) if group_match else default_label
                name = line_info.split(",")[-1].strip()
                
                # Yerel TV veya Radyo ise atla
                if is_local_or_unwanted(name, group):
                    continue

                if i + 1 < len(lines):
                    link = lines[i + 1].strip()
                    if link.startswith("http"):
                        entries.append((name, group, link))
        
        return threaded_verify_links(entries)
    except Exception as e:
        print(f"[{default_label}] Hata oluştu: {e}")
        return []

def main():
    print(f"--- Güncelleme Başlatıldı (main1): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    raw_channels = []
    
    for label, url in SOURCES.items():
        raw_channels += parse_m3u(url, label)
        
    seen_urls = set()
    seen_normalized_names = set()
    cleaned_channels = []

    for name, group, url in raw_channels:
        normalized_name = normalize_channel_name(name)
        
        # 1. URL Mükerrerliği Engeli
        if url in seen_urls:
            continue
            
        # 2. İsim Mükerrerliği Engeli
        if normalized_name in seen_normalized_names:
            continue

        seen_urls.add(url)
        seen_normalized_names.add(normalized_name)

        # Grup Adını Standartlaştır
        final_group = group
        if any(nat in normalized_name for nat in NATIONAL_WHITELIST):
            final_group = "Ulusal"

        cleaned_channels.append((name.strip(), final_group, url))

    # M3U Dosyasını Yaz
    with open("channels1.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("# Otomatik Oluşturulan Playlist - Sadece TV Kanalları (Radyosuz)\n")
        for name, group, url in cleaned_channels:
            f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')
            
    print(f"--- İşlem Tamamlandı: {len(cleaned_channels)} adet TV kanalı 'channels1.m3u' dosyasına kaydedildi. ---")

if __name__ == "__main__":
    main()
