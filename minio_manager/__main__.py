import sys
import time

from minio_manager.app import main
from minio_manager.classes.logging_config import logger
from minio_manager.utilities import get_error_count, start_time

try:
    main()
finally:
    end_time = time.time()
    logger.info(f"Execution took {end_time - start_time:.2f} seconds.")

    error_count = get_error_count()
    if error_count > 0:
        noun = "error" if error_count == 1 else "errors"
        logger.error(f"Encountered {error_count} {noun} during execution!")
        sys.exit(1)
