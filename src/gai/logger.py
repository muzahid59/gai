import logging
import os
import sys
from pathlib import Path
from typing import Optional
import pkg_resources


class GaiLogger:
    """Wrapper over Python's logging library for gai-commit."""
    
    _instance: Optional['GaiLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._logger is None:
            self._setup_logger()
    
    def _is_development_mode(self) -> bool:
        """Check if package is installed in development mode."""
        try:
            # Method 1: Check if installed as editable
            dist = pkg_resources.get_distribution('gai-commit')
            if hasattr(dist, 'location') and dist.location:
                # In development mode, location often contains 'src' or ends with the project directory
                location_path = Path(dist.location)
                
                # Check if we're in editable install (common patterns)
                is_editable = (
                    str(location_path).endswith('.egg-link') or
                    'src' in str(location_path) or
                    (location_path / 'src').exists() or
                    (location_path / 'setup.py').exists() or
                    (location_path / 'pyproject.toml').exists()
                )
                
                if is_editable:
                    return True
                    
                # Check if we have editable project location (pip install -e .)
                try:
                    # This is a more reliable way to check for editable installs
                    import subprocess
                    result = subprocess.run(['pip', 'show', 'gai-commit'], 
                                          capture_output=True, text=True)
                    if 'Editable project location:' in result.stdout:
                        return True
                except:
                    pass
                    
        except (pkg_resources.DistributionNotFound, Exception):
            pass
        
        # Method 2: Check if GAI_DEBUG environment variable is set
        env_debug = os.getenv('GAI_DEBUG', '').lower() in ('1', 'true', 'yes', 'on')
        
        # Method 3: Check if we're running from source directory
        try:
            current_file = Path(__file__).resolve()
            # If this file is in a 'src' directory, likely development
            is_src_install = 'src' in str(current_file)
            return env_debug or is_src_install
        except Exception:
            return env_debug
    
    def _setup_logger(self):
        """Setup logger configuration."""
        self._logger = logging.getLogger('gai-commit')
        
        # Clear any existing handlers
        self._logger.handlers.clear()
        
        # Determine if we're in development mode
        is_dev_mode = self._is_development_mode()
        
        # Set log level based on mode
        if is_dev_mode:
            log_level = logging.DEBUG
            self._logger.setLevel(log_level)
        else:
            # In production, only show warnings and errors by default
            log_level = logging.WARNING
            self._logger.setLevel(log_level)
        
        # Create formatters
        if is_dev_mode:
            # Detailed format for development
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
            )
            console_formatter = logging.Formatter(
                '🔧 %(levelname)s: %(message)s'
            )
        else:
            # Simple format for production
            formatter = logging.Formatter('%(levelname)s: %(message)s')
            console_formatter = formatter
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        self._logger.addHandler(console_handler)
        
        # File handler (only in development mode)
        if is_dev_mode:
            log_dir = Path.home() / ".config" / "gai-commit"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "debug.log"
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
            
            self._logger.debug(f"Development mode detected. Debug logging enabled.")
            self._logger.debug(f"Log file: {log_file}")
        else:
            self._logger.warning("Production mode - only warnings and errors will be shown")
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        if self._logger:
            self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        if self._logger:
            self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        if self._logger:
            self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        if self._logger:
            self._logger.error(message, *args, **kwargs)
    
    def is_debug_enabled(self) -> bool:
        """Check if debug logging is enabled."""
        return self._logger and self._logger.isEnabledFor(logging.DEBUG)
    
    def is_development_mode(self) -> bool:
        """Public method to check if in development mode."""
        return self._is_development_mode()


# Global logger instance
logger = GaiLogger()
