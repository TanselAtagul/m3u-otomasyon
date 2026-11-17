import re
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}
TIMEOUT = 5
MAX_WORKERS = 30
CHECK_LINKS = False 

# NOT: Sadece Türk kanallarını istiyorsanız "Müzik TV (Global)" satırını silebilirsiniz.
SOURCES = {
    "Türk Ulusal": "https://onureroz.com/indirmeler/turk/index.m3u",
    "Türk Yayınları (IPTV-Org)": "https://iptv-org.github.io/iptv/countries/tr.m3u",
    "Müzik TV (Global)": "https://iptv-org.github.io/iptv/categories/music.m3u" 
}

# 🇹🇷 Kabul Edilecek Temel Ulusal TV Kanalları
NATIONAL_WHITELIST = [
    "KANAL D", "KANALD", "SHOW TV", "SHOWTV", "STAR TV", "STARTV", "NOW TV", "NOWTV", "NOW",
    "TV 8", "TV8", "TV 8.5", "TV8.5", "TV8,5", "TV85", "KANAL 7", "KANAL7", "BEYAZ TV", "BEYAZTV",
    "TEVE 2", "TEVE2", "TV 2", "TV2", "DMAX", "D MAX", "TLC", 
    "HABERTÜRK", "HABERTURK", "HABER TÜRK", "HABER TURK", "NTV", "CNN TÜRK", "CNN TURK", "CNNTÜRK", "CNNTURK",
    "A HABER", "AHABER", "TGRT HABER", "TGRTHABER", "HABER GLOBAL", "HABERGLOBAL",
    "24 TV", "24TV", "TV 24", "TV24", "YİRMİDÖRT", "YIRMIDORT", "HALK TV", "HALKTV",
    "SÖZCÜ TV", "SOZCU TV", "SÖZCÜTV", "SOZCUTV", "SZC TV", "SZCTV", "TV 100", "TV100",
    "TELE 1", "TELE1", "KRT TV", "KRT", "ULUSAL KANAL", "ULUSALKANAL",
    "BENGÜTÜRK", "BENGUTURK", "BENGÜ TÜRK", "BENGU TURK",
    "TRT 1", "TRT1", "TRT HABER", "TRTHABER", "TRT BELGESEL", "TRTBELGESEL",
    "TRT SPOR", "TRTSPOR", "TRT ÇOCUK", "TRT COCUK", "TRTÇOCUK", "TRTCOCUK",
    "TRT MÜZİK", "TRT MUZIK", "TRTMÜZİK", "TRTMUZIK",
    "A SPOR", "ASPOR", "A NEWS", "ANEWS", "MİNİKA", "MINIKA", "VAV TV", "VAVTV"
]

# 🚫 Engellenecek Şehir / Bölge / Yerel Kelimeler (Regex ile Tam Kelime)
EXCLUDE_KEYWORDS = [
    "yerel", "local", "fatsa", "ordu", "bursa", "ege", "adana", "rize", "trabzon", "dost", "fb", "bjk", "gs", 
    "avaz", "arabi", "eba", "tempo", "fanatik", "mercan", "vuslat", "arma", "hür", "damar", "bürüksel",
    "antakya", "denizli", "kayseri", "konya", "edirne", "afyon", "sivas", "malatya", "sağlık", "kurdi", "sıla", "ezo", "zeyno", "bengü", 
    "fırat", "genc", "mbc", "maisum", "persiana", "hope", "eskişehir", "samsun", "mersin", "gaziantep", "balıkesir", "isparta", "tokat", 
    "elazığ", "kocaeli", "çorum", "manisa", "antalya", "bodrum", "çanakkale", "kahramanmaraş",
    "anadolu", "karadeniz", "akdeniz", "doğu", "güneydoğu", "trakya", "rumeli"
]

# 📻 RADYO FİLTRESİ
RADIO_KEYWORDS = ["RADYO", "RADIO", " FM ", "FM1", "FM2", "AUDIO", "RJD", "POWER FM", "SUPER FM", "PAL FM", "SLOW TURK"]

def is_radio(name, group=""):
    text_to_check = f"{name} {group}".upper()
    for key in RADIO_KEYWORDS:
        if key in text_to_check:
            return True
    if re.search(r'\b\w+FM\b', text_to_check):
        return True
    return False

def normalize_channel_name(name):
    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name)
    clean = re.sub(r'\b(HD|FHD|SD|UHD|4K|1080P|720P|CANLI|LIVE|TR|TURK|TURKEY)\b', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip().upper()
    return clean

def get_category(name, original_group=""):
    """Kanal isimlerini ve eski gruplarını analiz edip temiz Türkçe kategorilere ayırır."""
    name_upper = name.upper()
    orig_upper = original_group.upper()

    # 1. İsme Göre Kesin Kategori Atamaları (Öncelikli)
    if any(k in name_upper for k in ["SPOR", "SPORT", "TJK", "BEIN", "S SPORT"]):
        return "Spor"
    if any(k in name_upper for k in ["HABER", "NTV", "CNN", "24 TV", "TV 100", "TV100", "HALK", "TELE 1", "TELE1", "KRT", "BLOOMBERG", "NEWS", "A NEWS"]):
        return "Haber"
    if any(k in name_upper for k in ["BELGESEL", "DISCOVERY", "NAT GEO", "HISTORY", "TLC", "DMAX", "WILD", "ANIMAL"]):
        return "Belgesel"
    if any(k in name_upper for k in ["ÇOCUK", "COCUK", "KIDS", "CARTOON", "DISNEY", "MINIKA", "BABY", "NICKELODEON", "ZAROK"]):
        return "Çocuk"
    if any(k in name_upper for k in ["SİNEMA", "SINEMA", "FILM", "MOVIE", "ACTION", "COMEDY", "DRAMA", "DIZI", "DİZİ", "YESILCAM"]):
        return "Sinema & Dizi"
    if any(k in name_upper for k in ["MÜZİK", "MUZIK", "MUSIC", "MTV", "POWER", "KRAL", "NR1", "NUMBER", "VIVA", "DREAM", "AKUSTIK", "TRACE", "VEVO", "XITE"]):
        return "Müzik"
    if any(k in name_upper for k in ["DIYANET", "DİYANET", "SEMERKAND", "LALEGUL", "LALEGÜL", "KABE", "QURAN", "MENZIL"]):
        return "Dini"

    # 2. Üstteki kategorilere girmediyse ve Beyaz Listede varsa "Ulusal" yap
    for nat in NATIONAL_WHITELIST:
        if nat in name_upper:
            return "Ulusal"

    # 3. İsimden anlaşılamadıysa orijinal M3U grubuna bakarak Türkçeleştir
    if "MUSIC" in orig_upper: return "Müzik"
    if "NEWS" in orig_upper: return "Haber"
    if "KIDS" in orig_upper or "ANIMATION" in orig_upper: return "Çocuk"
    if "MOVIE" in orig_upper or "CINEMA" in orig_upper: return "Sinema & Dizi"
    if "DOCUMENTARY" in orig_upper: return "Belgesel"
    if "RELIGIOUS" in orig_upper: return "Dini"
    if "SPORTS" in orig_upper: return "Spor"

    # 4. Hiçbirine uymuyorsa
    return "Diğer"

def is_local_or_unwanted(name, group=""):
    name_upper = name.strip().upper()

    if is_radio(name, group):
        return True

    # Ulusal listede varsa DİREKT KABUL ET
    for national in NATIONAL_WHITELIST:
        if national in name_upper:
            return False

    if re.search(r"(KANAL|TIVI|TV)\s*\d+", name_upper):
        return True

    # Yasaklı kelimeleri "Tam Kelime" (Regex) olarak kontrol et
    name_lower = name.lower()
    pattern = r'\b(' + '|'.join(re.escape(kw) for kw in EXCLUDE_KEYWORDS) + r')\b'
    if re.search(pattern, name_lower):
        return True

    return False

def verify_link(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=False)
        return url if res.status_code == 200 else None
    except:
        return None

def threaded_verify_links(entries):
    if not CHECK_LINKS:
        return entries
        
    valid_results = []
    print(f"[{len(entries)} kanal için link doğrulaması yapılıyor. Bu işlem uzun sürebilir...]")
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
    print(f"--- Güncelleme Başlatıldı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
    raw_channels = []
    
    for label, url in SOURCES.items():
        raw_channels += parse_m3u(url, label)
        
    seen_urls = set()
    seen_normalized_names = set()
    cleaned_channels = []

    for name, group, url in raw_channels:
        normalized_name = normalize_channel_name(name)
        
        if url in seen_urls or normalized_name in seen_normalized_names:
            continue

        seen_urls.add(url)
        seen_normalized_names.add(normalized_name)

        # YENİ KATEGORİ SİSTEMİNİ UYGULA
        final_group = get_category(normalized_name, group)

        cleaned_channels.append((name.strip(), final_group, url))

    # Dosyayı kategoriye (group-title) göre A'dan Z'ye sıralayarak yaz
    cleaned_channels.sort(key=lambda x: (x[1], x[0]))

    with open("channels1.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("# Otomatik Oluşturulan Playlist - Sadece TV Kanalları (Radyosuz)\n")
        for name, group, url in cleaned_channels:
            f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')
            
    print(f"--- İşlem Tamamlandı: {len(cleaned_channels)} adet TV kanalı 'channels1.m3u' dosyasına kaydedildi. ---")

if __name__ == "__main__":
    main()
