import requests

# Kaynak M3U Bağlantıları
SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u",
    "https://iptv-org.github.io/iptv/index.category.m3u",
]

# Kategori ve İlgili Kanal Listeleri (Aranacak Kelimeler)
CATEGORIES = {
    "Türkiye - Genel": [
        "TRT 1", "ATV", "KANAL D", "SHOW TV", "STAR TV", "TV8", "NOW", "FOX", "BEYAZ TV", "KANAL 7"
    ],
    "Türkiye - Haber": [
        "TRT HABER", "HABERTÜRK", "NTV", "A HABER", "SÖZCÜ TV", "HALK TV", "TELE1", "CNN TÜRK", "24 TV", "TGRT HABER"
    ],
    "Türkiye - Belgesel": [
        "TRT BELGESEL", "HABERTURK BELGESEL", "TGRT BELGESEL", "AGRO TV"
    ],
    "Türkiye - Çocuk": [
        "TRT ÇOCUK", "MINIKA ÇOCUK", "MINIKA GO", "CARTOON NETWORK"
    ],
    "Türkiye - Müzik": [
        "POWER TV", "DREAM TURK", "KRAL POP", "NR1 TV", "NUMBER ONE TURK", "TRT MÜZİK"
    ],
    "Türkiye - +18": [
        # Kaynaklarda yetişkin kanalı varsa buraya ekleyebilirsiniz
    ],
    "Uluslararası - Genel": [
        "BBC", "CNN", "DW", "RTI", "TV5MONDE"
    ],
    "Uluslararası - Haber": [
        "BBC NEWS", "EURONEWS", "AL JAZEERA", "RUSSIA TODAY", "BLOOMBERG"
    ],
    "Uluslararası - Belgesel": [
        "CGTN DOCUMENTARY", "NASA TV"
    ],
    "Uluslararası - Çocuk": [
        "DISNEY CHANNEL", "NICKELODEON"
    ],
    "Uluslararası - Müzik": [
        "MTV", "CLUBBING TV"
    ]
}

my_playlist = "#EXTM3U\n"
added_urls = set()

for url in SOURCES:
    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()

        for i in range(len(lines)):
            if lines[i].startswith("#EXTINF"):
                channel_info = lines[i]
                stream_url = lines[i + 1] if i + 1 < len(lines) else ""

                if stream_url and stream_url not in added_urls:
                    # Tanımladığımız kategorilerde arama yapıyoruz
                    for group_name, keywords in CATEGORIES.items():
                        matched = False
                        for kw in keywords:
                            if kw.lower() in channel_info.lower():
                                # group-title parametresini ekleyerek M3U başlığını güncelliyoruz
                                updated_info = f'#EXTINF:-1 group-title="{group_name}",{channel_info.split(",")[-1]}'
                                my_playlist += f"{updated_info}\n{stream_url}\n"
                                added_urls.add(stream_url)
                                matched = True
                                break
                        if matched:
                            break
    except Exception as e:
        print(f"Hata ({url}): {e}")

with open("custom_list.m3u", "w", encoding="utf-8") as f:
    f.write(my_playlist)

print("M3U dosyası gruplandırılarak güncellendi.")
