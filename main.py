import requests

SOURCES = [
    "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/tr.m3u",
    "https://iptv-org.github.io/iptv/index.category.m3u",
]

# Listede olmasını istediğiniz kanal adları (Küçük/büyük harf duyarsızdır)
TARGET_CHANNELS = ["TRT 1", "ATV", "KANAL D", "SHOW TV", "BBC NEWS", "EURONEWS"]

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
                    for target in TARGET_CHANNELS:
                        if target.lower() in channel_info.lower():
                            my_playlist += f"{channel_info}\n{stream_url}\n"
                            added_urls.add(stream_url)
                            break
    except Exception as e:
        print(f"Hata ({url}): {e}")

with open("custom_list.m3u", "w", encoding="utf-8") as f:
    f.write(my_playlist)

print("M3U dosyası güncellendi.")
