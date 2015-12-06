# -*- coding: utf-8 -*-
import sys
import os


class Workspace(object):
    _config = {}
    _tmux = None
    _venv = []
    _session = {}
    _windows = []

    def __init__(self, tmux):
        """
        :param tmux: Tmux class instance
        """
        self._tmux = tmux

    def set_config(self, config):
        self._config = config

        # Prepare a virtualenv source command, if any
        # The specified virtualenv path can be absolute or relative
        # to the workspace's root directory.
        root = self._config.get('dir')
        venv = self._config.get('venv')
        if venv:
            if root and not os.path.isabs(venv):
                venv = os.path.join(root, venv)
            self._venv = [
                ' source "{}"'.format(os.path.join(venv, 'bin/activate'))]

    def start(self):
        """
        Create Tmux windows from `windows` configuration in YML

        :return Collection of window information
        """
        root = self._config.get('dir')
        if root:
            if not os.path.isdir(root):
                raise WorkspaceException('Directory does not exist', root)
            os.chdir(root)
        for window in self._config.get('windows', []):
            # Normalize window schema definition, a window definition:
            #   - string - window name
            #   - key/value - window name / command
            #   - dictionary - { panes: [], layout: '', post_cmd: '' / [] }
            if isinstance(window, str):
                name = window
            else:
                name = next(iter(window.keys()))
                window = window[name] or {}

            if isinstance(window, str):
                panes = [window]
                window = {}
            else:
                panes = window.get('panes', [])

            # Normalize post commands, can be string or list
            post_cmds = window.get('post_cmd', [])
            post_cmds = [post_cmds] if isinstance(post_cmds, str) \
                else post_cmds

            # Create session, window, and panes
            # with a layout and post commands.
            self._windows.append(
                self.create_window(
                    name, panes, post_cmds, window.get('layout')))

        return self._windows

    def stop(self, name=None):
        """
        Kill a workspace session

        :param name:
        """
        self._tmux.kill_session(name or self._session['name'])

    def create_window(self, name, panes, post_cmds, layout=None):
        """
        Create Tmux window and panes from configuration

        :param name:
        :param panes:
        :param post_cmds:
        :param layout:
        :return
        """
        if len(self._windows) > 0:
            window, pane = self._tmux.new_window(self._session['name'], name)
        else:
            self._session, window, pane = \
                self._tmux.new_session(self._config.get('name'), name)
            if not self._session:
                print('Error creating session buddy.')
                sys.exit(1)

        session_name = self._session['name']
        window['panes'] = []
        for pane_schema in panes:
            if len(window['panes']) > 0:
                pane = self._tmux.new_pane(session_name, name, pane['index'])
            window['panes'].append(pane)

            # Run commands+post-commands, and activate virtualenv
            cmds = next(iter(pane_schema.values())) \
                if isinstance(pane_schema, dict) else [pane_schema]
            cmds = self._venv + cmds + post_cmds
            for cmd in cmds:
                self._tmux.send_keys(session_name, name, pane['index'], cmd)

        self._tmux.set_layout(session_name, name, layout)
        return window


class WorkspaceException(Exception):
    def __init__(self, message, errors=''):
        super(WorkspaceException, self).__init__(message)
        self.errors = errors
        self.message = message
