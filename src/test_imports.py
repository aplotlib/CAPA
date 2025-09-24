#!/usr/bin/env python3
"""Test script to debug import issues"""

import sys
import os

# Add the project root to the Python path to allow src imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("Python version:", sys.version)
print("Current directory:", os.getcwd())
print("\nChecking src directory...")

# Check if src directory exists
if os.path.exists('src'):
    print("✓ src directory exists")
    print("Files in src:", os.listdir('src'))
else:
    print("✗ src directory not found")

# Try importing each module
print("\n" + "="*50)
print("Testing imports...")
print("="*50)

# Test parsers
try:
    from src.parsers import AIFileParser
    print("✓ Successfully imported AIFileParser from parsers.py")
except Exception as e:
    print(f"✗ Failed to import from parsers.py: {e}")

# Test data_processing
try:
    from src.data_processing import DataProcessor
    print("✓ Successfully imported DataProcessor from data_processing.py")
except Exception as e:
    print(f"✗ Failed to import from data_processing.py: {e}")

# Test analysis
try:
    from src.analysis import run_full_analysis, MetricsCalculator
    print("✓ Successfully imported from analysis.py")
except Exception as e:
    print(f"✗ Failed to import from analysis.py: {e}")

# Test compliance
try:
    from src.compliance import validate_capa_data
    print("✓ Successfully imported validate_capa_data from compliance.py")
except Exception as e:
    print(f"✗ Failed to import from compliance.py: {e}")

# Test document_generator
try:
    from src.document_generator import CapaDocumentGenerator
    print("✓ Successfully imported from document_generator.py")
except Exception as e:
    print(f"✗ Failed to import from document_generator.py: {e}")

# Test the DataProcessor class specifically
print("\n" + "="*50)
print("Testing DataProcessor class instantiation...")
print("="*50)

try:
    from src.data_processing import DataProcessor
    print("✓ Module imported successfully")
    # Try to instantiate
    processor = DataProcessor(openai_api_key="dummy_key_for_test")
    print("✓ DataProcessor instantiated successfully")
except Exception as e:
    print(f"✗ Error testing DataProcessor: {e}")
    import traceback
    traceback.print_exc()

print("\nDiagnostics complete.")
