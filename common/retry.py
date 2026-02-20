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
        except Exception as e:
            # TODO: 'func' has to be replaced with vendor ID or something
            logging.error(
                f'{e}: {func} raised an exception on attempt {attempt}.'
            )
            if attempt == attempts - 1:
                raise
            time.sleep(
                2 ** attempt
            )
    return None
