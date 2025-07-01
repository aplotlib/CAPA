# src/analysis.py

"""
Module for performing data analysis, including metric calculations, return
reason categorization, and quality insights generation.
"""

import pandas as pd
import re
from typing import Dict, List, Optional, Tuple

class ReturnReasonCategorizer:
    """
    Categorizes return reasons using a robust set of predefined patterns.
    """
    # Expanded and refined categories for better accuracy
    CATEGORIES = {
        'QUALITY_DEFECTS': {
            'patterns': [
                r'defective', r'broken', r'damaged', r'doesn\'?t?\s+work',
                r'poor\s+quality', r'fell?\s+apart', r'cheap', r'malfunction',
                r'not\s+working', r'stopped?\s+working', r'dead\s+on\s+arrival',
                r'doa', r'faulty', r'ripped', r'torn', r'hole'
            ],
            'keywords': ['defect', 'broken', 'damage', 'quality', 'malfunction', 'faulty', 'rip', 'tear']
        },
        'SIZE_FIT_ISSUES': {
            'patterns': [
                r'too\s+(small|large|big|tight|loose)', r'doesn\'?t?\s+fit',
                r'wrong\s+size', r'size\s+(issue|problem)',
                r'(small|large)r?\s+than\s+expected', r'runs?\s+(small|large|big)',
                r'fit\s+(issue|problem)', r'not\s+the\s+right\s+size'
            ],
            'keywords': ['size', 'fit', 'small', 'large', 'tight', 'loose', 'big']
        },
        'WRONG_PRODUCT_OR_DESCRIPTION': {
            'patterns': [
                r'wrong\s+(item|product|model|color)', r'not\s+as\s+described',
                r'incorrect\s+(item|product)', r'different\s+than\s+(pictured|described|ordered)',
                r'not\s+what\s+i\s+ordered', r'received?\s+(wrong|different)',
                r'misrepresented', r'missing\s+parts'
            ],
            'keywords': ['wrong', 'incorrect', 'different', 'not as described', 'misrepresent', 'missing']
        },
        'BUYER_REMORSE_OR_MISTAKE': {
            'patterns': [
                r'bought?\s+by\s+mistake', r'accidentally\s+ordered',
                r'ordered?\s+(wrong|incorrect)\s+item', r'no\s+longer\s+need',
                r'don\'?t?\s+need', r'changed?\s+my?\s+mind',
                r'found?\s+(better|cheaper|different)', r'duplicate\s+order'
            ],
            'keywords': ['mistake', 'accident', 'no longer', 'changed mind', 'duplicate']
        },
        'FUNCTIONALITY_OR_USABILITY': {
            'patterns': [
                r'not\s+comfortable', r'hard\s+to\s+use',
                r'difficult\s+to\s+(use|operate|handle)', r'unstable',
                r'complicated', r'confusing', r'uncomfortable', r'awkward',
                r'not\s+user\s+friendly', r'design\s+(flaw|issue|problem)'
            ],
            'keywords': ['uncomfortable', 'difficult', 'hard to use', 'unstable', 'design']
        },
        'COMPATIBILITY_ISSUES': {
            'patterns': [
                r'doesn\'?t?\s+fit\s+(my|the|our)?\s*(toilet|chair|walker|bed)',
                r'not\s+compatible', r'incompatible',
                r'won\'?t?\s+(fit|work)\s+with'
            ],
            'keywords': ['compatible', 'incompatible', 'fit with']
        }
    }

    def __init__(self):
        self.compiled_patterns = {
            category: [re.compile(p, re.IGNORECASE) for p in data['patterns']]
            for category, data in self.CATEGORIES.items()
        }

    def categorize_reason(self, reason: str, comment: str = "") -> Tuple[str, float]:
        """Categorizes a single return reason based on text analysis."""
        combined_text = f"{reason or ''} {comment or ''}".lower().strip()
        if not combined_text:
            return "UNCATEGORIZED",
