# -*- coding: utf-8 -*-
import json
import os
import subprocess
from .logger import Logger

log = Logger()


class TmuxException(Exception):
    pass


class Tmux(object):
    """
    Tmux controller
    """
    def command(self, cmd, formats=None, many=False):
        """
        Send custom Tmux command and return rich information

        :param cmd:
        :param formats:
        :param many:
        :return:
        """
        cmd.insert(0, 'tmux')
        if formats:
            fmt = '{'
            for key in formats:
                fmt += ''.join(['"', key, '": ', '"#{', key, '}", '])
            fmt = fmt[0:-2] + '}'
            cmd.append('-F')
            cmd.append(fmt)

        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            stdout = process.stdout.read()
            process.stdout.close()
            stderr = process.stderr.read()
            process.stderr.close()
            if stdout:
                lines = ','.join(stdout.decode('utf_8').split('\n')) \
                    .rstrip(',')
                stdout = json.loads('[' + lines + ']' if many else lines)
            if stderr:
                stderr = stderr.decode('utf_8').strip()

            return stdout, stderr
        except ValueError:
            raise TmuxException('Unable to serialize Tmux\'s response, '
                                'please report bug.')
        except Exception:
            raise TmuxException('Unable to execute Tmux, aborting.')

    def within_session(self):
        """
        Returns true if current within a Tmux session
        """
        return os.environ.get('TMUX') != ''

    def has_session(self, session_name):
        """
        Returns true if specified session currently exists

        :param session_name: The session name to match
        """
        try:
            cmds = ['tmux', 'has-session', '-t', session_name]
            # Compatibility code, python 2.x doesn't have subprocess.DEVNULL
            with open(os.devnull, 'wb') as DEVNULL:
                code = subprocess.check_call(cmds, stderr=DEVNULL)
        except subprocess.CalledProcessError as e:
            code = e.returncode
        return code == 0

    def new_session(self, session_name, win_name=''):
        """
        Create a new Tmux session

        :param session_name: New session's name
        :param win_name: The window's name within the new session
        :return: (session, window, pane)
        """
        cmds = ['new-session', '-Pd', '-s', session_name]
        if win_name:
            cmds.extend(['-n', win_name])

        output, errors = self.command(
            cmds,
            ['session_id', 'session_name', 'session_windows',
             'window_id', 'window_index', 'pane_index', 'pane_id'])

        if errors:
            raise TmuxException(errors)
        session = {}
        window = {}
        pane = {}
        for k, v in output.items():
            short_name = k.split('_')[1]
            if k.startswith('window_'):
                window[short_name] = v
            elif k.startswith('pane_'):
                pane[short_name] = v
            else:
                session[short_name] = v

        return session, window, pane

    def new_window(self, session_name, win_name=''):
        """
        Create a new Tmux window

        :param session_name: Target session name
        :param win_name: The new window's name
        :return: (window, pane)
        """
        cmds = ['new-window', '-Pd', '-t', session_name]
        if win_name:
            cmds.extend(['-n', win_name])

        output, errors = self.command(
            cmds,
            ['window_id', 'window_name', 'window_panes', 'window_active',
             'window_index', 'window_layout', 'pane_index', 'pane_id'])

        if errors:
            raise Exception('Error creating window: {}'.format(errors))
        window = {}
        pane = {}
        for k, v in output.items():
            short_name = k.split('_')[1]
            if k.startswith('pane_'):
                pane[short_name] = v
            else:
                window[short_name] = v

        return window, pane

    def new_pane(self, session_name, window_id, pane_id):
        """
        Create a new Tmux pane

        :param session_name: Target session name
        :param window_id: Window to split from
        :param pane_id: Pane to split from
        :return: Pane information
        """
        output, errors = self.command(
            ['split-window', '-h', '-P', '-t',
             '{}:{}.{}'.format(session_name, window_id, str(pane_id))],
            ['pane_id', 'pane_index', 'pane_active', 'pane_current_path',
             'pane_start_command', 'pane_current_command', 'pane_title'])
        if errors:
            raise TmuxException(errors)
        pane = {}
        for k, v in output.items():
            short_name = k.split('_')[1]
            pane[short_name] = v
        return pane

    def kill_session(self, session_name):
        """
        Kill a specified Tmux session
        """
        return self.command(['kill-session', '-t', session_name])

    def set_layout(self, session_name, win_name, layout=None):
        """
        Sets a Tmux session's specific window to a different layout

        :param session_name: Target session name
        :param win_name: Target window name
        :param layout: The layout name (even-horizontal, even-vertical,
                                        main-horizontal, main-vertical, tiled)
        """
        return self.command([
            'select-layout', '-t',
            '{}:{}'.format(session_name, win_name), layout or 'tiled'
        ])

    def send_keys(self, session_name, win_name, pane_index, cmd, enter=True):
        """
        Sends a Tmux session custom keys

        :param session_name: Target session name
        :param win_name: Target window name
        :param pane_index: Target pane index
        :param cmd: The string to enter
        :param enter: Finish with a carriage-return?
        """
        if cmd:
            return self.command([
                'send-keys', '-Rt',
                '{}:{}.{}'.format(session_name, win_name, str(pane_index)),
                cmd, 'C-m' if enter else ''
            ])

    def attach(self, session_name):
        """
        Attach to an existing Tmux session

        :param session_name: Target session name
        """
        if session_name:
            cmd = 'switch-client' if self.within_session() \
                else 'attach-session'
            return self.command([cmd, '-t', session_name])

    def get_windows(self, session_name):
        """
        Retrieve information for all windows in a session

        :param session_name: Target session name
        """
        return self.command(
            ['list-windows', '-t', session_name],
            ['window_id', 'window_name', 'window_panes', 'window_active',
             'window_index', 'window_layout'],
            many=True)

    def get_panes(self, session_name, window_name):
        """
        Retrieve information for all panes in a window

        :param session_name: Target session name
        :param window_name: Target window name
        """
        return self.command(
            ['list-panes', '-t', ':'.join([session_name, window_name])],
            ['pane_id', 'pane_active', 'pane_index', 'pane_start_command',
             'pane_current_command', 'pane_current_path', 'pane_title'],
            many=True)
