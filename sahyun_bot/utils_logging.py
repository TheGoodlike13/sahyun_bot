import logging
import time


class FormatterUTC(logging.Formatter):
    converter = time.gmtime
