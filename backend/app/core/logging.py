import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    log_handler = logging.StreamHandler(sys.stdout)
    
    # JSON formatting for ELK/OpenShift ingestion
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        json_indent=None
    )
    log_handler.setFormatter(formatter)
    
    logger = logging.getLogger("enterprise_rag")
    logger.addHandler(log_handler)
    logger.setLevel(logging.INFO)
    
    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").handlers = [log_handler]
    logging.getLogger("uvicorn.error").handlers = [log_handler]
    
    return logger

logger = setup_logging()