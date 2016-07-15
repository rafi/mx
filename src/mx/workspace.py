# -*- coding: utf-8 -*-
import re
import sys
import os
import subprocess
from .logger import Logger
from .tmux import Tmux
from .git import Git

log = Logger()


class WorkspaceException(Exception):
    def __init__(self, message, errors=''):
        super(WorkspaceException, self).__init__(message)
        self.errors = errors
        self.message = message


class Workspace(object):
    _tmux = Tmux()
    _config = {}
    _name = ''
    _root = ''
    _venv = []
    _session = {}
    _windows = []

    def __init__(self, config=None):
        """
        :param tmux: Tmux class instance
        """
        self.set_config(config)

    def set_config(self, config):
        self._config = config
        self._name = self._config.get('name')
        self._root = self._config.get('dir') or os.getcwd()
        self._root = os.path.expanduser(self._root)

        # Prepare a virtualenv source command, if any
        # The specified virtualenv path can be absolute or relative
        # to the workspace's root directory.
        venv = self._config.get('venv')
        if venv:
            venv = os.path.expanduser(venv)
            if self._root and not os.path.isabs(venv):
                venv = os.path.join(self._root, venv)
            self._venv = [
                ' source "{}"'.format(os.path.join(venv, 'bin/activate'))]

    def start(self):
        """
        Create Tmux windows from `windows` configuration in YML

        :return Collection of window information
        """
        if self._root:
            if not os.path.isdir(self._root):
                raise WorkspaceException('Directory does not exist',
                                         self._root)
            os.chdir(self._root)

        # Run commands before spawning windows
        for cmd in self._config.get('commands', []):
            retcode, stdout = subprocess.getstatusoutput(cmd)
            if retcode != 0:
                raise WorkspaceException(
                    'Error {} while running `{}`'.format(retcode, cmd), stdout)

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

        self.attach()
        return self._windows

    def stop(self, name=None):
        """
        Kill a workspace session

        :param name: Session name
        """
        self._tmux.kill_session(name or self._name)

    def attach(self, name=None):
        """
        Attach to a workspace session

        :param name: Session name
        """
        self._tmux.attach(name or self._name)

    def ls(self):
        """
        List windows and panes for a session
        """
        windows, errors = self._tmux.get_windows(self._name)
        if errors:
            raise WorkspaceException('Unable to list windows', errors)
        log.echo(' [blue]::[reset] Windows:')
        log.echo(repr(windows))

        for window in windows:
            win_id = window['window_id']
            panes, errors = self._tmux.get_panes(self._name, win_id)
            if errors:
                raise WorkspaceException('Unable to list panes', errors)
            log.echo(' [blue]::[reset] Window "{}" panes:'.format(win_id))
            log.echo(repr(panes))

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
            window, pane = self._tmux.new_window(self._name, name)
        else:
            self._session, window, pane = \
                self._tmux.new_session(self._name, name)
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

    @staticmethod
    def initialize(root_dir):
        """
        Initialize a new workspace .mx.yml file
        """
        dirs = next(os.walk(root_dir))[1]
        repos = []
        skipped = []
        for directory in dirs:
            os.chdir(os.path.join(root_dir, directory))
            if Git.is_git_repo():
                log.echo(' [blue]::[reset] Found directory'
                         ' `[white]{}[reset]`'.format(directory))
                url = Git.get_remote_url()
                name = url.replace(':', '/')
                name = re.sub('.git$', '', name)
                name = '/'.join(name.split('/')[-2:])
                if name.split('/')[1] == directory:
                    repos.append(name)
                else:
                    repos.append({'dir': directory, 'name': name})
            else:
                skipped.append(directory)

        log.echo(' [blue]::[yellow] Skipped[reset]'
                 ' non-git repositories: {}'.format(', '.join(skipped)))

        return {
            'name': os.path.basename(root_dir),
            'dir': root_dir,
            'repos': repos
        }
