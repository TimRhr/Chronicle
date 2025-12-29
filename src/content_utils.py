"""
Content utilities for link previews, embeds, and markdown processing.
"""
import html
import uuid
import ipaddress
import re
import socket
import requests
from bs4 import BeautifulSoup
import markdown
import bleach
from urllib.parse import urlparse, parse_qs


# Allowed HTML tags for sanitized content
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'del', 'code', 'pre', 'blockquote',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'a', 'img', 'hr', 'span', 'div'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
    'code': ['class'],
    'pre': ['class'],
    'span': ['class'],
    'div': ['class']
}


MAX_PREVIEW_BYTES = 2 * 1024 * 1024
MAX_PREVIEW_REDIRECTS = 5


def _is_private_host(hostname: str) -> bool:
    if not hostname:
        return True

    host = hostname.strip().lower()
    if host in {'localhost', 'localhost.localdomain'}:
        return True

    try:
        ip = ipaddress.ip_address(host)
        return (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        )
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return True

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except Exception:
            return True
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return True

    return False


def _validate_public_http_url(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except Exception:
        return None

    if parsed.scheme not in ('http', 'https'):
        return None
    if not parsed.netloc:
        return None
    if _is_private_host(parsed.hostname or ''):
        return None
    return url


def _fetch_html_with_redirect_checks(url: str, timeout: int = 5):
    current = _validate_public_http_url(url)
    if not current:
        return None

    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ChronicleBot/1.0)'}
    session = requests.Session()

    for _ in range(MAX_PREVIEW_REDIRECTS + 1):
        resp = session.get(
            current,
            headers=headers,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )

        if 300 <= resp.status_code < 400:
            loc = resp.headers.get('Location')
            if not loc:
                return None
            next_url = requests.compat.urljoin(current, loc)
            current = _validate_public_http_url(next_url)
            if not current:
                return None
            continue

        if resp.status_code >= 400:
            return None

        ctype = (resp.headers.get('Content-Type') or '').lower()
        if 'text/html' not in ctype and 'application/xhtml+xml' not in ctype and ctype:
            return None

        buf = bytearray()
        for chunk in resp.iter_content(chunk_size=16384):
            if not chunk:
                continue
            buf.extend(chunk)
            if len(buf) > MAX_PREVIEW_BYTES:
                return None

        encoding = resp.encoding or 'utf-8'
        try:
            return bytes(buf).decode(encoding, errors='replace')
        except Exception:
            return bytes(buf).decode('utf-8', errors='replace')

    return None


def fetch_open_graph(url, timeout=5):
    """Fetch Open Graph metadata from a URL."""
    try:
        html = _fetch_html_with_redirect_checks(url, timeout=timeout)
        if not html:
            return None

        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract Open Graph data
        og_data = {
            'url': url,
            'title': None,
            'description': None,
            'image_url': None,
            'site_name': None
        }
        
        # Open Graph tags
        og_title = soup.find('meta', property='og:title')
        og_desc = soup.find('meta', property='og:description')
        og_image = soup.find('meta', property='og:image')
        og_site = soup.find('meta', property='og:site_name')
        
        if og_title:
            og_data['title'] = og_title.get('content', '')[:500]
        if og_desc:
            og_data['description'] = og_desc.get('content', '')[:1000]
        if og_image:
            og_data['image_url'] = og_image.get('content', '')
        if og_site:
            og_data['site_name'] = og_site.get('content', '')[:200]
        
        # Fallback to standard meta tags
        if not og_data['title']:
            title_tag = soup.find('title')
            if title_tag:
                og_data['title'] = title_tag.text.strip()[:500]
        
        if not og_data['description']:
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                og_data['description'] = meta_desc.get('content', '')[:1000]
        
        # Fallback site name from domain
        if not og_data['site_name']:
            parsed = urlparse(url)
            og_data['site_name'] = parsed.netloc
        
        return og_data
    except Exception as e:
        return None


def detect_embed_type(url):
    """Detect if URL is an embeddable service and extract embed info."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # YouTube
    if 'youtube.com' in domain or 'youtu.be' in domain:
        video_id = None
        if 'youtu.be' in domain:
            video_id = parsed.path.strip('/')
        elif 'youtube.com' in domain:
            if '/watch' in parsed.path:
                qs = parse_qs(parsed.query)
                video_id = qs.get('v', [None])[0]
            elif '/embed/' in parsed.path:
                video_id = parsed.path.split('/embed/')[1].split('?')[0]
            elif '/shorts/' in parsed.path:
                video_id = parsed.path.split('/shorts/')[1].split('?')[0]
        if video_id:
            return {'type': 'youtube', 'id': video_id}
    
    # Vimeo
    if 'vimeo.com' in domain:
        match = re.search(r'vimeo\.com/(\d+)', url)
        if match:
            return {'type': 'vimeo', 'id': match.group(1)}
    
    # Spotify
    if 'spotify.com' in domain:
        # spotify.com/track/ID, spotify.com/album/ID, spotify.com/playlist/ID
        match = re.search(r'spotify\.com/(track|album|playlist|episode)/([a-zA-Z0-9]+)', url)
        if match:
            return {'type': 'spotify', 'id': f"{match.group(1)}/{match.group(2)}"}
    
    # SoundCloud - just mark as soundcloud, will use oEmbed
    if 'soundcloud.com' in domain:
        return {'type': 'soundcloud', 'id': url}
    
    # Twitter/X
    if 'twitter.com' in domain or 'x.com' in domain:
        match = re.search(r'(?:twitter|x)\.com/\w+/status/(\d+)', url)
        if match:
            return {'type': 'twitter', 'id': match.group(1)}
    
    # Instagram
    if 'instagram.com' in domain:
        match = re.search(r'instagram\.com/(?:p|reel)/([a-zA-Z0-9_-]+)', url)
        if match:
            return {'type': 'instagram', 'id': match.group(1)}
    
    return None


def extract_urls(text):
    """Extract all URLs from text."""
    url_pattern = r'https?://[^\s<>"\')\]]+(?:\([^\s<>"\')\]]*\))?[^\s<>"\')\].,!?]*'
    urls = re.findall(url_pattern, text)
    return urls


def process_link_preview(url):
    """Process a URL and return preview data with embed info if applicable."""
    result = {
        'url': url,
        'title': None,
        'description': None,
        'image_url': None,
        'site_name': None,
        'embed_type': None,
        'embed_id': None
    }
    
    # Check for embeddable content first
    embed_info = detect_embed_type(url)
    if embed_info:
        result['embed_type'] = embed_info['type']
        result['embed_id'] = embed_info['id']
    
    # Fetch Open Graph data
    og_data = fetch_open_graph(url)
    if og_data:
        result.update({
            'title': og_data.get('title'),
            'description': og_data.get('description'),
            'image_url': og_data.get('image_url'),
            'site_name': og_data.get('site_name')
        })
    
    # Default embed type to 'link' if we have OG data but no special embed
    if not result['embed_type'] and (result['title'] or result['description']):
        result['embed_type'] = 'link'
    
    return result


def generate_toc(text):
    """Generate table of contents from markdown headings."""
    if not text:
        return []
    
    toc = []
    # Match markdown headings
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    
    for match in heading_pattern.finditer(text):
        level = len(match.group(1))
        title = match.group(2).strip()
        # Create slug from title
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[\s_]+', '-', slug).strip('-')
        toc.append({
            'level': level,
            'title': title,
            'slug': slug
        })
    
    return toc


def render_markdown(text, with_toc=False):
    """Render markdown to HTML with sanitization and optional TOC."""
    if not text:
        return '' if not with_toc else ('', [])

    # 1. Extract injection blocks before markdown processing to protect them
    # and replace with placeholders
    text, injections = extract_injection_blocks(text)

    # Support GitHub-style strikethrough: ~~text~~
    # python-markdown doesn't support this by default; convert to <del> which is allowed.
    text = re.sub(r'(?<!~)~~(?!~)(.+?)(?<!~)~~(?!~)', r'<del>\1</del>', text)
    
    toc = generate_toc(text) if with_toc else []
    
    # Convert markdown to HTML with syntax highlighting
    html_content = markdown.markdown(
        text,
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
            'markdown.extensions.toc'
        ],
        extension_configs={
            'markdown.extensions.codehilite': {
                'css_class': 'highlight',
                'guess_lang': True,
                'linenums': False
            },
            'markdown.extensions.toc': {
                'slugify': lambda value, separator: re.sub(r'[\s_]+', '-', re.sub(r'[^\w\s-]', '', value.lower()).strip('-'))
            }
        }
    )
    
    # Sanitize HTML
    clean_html = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True
    )
    
    # Add target="_blank" to external links
    clean_html = re.sub(
        r'<a href="(https?://[^"]+)"',
        r'<a href="\1" target="_blank" rel="noopener noreferrer"',
        clean_html
    )
    
    # Parse @mentions and convert to profile links
    clean_html = parse_mentions(clean_html)

    # 2. Restore injection blocks as secure iframes
    clean_html = restore_injection_blocks(clean_html, injections)
    
    if with_toc:
        return clean_html, toc
    return clean_html


def extract_injection_blocks(text):
    """
    Finds ```injection ... ``` blocks, replaces them with placeholders,
    and returns the modified text and a dict of ID -> Content.
    """
    injections = {}
    
    def replace_block(match):
        content = match.group(1)
        block_id = str(uuid.uuid4())
        injections[block_id] = content
        return f'[CHRONICLE_INJECTION_BLOCK:{block_id}]'

    # Regex for ```injection\n...\n```
    # We use non-greedy matching for content
    pattern = re.compile(r'(?m)^```injection\s*\n(.*?)\n^```\s*$', re.DOTALL)
    processed_text = pattern.sub(replace_block, text)
    
    return processed_text, injections


def restore_injection_blocks(html_content, injections):
    """
    Replaces [CHRONICLE_INJECTION_BLOCK:ID] placeholders with secure iframes.
    """
    if not injections:
        return html_content

    def get_iframe_html(block_id):
        raw_code = injections.get(block_id, '')
        # Escape the code to be safe inside srcdoc attribute
        escaped_code = html.escape(raw_code, quote=True)
        
        # UI Container
        return f'''
        <div class="my-6 rounded-lg border border-light-border dark:border-dark-border bg-light-surface dark:bg-dark-surface overflow-hidden shadow-sm">
            <div class="flex items-center justify-between px-4 py-2 bg-gray-50 dark:bg-gray-800 border-b border-light-border dark:border-dark-border">
                <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-brand-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                    </svg>
                    <span class="text-xs font-bold text-gray-500 uppercase tracking-wider">HTML/JS Injection</span>
                </div>
                <div class="flex gap-2">
                     <div class="w-2 h-2 rounded-full bg-red-400"></div>
                     <div class="w-2 h-2 rounded-full bg-yellow-400"></div>
                     <div class="w-2 h-2 rounded-full bg-green-400"></div>
                </div>
            </div>
            <div class="relative w-full h-[400px] resize-y overflow-hidden bg-white">
                <iframe 
                    srcdoc="{escaped_code}"
                    sandbox="allow-scripts allow-forms allow-popups allow-modals"
                    class="w-full h-full border-0"
                    loading="lazy"
                    title="User Code Injection"
                ></iframe>
            </div>
        </div>
        '''

    # Pattern to match the placeholder, potentially wrapped in <p> tags by Markdown
    # Case 1: Wrapped in <p>
    p_pattern = re.compile(r'<p>\s*\[CHRONICLE_INJECTION_BLOCK:([a-f0-9-]+)\]\s*</p>')
    
    def p_replacer(match):
        return get_iframe_html(match.group(1))
        
    html_content = p_pattern.sub(p_replacer, html_content)
    
    # Case 2: Naked placeholder (just in case)
    naked_pattern = re.compile(r'\[CHRONICLE_INJECTION_BLOCK:([a-f0-9-]+)\]')
    
    def naked_replacer(match):
        return get_iframe_html(match.group(1))
        
    html_content = naked_pattern.sub(naked_replacer, html_content)
    
    return html_content


def parse_mentions(text):
    """Convert @username mentions to profile links."""
    if not text:
        return text
    
    def replace_mention(match):
        username = match.group(1)
        return f'<a href="/u/{username}" class="mention text-brand-teal hover:underline font-medium">@{username}</a>'
    
    return MENTION_PATTERN.sub(replace_mention, text)


MENTION_PATTERN = re.compile(r'(?<![a-zA-Z0-9_])@([a-zA-Z0-9_]{1,30})(?![a-zA-Z0-9_])')


def extract_mentions(text):
    if not text:
        return []
    usernames = MENTION_PATTERN.findall(text)
    return list(dict.fromkeys(usernames))


def highlight_search_terms(text, search_query):
    """Highlight search terms in text."""
    if not text or not search_query:
        return text
    
    # Split search query into terms
    terms = search_query.split()
    
    for term in terms:
        if len(term) >= 2:  # Only highlight terms with 2+ chars
            # Case-insensitive replacement with highlighting
            pattern = re.compile(f'({re.escape(term)})', re.IGNORECASE)
            text = pattern.sub(r'<mark class="bg-yellow-200 dark:bg-yellow-800 px-0.5 rounded">\1</mark>', text)
    
    return text


def get_embed_html(embed_type, embed_id):
    """Generate embed HTML for different services."""
    if embed_type == 'youtube':
        return f'''<div class="embed-container aspect-video rounded-lg overflow-hidden">
            <iframe src="https://www.youtube.com/embed/{embed_id}" 
                    class="w-full h-full" 
                    frameborder="0" 
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen></iframe>
        </div>'''
    
    elif embed_type == 'vimeo':
        return f'''<div class="embed-container aspect-video rounded-lg overflow-hidden">
            <iframe src="https://player.vimeo.com/video/{embed_id}" 
                    class="w-full h-full" 
                    frameborder="0" 
                    allow="autoplay; fullscreen; picture-in-picture" 
                    allowfullscreen></iframe>
        </div>'''
    
    elif embed_type == 'spotify':
        # embed_id format: "track/ID" or "album/ID" etc
        return f'''<div class="embed-container rounded-lg overflow-hidden">
            <iframe src="https://open.spotify.com/embed/{embed_id}" 
                    class="w-full" 
                    height="152" 
                    frameborder="0" 
                    allow="encrypted-media"></iframe>
        </div>'''
    
    elif embed_type == 'twitter':
        return f'''<div class="embed-container twitter-embed" data-tweet-id="{embed_id}">
            <blockquote class="twitter-tweet" data-dnt="true">
                <a href="https://twitter.com/x/status/{embed_id}">Lade Tweet...</a>
            </blockquote>
        </div>'''
    
    elif embed_type == 'instagram':
        return f'''<div class="embed-container instagram-embed" data-instagram-id="{embed_id}">
            <blockquote class="instagram-media" data-instgrm-permalink="https://www.instagram.com/p/{embed_id}/">
                <a href="https://www.instagram.com/p/{embed_id}/" target="_blank">Instagram Post</a>
            </blockquote>
        </div>'''
    
    return ''
