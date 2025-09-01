#!/usr/bin/env python3
"""
Test script to demonstrate production mode behavior.
Run this after installing the package in production mode to see the difference.
"""

import os
import sys

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from gai.logger import logger

def test_production_mode():
    """Test logging behavior in production mode."""
    print("=== Production Mode Test ===")
    print(f"Development mode: {logger.is_development_mode()}")
    print(f"Debug enabled: {logger.is_debug_enabled()}")
    print()
    
    print("Testing all log levels:")
    logger.debug("This is a debug message")
    logger.info("This is an info message") 
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    print()
    
    print("Note: In production mode, only ERROR messages are shown.")
    print("Debug messages are completely suppressed.")

if __name__ == "__main__":
    test_production_mode()
