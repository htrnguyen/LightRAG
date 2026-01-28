import logging
import logging.handlers
import sys
import os

# Try importing colorlog for colored output
try:
    import colorlog
    HAVE_COLORLOG = True
except ImportError:
    HAVE_COLORLOG = False

# Fallback ANSI codes
_ANSI_CODES = {
    'reset': '\033[0m',
    'bold': '\033[1m',
    'thin': '\033[2m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'white': '\033[37m',
    'bold_red': '\033[1;31m',
    'thin_white': '\033[2;37m',
}

def get_escape_code(name):
    """Get ANSI escape code, using colorlog if available, otherwise fallback."""
    if HAVE_COLORLOG:
        return colorlog.escape_codes.get(name, "")
    return _ANSI_CODES.get(name, "")

# ==========================================
# CUSTOM HANDLERS
# ==========================================
class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that gracefully handles closed streams during shutdown.

    This handler prevents "ValueError: I/O operation on closed file" errors
    that can occur when pytest or other test frameworks close stdout/stderr
    before Python's logging cleanup runs.
    """

    def flush(self):
        """Flush the stream, ignoring errors if the stream is closed."""
        try:
            super().flush()
        except (ValueError, OSError):
            # Stream is closed or otherwise unavailable, silently ignore
            pass

    def close(self):
        """Close the handler, ignoring errors if the stream is already closed."""
        try:
            super().close()
        except (ValueError, OSError):
            # Stream is closed or otherwise unavailable, silently ignore
            pass

# ==========================================
# CONFIGURATION CONSTANTS
# ==========================================
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
COL_WIDTH_LEVEL = 8
COL_WIDTH_SERVICE = 25
COL_WIDTH_LOCATION = 25

# Colors configuration (using colorlog scheme)
LOG_COLORS = {
    'DEBUG': 'thin_white',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
}

# Standard keys to ignore when checking for extra fields
STANDARD_LOG_RECORD_KEYS = {
    'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
    'funcName', 'levelname', 'levelno', 'lineno', 'message', 'module',
    'msecs', 'msg', 'name', 'pathname', 'process', 'processName',
    'relativeCreated', 'stack_info', 'thread', 'threadName', 'taskName'
}

class UnifiedFormatter(logging.Formatter):
    def __init__(self, use_color=True):
        super().__init__(fmt=None, datefmt=LOG_DATE_FORMAT)
        
        # Determine if we should use color
        if os.getenv('NO_COLOR'):
            self.use_color = False
        elif os.getenv('FORCE_COLOR') or os.getenv('CLICOLOR_FORCE'):
            self.use_color = True
        else:
            # Default logic: Use color if requested
            self.use_color = use_color

    def format(self, record):
        # 1. Timestamp
        asctime = self.formatTime(record, self.datefmt)
        
        # 2. Level
        levelname = record.levelname
        
        # 3. Service Name
        name = record.name
        if len(name) > COL_WIDTH_SERVICE:
            name = ".." + name[-(COL_WIDTH_SERVICE-2):]
        
        # 4. Location (file.py:line)
        filename = os.path.basename(record.pathname) if record.pathname else "unknown"
        location = f"{filename}:{record.lineno}"
        if len(location) > COL_WIDTH_LOCATION:
             location = location[:COL_WIDTH_LOCATION-2] + ".."

        # Handle colors
        if self.use_color:
            ts_color = get_escape_code('cyan')
            sep_color = get_escape_code('thin_white')
            svc_color = get_escape_code('magenta')
            loc_color = get_escape_code('blue')
            reset = get_escape_code('reset')
            
            # Level color
            log_color = LOG_COLORS.get(levelname, 'white')
            level_colored = get_escape_code(log_color) + f"{levelname:<{COL_WIDTH_LEVEL}}" + reset
            
            # Formatted parts
            asctime_str = f"{ts_color}{asctime}{reset}"
            sep = f"{sep_color} | {reset}"
            service_str = f"{svc_color}{name:<{COL_WIDTH_SERVICE}}{reset}"
            location_str = f"{loc_color}{location:<{COL_WIDTH_LOCATION}}{reset}"
        else:
            asctime_str = asctime
            sep = " | "
            level_colored = f"{levelname:<{COL_WIDTH_LEVEL}}"
            service_str = f"{name:<{COL_WIDTH_SERVICE}}"
            location_str = f"{location:<{COL_WIDTH_LOCATION}}"

        # 5. Message
        msg_raw = record.getMessage()
        msg_lines = msg_raw.splitlines()
        first_line = msg_lines[0] if msg_lines else ""
        
        # Construct Base Line
        base_line = f"{asctime_str}{sep}{level_colored}{sep}{service_str}{sep}{location_str}{sep}{first_line}"

        # 6. Extra Fields (Append to end of first line)
        extra_str = ""
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_RECORD_KEYS and not key.startswith('_'):
                if self.use_color:
                    extra_str += f"{sep}{get_escape_code('thin')}{key}={value}{reset}"
                else:
                    extra_str += f" | {key}={value}"
        
        final_log = base_line + extra_str

        # Add remaining message lines with proper indentation
        if len(msg_lines) > 1:
            indent_width = 19 + 3 + COL_WIDTH_LEVEL + 3 + COL_WIDTH_SERVICE + 3 + COL_WIDTH_LOCATION + 3
            indent_str = " " * indent_width
            for line in msg_lines[1:]:
                final_log += f"\n{indent_str}{line}"

        # 7. Exception handling (Custom multi-line)
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            
            # Construct standard multi-line indentation
            indent = " " * 19 
            sep_exc = " | "
            
            if self.use_color:
                err_tag = get_escape_code('red') + f"{'ERROR':<{COL_WIDTH_LEVEL}}" + get_escape_code('reset')
                trace_tag = get_escape_code('bold_red') + f"{'TRACE':<{COL_WIDTH_LEVEL}}" + get_escape_code('reset')
            else:
                err_tag = f"{'ERROR':<{COL_WIDTH_LEVEL}}"
                trace_tag = f"{'TRACE':<{COL_WIDTH_LEVEL}}"

            error_lines = []
            
            # Format exception values (possibly multi-line)
            exc_msg = str(exc_value) if exc_value else "Unknown Exception"
            for line in exc_msg.splitlines():
                if line.strip():
                    error_lines.append(f"\n{indent}{sep_exc}{err_tag}{sep_exc}{line}")
            
            # If we want trace (brief)
            import traceback
            summary = traceback.extract_tb(exc_traceback)
            if summary:
                # Show last 2 frames for context if available
                frames_to_show = summary[-2:] if len(summary) >= 2 else summary
                for frame in frames_to_show:
                    trace_msg = f"{frame.name} -> {os.path.basename(frame.filename)}:{frame.lineno}"
                    error_lines.append(f"\n{indent}{sep_exc}{trace_tag}{sep_exc}{trace_msg}")

            final_log += "".join(error_lines)

        return final_log

def setup_logging(log_level: str = "INFO"):
    """
    Setup unified logging for the entire application.
    Call this once at startup.
    """
    # 1. Get Root Logger
    root_logger = logging.getLogger()
    
    # 2. Clear existing handlers (to avoid duplicates)
    if root_logger.handlers:
        root_logger.handlers.clear()
        
    # 3. Set Level
    root_logger.setLevel(log_level)
    
    # 4. Create Console Handler with UnifiedFormatter
    console_handler = SafeStreamHandler(sys.stdout)
    formatter = UnifiedFormatter(use_color=True)
    console_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)
    
    # 5. Overwrite/Redirect Third-party Loggers
    # We want these to propagate to root so they use our formatter
    # And we want to disable their double-logging
    loggers_to_redirect = [
        "uvicorn", 
        "uvicorn.access", 
        "uvicorn.error",
        "fastapi", 
        "sqlalchemy.engine", 
        "sqlalchemy.pool"
    ]
    
    for name in loggers_to_redirect:
        logger = logging.getLogger(name)
        logger.handlers = []  # Remove their specific handlers
        logger.propagate = True # Allow bubbling up to root
        logger.setLevel(log_level) # Sync level

    # Special handling for uvicorn access to avoid double format
    # Uvicorn usually sets up its own handlers with its own formatters on startup
    # We might need to keep eye on it, but clearing handlers usually works.

def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance with valid configuration.
    Example: logger = get_logger(__name__)
    """
    if name is None:
        # Get the name of the calling module
        frame = sys._getframe(1)
        name = frame.f_globals.get('__name__', 'root')
    
    return logging.getLogger(name)
