import re
import logging

logger = logging.getLogger(__name__)

class CardParser:
    """Parser for MTG Arena card list format"""
    
    def __init__(self):
        # Regex patterns for different MTG Arena formats
        self.patterns = [
            # Pattern for: "4 Sol Ring (CMM) 464"
            re.compile(r'^\s*(\d+)\s+(.+?)\s+\(([A-Za-z0-9]+)\)(?:\s+\d+)?\s*$'),
            # Pattern for: "1 Lightning Bolt"
            re.compile(r'^\s*(\d+)\s+(.+?)\s*$'),
            # Pattern for: "Sol Ring" (no quantity, default to 1)
            re.compile(r'^\s*([^\d].+?)\s*$')
        ]
    
    def parse_card_list(self, card_list_text):
        """
        Parse MTG Arena format card list
        Returns list of dictionaries with card info
        """
        lines = card_list_text.strip().split('\n')
        parsed_cards = []
        line_number = 0
        
        for line in lines:
            line_number += 1
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            card_info = self._parse_line(line)
            if card_info:
                card_info['line_number'] = line_number
                parsed_cards.append(card_info)
                logger.debug(f"Parsed line {line_number}: {card_info}")
            else:
                logger.warning(f"Could not parse line {line_number}: {line}")
        
        # Consolidate duplicate cards (same name and set)
        consolidated = self._consolidate_cards(parsed_cards)
        
        logger.info(f"Parsed {len(lines)} lines, found {len(consolidated)} unique cards")
        return consolidated
    
    def _parse_line(self, line):
        """Parse a single line of the card list"""
        
        # Try each pattern in order
        for pattern in self.patterns:
            match = pattern.match(line)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:  # Quantity + Name + Set
                    quantity = int(groups[0])
                    name = groups[1].strip()
                    set_code = groups[2].upper()
                    
                    return {
                        'quantity': quantity,
                        'name': name,
                        'set_code': set_code,
                        'original_line': line
                    }
                    
                elif len(groups) == 2:  # Quantity + Name
                    quantity = int(groups[0])
                    name = groups[1].strip()
                    
                    return {
                        'quantity': quantity,
                        'name': name,
                        'set_code': None,
                        'original_line': line
                    }
                    
                elif len(groups) == 1:  # Just Name (no quantity)
                    name = groups[0].strip()
                    
                    return {
                        'quantity': 1,
                        'name': name,
                        'set_code': None,
                        'original_line': line
                    }
        
        return None
    
    def _consolidate_cards(self, parsed_cards):
        """Consolidate cards with same name and set, summing quantities"""
        card_map = {}
        
        for card in parsed_cards:
            # Create a unique key based on name and set
            key = (card['name'].lower(), (card.get('set_code') or '').upper())
            
            if key in card_map:
                # Add to existing card quantity
                card_map[key]['quantity'] += card['quantity']
                # Keep track of all original lines
                if 'original_lines' not in card_map[key]:
                    card_map[key]['original_lines'] = [card_map[key]['original_line']]
                card_map[key]['original_lines'].append(card['original_line'])
            else:
                # New card
                card_map[key] = card.copy()
        
        return list(card_map.values())
    
    def validate_card_list(self, card_list_text):
        """Validate card list format and return any issues"""
        lines = card_list_text.strip().split('\n')
        issues = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            
            if not self._parse_line(line):
                issues.append(f"Line {i}: Could not parse '{line}'")
        
        return issues
