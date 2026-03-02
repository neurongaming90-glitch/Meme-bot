"""
AI Engine — Groq llama3-70b
- Language detection
- Full chatbot with memory
- Meme intent detection
- Savage caption generation
- Meme query refinement
- Feedback collection
"""
import logging
import json
import re
import requests
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_HEADERS = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json"
}

# Per-user conversation history
user_sessions: dict = {}

SYSTEM_PROMPT = """Tu ek savage aur funny meme bot hai jiska naam "InstasMeme Bot" hai.
Tu Telegram pe kaam karta hai aur users ke liye memes dhundta hai.

PERSONALITY:
- Tu thoda arrogant hai, users ko light-heartedly roast karta hai
- Kabhi boring ya formal mat baat kar
- Emojis use kar but over mat kar
- Short aur punchy responses de
- User ki language detect kar aur usi mein baat kar:
  * Hindi likhein → Pure Hindi mein jawab
  * English likhein → English mein jawab  
  * Mixed/Hinglish → Hinglish mein jawab (default)

MEME DETECTION:
Agar user meme maang raha hai toh respond kar with JSON:
{"type": "meme_request", "query": "refined search query for memes", "style": "funny/dark/wholesome/dank/trending"}

Agar normal baat kar raha hai toh normal reply de (no JSON).

EXAMPLES:
User: "israel iran war meme chahiye"
Tu: {"type": "meme_request", "query": "israel iran war meme", "style": "dark"}

User: "hello"
Tu: "Aye! Kya scene hai? Meme chahiye ya sirf timepass karne aaya hai? 😏"

User: "bhai kuch funny do"  
Tu: {"type": "meme_request", "query": "funny dank memes", "style": "funny"}

IMPORTANT: JSON sirf tab de jab clearly meme manga ho. Baaki sab normal chat."""


def detect_language(text: str) -> str:
    """Simple language detection."""
    hindi_chars = len(re.findall(r'[\u0900-\u097F]', text))
    total_chars = len(text.replace(' ', ''))
    if total_chars == 0:
        return 'hinglish'
    ratio = hindi_chars / total_chars
    if ratio > 0.5:
        return 'hindi'
    elif ratio > 0.1:
        return 'hinglish'
    else:
        return 'english'


def call_groq(messages: list, max_tokens: int = 300) -> str:
    """Call Groq API."""
    try:
        payload = {
            "model": "llama3-70b-8192",
            "messages": messages,
            "temperature": 0.85,
            "max_tokens": max_tokens,
            "stream": False
        }
        resp = requests.post(GROQ_URL, headers=GROQ_HEADERS, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()['choices'][0]['message']['content'].strip()
        else:
            logger.error(f"Groq error {resp.status_code}: {resp.text[:200]}")
            return ""
    except Exception as e:
        logger.error(f"Groq call failed: {e}")
        return ""


def get_session(user_id: int) -> list:
    """Get or create user conversation session."""
    if user_id not in user_sessions:
        user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return user_sessions[user_id]


def clear_session(user_id: int):
    """Clear user session."""
    user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]


def chat(user_id: int, message: str) -> dict:
    """
    Main chat function.
    Returns: {
        'type': 'chat' | 'meme_request',
        'text': 'AI response text',
        'query': 'meme search query' (if meme_request),
        'style': 'funny/dark/etc' (if meme_request)
    }
    """
    session = get_session(user_id)

    # Add user message to history
    session.append({"role": "user", "content": message})

    # Keep session size manageable (last 20 messages + system)
    if len(session) > 21:
        session = [session[0]] + session[-20:]
        user_sessions[user_id] = session

    # Call Groq
    response = call_groq(session)

    if not response:
        # Fallback responses
        lang = detect_language(message)
        fallbacks = {
            'hindi': "Yaar, server slow hai abhi. Thoda ruk ja! 😅",
            'english': "Bruh, my brain lagged for a sec. Try again! 😅",
            'hinglish': "Aye bhai, server ne chhakka maar diya. Dobara try kar! 😅"
        }
        response = fallbacks.get(lang, fallbacks['hinglish'])

    # Add AI response to history
    session.append({"role": "assistant", "content": response})

    # Try to parse as JSON (meme request)
    try:
        # Find JSON in response
        json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            if data.get('type') == 'meme_request':
                return {
                    'type': 'meme_request',
                    'text': response,
                    'query': data.get('query', message),
                    'style': data.get('style', 'funny')
                }
    except Exception:
        pass

    return {'type': 'chat', 'text': response}


def get_intro(user_name: str, lang: str = 'hinglish') -> str:
    """Generate personalized intro for new user."""
    prompts = {
        'hindi': f"Ek naye user '{user_name}' ne bot join kiya. Unhe 2-3 line mein savage lekin friendly intro de. Bot ka naam InstasMeme Bot hai. Short rakho.",
        'english': f"New user '{user_name}' just joined. Give them a savage but friendly 2-3 line intro. Bot name is InstasMeme Bot. Keep it short.",
        'hinglish': f"Naya user '{user_name}' aaya hai. Use 2-3 line mein savage lekin friendly Hinglish intro de. Bot ka naam InstasMeme Bot hai. Short rakho."
    }
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompts.get(lang, prompts['hinglish'])}
    ]
    result = call_groq(messages, max_tokens=150)
    if not result:
        defaults = {
            'hindi': f"Aye {user_name}! 😈 InstasMeme Bot mein swagat hai!\nYahan memes milenge — funny, dark, dank — sab kuch!\nBas bata kya chahiye, baki main dekh lunga. 😏",
            'english': f"Yo {user_name}! 😈 Welcome to InstasMeme Bot!\nFunny, dark, dank — all memes here!\nJust tell me what you want. 😏",
            'hinglish': f"Aye {user_name}! 😈 InstasMeme Bot mein welcome!\nYahan funny, dark, dank — har type ke memes milenge!\nBas bol kya chahiye, baki main handle karunga. 😏"
        }
        return defaults.get(lang, defaults['hinglish'])
    return result


def generate_caption(query: str, style: str, lang: str = 'hinglish') -> str:
    """Generate savage/funny caption for meme."""
    prompt = f"Generate a savage and funny caption for a '{style}' meme about '{query}'. Language: {lang}. Max 2 lines. Use emojis. No explanation."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    result = call_groq(messages, max_tokens=80)
    if not result:
        captions = {
            'hindi': f"Jab koi {query} ke baare mein pooche 💀",
            'english': f"When someone asks about {query} 💀",
            'hinglish': f"Jab {query} ka scene ho 💀"
        }
        return captions.get(lang, captions['hinglish'])
    return result


def get_feedback_prompt(query: str, count: int, lang: str = 'hinglish') -> str:
    """Generate feedback message after showing memes."""
    prompt = f"User ne '{query}' ke {count} memes dekhe. Ab savage tarike se feedback maango — aur chahiye, alag type chahiye, ya theek hai? Language: {lang}. Max 2 lines."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    result = call_groq(messages, max_tokens=80)
    if not result:
        defaults = {
            'hindi': f"Kaisa laga? 😏 Aur chahiye ya kuch alag dhundhe?",
            'english': f"How was that? 😏 Want more or something different?",
            'hinglish': f"Kaisa laga? 😏 Aur chahiye ya different type try karein?"
        }
        return defaults.get(lang, defaults['hinglish'])
    return result


def refine_query(user_input: str, previous_query: str, lang: str = 'hinglish') -> str:
    """Refine meme search query based on user feedback."""
    prompt = f"User pehle '{previous_query}' memes dekh raha tha. Ab bola: '{user_input}'. Ek refined search query do memes ke liye. Sirf query do, kuch nahi."
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    result = call_groq(messages, max_tokens=30)
    return result.strip('"\'') if result else previous_query
