# -*- coding: utf-8 -*-
import sys
import re


class Logger(object):
    """
    Terminal logger with color-support
    """
    _is_tty = sys.stdout.isatty()
    _colors = {'reset': 0, 'black': 30, 'white': 37,
               'cyan': 36, 'magenta': 35, 'blue': 34,
               'yellow': 33, 'green': 32, 'red': 31}

    def echo(self, *args):
        """
        Prints text to terminal with color codes
        Example:
          log.echo('[green]hey [boldred]there!')

        :param args: Multiple string messages
        """
        for arg in args:
            msg = re.sub(r'\[(bold)?([a-z]+)\]', self._colorize, arg)
            print(''.join([msg, '\x1b[0m']))

    def _colorize(self, match):
        if not self._is_tty:
            return ''
        attr = ['1' if match.group(1) == 'bold' else '0']
        attr.append(str(self._colors[match.group(2)]))
        return '\x1b[{}m'.format(';'.join(attr))
