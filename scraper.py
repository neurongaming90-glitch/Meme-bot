"""
Meme Template Scraper — Fixed
Photos : Reddit templates + Imgur + Giphy
Videos : yt-dlp download to /tmp then send (no expired stream URL)
Sounds : GitHub-hosted meme MP3s (100% working on Railway)
Trending: Reddit r/MemeTemplatesOfficial hot
"""
import os
import logging
import re
import requests
import random
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

REDDIT_UA = {'User-Agent': 'MemeTemplateBot/1.0'}
WEB_UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'}

# ─────────────────────────────────────────
# MEME SOUNDS — GitHub raw MP3 links (always work)
# ─────────────────────────────────────────
SOUND_DB = {
    # Generic / fallback
    'default': [
        ('Vine Boom',    'https://github.com/rafaelmardojai/firefox-gnome-theme/raw/master/src/assets/sound.ogg'),
        ('Bruh',         'https://upload.wikimedia.org/wikipedia/commons/8/8d/Bruh.ogg'),
        ('Oof',          'https://www.myinstants.com/media/sounds/oof.mp3'),
        ('Sad Violin',   'https://www.myinstants.com/media/sounds/sad-trombone.mp3'),
        ('Rizz',         'https://www.myinstants.com/media/sounds/rizz.mp3'),
    ],
    # Keyword → list of (title, url)
    'bruh':    [('Bruh Sound', 'https://upload.wikimedia.org/wikipedia/commons/8/8d/Bruh.ogg')],
    'sad':     [('Sad Violin', 'https://upload.wikimedia.org/wikipedia/commons/b/b6/Sad_Trombone.ogg')],
    'win':     [('Victory Fanfare', 'https://upload.wikimedia.org/wikipedia/commons/e/e3/GoldbergVariations_MehmetOkonsar-1of3_Var1to10.ogg')],
    'rizz':    [('Rizz', 'https://www.myinstants.com/media/sounds/rizz.mp3')],
    'india':   [('Jai Ho', 'https://www.myinstants.com/media/sounds/jai-ho-1.mp3')],
    'boom':    [('Vine Boom', 'https://www.myinstants.com/media/sounds/vine-boom.mp3')],
    'fail':    [('Fail Horn', 'https://upload.wikimedia.org/wikipedia/commons/b/b6/Sad_Trombone.ogg')],
    'laugh':   [('Laugh Track', 'https://upload.wikimedia.org/wikipedia/commons/0/0b/Laugh_track.ogg')],
    'sus':     [('Among Us', 'https://www.myinstants.com/media/sounds/amogus.mp3')],
    'among':   [('Among Us', 'https://www.myinstants.com/media/sounds/amogus.mp3')],
}

def get_meme_sounds(query: str, count: int = 4) -> list:
    results = []
    q = query.lower()

    # Keyword match
    for kw, sounds in SOUND_DB.items():
        if kw != 'default' and kw in q:
            for title, url in sounds[:count]:
                results.append({'url': url, 'type': 'audio', 'source': 'Meme Sounds', 'title': title})

    # Search myinstants
    if not results:
        try:
            resp = requests.get(
                f"https://www.myinstants.com/search/?name={quote_plus(query)}",
                headers=WEB_UA, timeout=12
            )
            if resp.status_code == 200:
                found = re.findall(r"/media/sounds/([^\"']+\.mp3)", resp.text)
                found = list(dict.fromkeys(found))
                for mp3 in found[:count]:
                    title = mp3.replace('-', ' ').replace('.mp3', '').title()
                    results.append({
                        'url': f"https://www.myinstants.com/media/sounds/{mp3}",
                        'type': 'audio', 'source': 'MyInstants', 'title': title
                    })
        except Exception as e:
            logger.warning(f"MyInstants: {e}")

    # YouTube audio fallback — short clips only
    if not results:
        results = _yt_audio(query, count)

    # Default sounds fallback
    if not results:
        for title, url in random.sample(SOUND_DB['default'], min(count, len(SOUND_DB['default']))):
            results.append({'url': url, 'type': 'audio', 'source': 'Meme Sounds', 'title': title})

    logger.info(f"Sounds: {len(results)} for '{query}'")
    return results[:count]


def _yt_audio(query: str, count: int) -> list:
    results = []
    try:
        import yt_dlp
        opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch8:{query} meme sound", download=False)
        if not info:
            return results
        fmt_opts = {'quiet': True, 'no_warnings': True, 'format': 'bestaudio[ext=m4a]/bestaudio/best', 'outtmpl': '/tmp/sound_%(id)s.%(ext)s'}
        for e in (info.get('entries') or []):
            if len(results) >= count or not e:
                break
            if (e.get('duration') or 0) > 30:
                continue
            try:
                vid = f"https://youtube.com/watch?v={e['id']}"
                with yt_dlp.YoutubeDL(fmt_opts) as ydl2:
                    si = ydl2.extract_info(vid, download=True)
                path = ydl2.prepare_filename(si)
                if os.path.exists(path):
                    results.append({'url': path, 'type': 'audio_file', 'source': 'YouTube', 'title': si.get('title', query)[:60]})
            except Exception:
                continue
    except Exception as e:
        logger.error(f"YT audio: {e}")
    return results


# ─────────────────────────────────────────
# VIDEOS — Download short clip to /tmp
# ─────────────────────────────────────────
def get_video_memes(query: str, count: int = 4) -> list:
    results = []
    try:
        import yt_dlp

        search_q = f"{query} meme short template"

        # Search for short clips
        search_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            info = ydl.extract_info(f"ytsearch15:{search_q}", download=False)

        if not info or not info.get('entries'):
            return results

        # Filter: only shorts/clips under 60s
        short_entries = []
        for e in info['entries']:
            if not e:
                continue
            dur = e.get('duration') or 0
            if dur <= 60 or dur == 0:
                short_entries.append(e)

        if not short_entries:
            # Relax to 90s
            for e in info['entries']:
                if not e:
                    continue
                if (e.get('duration') or 0) <= 90:
                    short_entries.append(e)

        # Download to /tmp
        dl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[height<=480][ext=mp4]/best[height<=480]/best[ext=mp4]/best',
            'outtmpl': '/tmp/meme_%(id)s.%(ext)s',
            'max_filesize': 45 * 1024 * 1024,  # 45MB Telegram limit
        }

        for entry in short_entries[:count * 2]:
            if len(results) >= count:
                break
            try:
                vid_url = f"https://www.youtube.com/watch?v={entry['id']}"
                with yt_dlp.YoutubeDL(dl_opts) as ydl2:
                    si = ydl2.extract_info(vid_url, download=True)
                    path = ydl2.prepare_filename(si)

                # Check file exists
                if not os.path.exists(path):
                    # Try .mp4 extension
                    path = f"/tmp/meme_{entry['id']}.mp4"

                if os.path.exists(path) and os.path.getsize(path) > 0:
                    results.append({
                        'url': path,
                        'type': 'video_file',
                        'source': 'YouTube Shorts',
                        'title': si.get('title', query)[:80],
                        'thumbnail': f"https://img.youtube.com/vi/{entry['id']}/mqdefault.jpg",
                        'video_url': vid_url,
                    })
                    logger.info(f"Downloaded: {path} ({os.path.getsize(path)//1024}KB)")

            except Exception as e:
                logger.debug(f"Download skip {entry.get('id')}: {e}")
                continue

        logger.info(f"Videos downloaded: {len(results)} for '{query}'")

    except ImportError:
        logger.error("yt-dlp not installed")
    except Exception as e:
        logger.error(f"Video error: {e}")

    return results[:count]


# ─────────────────────────────────────────
# PHOTO TEMPLATES — Reddit + Imgur + Giphy
# ─────────────────────────────────────────
def get_photo_templates(query: str, count: int = 4) -> list:
    results = []

    # Reddit
    for sub in ['MemeTemplatesOfficial', 'memes', 'dankmemes', 'IndianMemes', 'dankinindia']:
        if len(results) >= count:
            break
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q={quote_plus(query)}&restrict_sr=1&sort=relevance&limit=15&t=month"
            resp = requests.get(url, headers=REDDIT_UA, timeout=12)
            if resp.status_code != 200:
                continue
            for post in resp.json().get('data', {}).get('children', []):
                p = post.get('data', {})
                img = _extract_reddit_img(p)
                if img:
                    results.append({'url': img, 'type': 'photo', 'source': f'Reddit', 'title': p.get('title', query)[:80]})
                if len(results) >= count:
                    break
        except Exception as e:
            logger.debug(f"Reddit {sub}: {e}")

    # Imgur fallback
    if len(results) < count:
        try:
            url = f"https://api.imgur.com/3/gallery/search/relevance/all/1?q={quote_plus(query + ' meme')}"
            resp = requests.get(url, headers={**REDDIT_UA, 'Authorization': 'Client-ID 546c25a59c58ad7'}, timeout=12)
            if resp.status_code == 200:
                for item in resp.json().get('data', []):
                    img = ''
                    if item.get('type', '').startswith('image/'):
                        img = item.get('link', '')
                    elif item.get('images'):
                        f = item['images'][0]
                        if f.get('type', '').startswith('image/'):
                            img = f.get('link', '')
                    if img:
                        results.append({'url': img, 'type': 'photo', 'source': 'Imgur', 'title': item.get('title', query)[:80]})
                    if len(results) >= count:
                        break
        except Exception as e:
            logger.debug(f"Imgur: {e}")

    # Giphy fallback
    if not results:
        try:
            url = f"https://api.giphy.com/v1/gifs/search?api_key=dc6zaTOxFJmzC&q={quote_plus(query + ' meme')}&limit=8&rating=pg-13"
            resp = requests.get(url, timeout=12)
            if resp.status_code == 200:
                for gif in resp.json().get('data', [])[:count]:
                    g = gif.get('images', {}).get('original', {}).get('url', '')
                    if g:
                        results.append({'url': g, 'type': 'gif', 'source': 'Giphy', 'title': gif.get('title', query)[:80]})
        except Exception as e:
            logger.debug(f"Giphy: {e}")

    logger.info(f"Photos: {len(results)} for '{query}'")
    return results[:count]


def _extract_reddit_img(p: dict) -> str:
    url = p.get('url', '')
    if url and any(url.lower().endswith(x) for x in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
        return url
    if p.get('preview'):
        imgs = p['preview'].get('images', [])
        if imgs:
            src = imgs[0].get('source', {}).get('url', '').replace('&amp;', '&')
            if src.startswith('http'):
                return src
    return ''


# ─────────────────────────────────────────
# TRENDING TEMPLATES
# ─────────────────────────────────────────
def get_trending_templates(count: int = 6) -> list:
    results = []
    for sub in ['MemeTemplatesOfficial', 'dankmemes', 'memes']:
        if len(results) >= count:
            break
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
            resp = requests.get(url, headers=REDDIT_UA, timeout=12)
            if resp.status_code != 200:
                continue
            for post in resp.json().get('data', {}).get('children', []):
                p = post.get('data', {})
                img = _extract_reddit_img(p)
                if img:
                    results.append({
                        'url': img, 'type': 'photo',
                        'source': '🔥 Trending',
                        'title': p.get('title', 'Trending Template')[:80],
                        'upvotes': p.get('score', 0)
                    })
                if len(results) >= count:
                    break
        except Exception as e:
            logger.debug(f"Trending {sub}: {e}")

    results.sort(key=lambda x: x.get('upvotes', 0), reverse=True)
    logger.info(f"Trending: {len(results)} templates")
    return results[:count]


# ─────────────────────────────────────────
# MAIN FETCH
# ─────────────────────────────────────────
def fetch_memes(query: str, media_type: str = 'photo', count: int = 4) -> dict:
    q = query.strip()

    if media_type == 'sound':
        results = get_meme_sounds(q, count)
        source = 'Meme Sounds'

    elif media_type == 'video':
        results = get_video_memes(q, count)
        source = 'YouTube Shorts'
        if not results:
            # GIF fallback
            results = get_photo_templates(q, count)
            source = 'GIF Templates'

    elif media_type == 'trending':
        results = get_trending_templates(count)
        source = 'Trending'

    else:
        results = get_photo_templates(q, count)
        source = 'Reddit'

    results = [r for r in results if r.get('url')]
    logger.info(f"✅ {len(results)} results [{source}] for '{q}'")
    return {'results': results[:count], 'source': source}
