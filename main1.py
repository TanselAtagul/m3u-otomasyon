
    

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

# 🌐 Kaynaklara Yeni Yetişkin (+18) Listesi Eklendi
SOURCES = {
    "Türk Ulusal": "https://onureroz.com/indirmeler/turk/index.m3u",
    "Türk Yayınları (IPTV-Org)": "https://iptv-org.github.io/iptv/countries/tr.m3u",
    "Yetişkin (+18)": "https://raw.githubusercontent.com/Izanami1618/AdultChannels/refs/heads/main/%2B18%20Channels"
    #"Müzik TV (Global)": "https://iptv-org.github.io/iptv/categories/music.m3u"
}

# 🇹🇷 Kanal Logoları Kütüphanesi
LOGOS = {
    "TRT HABER": "https://upload.wikimedia.org/wikipedia/commons/b/b3/TRT_Haber_logo_2021.png",
    "TRT SPOR": "https://upload.wikimedia.org/wikipedia/commons/a/ae/TRT_Spor_logo_2021.png",
    "TRT BELGESEL": "https://upload.wikimedia.org/wikipedia/commons/8/82/TRT_Belgesel_logo_2021.png",
    "TRT ÇOCUK": "https://upload.wikimedia.org/wikipedia/commons/7/7b/TRT_%C3%87ocuk_logo_2021.png",
    "TRT MÜZİK": "https://upload.wikimedia.org/wikipedia/commons/8/8f/TRT_M%C3%BCzik_logo_2021.png",
    "A SPOR": "https://upload.wikimedia.org/wikipedia/commons/2/23/A_Spor_logo.png",
    "A HABER": "https://upload.wikimedia.org/wikipedia/commons/5/52/A_Haber_logo.png",
    "NTV": "https://upload.wikimedia.org/wikipedia/commons/3/36/NTV_logo.png",
    "CNN TURK": "https://upload.wikimedia.org/wikipedia/commons/8/80/CNN_T%C3%BCrk_logo.png",
    "HABERTURK": "https://upload.wikimedia.org/wikipedia/commons/6/61/Habert%C3%BCrk_TV_logo.png",
    "HALK TV": "https://upload.wikimedia.org/wikipedia/commons/8/8c/Halk_TV_logo.png",
    "TELE 1": "https://upload.wikimedia.org/wikipedia/commons/c/c2/Tele1_logo.png",
    "KRT TV": "https://upload.wikimedia.org/wikipedia/commons/7/7c/KRT_TV_logo.png",
    "TV 100": "https://upload.wikimedia.org/wikipedia/commons/5/55/Tv100_logo.png",
    "24 TV": "https://upload.wikimedia.org/wikipedia/commons/5/50/24_TV_logo.png",
    "DMAX": "https://upload.wikimedia.org/wikipedia/commons/8/87/DMAX_Turkey_logo.png",
    "TLC": "https://upload.wikimedia.org/wikipedia/commons/3/36/TLC_Turkey_logo.png",
    "CNBC-E": "https://upload.wikimedia.org/wikipedia/commons/8/8b/CNBC-e_logo.png"
}

# 🇹🇷 Dinamik Olarak Çekilecek Diğer Kanallar
NATIONAL_WHITELIST = [
    "TEVE 2", "TEVE2", "TV 2", "TV2", "DMAX", "D MAX", "TLC", "CNBC-E", "CNBCE", 
    "HABERTÜRK", "HABERTURK", "HABER TÜRK", "HABER TURK", "NTV", "CNN TÜRK", "CNN TURK", "CNNTÜRK", "CNNTURK",
    "A HABER", "AHABER", "TGRT HABER", "TGRTHABER", "HABER GLOBAL", "HABERGLOBAL",
    "24 TV", "24TV", "TV 24", "TV24", "YİRMİDÖRT", "YIRMIDORT", "HALK TV", "HALKTV",
    "TV 100", "TV100", "TELE 1", "TELE1", "KRT TV", "KRT", "ULUSAL KANAL", "ULUSALKANAL",
    "TRT 4K", "TRT HABER", "TRTHABER", "TRT BELGESEL", "TRTBELGESEL",
    "TRT WORLD", "TRT SPOR", "TRTSPOR", "TRT ÇOCUK", "TRT COCUK", "TRTÇOCUK", "TRTCOCUK",
    "TRT MÜZİK", "TRT MUZIK", "TRTMÜZİK", "TRTMUZIK",
    "A SPOR", "ASPOR", "A NEWS", "ANEWS", "MİNİKA", "MINIKA"
]

# 🛑 MUTLAK YASAKLILAR
STRICT_BLOCK_WORDS = [
    "DIYANET", "DİYANET", "SEMERKAND", "LALEGUL", "LALEGÜL", "KABE", "QURAN", "MENZIL", 
    "MEKKE", "MEDINE", "MADINAH", "MAKKAH", "ZAHRA", "RAFIDAIN", "THAQALAYN", "MUKABELE", 
    "SERCEM", "IKRA", "İSVİÇRE", "ISVICRE", "AVRUPA", "GURBET", "TAGESSCHAU", "RAKUTEN", 
    "SHEMAROO", "ALMAHRIAH", "MEKAMELEEN", "NDR", "INTV", "AUSTRALIA", "AL QURAN",
    "BENGU", "BENGÜ", "BEYAZ", "SOZCU", "SÖZCÜ", "SZC", "TABII", "TABİİ", "TRT 2", "TRT 3", 
    "TRT TURK", "TRT TÜRK", "TV 8.5", "TV8.5", "TV 8,5", "TV85", "TVNET", "TV NET", "VAV",
    "TV 25", "TV 264", "HABER 61", "HABER61", "AS TV", "OLAYTURK", "TH TURK HABER", "TURKHABER"
]

# 🚫 Engellenecek Şehir / Bölge / Yerel Kelimeler
EXCLUDE_KEYWORDS = [
    "yerel", "local", "fatsa", "ordu", "bursa", "ege", "adana", "rize", "trabzon", "dost", "fb", "bjk", "gs", 
    "avaz", "arabi", "eba", "tempo", "fanatik", "mercan", "vuslat", "arma", "hür", "damar", "bürüksel",
    "antakya", "denizli", "kayseri", "konya", "edirne", "afyon", "sivas", "malatya", "sağlık", "kurdi", "sıla", "ezo", "zeyno", 
    "fırat", "genc", "mbc", "maisum", "persiana", "hope", "eskişehir", "samsun", "mersin", "gaziantep", "balıkesir", "isparta", "tokat", 
    "elazığ", "kocaeli", "çorum", "manisa", "antalya", "bodrum", "çanakkale", "kahramanmaraş",
    "anadolu", "karadeniz", "akdeniz", "doğu", "güneydoğu", "trakya", "rumeli",
    "alanya", "aksu", "aras", "brüksel", "cekmekoy", "erciyes", "hunat", "icel", "izmir", 
    "kardelen", "kent", "metropol", "mugla", "olay", "pazarcik", "urfa", "van", "deniz", "derin",
    "ada", "bric", "ciftci", "tarim", "finest", "ilke", "life", "sun", "ton", "tva", "kanal z", "atv"
]

def is_radio(name, group=""):
    text_to_check = f"{name} {group}".upper()
    if re.search(r'\b(FM|RADYO|RADIO|AUDIO|PODCAST|LISTEN|RADIOS)\b', text_to_check):
        return True
    radio_clues = [
        "POWER FM", "SUPER FM", "PAL FM", "SLOW TURK", "VIRGIN", "METRO FM", 
        "JOY FM", "KRAL FM", "ALEM FM", "FENOMEN", "SHOW RADYO", "BEST FM", 
        "BABA RADYO", "LIG RADYO", "TRT FM", "RJD"
    ]
    for clue in radio_clues:
        if clue in text_to_check:
            return True
    return False

def normalize_channel_name(name):
    clean = re.sub(r'[\(\[\{].*?[\)\]\}]', '', name)
    clean = re.sub(r'\b(HD|FHD|SD|UHD|4K|1080P|720P|CANLI|LIVE|TR|TURK|TURKEY)\b', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\s+', ' ', clean).strip().upper()
    return clean

def get_category(name, original_group=""):
    name_upper = name.upper()
    orig_upper = original_group.upper()

    if any(k in name_upper for k in ["SPOR", "SPORT", "TJK", "BEIN", "S SPORT"]): return "3. Spor"
    if any(k in name_upper for k in ["HABER", "NTV", "CNN", "24 TV", "TV 100", "TV100", "HALK", "TELE 1", "TELE1", "KRT", "BLOOMBERG", "NEWS", "A NEWS"]): return "2. Haber"
    if any(k in name_upper for k in ["BELGESEL", "DISCOVERY", "NAT GEO", "HISTORY", "TLC", "DMAX", "WILD", "ANIMAL"]): return "5. Belgesel"
    if any(k in name_upper for k in ["ÇOCUK", "COCUK", "KIDS", "CARTOON", "DISNEY", "MINIKA", "BABY", "NICKELODEON", "ZAROK"]): return "6. Çocuk"
    if any(k in name_upper for k in ["SİNEMA", "SINEMA", "FILM", "MOVIE", "ACTION", "COMEDY", "DRAMA", "DIZI", "DİZİ", "YESILCAM"]): return "4. Sinema & Dizi"
    if any(k in name_upper for k in ["MÜZİK", "MUZIK", "MUSIC", "MTV", "POWER", "KRAL", "NR1", "NUMBER", "VIVA", "DREAM", "AKUSTIK", "TRACE", "VEVO", "XITE", "STINGRAY"]): return "7. Müzik"
    
    # Yeni Eklenen Yetişkin Kategori Yönlendirmesi
    if any(k in name_upper for k in ["ADULT", "XXX", "18+", "PORN", "BRAZZERS", "HUSTLER", "DORCEL", "PLAYBOY", "PRIVATE", "BABES", "TUSHY", "BLACKED", "BANG BROS"]): return "8. Yetişkin"
    if any(a in orig_upper for a in ["YETİŞKİN", "YETISKIN", "ADULT", "XXX", "+18", "18+"]): return "8. Yetişkin"

    for nat in NATIONAL_WHITELIST:
        if nat in name_upper:
            return "1. Ulusal"

    if "MUSIC" in orig_upper: return "7. Müzik"
    if "NEWS" in orig_upper: return "2. Haber"
    if "KIDS" in orig_upper or "ANIMATION" in orig_upper: return "6. Çocuk"
    if "MOVIE" in orig_upper or "CINEMA" in orig_upper: return "4. Sinema & Dizi"
    if "DOCUMENTARY" in orig_upper: return "5. Belgesel"
    if "SPORTS" in orig_upper: return "3. Spor"

    return "Diğer"

def is_local_or_unwanted(name, group=""):
    name_upper = name.strip().upper()
    group_upper = group.upper()

    if any(block in name_upper for block in STRICT_BLOCK_WORDS):
        return True

    if is_radio(name, group):
        return True

    # MÜZİK VE YETİŞKİN KANALLARINA ÖZEL İZİN (Bu kanallar filtreye takılıp silinmez)
    if "MUSIC" in group_upper or any(m in name_upper for m in ["MUSIC", "MTV", "VEVO", "TRACE", "STINGRAY", "XITE"]):
        return False
    if any(a in group_upper for a in ["YETİŞKİN", "ADULT", "XXX", "+18", "18+"]) or any(a in name_upper for a in ["XXX", "BRAZZERS", "HUSTLER", "ADULT"]):
        return False

    name_lower = name.lower()
    pattern = r'\b(' + '|'.join(re.escape(kw) for kw in EXCLUDE_KEYWORDS) + r')\b'
    if re.search(pattern, name_lower):
        return True

    for national in NATIONAL_WHITELIST:
        if national in name_upper:
            return False

    if re.search(r"(KANAL|TIVI|TV)\s*\d+", name_upper):
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
    print(f"[{len(entries)} kanal için link doğrulaması yapılıyor...]")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_map = {
            executor.submit(verify_link, link): (name, group, logo, link)
            for name, group, logo, link in entries
        }
        for future in as_completed(future_map):
            name, group, logo, link = future_map[future]
            if future.result():
                valid_results.append((name, group, logo, link))
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
                
                logo_match = re.search(r'tvg-logo="([^"]+)"', line_info, re.IGNORECASE)
                logo = logo_match.group(1) if logo_match else ""

                name = line_info.split(",")[-1].strip()
                
                if is_local_or_unwanted(name, group):
                    continue

                if i + 1 < len(lines):
                    link = lines[i + 1].strip()
                    if link.startswith("http"):
                        entries.append((name, group, logo, link))
        
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

    for name, group, logo, url in raw_channels:
        normalized_name = normalize_channel_name(name)
        nospace_name = normalized_name.replace(" ", "")
        
        if url in seen_urls or nospace_name in seen_normalized_names:
            continue

        seen_urls.add(url)
        seen_normalized_names.add(nospace_name)

        final_group = get_category(normalized_name, group)
        if final_group == "Diğer":
            continue

        dict_logo = LOGOS.get(normalized_name, "")
        final_logo = dict_logo if dict_logo else logo

        cleaned_channels.append((name.strip(), final_group, final_logo, url))

    cleaned_channels.sort(key=lambda x: (x[1], x[0]))

    # --- MANUEL EKLENEN KANALLAR (Resmi & Kesintisiz Ulusal Yayınlar) ---
    manual_channels = [
        ("ATV HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/e/e0/ATV_logo.png", "https://trkvz-live.daioncdn.net/atv/atv.m3u8"),
        ("Kanal D HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/e/eb/Kanal_D_logo_2013.png", "https://demiroren.daioncdn.net/kanald/kanald.m3u8"),
        ("Show TV HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/9/90/Show_TV_logo.png", "https://ciner.daioncdn.net/showtv/showtv.m3u8"),
        ("Star TV HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/8/87/Star_TV_logo_2020.png", "https://dogus.daioncdn.net/startv/startv.m3u8"),
        ("NOW TV HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/9/9f/Now_TV_Turkey_logo.png", "https://uycyyuuzyh.turknet.ercdn.net/nphindgytw/nowtv/nowtv.m3u8"),
        ("TV8 HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/0/07/TV8_logo.png", "https://tv8.daioncdn.net/tv8/tv8.m3u8"),
        ("Kanal 7 HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/1/1d/Kanal_7_logo.png", "https://kanal7-live.daioncdn.net/kanal7/kanal7_1080p.m3u8"),
        ("TRT 1 HD", "1. Ulusal", "https://upload.wikimedia.org/wikipedia/commons/9/94/TRT_1_logo_2021.png", "https://tv-trt1.medya.trt.com.tr/master_720.m3u8")
    ]
    
    cleaned_channels.extend(manual_channels)
    cleaned_channels.sort(key=lambda x: (x[1], x[0]))
    # ----------------------------------------------

    with open("channels1.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write("# Otomatik Oluşturulan Playlist - Sadece TV Kanalları (Radyosuz)\n")
        for name, group, logo, url in cleaned_channels:
            logo_attr = f' tvg-logo="{logo}"' if logo else ""
            f.write(f'#EXTINF:-1 group-title="{group}"{logo_attr},{name}\n{url}\n')
            
    print(f"--- İşlem Tamamlandı: {len(cleaned_channels)} adet TV kanalı 'channels1.m3u' dosyasına kaydedildi. ---")

if __name__ == "__main__":
    main()
