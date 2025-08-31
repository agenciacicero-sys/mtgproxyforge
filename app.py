import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.middleware.proxy_fix import ProxyFix
from scryfall_service import ScryfallService
from pdf_generator import PDFGenerator
from card_parser import CardParser
import tempfile

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "mtg-proxy-forge-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize services
scryfall_service = ScryfallService()
pdf_generator = PDFGenerator()
card_parser = CardParser()

@app.route('/')
def index():
    """Main page with card list input"""
    return render_template('index.html')

@app.route('/api/process-list', methods=['POST'])
def process_list():
    """Process MTG Arena card list and return card data with editions"""
    try:
        # Check if request has JSON data
        if not request.is_json:
            logger.error("Request is not JSON")
            return jsonify({'error': 'Request must be JSON'}), 400

        data = request.get_json()
        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No data received'}), 400

        card_list_text = data.get('cardList', '').strip()

        if not card_list_text:
            return jsonify({'error': 'Empty card list provided'}), 400

        logger.info(f"Processing card list with {len(card_list_text.split(chr(10)))} lines")

        # Parse the card list
        parsed_cards = card_parser.parse_card_list(card_list_text)

        if not parsed_cards:
            return jsonify({'error': 'No valid cards found in the list'}), 400

        # Process each unique card
        processed_cards = []
        for card_info in parsed_cards:
            try:
                logger.info(f"Processing card: {card_info['name']}")
                logger.debug(f"Card info: {card_info}")

                # Get card data with Portuguese priority
                try:
                    card_data = scryfall_service.get_card_by_name(card_info['name'])
                    logger.debug(f"Card data received: {card_data.get('name') if card_data else None} (lang: {card_data.get('lang') if card_data else None})")
                except Exception as api_error:
                    logger.error(f"Scryfall API error for {card_info['name']}: {str(api_error)}")
                    card_data = None

                if card_data:
                    logger.debug("Getting editions for card...")
                    # Get all available editions for this card (with timeout protection)
                    try:
                        editions = scryfall_service.get_card_editions(card_info['name'])
                        logger.debug(f"Got {len(editions) if editions else 0} editions")
                    except Exception as e:
                        logger.warning(f"Failed to get editions for {card_info['name']}: {str(e)}")
                        editions = []

                    logger.debug("Processing default edition...")
                    # Find the default edition (specified in list or most recent)
                    set_code = card_info.get('set_code')
                    logger.debug(f"Set code from card_info: {set_code}")
                    default_edition = set_code.upper() if set_code else None
                    logger.debug(f"Default edition: {default_edition}")

                    # Priority: 1) Portuguese card_data if found, 2) Specified edition, 3) Most recent
                    if card_data.get('lang') == 'pt':
                        # Use the Portuguese version we already found
                        logger.debug("Using Portuguese version as priority")
                    elif default_edition and editions:
                        # Try to find the specified edition
                        logger.debug("Looking for specified edition in available editions...")
                        default_card = next((ed for ed in editions if (ed.get('set') or '').upper() == default_edition), None)
                        if default_card:
                            logger.debug("Found specified edition, using it")
                            card_data = default_card
                    elif editions:
                        # Use the first edition (sorted with Portuguese priority)
                        first_edition = editions[0]
                        if first_edition.get('lang') == 'pt':
                            logger.debug("Using first Portuguese edition from editions list")
                            card_data = first_edition

                    logger.debug("Building processed card data...")
                    try:
                        # Get unique languages from editions
                        languages = scryfall_service.get_unique_languages(editions) if editions else []

                        processed_card = {
                            'name': card_data.get('printed_name') or card_data.get('name', ''),
                            'quantity': card_info['quantity'],
                            'image_url': card_data.get('image_uris', {}).get('large') or card_data.get('image_uris', {}).get('normal', ''),
                            'scryfall_id': card_data.get('id', ''),
                            'set_code': (card_data.get('set') or '').upper(),
                            'set_name': card_data.get('set_name', ''),
                            'lang': card_data.get('lang', 'en'),
                            'lang_name': scryfall_service._get_language_name(card_data.get('lang', 'en')),
                            'editions': editions or [],
                            'languages': languages,
                            'original_name': card_info['name']  # Keep original for reference
                        }
                        logger.debug("Processed card data built successfully")
                        processed_cards.append(processed_card)
                        logger.info(f"Successfully processed: {processed_card['name']} ({processed_card['quantity']}x)")
                    except Exception as e:
                        logger.error(f"Error building processed card data: {str(e)}")
                        raise
                else:
                    logger.warning(f"Card not found: {card_info['name']}")
                    # Add placeholder for not found cards
                    processed_cards.append({
                        'name': card_info['name'],
                        'quantity': card_info['quantity'],
                        'image_url': '',
                        'scryfall_id': '',
                        'set_code': card_info.get('set_code') or '',
                        'set_name': '',
                        'editions': [],
                        'original_name': card_info['name'],
                        'error': 'Card not found'
                    })

            except Exception as e:
                logger.error(f"Error processing card {card_info['name']}: {str(e)}")
                processed_cards.append({
                    'name': card_info['name'],
                    'quantity': card_info['quantity'],
                    'image_url': '',
                    'scryfall_id': '',
                    'set_code': card_info.get('set_code') or '',
                    'set_name': '',
                    'editions': [],
                    'original_name': card_info['name'],
                    'error': f'Network error - please try again'
                })

        total_cards = sum(card['quantity'] for card in processed_cards)
        estimated_pages = (total_cards + 8) // 9  # Round up for 9 cards per page

        return jsonify({
            'cards': processed_cards,
            'total_cards': total_cards,
            'estimated_pages': estimated_pages
        })

    except Exception as e:
        logger.error(f"Error in process_list: {str(e)}")
        return jsonify({'error': f'Failed to process card list: {str(e)}'}), 500

@app.route('/api/get-card-by-edition', methods=['POST'])
def get_card_by_edition():
    """Get specific card data for a selected edition"""
    try:
        data = request.get_json()
        card_name = data.get('cardName')
        set_code = data.get('setCode')

        if not card_name or not set_code:
            return jsonify({'error': 'Missing card name or set code'}), 400

        # Get card from specific edition
        card_data = scryfall_service.get_card_by_name_and_set(card_name, set_code)

        if card_data:
            # Check for Portuguese version availability
            portuguese_card = scryfall_service.get_card_by_name_and_set(card_name, set_code, lang='pt')
            is_portuguese_available = bool(portuguese_card)

            return jsonify({
                'name': card_data.get('printed_name') or card_data.get('name', ''),
                'image_url': card_data.get('image_uris', {}).get('large') or card_data.get('image_uris', {}).get('normal', ''),
                'scryfall_id': card_data.get('id', ''),
                'set_code': (card_data.get('set') or '').upper(),
                'set_name': card_data.get('set_name', ''),
                'lang': card_data.get('lang', 'en'),
                'lang_name': scryfall_service._get_language_name(card_data.get('lang', 'en')),
                'is_portuguese_available': is_portuguese_available
            })
        else:
            return jsonify({'error': 'Card not found in specified edition'}), 404

    except Exception as e:
        logger.error(f"Error in get_card_by_edition: {str(e)}")
        return jsonify({'error': f'Failed to get card data: {str(e)}'}), 500

@app.route('/api/get-card-by-lang-and-set', methods=['POST'])
def get_card_by_lang_and_set():
    """Get card editions filtered by language and/or set"""
    try:
        data = request.get_json()
        card_name = data.get('cardName')
        set_code = data.get('setCode')
        lang_code = data.get('langCode')

        logger.info(f"Getting card by filters: name={card_name}, set={set_code}, lang={lang_code}")

        if not card_name:
            return jsonify({'error': 'Missing card name'}), 400

        # Get all editions for the card
        editions = scryfall_service.get_card_editions(card_name)
        logger.debug(f"Found {len(editions)} total editions")

        # Always get unique languages from ALL editions first (regardless of filters)
        all_languages = scryfall_service.get_unique_languages(editions)
        logger.debug(f"All available languages: {[lang['code'] for lang in all_languages]}")

        # Filter editions based on criteria
        filtered_editions = []
        for edition in editions:
            include = True
            edition_set = edition.get('set', '').upper()
            edition_lang = edition.get('lang', 'en')

            logger.debug(f"Checking edition: {edition_set} (lang: {edition_lang})")

            if set_code and edition_set != set_code.upper():
                logger.debug(f"Skipping edition {edition_set} - doesn't match requested set {set_code}")
                include = False

            if lang_code and edition_lang != lang_code:
                logger.debug(f"Skipping edition {edition_set} - language {edition_lang} doesn't match {lang_code}")
                include = False

            if include:
                logger.debug(f"Including edition: {edition_set} (lang: {edition_lang})")
                # Add Portuguese availability flag
                portuguese_version_exists = any(
                    ed['set'].upper() == edition_set and ed['lang'] == 'pt'
                    for ed in editions
                )
                edition['is_portuguese_available'] = portuguese_version_exists
                filtered_editions.append(edition)

        logger.info(f"Filtered to {len(filtered_editions)} matching editions")
        
        # Get unique sets from filtered results
        sets = list({ed['set']: ed['set_name'] for ed in filtered_editions}.items())
        sets.sort(key=lambda x: x[1])  # Sort by set name

        # Return the first matching card if found, plus filter options
        selected_card = None
        if filtered_editions:
            selected_card = {
                'name': filtered_editions[0].get('name', ''),
                'image_url': filtered_editions[0].get('image_uris', {}).get('large') or filtered_editions[0].get('image_uris', {}).get('normal', ''),
                'scryfall_id': filtered_editions[0].get('id', ''),
                'set_code': filtered_editions[0].get('set', '').upper(),
                'set_name': filtered_editions[0].get('set_name', ''),
                'lang': filtered_editions[0].get('lang', 'en'),
                'lang_name': scryfall_service._get_language_name(filtered_editions[0].get('lang', 'en')),
                'is_portuguese_available': filtered_editions[0].get('is_portuguese_available', False)
            }
            logger.info(f"Selected card: {selected_card['name']} from {selected_card['set_code']} in {selected_card['lang']}")
        else:
            logger.warning(f"No matching editions found for filters: set={set_code}, lang={lang_code}")

        return jsonify({
            'card': selected_card,
            'available_languages': all_languages,
            'available_sets': [{'code': s[0], 'name': s[1]} for s in sets],
            'total_matches': len(filtered_editions)
        })

    except Exception as e:
        logger.error(f"Error in get_card_by_lang_and_set: {str(e)}")
        return jsonify({'error': f'Failed to get card data: {str(e)}'}), 500

@app.route('/api/generate-pdf', methods=['POST'])
def generate_pdf():
    """Generate PDF with selected cards and configurations"""
    try:
        data = request.get_json()
        cards = data.get('cards', [])
        config = data.get('config', {})

        if not cards:
            return jsonify({'error': 'No cards provided'}), 400

        logger.info(f"Generating PDF for {len(cards)} unique cards")

        # Create temporary file for PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_file.close()

        # Generate PDF
        success = pdf_generator.generate_pdf(cards, temp_file.name, config)

        if success:
            return send_file(
                temp_file.name,
                as_attachment=True,
                download_name='mtg_proxy_cards.pdf',
                mimetype='application/pdf'
            )
        else:
            return jsonify({'error': 'Failed to generate PDF'}), 500

    except Exception as e:
        logger.error(f"Error in generate_pdf: {str(e)}")
        return jsonify({'error': f'Failed to generate PDF: {str(e)}'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)