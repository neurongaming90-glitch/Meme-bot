"""
Meme Scraper — ALL SOURCES COMBINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PHOTO TEMPLATES:
  1. indianmemetemplates.com (PRIMARY - Indian memes)
  2. Imgflip API (popular meme templates)
  3. KnowYourMeme (meme info + images)
  4. 9gag search

TRENDING:
  1. indianmemetemplates.com/category/trending/
  2. 9gag hot feed

SOUNDS:
  1. Indian meme sounds (hardcoded - 25+ sounds)
  2. MyInstants search
  3. Freesound.org
  4. Zapsplat

VIDEO:
  1. indianmemetemplates.com video clips
  2. 9gag GIFs/videos
"""
import logging
import re
import requests
import random
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

BASE_IMT = "https://indianmemetemplates.com"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# ─────────────────────────────────────────
# INDIAN MEME SOUNDS — hardcoded 25+ sounds
# ─────────────────────────────────────────
INDIAN_SOUNDS = {
    "airhorn":       "https://www.myinstants.com/media/sounds/air-horn-club.mp3",
    "angels":        "https://www.myinstants.com/media/sounds/angels-singing.mp3",
    "bruh":          "https://www.myinstants.com/media/sounds/bruh.mp3",
    "ba dun tss":    "https://www.myinstants.com/media/sounds/ba-dum-tss.mp3",
    "boom":          "https://www.myinstants.com/media/sounds/vine-boom.mp3",
    "vine boom":     "https://www.myinstants.com/media/sounds/vine-boom.mp3",
    "explosion":     "https://www.myinstants.com/media/sounds/vine-boom.mp3",
    "boo":           "https://www.myinstants.com/media/sounds/crowd-booing.mp3",
    "fail":          "https://www.myinstants.com/media/sounds/sad-trombone.mp3",
    "sad":           "https://www.myinstants.com/media/sounds/sad-trombone.mp3",
    "fbi":           "https://www.myinstants.com/media/sounds/fbi-open-up.mp3",
    "laugh":         "https://www.myinstants.com/media/sounds/crowd-laughing.mp3",
    "cheer":         "https://www.myinstants.com/media/sounds/crowd-cheering.mp3",
    "wow":           "https://www.myinstants.com/media/sounds/wow.mp3",
    "drum roll":     "https://www.myinstants.com/media/sounds/drum-roll.mp3",
    "dun dun":       "https://www.myinstants.com/media/sounds/dun-dun-dun.mp3",
    "windows":       "https://www.myinstants.com/media/sounds/windows-xp-error.mp3",
    "error":         "https://www.myinstants.com/media/sounds/windows-xp-error.mp3",
    "mario":         "https://www.myinstants.com/media/sounds/super-mario-game-over.mp3",
    "game over":     "https://www.myinstants.com/media/sounds/super-mario-game-over.mp3",
    "suspense":      "https://www.myinstants.com/media/sounds/suspense.mp3",
    "record":        "https://www.myinstants.com/media/sounds/record-scratch.mp3",
    "wrong":         "https://www.myinstants.com/media/sounds/wrong-answer.mp3",
    "slap":          "https://www.myinstants.com/media/sounds/slap.mp3",
    "fart":          "https://www.myinstants.com/media/sounds/fart.mp3",
    "noice":         "https://www.myinstants.com/media/sounds/noice.mp3",
    "oh no":         "https://www.myinstants.com/media/sounds/oh-no.mp3",
    "sus":           "https://www.myinstants.com/media/sounds/amogus.mp3",
    "among us":      "https://www.myinstants.com/media/sounds/amogus.mp3",
    "rizz":          "https://www.myinstants.com/media/sounds/rizz.mp3",
}


# ══════════════════════════════════════════
# 1. INDIANMEMETEMPLATES.COM
# ══════════════════════════════════════════
def _imt_extract_images(html: str, count: int = 6) -> list:
    imgs = re.findall(
        r'<img[^>]+src="(https://(?:i\d\.wp\.com/)?indianmemetemplates\.com/wp-content/uploads/[^"?]+\.(?:webp|jpg|jpeg|png))[^"]*"',
        html
    )
    seen, clean = set(), []
    for img in imgs:
        base = img.split('?')[0]
        if any(x in img for x in ['resize=40', 'resize=50', 'cropped', 'logo', 'favicon', '150x']):
            continue
        if base not in seen:
            seen.add(base)
            clean.append(base)
    return clean[:count]

def _imt_extract_titles(html: str) -> list:
    t = re.findall(r'<h2[^>]*>\s*<a[^>]*>([^<]+)</a>\s*</h2>', html)
    t += re.findall(r'<h1[^>]*class="[^"]*entry-title[^"]*"[^>]*>([^<]+)</h1>', html)
    return [x.strip() for x in t]

def imt_search(query: str, count: int = 4) -> list:
    results = []
    try:
        resp = SESSION.get(f"{BASE_IMT}/?s={quote_plus(query)}", timeout=15)
        if resp.status_code == 200:
            imgs = _imt_extract_images(resp.text, count * 2)
            titles = _imt_extract_titles(resp.text)
            for i, img in enumerate(imgs[:count]):
                results.append({
                    'url': img, 'type': 'photo',
                    'source': '🇮🇳 IndianMemeTemplates',
                    'title': titles[i] if i < len(titles) else f"{query} template"
                })
        # Try direct slug
        if not results:
            slug = query.lower().strip().replace(' ', '-')
            r2 = SESSION.get(f"{BASE_IMT}/{slug}/", timeout=12)
            if r2.status_code == 200:
                for img in _imt_extract_images(r2.text, count):
                    results.append({'url': img, 'type': 'photo', 'source': '🇮🇳 IndianMemeTemplates', 'title': query.title()})
        logger.info(f"IMT search: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"IMT search: {e}")
    return results[:count]

def imt_trending(count: int = 6) -> list:
    results = []
    try:
        resp = SESSION.get(f"{BASE_IMT}/category/trending/", timeout=15)
        if resp.status_code == 200:
            imgs = _imt_extract_images(resp.text, count * 2)
            titles = _imt_extract_titles(resp.text)
            for i, img in enumerate(imgs[:count]):
                results.append({
                    'url': img, 'type': 'photo',
                    'source': '🔥 IMT Trending',
                    'title': titles[i] if i < len(titles) else "Trending Template"
                })
        logger.info(f"IMT trending: {len(results)}")
    except Exception as e:
        logger.error(f"IMT trending: {e}")
    return results[:count]

def imt_video_clips(count: int = 4) -> list:
    results = []
    try:
        resp = SESSION.get(f"{BASE_IMT}/meme-clips-for-youtube-video-editing/", timeout=15)
        if resp.status_code == 200:
            vids = re.findall(
                r'href="(https://indianmemetemplates\.com/wp-content/uploads/[^"]+\.(?:mp4|webm))"',
                resp.text
            )
            for i, v in enumerate(vids[:count]):
                results.append({'url': v, 'type': 'video', 'source': 'IMT Clips', 'title': f"Meme Clip {i+1}"})
            if not results:
                for img in _imt_extract_images(resp.text, count):
                    results.append({'url': img, 'type': 'photo', 'source': 'IMT Templates', 'title': 'Meme Template'})
        logger.info(f"IMT videos: {len(results)}")
    except Exception as e:
        logger.error(f"IMT videos: {e}")
    return results[:count]


# ══════════════════════════════════════════
# 2. IMGFLIP API
# ══════════════════════════════════════════
_imgflip_cache = []

def _load_imgflip():
    global _imgflip_cache
    if _imgflip_cache:
        return _imgflip_cache
    try:
        r = SESSION.get("https://api.imgflip.com/get_memes", timeout=15)
        if r.status_code == 200 and r.json().get('success'):
            _imgflip_cache = r.json()['data']['memes']
            logger.info(f"Imgflip loaded: {len(_imgflip_cache)} templates")
    except Exception as e:
        logger.error(f"Imgflip load: {e}")
    return _imgflip_cache

def imgflip_search(query: str, count: int = 4) -> list:
    memes = _load_imgflip()
    if not memes:
        return []
    q = query.lower()
    scored = []
    for m in memes:
        n = m.get('name', '').lower()
        s = 3 if q in n else sum(1 for w in q.split() if w in n)
        if s > 0:
            scored.append((s, m))
    scored.sort(key=lambda x: (x[0], x[1].get('captions', 0)), reverse=True)
    pool = [m for _, m in scored] if scored else memes
    results = []
    for m in pool[:count]:
        results.append({'url': m['url'], 'type': 'photo', 'source': 'Imgflip', 'title': m['name']})
    logger.info(f"Imgflip: {len(results)} for '{query}'")
    return results[:count]


# ══════════════════════════════════════════
# 3. KNOWYOURMEME
# ══════════════════════════════════════════
def kym_search(query: str, count: int = 4) -> list:
    results = []
    try:
        resp = SESSION.get(f"https://knowyourmeme.com/search?q={quote_plus(query)}", timeout=15)
        if resp.status_code == 200:
            imgs = re.findall(r'<img[^>]+src="(https://i\.kym-cdn\.com/[^"?]+\.(?:jpg|jpeg|png|gif))"', resp.text)
            imgs = [i for i in imgs if not any(x in i for x in ['thumb', '50x', 'avatar'])]
            names = re.findall(r'<a[^>]+href="/memes/([^"]+)"', resp.text)
            for i, img in enumerate(list(dict.fromkeys(imgs))[:count]):
                name = names[i].replace('-', ' ').title() if i < len(names) else query.title()
                results.append({'url': img, 'type': 'photo', 'source': 'KnowYourMeme', 'title': name})
        logger.info(f"KYM: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"KYM: {e}")
    return results[:count]


# ══════════════════════════════════════════
# 4. 9GAG
# ══════════════════════════════════════════
def gag_trending(count: int = 6) -> list:
    results = []
    try:
        url = "https://9gag.com/v1/feed-posts/type/hot?appId=a_dd8f2b7d304a10edaf6f29517ea0ca4d&itemCount=10&type=hot&c=10"
        resp = SESSION.get(url, headers={**HEADERS, 'x-pkg-name': 'com.ninegag.android.app'}, timeout=15)
        if resp.status_code == 200:
            for post in resp.json().get('data', {}).get('posts', []):
                imgs = post.get('images', {})
                for key in ['image700', 'image460', 'imageFbThumbnail']:
                    img = imgs.get(key, {})
                    if isinstance(img, dict) and img.get('url', '').startswith('http'):
                        results.append({
                            'url': img['url'], 'type': 'photo',
                            'source': '9GAG', 'title': post.get('title', 'Trending')[:80]
                        })
                        break
                if len(results) >= count:
                    break
        if not results:
            r2 = SESSION.get("https://9gag.com/trending", timeout=15)
            imgs = re.findall(r'"imageUrl":"(https://img-cdn\.9gag\.com/[^"]+)"', r2.text)
            for img in list(dict.fromkeys(imgs))[:count]:
                results.append({'url': img, 'type': 'photo', 'source': '9GAG', 'title': 'Trending Meme'})
        logger.info(f"9gag trending: {len(results)}")
    except Exception as e:
        logger.error(f"9gag trending: {e}")
    return results[:count]

def gag_search(query: str, count: int = 4) -> list:
    results = []
    try:
        resp = SESSION.get(f"https://9gag.com/search?query={quote_plus(query)}", timeout=15)
        if resp.status_code == 200:
            imgs = re.findall(r'"imageUrl":"(https://img-cdn\.9gag\.com/[^"]+)"', resp.text)
            imgs += re.findall(r'data-image="(https://img-cdn\.9gag\.com/[^"]+)"', resp.text)
            for img in list(dict.fromkeys(imgs))[:count]:
                results.append({'url': img, 'type': 'photo', 'source': '9GAG', 'title': f"{query} meme"})
        logger.info(f"9gag search: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"9gag search: {e}")
    return results[:count]


# ══════════════════════════════════════════
# 5. SOUNDS — MyInstants + Freesound + Zapsplat
# ══════════════════════════════════════════
def myinstants_search(query: str, count: int = 4) -> list:
    results = []
    try:
        resp = SESSION.get(f"https://www.myinstants.com/search/?name={quote_plus(query)}", timeout=12)
        if resp.status_code == 200:
            mp3s = list(dict.fromkeys(re.findall(r"/media/sounds/([^\"']+\.mp3)", resp.text)))
            names = re.findall(r'class="instant-name"[^>]*>\s*([^<]+)', resp.text)
            for i, mp3 in enumerate(mp3s[:count]):
                name = names[i].strip() if i < len(names) else mp3.replace('-',' ').replace('.mp3','').title()
                results.append({'url': f"https://www.myinstants.com/media/sounds/{mp3}", 'type': 'audio', 'source': 'MyInstants', 'title': name[:60]})
        logger.info(f"MyInstants: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"MyInstants: {e}")
    return results[:count]

def freesound_search(query: str, count: int = 4) -> list:
    results = []
    try:
        resp = SESSION.get(f"https://freesound.org/search/?q={quote_plus(query+' meme')}&f=duration:[0+TO+10]", timeout=12)
        if resp.status_code == 200:
            previews = re.findall(r'"preview-hq-mp3":"(https://[^"]+\.mp3)"', resp.text)
            names = re.findall(r'class="[^"]*sound_filename[^"]*"[^>]*>([^<]+)', resp.text)
            for i, p in enumerate(previews[:count]):
                name = names[i].strip() if i < len(names) else f"{query} sound"
                results.append({'url': p, 'type': 'audio', 'source': 'Freesound', 'title': name[:60]})
        logger.info(f"Freesound: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"Freesound: {e}")
    return results[:count]

def zapsplat_search(query: str, count: int = 4) -> list:
    results = []
    try:
        resp = SESSION.get(f"https://www.zapsplat.com/sound-effect-search/?s={quote_plus(query)}", timeout=12)
        if resp.status_code == 200:
            mp3s = re.findall(r'<source[^>]+src="(https://[^"]+\.mp3)"', resp.text)
            mp3s += re.findall(r'data-src="(https://www\.zapsplat\.com/[^"]+\.mp3)"', resp.text)
            titles = re.findall(r'<h2[^>]+class="[^"]*title[^"]*"[^>]*>\s*<a[^>]*>([^<]+)</a>', resp.text)
            for i, mp3 in enumerate(mp3s[:count]):
                name = titles[i].strip() if i < len(titles) else f"{query} effect"
                results.append({'url': mp3, 'type': 'audio', 'source': 'Zapsplat', 'title': name[:60]})
        logger.info(f"Zapsplat: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"Zapsplat: {e}")
    return results[:count]

def get_sounds(query: str, count: int = 4) -> list:
    results = []
    q = query.lower()

    # 1. Keyword match from Indian sounds
    for kw, url in INDIAN_SOUNDS.items():
        if kw in q:
            results.append({'url': url, 'type': 'audio', 'source': '🇮🇳 Indian Meme Sounds', 'title': kw.title() + ' Sound'})
            if len(results) >= count:
                break

    # 2. MyInstants
    if len(results) < count:
        results.extend(myinstants_search(q, count - len(results)))

    # 3. Freesound
    if len(results) < count:
        results.extend(freesound_search(q, count - len(results)))

    # 4. Zapsplat
    if len(results) < count:
        results.extend(zapsplat_search(q, count - len(results)))

    # 5. Random Indian sounds fallback
    if not results:
        items = list(INDIAN_SOUNDS.items())
        random.shuffle(items)
        for name, url in items[:count]:
            results.append({'url': url, 'type': 'audio', 'source': '🇮🇳 Indian Meme Sounds', 'title': name.title() + ' Effect'})

    logger.info(f"Total sounds: {len(results)} for '{query}'")
    return results[:count]


# ══════════════════════════════════════════
# MAIN FETCH — All sources combined
# ══════════════════════════════════════════
def fetch_memes(query: str, media_type: str = 'photo', count: int = 4) -> dict:
    q = query.strip()
    results = []
    source = 'Unknown'

    # ── SOUND ──
    if media_type == 'sound':
        results = get_sounds(q, count)
        source = 'Multi-Source Sounds'

    # ── TRENDING ──
    elif media_type == 'trending':
        # IMT trending + 9gag trending combined
        imt = imt_trending(count)
        gag = gag_trending(count)
        # Interleave both sources
        combined = []
        for i in range(max(len(imt), len(gag))):
            if i < len(imt):
                combined.append(imt[i])
            if i < len(gag):
                combined.append(gag[i])
        results = combined[:count]
        source = '🔥 IMT + 9GAG Trending'

    # ── VIDEO ──
    elif media_type == 'video':
        results = imt_video_clips(count)
        source = 'IMT Video Clips'
        if len(results) < count:
            results.extend(gag_search(q, count - len(results)))
            source = 'IMT + 9GAG'

    # ── PHOTO TEMPLATE ──
    else:
        # All sources combined — best results from each
        imt = imt_search(q, 2)          # 2 from IMT (Indian focus)
        flip = imgflip_search(q, 1)      # 1 from Imgflip
        kym = kym_search(q, 1)           # 1 from KnowYourMeme

        results = imt + flip + kym

        # If still not enough, fill from 9gag
        if len(results) < count:
            results.extend(gag_search(q, count - len(results)))

        # Last resort: IMT homepage latest
        if not results:
            results = imt_trending(count)

        source = 'IMT + Imgflip + KYM + 9GAG'

    results = [r for r in results if r.get('url', '').startswith('http')]
    logger.info(f"✅ {len(results)} [{source}] for '{q}'")
    return {'results': results[:count], 'source': source}
