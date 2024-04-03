import sys
import time

from minio_manager.app import main
from minio_manager.classes.logging_config import logger
from minio_manager.utilities import error_count, start_time

try:
    main()
finally:
    end_time = time.time()
    logger.info(f"Execution took {end_time - start_time:.2f} seconds.")

    if error_count > 0:
        logger.error(f"Encountered {error_count} errors.")
        sys.exit(1)
