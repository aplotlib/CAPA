#!/usr/bin/env python3
"""Test script to debug import issues"""

import sys
import os

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
    from src.parsers import AIFileParser, parse_file
    print("✓ Successfully imported from parsers.py")
except Exception as e:
    print(f"✗ Failed to import from parsers.py: {e}")

# Test data_processing
try:
    from src.data_processing import DataProcessor, standardize_sales_data, standardize_returns_data
    print("✓ Successfully imported from data_processing.py")
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
    from src.compliance import validate_capa_data, generate_compliance_checklist, get_regulatory_guidelines
    print("✓ Successfully imported from compliance.py")
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
print("Testing DataProcessor class...")
print("="*50)

try:
    import src.data_processing as dp
    print("Module imported successfully")
    print(f"Module file: {dp.__file__ if hasattr(dp, '__file__') else 'Unknown'}")
    print(f"Module contents: {dir(dp)}")
    
    if hasattr(dp, 'DataProcessor'):
        print("✓ DataProcessor class found")
        # Try to instantiate
        processor = dp.DataProcessor()
        print("✓ DataProcessor instantiated successfully")
    else:
        print("✗ DataProcessor class not found in module")
        
except Exception as e:
    print(f"✗ Error testing DataProcessor: {e}")
    import traceback
    traceback.print_exc()

print("\nDiagnostics complete.")
