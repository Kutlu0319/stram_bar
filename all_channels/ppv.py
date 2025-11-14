import json
import asyncio
from playwright.async_api import async_playwright

API_ENDPOINT = "https://ppv.to/api/streams"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Referer": "https://ppv.to"
}

async def fetch_streams_data():
    """API üzerinden kategori + kanal listesini alır."""
    import requests
    r = requests.get(API_ENDPOINT, headers=HEADERS)
    r.raise_for_status()
    return r.json()


async def get_m3u8_with_browser(url):
    """Gerçek tarayıcı açıp JS çalıştırarak m3u8 linkini network trafiğinden yakalar."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        m3u8_link = None

        def on_request(request):
            nonlocal m3u8_link
            if ".m3u8" in request.url:
                m3u8_link = request.url

        page.on("request", on_request)

        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
        except:
            pass

        await browser.close()
        return m3u8_link


async def extract_m3u8(uri_name):
    """ppv.to → embednow.top iki kaynaktan sırayla deneyerek m3u8 bulur."""
    urls = [
        f"https://ppv.to/live/{uri_name}",
        f"https://embednow.top/embed/{uri_name}"
    ]

    for u in urls:
        m3u8 = await get_m3u8_with_browser(u)
        if m3u8:
            return m3u8

    return None


async def generate_m3u_playlist():
    """Tüm kanalların m3u8 linklerini tarayıcıyla çözüp .m3u dosyası üretir."""
    data = await fetch_streams_data()

    m3u = "#EXTM3U\n"

    for category in data.get("streams", []):
        category_name = category.get("category", "Unknown")

        for stream in category.get("streams", []):
            name = stream.get("name")
            uri_name = stream.get("uri_name")
            poster = stream.get("poster")

            print(f"► Çözülüyor: {name} ({uri_name}) ...")

            m3u8 = await extract_m3u8(uri_name)

            if not m3u8:
                print(f"⚠ m3u8 bulunamadı → {name}")
                continue

            print(f"✔ m3u8 bulundu → {m3u8}")

            m3u += f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category_name.upper()}",{name}\n'
            m3u += '#EXTVLCOPT:http-origin=https://ppv.to\n'
            m3u += '#EXTVLCOPT:http-referrer=https://ppv.to/\n'
            m3u += '#EXTVLCOPT:http-user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36\n'
            m3u += f"{m3u8}\n"

    with open("ppv.m3u8", "w") as f:
        f.write(m3u)

    print("\n🎉 M3U listesi oluşturuldu: ppv.m3u8")


# Programı çalıştır
asyncio.run(generate_m3u_playlist())
