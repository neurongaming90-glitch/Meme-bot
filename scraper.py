"""
Meme Scraper — YouTube (primary) + Instagram (fallback)
Photos: YouTube thumbnails + Instagram
Videos: YouTube via yt-dlp
Sound: YouTube audio via yt-dlp
GIF fallback: Giphy
"""
import logging
import re
import requests
import json
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


# ─────────────────────────────────────────
# YOUTUBE — Videos, Audio, Thumbnails
# ─────────────────────────────────────────
def scrape_youtube(query: str, count: int = 4, audio_only: bool = False, thumb_only: bool = False) -> list:
    """Get YouTube content using yt-dlp."""
    results = []
    try:
        import yt_dlp

        search_q = f"{query} meme" if 'meme' not in query.lower() else query

        # Step 1: Fast search
        search_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(search_opts) as ydl:
            search_info = ydl.extract_info(
                f"ytsearch{count * 3}:{search_q}",
                download=False
            )

        if not search_info or 'entries' not in search_info:
            logger.warning(f"YT search no results for: {search_q}")
            return results

        entries = [e for e in search_info['entries'] if e and e.get('id')]

        if thumb_only:
            # Just return thumbnails — no stream URL needed
            for entry in entries[:count]:
                vid_id = entry.get('id', '')
                thumb = f"https://img.youtube.com/vi/{vid_id}/hqdefault.jpg"
                results.append({
                    'url': thumb,
                    'type': 'photo',
                    'source': 'YouTube',
                    'title': entry.get('title', query)[:80],
                    'video_url': f"https://youtu.be/{vid_id}"
                })
            logger.info(f"YT thumbnails: {len(results)} for '{query}'")
            return results

        # Get stream URLs
        fmt = 'bestaudio[ext=m4a]/bestaudio/best' if audio_only else 'best[height<=720][ext=mp4]/best[height<=720]/best'
        stream_opts = {'quiet': True, 'no_warnings': True, 'format': fmt}

        for entry in entries:
            if len(results) >= count:
                break
            try:
                duration = entry.get('duration') or 0
                if duration > 180:  # Skip > 3 min
                    continue

                vid_url = f"https://www.youtube.com/watch?v={entry['id']}"
                with yt_dlp.YoutubeDL(stream_opts) as ydl2:
                    info = ydl2.extract_info(vid_url, download=False)

                stream_url = info.get('url', '')
                if not stream_url:
                    continue

                results.append({
                    'url': stream_url,
                    'thumbnail': f"https://img.youtube.com/vi/{entry['id']}/hqdefault.jpg",
                    'type': 'audio' if audio_only else 'video',
                    'source': 'YouTube',
                    'title': info.get('title', search_q)[:80],
                    'video_url': vid_url,
                    'duration': duration,
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
# INSTAGRAM — Photos via public scrape
# ─────────────────────────────────────────
def scrape_instagram(query: str, count: int = 4) -> list:
    """Scrape Instagram public hashtag page."""
    results = []
    try:
        # Build hashtag from query
        tag = re.sub(r'[^a-zA-Z0-9]', '', query.lower().replace(' ', '')) + 'meme'

        url = f"https://www.instagram.com/explore/tags/{tag}/"
        headers = {
            **HEADERS,
            'X-Requested-With': 'XMLHttpRequest',
        }

        resp = requests.get(url, headers=headers, timeout=15)
        html = resp.text

        # Extract image URLs from script tags
        matches = re.findall(r'"display_url":"(https://[^"]+)"', html)
        matches = [u.replace('\\u0026', '&') for u in matches if 'cdninstagram' in u or 'fbcdn' in u]
        matches = list(dict.fromkeys(matches))  # deduplicate

        for url in matches[:count]:
            results.append({
                'url': url,
                'type': 'photo',
                'source': 'Instagram',
                'title': f"{query} meme"
            })

        logger.info(f"Instagram: {len(results)} for tag #{tag}")

    except Exception as e:
        logger.error(f"Instagram error: {e}")

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
# MAIN FETCH
# ─────────────────────────────────────────
def fetch_memes(query: str, media_type: str = 'photo', count: int = 4) -> dict:
    """
    Main fetch with fallback chain.
    Photos:  YouTube thumbnails → Instagram → Giphy
    Videos:  YouTube stream → YouTube thumbnails + link
    Sound:   YouTube audio
    """
    results = []
    source = 'Unknown'

    # Clean query
    clean_query = query.strip()

    if media_type == 'sound':
        logger.info(f"🔊 SOUND: {clean_query}")
        results = scrape_youtube(clean_query, count, audio_only=True)
        source = 'YouTube'

        if not results:
            logger.info("YT audio failed → GIF fallback")
            results = scrape_giphy(clean_query, count)
            source = 'Giphy'

    elif media_type == 'video':
        logger.info(f"🎬 VIDEO: {clean_query}")
        results = scrape_youtube(clean_query, count, audio_only=False)
        source = 'YouTube'

        if not results:
            logger.info("YT video failed → thumbnails")
            results = scrape_youtube(clean_query, count, thumb_only=True)
            source = 'YouTube'

        if not results:
            logger.info("YT thumbs failed → Giphy")
            results = scrape_giphy(clean_query, count)
            source = 'Giphy'

    else:  # photo
        logger.info(f"📷 PHOTO: {clean_query}")

        # Primary: YouTube thumbnails (fast, no stream needed)
        results = scrape_youtube(clean_query, count, thumb_only=True)
        source = 'YouTube'

        # Fallback 1: Instagram
        if len(results) < count:
            logger.info(f"YT gave {len(results)}, trying Instagram...")
            insta = scrape_instagram(clean_query, count - len(results))
            results.extend(insta)
            if insta:
                source = 'YouTube+Instagram' if results else 'Instagram'

        # Fallback 2: Giphy
        if not results:
            logger.info("All failed → Giphy")
            results = scrape_giphy(clean_query, count)
            source = 'Giphy'

    # Remove empty/invalid
    results = [r for r in results if r.get('url', '').startswith('http')]

    logger.info(f"✅ Final: {len(results)} from {source} for '{clean_query}'")
    return {'results': results[:count], 'source': source}
