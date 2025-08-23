import os
import glob
import time
import threading
import shutil
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s %(asctime)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('File Cleaner')

class FileCleaner:

    """
    A class to automatically delete files in the background based on
    specified glob patterns and age.
    """

    def __init__(self, patterns, max_age_seconds=3600, interval_seconds=3600):
        """
        Initializes the FileCleaner and starts its background cleanup thread.

        Args:
            patterns (list): A list of glob patterns to search for files.
            max_age_seconds (int): The maximum age of a file in seconds.
                                   Files older than this will be deleted.
                                   Defaults to 3600 (1 hour).
            interval_seconds (int): How often, in seconds, the cleanup
                                    task should run. Defaults to 3600 (1 hour).
        """
            
        self.patterns = patterns
        self.max_age_seconds = max_age_seconds
        self.interval_seconds = interval_seconds
        self.script_dir = Path(__file__).parent.resolve()

        self._stop_event = threading.Event()
        
        self.thread = threading.Thread(target=self._run_cleanup_loop, daemon=True)
        self.thread.start()
        logger.info(f"--- Background file cleaner started. Will run every {self.interval_seconds} seconds. ---")

    def _run_cleanup_loop(self):
        """The main loop for the background thread."""
        while not self._stop_event.wait(self.interval_seconds):
            logger.info("\n--- [Auto-Cleanup] Running scheduled job... ---")
            self.cleanup_files()

    def cleanup_files(self):
        """
        Iterates through glob patterns, deleting files and directories older
        than the specified max_age_seconds.
        """
        current_time = time.time()
        total_deleted_items = 0

        patterns_to_check = [
            "../../tmp/*"
        ]

        for pattern in patterns_to_check:
            full_pattern_path = self.script_dir / pattern
            # Note: not recursive
            found_paths = glob.glob(str(full_pattern_path))

            for path_str in found_paths:
                path = Path(path_str)
                try:
                    mod_time = path.stat().st_mtime
                    age_seconds = current_time - mod_time

                    if age_seconds > self.max_age_seconds:
                        if path.is_file():
                            logger.info(f"  DELETING FILE: {path.name} (Age: {age_seconds:.0f}s)")
                            os.remove(path)
                            total_deleted_items += 1
                        elif path.is_dir():
                            logger.info(f"  DELETING DIRECTORY: {path.name} (Age: {age_seconds:.0f}s)")
                            shutil.rmtree(path)
                            total_deleted_items += 1

                except FileNotFoundError:
                    logger.info(f"  ERROR: Path not found during check: {path.name}")
                except Exception as e:
                    logger.info(f"  ERROR: Could not process {path.name}: {e}")
        
        logger.info(f"--- [Auto-Cleanup] Job finished. Total items deleted: {total_deleted_items} ---")


    def stop(self):
        """Stops the background cleanup thread gracefully."""
        logger.info("--- Stopping background file cleaner... ---")
        self._stop_event.set()