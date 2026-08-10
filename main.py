import requests
import re

# Kaynak M3U Bağlantıları
SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u",
    "https://iptv-org.github.io/iptv/index.category.m3u",
]

# Kategoriler ve Aratılacak Kanal İsimleri
CATEGORIES = {
    "Türkiye - Genel": [
        "TRT 1", "ATV", "KANAL D", "SHOW TV", "STAR TV", "TV8", "NOW", "KANAL 7"
    ],
    "Türkiye - Haber": [
        "TRT HABER", "HABERTÜRK", "NTV", "A HABER", "SÖZCÜ TV", "HALK TV", "CNN TÜRK"
    ],
    "Türkiye - Belgesel": [
        "TRT BELGESEL", "HABERTURK BELGESEL", "TGRT BELGESEL", "AGRO TV", 
        "TLC", "HABITAT", "YABAN TV"
    ],
    "Türkiye - Çocuk": [
        "TRT ÇOCUK", "MINIKA ÇOCUK", "MINIKA GO", "CARTOON NETWORK", 
        "ZAROK TV", "CARTOONITO", "KIDS ARENA", "SPACE TOON", 
        "MOONBUG", "DA VINCI"
    ],
    "Türkiye - Müzik": [
        "POWER TV", "DREAM TURK", "KRAL POP", "NR1 TV", "NUMBER ONE", 
        "TRT MÜZİK", "TATLISES"
    ],
    "Türkiye - Radyo": [
        "45'LİK", "FENOMEN", "JOYTÜRK", "KRAL FM", "SLOWTÜRK", 
        "POWER FM", "ALEM FM", "SUPER FM", "METRO FM", "PAL FM"
    ],
    "Uluslararası - Genel": [
        "BBC ONE", "BBC TWO", "ITV", "CHANNEL 4",
        "DAS ERSTE", "ARD", "ZDF", "RTL", "PROSIEBEN",
        "TF1", "FRANCE 2", "FRANCE 3", "M6",
        "RAI 1", "RAI 2", "RAI 3", "CANALE 5",
        "LA 1", "ANTENA 3", "TELECINCO"
    ],
    "Uluslararası - Müzik": [
        "DELUXE MUSIC", "SCHLAGER DELUXE", "NRJ HITS", "CITY TV", "THE VOICE", 
        "BALKANIKA", "KISS TV", "ZU TV", "UTV ROMANIA", "RU.TV", "MUZ-TV", 
        "BRIDGE TV", "DM SAT", "IDJ TV", "ESKA TV", "POLO TV", "STARS.TV", 
        "MUSIC BOX", "MAD TV", "M1", "M2"
    ],
    "Uluslararası - Haber": [
        "BBC NEWS", "EURONEWS", "AL JAZEERA", "BLOOMBERG"
    ],
    "Uluslararası - Belgesel": [
        "CGTN DOCUMENTARY", "NASA TV", "ARTE", "FRANCE 5", 
        "ZDFINFO", "3SAT", "BBC FOUR"
    ]
}

def get_quality_score(title, url):
    """Yayın kalitesine göre puan verir (En yüksek çözünürlüğü seçmek için)."""
    combined = (title + " " + url).lower()
    if "1080" in combined or "fhd" in combined or "fullhd" in combined:
        return 4
    if "720" in combined or "hd" in combined:
        return 3
    if "480" in combined or "sd" in combined:
        return 2
    if "360" in combined:
        return 1
    return 0

# Seçilen en iyi kanalları tutacak sözlük: (group_name, target_name) -> (score, stream_url)
best_streams = {}

for url in SOURCES:
    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()

        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_info = lines[i]
                stream_url = lines[i + 1] if i + 1 < len(lines) else ""

                if not stream_url or not stream_url.startswith("http"):
                    continue

                raw_name = line_info.split(",")[-1].strip()

                for group_name, channel_list in CATEGORIES.items():
                    matched = False
                    for target_name in channel_list:
                        # Regex ile tam kelime eşleşmesi kontrolü (örn: "ATV" ararken "ATV Alanya" eşleşmez)
                        pattern = r'(?i)\b' + re.escape(target_name) + r'\b'
                        if re.search(pattern, raw_name):
                            score = get_quality_score(raw_name, stream_url)
                            key = (group_name, target_name)
                            
                            # Eğer daha önce eklenmemişse veya yeni linkin kalitesi daha yüksekse güncelle
                            if key not in best_streams or score > best_streams[key]["score"]:
                                best_streams[key] = {
                                    "score": score,
                                    "url": stream_url
                                }
                            matched = True
                            break
                    if matched:
                        break
    except Exception as e:
        print(f"Hata ({url}): {e}")

# M3U Dosyasını Oluşturma
my_playlist = "#EXTM3U\n"
for (group_name, target_name), data in best_streams.items():
    clean_extinf = f'#EXTINF:-1 group-title="{group_name}",{target_name}'
    my_playlist += f"{clean_extinf}\n{data['url']}\n"

with open("custom_list.m3u", "w", encoding="utf-8") as f:
    f.write(my_playlist)

print("M3U dosyası tekil ve en yüksek çözünürlüklü kanallarla başarıyla güncellendi.")
