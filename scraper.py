"""
Meme Scraper — Fixed for Railway
Photos: Reddit API + Imgur fallback
Videos: YouTube via yt-dlp
Sound: YouTube audio via yt-dlp
GIF fallback: Giphy
"""
import logging
import re
import requests
import random
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'MemeBot/2.0 (by /u/memebot)',
    'Accept': 'application/json',
}

MEME_SUBREDDITS = ['memes', 'dankmemes', 'funny', 'me_irl', 'IndianMemes', 'dankinindia']


# ─────────────────────────────────────────
# REDDIT PHOTOS
# ─────────────────────────────────────────
def scrape_reddit_photos(query: str, count: int = 4) -> list:
    results = []
    try:
        search_url = f"https://www.reddit.com/search.json?q={quote_plus(query + ' meme')}&type=link&sort=relevance&limit=50&t=month"
        resp = requests.get(search_url, headers=HEADERS, timeout=15)

        if resp.status_code == 200:
            posts = resp.json().get('data', {}).get('children', [])
            for post in posts:
                p = post.get('data', {})
                url = p.get('url', '')
                if url and any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    results.append({
                        'url': url,
                        'type': 'photo',
                        'source': 'Reddit',
                        'title': p.get('title', query)[:80]
                    })
                elif p.get('preview'):
                    images = p.get('preview', {}).get('images', [])
                    if images:
                        img_url = images[0].get('source', {}).get('url', '').replace('&amp;', '&')
                        if img_url and img_url.startswith('http'):
                            results.append({
                                'url': img_url,
                                'type': 'photo',
                                'source': 'Reddit',
                                'title': p.get('title', query)[:80]
                            })
                if len(results) >= count:
                    break

        # Try subreddits if not enough
        if len(results) < count:
            for sub in random.sample(MEME_SUBREDDITS, min(3, len(MEME_SUBREDDITS))):
                if len(results) >= count:
                    break
                try:
                    sub_url = f"https://www.reddit.com/r/{sub}/search.json?q={quote_plus(query)}&restrict_sr=1&sort=relevance&limit=20"
                    r2 = requests.get(sub_url, headers=HEADERS, timeout=10)
                    if r2.status_code == 200:
                        for post in r2.json().get('data', {}).get('children', []):
                            p = post.get('data', {})
                            url = p.get('url', '')
                            img_url = ''
                            if url and any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                                img_url = url
                            elif p.get('preview'):
                                imgs = p.get('preview', {}).get('images', [])
                                if imgs:
                                    img_url = imgs[0].get('source', {}).get('url', '').replace('&amp;', '&')
                            if img_url and img_url.startswith('http'):
                                results.append({
                                    'url': img_url,
                                    'type': 'photo',
                                    'source': f'Reddit',
                                    'title': p.get('title', query)[:80]
                                })
                            if len(results) >= count:
                                break
                except Exception:
                    continue

        logger.info(f"Reddit photos: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"Reddit error: {e}")
    return results[:count]


# ─────────────────────────────────────────
# IMGUR
# ─────────────────────────────────────────
def scrape_imgur(query: str, count: int = 4) -> list:
    results = []
    try:
        url = f"https://api.imgur.com/3/gallery/search/relevance/all/1?q={quote_plus(query + ' meme')}"
        headers = {**HEADERS, 'Authorization': 'Client-ID 546c25a59c58ad7'}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            for item in resp.json().get('data', []):
                img_url = ''
                if item.get('type', '').startswith('image/'):
                    img_url = item.get('link', '')
                elif item.get('images'):
                    first = item['images'][0]
                    if first.get('type', '').startswith('image/'):
                        img_url = first.get('link', '')
                if img_url:
                    results.append({
                        'url': img_url,
                        'type': 'photo',
                        'source': 'Imgur',
                        'title': item.get('title', query)[:80]
                    })
                if len(results) >= count:
                    break
        logger.info(f"Imgur: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"Imgur error: {e}")
    return results[:count]


# ─────────────────────────────────────────
# GIPHY — GIF fallback
# ─────────────────────────────────────────
def scrape_giphy(query: str, count: int = 4) -> list:
    results = []
    try:
        api_key = "dc6zaTOxFJmzC"
        url = f"https://api.giphy.com/v1/gifs/search?api_key={api_key}&q={quote_plus(query + ' meme')}&limit={count * 2}&rating=pg-13"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            for gif in resp.json().get('data', [])[:count]:
                gif_url = gif.get('images', {}).get('original', {}).get('url', '')
                if gif_url:
                    results.append({
                        'url': gif_url,
                        'type': 'gif',
                        'source': 'Giphy',
                        'title': gif.get('title', query)[:80]
                    })
        logger.info(f"Giphy: {len(results)} for '{query}'")
    except Exception as e:
        logger.error(f"Giphy error: {e}")
    return results[:count]


# ─────────────────────────────────────────
# YOUTUBE — Video & Sound
# ─────────────────────────────────────────
def scrape_youtube(query: str, count: int = 4, audio_only: bool = False) -> list:
    results = []
    try:
        import yt_dlp

        search_q = f"{query} meme" if 'meme' not in query.lower() else query

        # Search
        search_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            search_info = ydl.extract_info(f"ytsearch{count * 3}:{search_q}", download=False)

        if not search_info or 'entries' not in search_info:
            return results

        fmt = 'bestaudio[ext=m4a]/bestaudio/best' if audio_only else 'best[height<=720][ext=mp4]/best[height<=720]/best'
        stream_opts = {'quiet': True, 'no_warnings': True, 'format': fmt}

        for entry in search_info['entries']:
            if len(results) >= count:
                break
            if not entry:
                continue
            try:
                duration = entry.get('duration') or 0
                if duration > 180:
                    continue
                vid_url = f"https://www.youtube.com/watch?v={entry['id']}"
                with yt_dlp.YoutubeDL(stream_opts) as ydl2:
                    info = ydl2.extract_info(vid_url, download=False)
                stream_url = info.get('url', '')
                if not stream_url:
                    continue
                results.append({
                    'url': stream_url,
                    'thumbnail': info.get('thumbnail', ''),
                    'type': 'audio' if audio_only else 'video',
                    'source': 'YouTube',
                    'title': info.get('title', search_q)[:80],
                    'video_url': vid_url,
                    'duration': duration,
                    'ext': info.get('ext', 'mp4')
                })
            except Exception as e:
                logger.debug(f"YT entry skip: {e}")
                continue

        logger.info(f"YouTube {'audio' if audio_only else 'video'}: {len(results)} for '{query}'")
    except ImportError:
        logger.error("yt-dlp not installed!")
    except Exception as e:
        logger.error(f"YouTube error: {e}")
    return results[:count]


# ─────────────────────────────────────────
# MAIN FETCH
# ─────────────────────────────────────────
def fetch_memes(query: str, media_type: str = 'photo', count: int = 4) -> dict:
    results = []
    source = 'Unknown'
    clean_query = re.sub(r'\b(funny|dank|meme|memes)\b', '', query, flags=re.IGNORECASE).strip()
    if not clean_query:
        clean_query = query

    if media_type == 'sound':
        logger.info(f"🔊 SOUND: {clean_query}")
        results = scrape_youtube(clean_query, count, audio_only=True)
        source = 'YouTube'

    elif media_type == 'video':
        logger.info(f"🎬 VIDEO: {clean_query}")
        results = scrape_youtube(clean_query, count, audio_only=False)
        source = 'YouTube'
        if not results:
            logger.info("YT video failed → Giphy GIF")
            results = scrape_giphy(clean_query, count)
            source = 'Giphy'

    else:  # photo
        logger.info(f"📷 PHOTO: {clean_query}")
        results = scrape_reddit_photos(clean_query, count)
        source = 'Reddit'

        if len(results) < count:
            extra = scrape_imgur(clean_query, count - len(results))
            results.extend(extra)
            source = 'Reddit+Imgur' if results else 'Imgur'

        if not results:
            results = scrape_giphy(clean_query, count)
            source = 'Giphy'

    results = [r for r in results if r.get('url')]
    logger.info(f"✅ {len(results)} results from {source}")
    return {'results': results[:count], 'source': source}
