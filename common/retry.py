import time
import logging


# TODO: The current exception catching is prone to ValueError and AttributeError exceptions, among others.
# TODO: That could be fixed by specifying the exception types in the function call
def with_retry(
    func,
    exception_types=(Exception,),
    label=None
    ):
    attempts = 3

    display_name = label or repr(func)

    for attempt in range(
        attempts
    ):
        try:
            return func()
        except Exception as e:
            logging.error(
                f'{e}: {display_name} raised an exception on attempt {attempt}.'
            )
            if attempt == attempts - 1:
                raise
            time.sleep(
                2 ** attempt
            )
    return None
