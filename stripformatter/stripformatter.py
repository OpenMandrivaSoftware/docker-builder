from logging import Formatter
import re

class StripFormatter(Formatter):
        def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

        def format(self, *args, **kwargs):
                fmt = super().format(*args, **kwargs)

                if 'dnf.conf' in fmt:
                  return '[SENSIBLE INFORMATION]'

                return fmt

        def formatTime(self, *args, **kwargs):
                return super().format(*args, **kwargs)

        def formatException(self, *args, **kwargs):
                return super().format(*args, **kwargs)

        def formatStack(self, *args, **kwargs):
                return super().format(*args, **kwargs)

