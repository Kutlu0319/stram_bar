import requests
import re
import json
import base64

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Referer": "https://ppv.to"
}

def extract_from_base64(content):
    """Base64 içinde gömülü .m3u8 linklerini bulur."""
    matches = re.findall(r'([A-Za-z0-9+/=]{20,})', content)
    for m in matches:
        try:
            decoded = base64.b64decode(m).decode(errors="ignore")
            if ".m3u8" in decoded:
                return decoded
        except:
            pass
    return None


def extract_from_json(content):
    """JS/JSON objesi içinden .m3u8 bulur."""
    json_candidates = re.findall(r'\{.*?\}', content, re.DOTALL)
    for jc in json_candidates:
        try:
            data = json.loads(jc)
            text = json.dumps(data)
            m = re.search(r'https?://[^"\']+\.m3u8', text)
            if m:
                return m.group(0)
        except:
            continue
    return None


def extract_direct_regex(content):
    """Düz HTML veya JS içindeki .m3u8 linkini bulur."""
    m = re.search(r'https?://[^\s"\']+\.m3u8[^"\']*', content)
    if m:
        return m.group(0)
    return None


def extract_js_player_configs(content):
    """JS player config içinden .m3u8 adreslerini bulur (jwplayer, hls.js, clappr, videojs)."""

    patterns = [
        r'file["\']?\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)',          # jwplayer
        r'source["\']?\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)',        # clappr/videojs
        r'url["\']?\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)',           # hls.js config
        r'src["\']?\s*[:=]\s*["\'](https?://[^"\']+\.m3u8[^"\']*)',           # generic
    ]

    for p in patterns:
        m = re.search(p, content)
        if m:
            return m.group(1)
    return None


def extract_fetch_requests(content):
    """JS fetch veya xhr çağrılarını bulup içeriği çeker. İçinde m3u8 varsa döndürür."""
    urls = re.findall(r'fetch\(["\'](https?://[^"\']+)', content)
    urls += re.findall(r'XMLHttpRequest\(.+?["\'](https?://[^"\']+)', content)

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS)
            if r.status_code == 200 and ".m3u8" in r.text:
                m = re.search(r'https?://[^\s"\']+\.m3u8', r.text)
                if m:
                    return m.group(0)
        except:
            continue
    return None


def extract_m3u8_advanced(url):
    """Gelişmiş extractor – tüm kaynaklardan m3u8 arar."""
    try:
        html = requests.get(url, headers=HEADERS).text
    except:
        return None

    # 1) Direkt HTML’den alma
    m = extract_direct_regex(html)
    if m:
        return m

    # 2) JS player config’ten alma
    m = extract_js_player_configs(html)
    if m:
        return m

    # 3) Base64 çözme
    m = extract_from_base64(html)
    if m:
        return m

    # 4) JSON parse ederek alma
    m = extract_from_json(html)
    if m:
        return m

    # 5) fetch/xhr çağrılarından alma
    m = extract_fetch_requests(html)
    if m:
        return m

    # Son çare: embed iç iframe'leri tara
    iframes = re.findall(r'<iframe[^>]+src=["\']([^"\']+)', html)
    for iframe in iframes:
        if not iframe.startswith("http"):
            iframe = "https:" + iframe
        m = extract_m3u8_advanced(iframe)
        if m:
            return m

    return None
