import os
import sys
import time
from pathlib import Path


def get_template_name(pathfile):
    return Path(os.path.relpath(pathfile)).as_posix()


def progress_bar(
    iterable, prefix='', suffix='', decimals=1, length=100, fill='#', printEnd="\r",
    enabled=None, stream=None,
):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    total = len(iterable)
    stream = stream or sys.stderr
    if enabled is None:
        enabled = stream.isatty()

    if total == 0 or not enabled:
        for item in iterable:
            yield item
        return

    # Progress Bar Printing Function
    def print_progress_bar(iteration):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)
        current_time = time.strftime('%Y-%m-%d %H:%M:%S')
        print(
            f'\r{current_time} INFO {prefix} |{bar}| {percent}% {suffix}',
            end=printEnd,
            file=stream,
        )

    # Initial Call
    print_progress_bar(0)
    # Update Progress Bar
    for i, item in enumerate(iterable):
        yield item
        print_progress_bar(i + 1)
    # Print New Line on Complete
    print(file=stream)
