import requests

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

my_playlist = "#EXTM3U\n"
added_channels = set()

for url in SOURCES:
    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()

        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                line_info = lines[i]
                stream_url = lines[i + 1] if i + 1 < len(lines) else ""

                if not stream_url or stream_url in added_channels:
                    continue

                raw_name = line_info.split(",")[-1].strip()

                for group_name, channel_list in CATEGORIES.items():
                    matched = False
                    for target_name in channel_list:
                        if target_name.lower() in raw_name.lower():
                            clean_extinf = f'#EXTINF:-1 group-title="{group_name}",{target_name}'
                            my_playlist += f"{clean_extinf}\n{stream_url}\n"
                            added_channels.add(stream_url)
                            matched = True
                            break
                    if matched:
                        break
    except Exception as e:
        print(f"Hata ({url}): {e}")

with open("custom_list.m3u", "w", encoding="utf-8") as f:
    f.write(my_playlist)

print("M3U dosyası başarıyla güncellendi.")
