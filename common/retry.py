import time
import logging


def with_retry(
    func,
    attempts: int = None,
    label=None, ):
    if attempts is None:
        attempts = 3

    display_name = label or repr(func)

    for attempt in range(
        attempts
    ):
        try:
            return func()
        except Exception as e:
            # TODO: 'func' has to be replaced with vendor ID or something
            logging.error(
                f'{e}: {display_name} raised an exception on attempt {attempt}.'
            )
            if attempt == attempts - 1:
                raise
            time.sleep(
                2 ** attempt
            )
    return None
