import pytest
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gai.logger import GaiLogger, logger

def test_logger_singleton():
    """Test that logger is a singleton."""
    logger1 = GaiLogger()
    logger2 = GaiLogger()
    assert logger1 is logger2

def test_development_mode_detection():
    """Test development mode detection."""
    # Should detect development mode when installed with pip install -e .
    is_dev = logger.is_development_mode()
    assert isinstance(is_dev, bool)

def test_logging_levels():
    """Test that all logging levels work."""
    logger.debug("Test debug message")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    # If we get here without exceptions, logging is working

def test_debug_enabled_check():
    """Test debug enabled check."""
    debug_enabled = logger.is_debug_enabled()
    assert isinstance(debug_enabled, bool)

class TestEnvironmentOverride:
    """Test environment variable override."""
    
    def test_gai_debug_override(self):
        """Test that GAI_DEBUG=1 enables debug mode."""
        # Save original value
        original_debug = os.environ.get('GAI_DEBUG')
        
        try:
            # Set environment variable
            os.environ['GAI_DEBUG'] = '1'
            
            # Create new logger instance
            test_logger = GaiLogger()
            
            # Should be in debug mode
            assert test_logger.is_debug_enabled()
        finally:
            # Clean up
            if original_debug is not None:
                os.environ['GAI_DEBUG'] = original_debug
            elif 'GAI_DEBUG' in os.environ:
                del os.environ['GAI_DEBUG']
    
    def test_gai_force_production_override(self):
        """Test that GAI_FORCE_PRODUCTION=1 forces production mode."""
        # Save original values
        original_production = os.environ.get('GAI_FORCE_PRODUCTION')
        
        try:
            # Set environment variable
            os.environ['GAI_FORCE_PRODUCTION'] = '1'
            
            # Reset singleton for clean test
            GaiLogger._instance = None
            
            # Create new logger instance
            test_logger = GaiLogger()
            
            # Should be in production mode
            assert not test_logger.is_development_mode()
            assert not test_logger.is_debug_enabled()
        finally:
            # Clean up
            if original_production is not None:
                os.environ['GAI_FORCE_PRODUCTION'] = original_production
            elif 'GAI_FORCE_PRODUCTION' in os.environ:
                del os.environ['GAI_FORCE_PRODUCTION']
            
            # Reset singleton for other tests
            GaiLogger._instance = None
