import requests
import time
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)

class ScryfallService:
    """Service for interacting with Scryfall API with Portuguese priority"""
    
    BASE_URL = "https://api.scryfall.com"
    REQUEST_DELAY = 0.1  # 100ms delay between requests to respect rate limits
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'MTG-Proxy-Forge/1.0'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Ensure we don't exceed Scryfall's rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.REQUEST_DELAY:
            time.sleep(self.REQUEST_DELAY - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, url, params=None, max_retries=3):
        """Make a request to Scryfall API with rate limiting and retry logic"""
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=15)
                logger.debug(f"Request to {url} with params {params}: {response.status_code}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                elif response.status_code == 429:  # Rate limited
                    logger.warning("Rate limited by Scryfall API, waiting...")
                    time.sleep(1)
                    continue
                else:
                    logger.warning(f"Scryfall API returned {response.status_code}: {response.text}")
                    return None
                    
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                logger.warning(f"Network error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error(f"All {max_retries} attempts failed for {url}")
                    return None
            except requests.exceptions.RequestException as e:
                logger.error(f"Request to Scryfall failed: {str(e)}")
                return None
        
        return None
    
    def get_card_by_name(self, card_name):
        """
        Get card data by name with Portuguese priority and English fallback
        Uses fuzzy search followed by ID-based lookup for language handling
        """
        try:
            # Step 1: Get card ID using fuzzy search
            fuzzy_url = f"{self.BASE_URL}/cards/named"
            fuzzy_params = {'fuzzy': card_name}
            
            logger.info(f"Searching for card: {card_name}")
            card_data = self._make_request(fuzzy_url, fuzzy_params)
            
            if not card_data:
                logger.warning(f"Card not found with fuzzy search: {card_name}")
                return None
            
            card_id = card_data.get('id')
            if not card_id:
                logger.warning(f"No ID found for card: {card_name}")
                return card_data  # Return what we have
            
            # Step 2: Try to get Portuguese version using the ID
            id_url = f"{self.BASE_URL}/cards/{card_id}"
            
            # Try Portuguese first
            pt_params = {'lang': 'pt'}
            pt_card = self._make_request(id_url, pt_params)
            
            if pt_card and pt_card.get('lang') == 'pt':
                logger.info(f"Found Portuguese version of: {card_name}")
                return pt_card
            elif pt_card:
                logger.debug(f"Received card but language is {pt_card.get('lang')}, not Portuguese")
            
            # Fallback to English (no lang parameter)
            en_card = self._make_request(id_url)
            if en_card:
                logger.info(f"Using English fallback for: {card_name}")
                return en_card
            
            # If ID lookup fails, return the original fuzzy result
            logger.info(f"Using fuzzy search result for: {card_name}")
            return card_data
            
        except Exception as e:
            logger.error(f"Error searching for card {card_name}: {str(e)}")
            return None
    
    def get_card_by_name_and_set(self, card_name, set_code):
        """Get card from specific edition with Portuguese priority"""
        try:
            exact_url = f"{self.BASE_URL}/cards/named"
            
            # Try Portuguese first
            pt_params = {
                'exact': card_name,
                'set': (set_code or '').lower(),
                'lang': 'pt'
            }
            
            logger.info(f"Searching for {card_name} in set {set_code} (Portuguese)")
            pt_card = self._make_request(exact_url, pt_params)
            
            if pt_card:
                return pt_card
            
            # Try with English name if Portuguese fails
            en_params = {
                'exact': card_name,
                'set': (set_code or '').lower()
            }
            
            logger.info(f"Searching for {card_name} in set {set_code} (English fallback)")
            en_card = self._make_request(exact_url, en_params)
            
            if en_card:
                return en_card
            
            # If exact match fails, try fuzzy search within set
            fuzzy_params = {
                'fuzzy': card_name,
                'set': (set_code or '').lower()
            }
            
            logger.info(f"Fuzzy searching for {card_name} in set {set_code}")
            fuzzy_card = self._make_request(exact_url, fuzzy_params)
            
            return fuzzy_card
            
        except Exception as e:
            logger.error(f"Error searching for card {card_name} in set {set_code}: {str(e)}")
            return None
    
    def get_card_editions(self, card_name, limit=200):
        """Get all available editions for a card with language information"""
        try:
            search_url = f"{self.BASE_URL}/cards/search"
            params = {
                'q': f'!"{card_name}"',
                'unique': 'prints',
                'order': 'released'
            }
            
            logger.info(f"Getting editions for: {card_name}")
            response = self._make_request(search_url, params)
            
            if not response or 'data' not in response:
                logger.warning(f"No editions found for: {card_name}")
                return []
            
            editions = []
            sets_with_portuguese = set()  # Track which sets have Portuguese versions
            
            # First pass: collect all editions and track Portuguese availability
            for card in response['data']:
                if len(editions) >= limit:
                    break
                    
                # Get language information
                lang = card.get('lang', 'en')
                lang_name = self._get_language_name(lang)
                set_code = (card.get('set') or '').upper()
                
                # Track sets that have Portuguese versions
                if lang == 'pt':
                    sets_with_portuguese.add(set_code)
                
                edition_info = {
                    'name': card.get('printed_name') or card.get('name', ''),
                    'set': set_code,
                    'set_name': card.get('set_name', ''),
                    'released_at': card.get('released_at', ''),
                    'image_uris': card.get('image_uris', {}),
                    'id': card.get('id', ''),
                    'rarity': card.get('rarity', ''),
                    'lang': lang,
                    'lang_name': lang_name
                }
                editions.append(edition_info)
            
            # Second pass: add Portuguese availability info to all editions
            for edition in editions:
                edition['has_portuguese'] = edition['set'] in sets_with_portuguese
            
            # Sort by language priority (Portuguese first), then by release date
            def sort_key(x):
                lang_priority = 0 if x.get('lang') == 'pt' else 1
                return (lang_priority, x.get('released_at', ''))
            
            editions.sort(key=sort_key, reverse=True)
            
            logger.info(f"Found {len(editions)} editions for {card_name}")
            return editions
            
        except Exception as e:
            logger.error(f"Error getting editions for card {card_name}: {str(e)}")
            return []
    
    def _get_language_name(self, lang_code):
        """Convert language code to display name"""
        lang_map = {
            'en': 'Inglês',
            'pt': 'Português',
            'es': 'Espanhol',
            'fr': 'Francês',
            'de': 'Alemão',
            'it': 'Italiano',
            'ja': 'Japonês',
            'ko': 'Coreano',
            'ru': 'Russo',
            'zhs': 'Chinês Simplificado',
            'zht': 'Chinês Tradicional'
        }
        return lang_map.get(lang_code, f'Idioma ({lang_code})')
    
    def get_unique_languages(self, editions):
        """Get unique languages from editions list"""
        languages = set()
        for edition in editions:
            languages.add((edition.get('lang', 'en'), edition.get('lang_name', 'Inglês')))
        
        # Sort with Portuguese first
        sorted_langs = sorted(languages, key=lambda x: (0 if x[0] == 'pt' else 1, x[1]))
        return [{'code': lang[0], 'name': lang[1]} for lang in sorted_langs]
