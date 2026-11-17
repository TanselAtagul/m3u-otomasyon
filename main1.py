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

# LİNKLERİN ÇALIŞIP ÇALIŞMADIĞINI TEST ETMEK İSTİYORSANIZ True YAPIN.
# (Ücretsiz IPTV listelerinde link testi genellikle kanalların %90'ını siler)
CHECK_LINKS = False 

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

# 🚫 Engellenecek Şehir / Bölge / Yerel Kelimeler (Genel kelimeler çıkarıldı)
EXCLUDE_KEYWORDS = [
    "yerel", "local", "fatsa", "ordu", "bursa", "ege", "adana", "rize", "trabzon", "dost", "fb", "bjk", "gs", 
    "avaz", "diyanet", "arabi", "eba", "tempo", "fanatik", "mercan", "vuslat", "arma", "hür", "damar", "bürüksel",
    "antakya", "denizli", "kayseri", "konya", "edirne", "afyon", "sivas", "malatya", "sağlık", "kurdi", "sıla", "ezo", "zeyno", "bengü", "tjk",
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
        # stream=False yapıldı, sadece başlıklar (headers) çekilerek hızlandırıldı
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT, stream=False)
        return url if res.status_code == 200 else None
    except:
        return None

def threaded_verify_links(entries):
    if not CHECK_LINKS:
        return entries # Link kontrolü kapalıysa direkt listeyi döndür
        
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

        final_group = group
        if any(nat in normalized_name for nat in NATIONAL_WHITELIST):
            final_group = "Ulusal TV"

        cleaned_channels.append((name.strip(), final_group, url))

    with open("channels1.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("# Otomatik Oluşturulan Playlist - Sadece TV Kanalları (Radyosuz)\n")
        for name, group, url in cleaned_channels:
            f.write(f'#EXTINF:-1 group-title="{group}",{name}\n{url}\n')
            
    print(f"--- İşlem Tamamlandı: {len(cleaned_channels)} adet TV kanalı 'channels1.m3u' dosyasına kaydedildi. ---")

if __name__ == "__main__":
    main()
