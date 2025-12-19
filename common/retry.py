import time
import logging


def with_retry(
    func,
    attempts=3, ):
    for attempt in range(
        attempts
    ):
        try:
            return func()
        except Exception:
            logging.error(
                f'Failed to fetch content for {func} on attempt {attempt}.'
            )
            if attempt == attempts - 1:
                raise
            time.sleep(
                2 ** attempt
            )
