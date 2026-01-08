"""
Enhanced AI Analysis Module - Dual AI with Speed Optimization
Version 15.0 - B2B Optimized

Key Features:
- Dual AI support with intelligent routing
- Batch processing for speed
- Claude Haiku for fast categorization/summarization
- GPT-3.5 for complex cases
- Parallel API calls
- Dynamic Worker Scaling
"""

import logging
import os
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from enum import Enum
import time
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe imports
def safe_import(module_name):
    try:
        return __import__(module_name), True
    except ImportError:
        logger.warning(f"Module {module_name} not available")
        return None, False

# Check for dependencies
requests, has_requests = safe_import('requests')

# API Configuration
API_TIMEOUT = 45  # Increased for longer summaries
MAX_RETRIES = 2

# Token configurations by mode
TOKEN_LIMITS = {
    'standard': 100,     
    'enhanced': 200,     
    'extreme': 400,      
    'chat': 500,
    'summary': 300       # Increased for detailed reasons
}

# Model configurations
MODELS = {
    'openai': {
        'standard': 'gpt-3.5-turbo',
        'enhanced': 'gpt-3.5-turbo',
        'extreme': 'gpt-4',
        'chat': 'gpt-3.5-turbo',
        'summary': 'gpt-3.5-turbo'
    },
    'claude': {
        'standard': 'claude-3-haiku-20240307',
        'enhanced': 'claude-3-haiku-20240307',
        'extreme': 'claude-3-sonnet-20240229',
        'chat': 'claude-3-haiku-20240307',
        'summary': 'claude-3-haiku-20240307'
    }
}

# Updated pricing per 1K tokens
PRICING = {
    # OpenAI
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
    'gpt-4': {'input': 0.03, 'output': 0.06},
    'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
    # Claude (Anthropic)
    'claude-3-haiku-20240307': {'input': 0.00025, 'output': 0.00125},
    'claude-3-sonnet-20240229': {'input': 0.003, 'output': 0.015},
    'claude-3-opus-20240229': {'input': 0.015, 'output': 0.075}
}

# Medical Device Return Categories
MEDICAL_DEVICE_CATEGORIES = [
    'Size/Fit Issues',
    'Comfort Issues',
    'Product Defects/Quality',
    'Performance/Effectiveness',
    'Stability/Positioning Issues',
    'Equipment Compatibility',
    'Design/Material Issues',
    'Wrong Product/Misunderstanding',
    'Missing Components',
    'Customer Error/Changed Mind',
    'Shipping/Fulfillment Issues',
    'Assembly/Usage Difficulty',
    'Medical/Health Concerns',
    'Price/Value',
    'Other/Miscellaneous'
]

# FBA reason code mapping
FBA_REASON_MAP = {
    'NOT_COMPATIBLE': 'Equipment Compatibility',
    'DAMAGED_BY_FC': 'Product Defects/Quality',
    'DAMAGED_BY_CARRIER': 'Shipping/Fulfillment Issues',
    'DEFECTIVE': 'Product Defects/Quality',
    'NOT_AS_DESCRIBED': 'Wrong Product/Misunderstanding',
    'WRONG_ITEM': 'Wrong Product/Misunderstanding',
    'MISSING_PARTS': 'Missing Components',
    'QUALITY_NOT_ADEQUATE': 'Product Defects/Quality',
    'UNWANTED_ITEM': 'Customer Error/Changed Mind',
    'UNAUTHORIZED_PURCHASE': 'Customer Error/Changed Mind',
    'CUSTOMER_DAMAGED': 'Customer Error/Changed Mind',
    'SWITCHEROO': 'Wrong Product/Misunderstanding',
    'EXPIRED_ITEM': 'Product Defects/Quality',
    'DAMAGED_GLASS_VIAL': 'Product Defects/Quality',
    'DIFFERENT_PRODUCT': 'Wrong Product/Misunderstanding',
    'MISSING_ITEM': 'Missing Components',
    'NOT_DELIVERED': 'Shipping/Fulfillment Issues',
    'ORDERED_WRONG_ITEM': 'Customer Error/Changed Mind',
    'UNNEEDED_ITEM': 'Customer Error/Changed Mind',
    'BAD_GIFT': 'Customer Error/Changed Mind',
    'INACCURATE_WEBSITE_DESCRIPTION': 'Wrong Product/Misunderstanding',
    'BETTER_PRICE_AVAILABLE': 'Price/Value',
    'DOES_NOT_FIT': 'Size/Fit Issues',
    'NOT_COMPATIBLE_WITH_DEVICE': 'Equipment Compatibility',
    'UNSATISFACTORY_PRODUCT': 'Performance/Effectiveness',
    'ARRIVED_LATE': 'Shipping/Fulfillment Issues',
    'TOO_SMALL': 'Size/Fit Issues',
    'TOO_LARGE': 'Size/Fit Issues',
    'UNCOMFORTABLE': 'Comfort Issues',
    'DIFFICULT_TO_USE': 'Assembly/Usage Difficulty',
    'DAMAGED': 'Product Defects/Quality',
    'BROKEN': 'Product Defects/Quality',
    'POOR_QUALITY': 'Product Defects/Quality',
    'NOT_WORKING': 'Product Defects/Quality',
    'DOESNT_WORK': 'Product Defects/Quality'
}

# Quick categorization patterns for speed
QUICK_PATTERNS = {
    'Size/Fit Issues': [
        r'too (small|large|big|tight|loose)', r'doesn[\']?t fit', r'wrong size',
        r'size issue', r'(small|large)r than expected', r'fit issue'
    ],
    'Product Defects/Quality': [
        r'defect', r'broken', r'damaged', r'poor quality', r'doesn[\']?t work',
        r'stopped working', r'malfunction', r'fell apart', r'ripped', r'torn'
    ],
    'Wrong Product/Misunderstanding': [
        r'wrong (item|product)', r'not as described', r'different than',
        r'thought it was', r'expected', r'not what I ordered'
    ],
    'Customer Error/Changed Mind': [
        r'changed mind', r'don[\']?t need', r'ordered by mistake',
        r'accidentally', r'no longer need', r'bought wrong'
    ],
    'Comfort Issues': [
        r'uncomfort', r'hurts', r'painful', r'too (hard|soft|firm)',
        r'causes pain', r'irritat'
    ],
    'Equipment Compatibility': [
        r'doesn[\']?t fit (my|the)', r'not compatible', r'incompatible',
        r'doesn[\']?t work with', r'won[\']?t fit'
    ]
}

# Compile patterns for speed
COMPILED_PATTERNS = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in QUICK_PATTERNS.items()
}

class AIProvider(Enum):
    OPENAI = "openai"
    CLAUDE = "claude"
    BOTH = "both"
    FASTEST = "fastest"

@dataclass
class CostEstimate:
    """Cost estimation data class"""
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    
    def to_dict(self):
        return {
            'provider': self.provider,
            'model': self.model,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'input_cost': self.input_cost,
            'output_cost': self.output_cost,
            'total_cost': self.total_cost
        }

def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation)"""
    return max(len(text) // 4, len(text.split()) * 4 // 3)

def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> CostEstimate:
    """Calculate cost for API usage"""
    if model not in PRICING:
        logger.warning(f"Model {model} not in pricing table")
        return CostEstimate("unknown", model, input_tokens, output_tokens, 0, 0, 0)
    
    pricing = PRICING[model]
    input_cost = (input_tokens / 1000) * pricing['input']
    output_cost = (output_tokens / 1000) * pricing['output']
    total_cost = input_cost + output_cost
    
    provider = 'openai' if 'gpt' in model else 'claude'
    
    return CostEstimate(
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost
    )

def quick_categorize(complaint: str, fba_reason: str = None) -> Optional[str]:
    """Quick pattern-based categorization for speed"""
    if not complaint:
        return None
    
    # Check FBA reason first
    if fba_reason and fba_reason in FBA_REASON_MAP:
        return FBA_REASON_MAP[fba_reason]
    
    complaint_lower = complaint.lower()
    
    # Check compiled patterns
    for category, patterns in COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(complaint_lower):
                return category
    
    return None

def detect_severity(complaint: str, category: str) -> str:
    """Detect severity level of complaint"""
    complaint_lower = complaint.lower()
    
    # Critical keywords
    critical_keywords = ['injury', 'injured', 'hospital', 'emergency', 'dangerous', 'unsafe', 'hazard']
    if any(keyword in complaint_lower for keyword in critical_keywords):
        return 'critical'
    
    if category == 'Medical/Health Concerns':
        return 'critical'
    
    # Major keywords
    major_keywords = ['defective', 'broken', 'malfunction', 'unusable', 'failed', 'stopped working']
    if any(keyword in complaint_lower for keyword in major_keywords):
        return 'major'
    
    if category in ['Product Defects/Quality', 'Performance/Effectiveness']:
        return 'major'
    
    return 'minor'

class CostTracker:
    """Track API costs across sessions"""
    
    def __init__(self):
        self.session_costs = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
        self.api_calls = 0
        self.start_time = datetime.now()
        self.quick_categorizations = 0
        self.ai_categorizations = 0
    
    def add_cost(self, cost_estimate: CostEstimate):
        """Add cost to tracking"""
        self.session_costs.append(cost_estimate)
        self.total_input_tokens += cost_estimate.input_tokens
        self.total_output_tokens += cost_estimate.output_tokens
        self.total_cost += cost_estimate.total_cost
        self.api_calls += 1
    
    def add_quick_categorization(self):
        """Track quick categorization"""
        self.quick_categorizations += 1
    
    def add_ai_categorization(self):
        """Track AI categorization"""
        self.ai_categorizations += 1
    
    def get_summary(self) -> Dict[str, Any]:
        """Get cost summary"""
        duration = (datetime.now() - self.start_time).total_seconds() / 60
        
        return {
            'total_cost': round(self.total_cost, 4),
            'api_calls': self.api_calls,
            'total_tokens': self.total_input_tokens + self.total_output_tokens,
            'quick_categorizations': self.quick_categorizations,
            'ai_categorizations': self.ai_categorizations,
            'speed_improvement': f"{self.quick_categorizations / max(1, self.quick_categorizations + self.ai_categorizations) * 100:.1f}%",
            'average_cost_per_call': round(self.total_cost / max(1, self.api_calls), 4),
            'duration_minutes': round(duration, 1),
            'breakdown_by_provider': self._get_provider_breakdown()
        }
    
    def _get_provider_breakdown(self) -> Dict[str, Dict]:
        """Get cost breakdown by provider"""
        breakdown = {'openai': {'calls': 0, 'cost': 0}, 'claude': {'calls': 0, 'cost': 0}}
        
        for cost in self.session_costs:
            provider = cost.provider
            if provider in breakdown:
                breakdown[provider]['calls'] += 1
                breakdown[provider]['cost'] += cost.total_cost
        
        return breakdown

class EnhancedAIAnalyzer:
    """Main AI analyzer with dual AI support and speed optimization"""
    
    def __init__(self, provider: AIProvider = AIProvider.FASTEST, max_workers: int = 5):
        self.provider = provider
        self.max_workers = max_workers
        self.openai_key = self._get_api_key('openai')
        self.claude_key = self._get_api_key('claude')
        
        # Initialize tracking
        self.cost_tracker = CostTracker()
        
        # Initialize API availability
        self.openai_configured = bool(self.openai_key and has_requests)
        self.claude_configured = bool(self.claude_key and has_requests)
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Session for connection pooling
        self.session = None
        if has_requests:
            self.session = requests.Session()
        
        logger.info(f"AI Analyzer initialized - OpenAI: {self.openai_configured}, Claude: {self.claude_configured}, Mode: {provider.value}, Workers: {self.max_workers}")
    
    def _get_api_key(self, provider: str) -> Optional[str]:
        """Get API key from multiple sources"""
        # Try Streamlit secrets first
        try:
            import streamlit as st
            if hasattr(st, 'secrets'):
                if provider == 'openai':
                    for key_name in ["OPENAI_API_KEY", "openai_api_key", "openai"]:
                        if key_name in st.secrets:
                            key_value = str(st.secrets[key_name]).strip()
                            if key_value and key_value.startswith('sk-'):
                                logger.info(f"Found {provider} key in Streamlit secrets")
                                return key_value
                elif provider == 'claude':
                    for key_name in ["ANTHROPIC_API_KEY", "anthropic_api_key", "claude_api_key", "claude"]:
                        if key_name in st.secrets:
                            key_value = str(st.secrets[key_name]).strip()
                            if key_value:
                                logger.info(f"Found {provider} key in Streamlit secrets")
                                return key_value
        except Exception as e:
            logger.debug(f"Streamlit secrets not available: {e}")
        
        # Try environment variables
        env_vars = {
            'openai': ["OPENAI_API_KEY", "OPENAI_API"],
            'claude': ["ANTHROPIC_API_KEY", "CLAUDE_API_KEY"]
        }
        
        for env_name in env_vars.get(provider, []):
            api_key = os.environ.get(env_name, '').strip()
            if api_key:
                logger.info(f"Found {provider} key in environment")
                return api_key
        
        logger.warning(f"No {provider} API key found")
        return None
    
    def get_api_status(self) -> Dict[str, Any]:
        """Get API status with cost summary"""
        status = {
            'available': self.openai_configured or self.claude_configured,
            'openai_configured': self.openai_configured,
            'claude_configured': self.claude_configured,
            'dual_ai_available': self.openai_configured and self.claude_configured,
            'provider': self.provider.value,
            'cost_summary': self.cost_tracker.get_summary(),
            'message': ''
        }
        
        if status['dual_ai_available']:
            status['message'] = 'Both OpenAI and Claude APIs are configured'
        elif self.openai_configured:
            status['message'] = 'OpenAI API is configured (Claude not available)'
        elif self.claude_configured:
            status['message'] = 'Claude API is configured (OpenAI not available)'
        else:
            status['message'] = 'No APIs configured'
        
        return status
    
    def _call_openai(self, prompt: str, system_prompt: str, mode: str = 'standard') -> Tuple[Optional[str], Optional[CostEstimate]]:
        """Call OpenAI API with cost tracking"""
        if not self.openai_configured:
            return None, None
        
        model = MODELS['openai'].get(mode, MODELS['openai']['standard'])
        max_tokens = TOKEN_LIMITS.get(mode, TOKEN_LIMITS['standard'])
        
        # Estimate input tokens
        input_tokens = estimate_tokens(system_prompt + prompt)
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.openai_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = (self.session or requests).post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=API_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"].strip()
                    
                    # Get actual token usage
                    usage = result.get("usage", {})
                    actual_input = usage.get("prompt_tokens", input_tokens)
                    actual_output = usage.get("completion_tokens", len(content.split()))
                    
                    # Calculate cost
                    cost = calculate_cost(model, actual_input, actual_output)
                    self.cost_tracker.add_cost(cost)
                    
                    return content, cost
                
                elif response.status_code == 429:
                    wait_time = min(2 ** attempt, 10)
                    logger.warning(f"OpenAI rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                else:
                    logger.error(f"OpenAI API error {response.status_code}")
                    return None, None
                    
            except Exception as e:
                logger.error(f"OpenAI call error: {e}")
                if attempt == MAX_RETRIES - 1:
                    return None, None
                time.sleep(1)
        
        return None, None
    
    def _call_claude(self, prompt: str, system_prompt: str, mode: str = 'standard') -> Tuple[Optional[str], Optional[CostEstimate]]:
        """Call Claude API with cost tracking"""
        if not self.claude_configured:
            return None, None
        
        model = MODELS['claude'].get(mode, MODELS['claude']['standard'])
        max_tokens = TOKEN_LIMITS.get(mode, TOKEN_LIMITS['standard'])
        
        # Estimate input tokens
        input_tokens = estimate_tokens(system_prompt + prompt)
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.claude_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = (self.session or requests).post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload,
                    timeout=API_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result["content"][0]["text"].strip()
                    
                    # Get actual token usage
                    usage = result.get("usage", {})
                    actual_input = usage.get("input_tokens", input_tokens)
                    actual_output = usage.get("output_tokens", len(content.split()))
                    
                    # Calculate cost
                    cost = calculate_cost(model, actual_input, actual_output)
                    self.cost_tracker.add_cost(cost)
                    
                    return content, cost
                
                elif response.status_code == 429:
                    wait_time = min(2 ** attempt, 10)
                    logger.warning(f"Claude rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                else:
                    logger.error(f"Claude API error {response.status_code}: {response.text}")
                    return None, None
                    
            except Exception as e:
                logger.error(f"Claude call error: {e}")
                if attempt == MAX_RETRIES - 1:
                    return None, None
                time.sleep(1)
        
        return None, None
    
    def summarize_batch(self, items: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Summarize a batch of tickets for B2B reports"""
        # Updated prompt: No word limit, focus on accuracy
        system_prompt = "You are a customer service analyst. Summarize the return/replacement reason. Provide an accurate, detailed description of the 'Why' (e.g., 'Product defective', 'Customer changed mind', 'Wrong item sent'). Do not arbitrarily limit length; use as many words as necessary to fully capture the issue."
        
        futures = []
        results = []
        
        for item in items:
            prompt = f"Subject: {item.get('subject', '')}\nDetails: {item.get('details', '')}\nSummary:"
            
            # Default to fastest or configured
            use_claude = self.claude_configured and (self.provider == AIProvider.CLAUDE or self.provider == AIProvider.FASTEST or self.provider == AIProvider.BOTH)
            
            if use_claude:
                future = self.executor.submit(self._call_claude, prompt, system_prompt, 'summary')
            elif self.openai_configured:
                future = self.executor.submit(self._call_openai, prompt, system_prompt, 'summary')
            else:
                future = None
                
            futures.append((future, item))
            
        # Collect results
        for future, item in futures:
            summary = "Summary Unavailable"
            if future:
                try:
                    resp, _ = future.result(timeout=API_TIMEOUT)
                    if resp:
                        summary = resp
                except Exception as e:
                    logger.error(f"Summary error: {e}")
            
            # Return new dict with summary
            result_item = item.copy()
            result_item['summary'] = summary
            results.append(result_item)
            
        return results

    def generate_text(self, prompt: str, system_prompt: str, mode: str = 'chat') -> Optional[str]:
        """Generate a single response for general analysis or chat use cases."""
        if self.provider == AIProvider.FASTEST:
            if self.claude_configured:
                response, _ = self._call_claude(prompt, system_prompt, mode)
                if response:
                    return response
            if self.openai_configured:
                response, _ = self._call_openai(prompt, system_prompt, mode)
                if response:
                    return response
            return None

        if self.provider == AIProvider.BOTH:
            openai_future = None
            claude_future = None

            if self.openai_configured:
                openai_future = self.executor.submit(
                    self._call_openai, prompt, system_prompt, mode
                )
            if self.claude_configured:
                claude_future = self.executor.submit(
                    self._call_claude, prompt, system_prompt, mode
                )

            openai_result = None
            claude_result = None

            if openai_future:
                try:
                    openai_response, _ = openai_future.result(timeout=API_TIMEOUT)
                    if openai_response:
                        openai_result = openai_response
                except Exception as e:
                    logger.error(f"OpenAI chat call failed: {e}")

            if claude_future:
                try:
                    claude_response, _ = claude_future.result(timeout=API_TIMEOUT)
                    if claude_response:
                        claude_result = claude_response
                except Exception as e:
                    logger.error(f"Claude chat call failed: {e}")

            if openai_result and claude_result:
                return max([openai_result, claude_result], key=len)
            return openai_result or claude_result

        if self.provider == AIProvider.OPENAI and self.openai_configured:
            response, _ = self._call_openai(prompt, system_prompt, mode)
            return response
        if self.provider == AIProvider.CLAUDE and self.claude_configured:
            response, _ = self._call_claude(prompt, system_prompt, mode)
            return response

        return None

    def categorize_return(self, complaint: str, fba_reason: str = None, mode: str = 'standard') -> Tuple[str, float, str, str]:
        """Categorize return with speed optimization"""
        if not complaint or not complaint.strip():
            return 'Other/Miscellaneous', 0.1, 'none', 'en'
        
        # Try quick categorization first
        quick_category = quick_categorize(complaint, fba_reason)
        if quick_category:
            self.cost_tracker.add_quick_categorization()
            severity = detect_severity(complaint, quick_category)
            return quick_category, 0.9, severity, 'en'
        
        # AI categorization
        self.cost_tracker.add_ai_categorization()
        
        # Build prompts
        system_prompt = """You are a medical device quality expert. Categorize this return into exactly one category from the provided list. Respond with ONLY the category name, nothing else."""
        
        categories_list = '\n'.join(f'- {cat}' for cat in MEDICAL_DEVICE_CATEGORIES)
        
        user_prompt = f"""Complaint: "{complaint}"

Categories:
{categories_list}

Category:"""
        
        # Choose provider based on mode
        if self.provider == AIProvider.FASTEST:
            # Use Claude Haiku for speed
            if self.claude_configured:
                response, _ = self._call_claude(user_prompt, system_prompt, 'standard')
                if response:
                    category = self._clean_category_response(response)
                    severity = detect_severity(complaint, category)
                    return category, 0.85, severity, 'en'
            # Fallback to OpenAI
            if self.openai_configured:
                response, _ = self._call_openai(user_prompt, system_prompt, 'standard')
                if response:
                    category = self._clean_category_response(response)
                    severity = detect_severity(complaint, category)
                    return category, 0.85, severity, 'en'
        
        elif self.provider == AIProvider.BOTH:
            # Parallel calls for consensus
            openai_future = None
            claude_future = None
            
            if self.openai_configured:
                openai_future = self.executor.submit(
                    self._call_openai, user_prompt, system_prompt, mode
                )
            
            if self.claude_configured:
                claude_future = self.executor.submit(
                    self._call_claude, user_prompt, system_prompt, mode
                )
            
            # Get results
            openai_result = None
            claude_result = None
            
            if openai_future:
                try:
                    openai_response, _ = openai_future.result(timeout=API_TIMEOUT)
                    if openai_response:
                        openai_result = self._clean_category_response(openai_response)
                except Exception as e:
                    logger.error(f"OpenAI parallel call failed: {e}")
            
            if claude_future:
                try:
                    claude_response, _ = claude_future.result(timeout=API_TIMEOUT)
                    if claude_response:
                        claude_result = self._clean_category_response(claude_response)
                except Exception as e:
                    logger.error(f"Claude parallel call failed: {e}")
            
            # Determine final category
            if openai_result and claude_result:
                if openai_result == claude_result:
                    category = openai_result
                    confidence = 0.95
                else:
                    # Prefer non-misc category
                    category = openai_result if openai_result != 'Other/Miscellaneous' else claude_result
                    confidence = 0.8
            elif openai_result:
                category = openai_result
                confidence = 0.85
            elif claude_result:
                category = claude_result
                confidence = 0.85
            else:
                category = 'Other/Miscellaneous'
                confidence = 0.3
            
            severity = detect_severity(complaint, category)
            return category, confidence, severity, 'en'
        
        else:
            # Single provider mode
            if self.provider == AIProvider.OPENAI and self.openai_configured:
                response, _ = self._call_openai(user_prompt, system_prompt, mode)
            elif self.provider == AIProvider.CLAUDE and self.claude_configured:
                response, _ = self._call_claude(user_prompt, system_prompt, mode)
            else:
                response = None
            
            if response:
                category = self._clean_category_response(response)
                severity = detect_severity(complaint, category)
                return category, 0.85, severity, 'en'
        
        # Final fallback
        return 'Other/Miscellaneous', 0.3, 'none', 'en'
    
    def categorize_batch(self, complaints: List[Dict[str, Any]], mode: str = 'standard') -> List[Dict[str, Any]]:
        """Categorize multiple complaints in parallel for speed"""
        results = []
        futures = []
        
        # Submit all tasks
        for item in complaints:
            future = self.executor.submit(
                self.categorize_return,
                item.get('complaint', ''),
                item.get('fba_reason'),
                mode
            )
            futures.append((future, item))
        
        # Collect results
        for future, item in futures:
            try:
                category, confidence, severity, language = future.result(timeout=API_TIMEOUT)
                result = item.copy()
                result.update({
                    'category': category,
                    'confidence': confidence,
                    'severity': severity,
                    'language': language
                })
                results.append(result)
            except Exception as e:
                logger.error(f"Batch categorization error: {e}")
                result = item.copy()
                result.update({
                    'category': 'Other/Miscellaneous',
                    'confidence': 0.1,
                    'severity': 'none',
                    'language': 'en'
                })
                results.append(result)
        
        return results
    
    def _clean_category_response(self, response: str) -> str:
        """Clean AI response to extract category"""
        response = response.strip().strip('"').strip("'").strip()
        
        # Remove common prefixes
        prefixes = ['Category:', 'The category is:', 'Answer:']
        for prefix in prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        # Try exact match first
        for valid_cat in MEDICAL_DEVICE_CATEGORIES:
            if response == valid_cat or response.lower() == valid_cat.lower():
                return valid_cat
        
        # Try partial match
        response_lower = response.lower()
        for valid_cat in MEDICAL_DEVICE_CATEGORIES:
            if valid_cat.lower() in response_lower:
                return valid_cat
        
        # Try keyword match
        for valid_cat in MEDICAL_DEVICE_CATEGORIES:
            cat_words = set(valid_cat.lower().split('/'))
            response_words = set(response_lower.split())
            if cat_words & response_words:
                return valid_cat
        
        return 'Other/Miscellaneous'
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get detailed cost summary"""
        return self.cost_tracker.get_summary()
    
    def estimate_remaining_cost(self, remaining_items: int) -> float:
        """Estimate cost for remaining items"""
        # Consider quick categorization rate
        summary = self.cost_tracker.get_summary()
        quick_rate = self.cost_tracker.quick_categorizations / max(1, 
            self.cost_tracker.quick_categorizations + self.cost_tracker.ai_categorizations)
        
        # Adjust estimate based on quick categorization rate
        ai_items = remaining_items * (1 - quick_rate)
        
        if self.cost_tracker.api_calls > 0:
            avg_cost = self.cost_tracker.total_cost / self.cost_tracker.api_calls
            return round(avg_cost * ai_items, 2)
        
        return 0.0
    
    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        if hasattr(self, 'session') and self.session:
            self.session.close()

# Helper functions for batch processing
def process_dataframe_in_batches(df, analyzer, batch_size=20):
    """Process dataframe in batches for speed"""
    total_rows = len(df)
    results = []
    
    for i in range(0, total_rows, batch_size):
        batch = df.iloc[i:i+batch_size]
        batch_data = []
        
        for idx, row in batch.iterrows():
            batch_data.append({
                'index': idx,
                'complaint': str(row.get('Complaint', '')),
                'fba_reason': str(row.get('FBA_Reason_Code', '')) if 'FBA_Reason_Code' in row else None
            })
        
        # Process batch
        batch_results = analyzer.categorize_batch(batch_data)
        results.extend(batch_results)
    
    return results

# Export all components
__all__ = [
    'EnhancedAIAnalyzer',
    'AIProvider',
    'MEDICAL_DEVICE_CATEGORIES',
    'FBA_REASON_MAP',
    'detect_severity',
    'CostEstimate',
    'CostTracker',
    'estimate_tokens',
    'calculate_cost',
    'process_dataframe_in_batches',
    'quick_categorize'
]
