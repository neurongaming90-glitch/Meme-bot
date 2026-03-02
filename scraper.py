"""
Meme Scraper — Pinterest → YouTube → Instagram fallback chain
"""
import logging
import re
import requests
import random
import time
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

HEADERS_LIST = [
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    },
    {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-GB,en;q=0.5',
    },
    {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
        'Accept': '*/*',
    }
]


def get_headers():
    return random.choice(HEADERS_LIST)


# ─────────────────────────────────────────
# PINTEREST SCRAPER
# ─────────────────────────────────────────
def scrape_pinterest(query: str, count: int = 4) -> list:
    """Scrape Pinterest for meme images."""
    results = []
    try:
        search_url = f"https://www.pinterest.com/search/pins/?q={quote_plus(query + ' meme')}"

        session = requests.Session()
        session.headers.update(get_headers())

        # Pinterest API endpoint
        api_url = f"https://www.pinterest.com/resource/BaseSearchResource/get/?source_url=/search/pins/?q={quote_plus(query)}&data=%7B%22options%22%3A%7B%22query%22%3A%22{quote_plus(query + ' meme')}%22%2C%22scope%22%3A%22pins%22%2C%22page_size%22%3A25%7D%7D"

        resp = session.get(api_url, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            pins = data.get('resource_response', {}).get('data', {}).get('results', [])

            for pin in pins[:count * 2]:
                try:
                    images = pin.get('images', {})
                    # Try different image sizes
                    for size in ['orig', '736x', '474x']:
                        img = images.get(size, {})
                        url = img.get('url', '')
                        if url and url.startswith('http'):
                            results.append({
                                'url': url,
                                'type': 'photo',
                                'source': 'Pinterest',
                                'title': pin.get('title', '') or pin.get('description', '')[:50]
                            })
                            break
                    if len(results) >= count:
                        break
                except Exception:
                    continue

        # Fallback: scrape HTML
        if not results:
            resp2 = session.get(search_url, timeout=15)
            if resp2.status_code == 200:
                urls = re.findall(r'https://i\.pinimg\.com/[^"\']+\.(?:jpg|jpeg|png|gif)', resp2.text)
                urls = list(dict.fromkeys(urls))  # deduplicate
                for url in urls[:count]:
                    results.append({
                        'url': url,
                        'type': 'photo',
                        'source': 'Pinterest',
                        'title': query
                    })

        logger.info(f"Pinterest: {len(results)} results for '{query}'")

    except Exception as e:
        logger.warning(f"Pinterest failed: {e}")

    return results[:count]


# ─────────────────────────────────────────
# YOUTUBE SCRAPER (yt-dlp)
# ─────────────────────────────────────────
def scrape_youtube(query: str, count: int = 4, audio_only: bool = False) -> list:
    """Search YouTube and get video/audio URLs using yt-dlp."""
    results = []
    try:
        import yt_dlp

        search_query = f"{query} meme" if 'meme' not in query.lower() else query

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'default_search': f'ytsearch{count * 2}',
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{count * 2}:{search_query}", download=False)

        if not info or 'entries' not in info:
            return results

        for entry in info['entries'][:count * 2]:
            if not entry:
                continue
            try:
                video_id = entry.get('id', '')
                title = entry.get('title', query)
                duration = entry.get('duration', 0) or 0

                # Skip very long videos
                if duration > 300:
                    continue

                video_url = f"https://www.youtube.com/watch?v={video_id}"

                # Get direct stream URL
                stream_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'bestaudio/best' if audio_only else 'best[height<=720]/best',
                }

                with yt_dlp.YoutubeDL(stream_opts) as ydl2:
                    stream_info = ydl2.extract_info(video_url, download=False)

                stream_url = stream_info.get('url', '')
                thumbnail = stream_info.get('thumbnail', '')

                if stream_url:
                    results.append({
                        'url': stream_url,
                        'thumbnail': thumbnail,
                        'type': 'audio' if audio_only else 'video',
                        'source': 'YouTube',
                        'title': title,
                        'video_url': video_url,
                        'duration': duration
                    })

                if len(results) >= count:
                    break

            except Exception as e:
                logger.debug(f"YT entry error: {e}")
                continue

        logger.info(f"YouTube: {len(results)} results for '{query}'")

    except ImportError:
        logger.error("yt-dlp not installed!")
    except Exception as e:
        logger.warning(f"YouTube failed: {e}")

    return results[:count]


# ─────────────────────────────────────────
# INSTAGRAM SCRAPER
# ─────────────────────────────────────────
def scrape_instagram(query: str, count: int = 4) -> list:
    """Scrape Instagram for meme content."""
    results = []
    try:
        # Use Instagram's web API
        tag = query.lower().replace(' ', '').replace('meme', '') + 'meme'
        url = f"https://www.instagram.com/explore/tags/{quote_plus(tag)}/?__a=1&__d=dis"

        resp = requests.get(url, headers=get_headers(), timeout=15)

        if resp.status_code == 200:
            try:
                data = resp.json()
                edges = data.get('graphql', {}).get('hashtag', {}).get('edge_hashtag_to_media', {}).get('edges', [])

                for edge in edges[:count * 2]:
                    node = edge.get('node', {})
                    img_url = node.get('display_url', '')
                    if img_url:
                        results.append({
                            'url': img_url,
                            'type': 'photo',
                            'source': 'Instagram',
                            'title': node.get('edge_media_to_caption', {}).get('edges', [{}])[0].get('node', {}).get('text', query)[:50]
                        })
                    if len(results) >= count:
                        break
            except Exception:
                pass

        logger.info(f"Instagram: {len(results)} results for '{query}'")

    except Exception as e:
        logger.warning(f"Instagram failed: {e}")

    return results[:count]


# ─────────────────────────────────────────
# REDDIT SCRAPER (bonus fallback)
# ─────────────────────────────────────────
def scrape_reddit(query: str, count: int = 4) -> list:
    """Scrape Reddit meme subreddits."""
    results = []
    try:
        subreddits = ['memes', 'dankmemes', 'funny', 'AdviceAnimals']
        search_url = f"https://www.reddit.com/search.json?q={quote_plus(query + ' meme')}&type=link&sort=relevance&limit=25"

        headers = get_headers()
        headers['User-Agent'] = 'MemeBot/1.0'

        resp = requests.get(search_url, headers=headers, timeout=15)

        if resp.status_code == 200:
            data = resp.json()
            posts = data.get('data', {}).get('children', [])

            for post in posts:
                p = post.get('data', {})
                url = p.get('url', '')
                # Only image posts
                if url and any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    results.append({
                        'url': url,
                        'type': 'photo',
                        'source': 'Reddit',
                        'title': p.get('title', query)[:60]
                    })
                if len(results) >= count:
                    break

        logger.info(f"Reddit: {len(results)} results for '{query}'")

    except Exception as e:
        logger.warning(f"Reddit failed: {e}")

    return results[:count]


# ─────────────────────────────────────────
# MAIN FETCH FUNCTION — Fallback Chain
# ─────────────────────────────────────────
def fetch_memes(query: str, media_type: str = 'photo', count: int = 4) -> dict:
    """
    Main fetch with fallback chain.
    media_type: 'photo', 'video', 'sound'
    Returns: {'results': [...], 'source': 'Pinterest/YouTube/etc'}
    """
    results = []
    source = 'Unknown'

    if media_type == 'sound':
        # Sound: YouTube audio only
        logger.info(f"Fetching SOUND: {query}")
        results = scrape_youtube(query, count, audio_only=True)
        source = 'YouTube'

    elif media_type == 'video':
        # Video: YouTube first
        logger.info(f"Fetching VIDEO: {query}")
        results = scrape_youtube(query, count, audio_only=False)
        source = 'YouTube'

        if not results:
            logger.info("YouTube failed → Instagram")
            results = scrape_instagram(query, count)
            source = 'Instagram'

    else:
        # Photo: Pinterest → Reddit → Instagram chain
        logger.info(f"Fetching PHOTO: {query}")

        results = scrape_pinterest(query, count)
        source = 'Pinterest'

        if not results:
            logger.info("Pinterest failed → Reddit")
            results = scrape_reddit(query, count)
            source = 'Reddit'

        if not results:
            logger.info("Reddit failed → Instagram")
            results = scrape_instagram(query, count)
            source = 'Instagram'

        if not results:
            logger.info("Instagram failed → YouTube thumbnails")
            yt_results = scrape_youtube(query, count, audio_only=False)
            for r in yt_results:
                if r.get('thumbnail'):
                    results.append({
                        'url': r['thumbnail'],
                        'type': 'photo',
                        'source': 'YouTube',
                        'title': r['title']
                    })
            source = 'YouTube'

    logger.info(f"Final: {len(results)} results from {source}")
    return {'results': results, 'source': source}
