#!/usr/bin/python
# -*- coding: utf-8 -*-
import yaml
import re
import json
import subprocess
import sys
import os
import argparse

__author__ = "Rafael Bodill"
__copyright__ = "Copyright (C) 2015 Rafael Bodill"
__license__ = "MIT"
__version__ = "0.2"


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
            print(msg, '\x1b[0m')

    def _colorize(self, match):
        if not self._is_tty:
            return ''
        attr = ['1' if match.group(1) == 'bold' else '0']
        attr.append(str(self._colors[match.group(2)]))
        return '\x1b[{}m'.format(';'.join(attr))


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
                stdout = json.loads('['+lines+']' if many else lines)
            if stderr:
                stderr = stderr.decode('utf_8').strip()

            return stdout, stderr
        except Exception as e:
            log.echo('[red]ERROR: [reset]Unable to execute Tmux, aborting.')
            print(repr(e))
            sys.exit(3)
        except ValueError:
            print('Unable to serialize Tmux\'s response, please report bug.')
            print(repr(e))
            sys.exit(4)

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
            code = subprocess.check_call(cmds, stderr=subprocess.DEVNULL)
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
            raise WorkspaceException('Error creating session', errors)
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
            ['split-window', '-P', '-t',
             ':'.join([session_name, window_id])+'.'+str(pane_id), '-h'],
            ['pane_id', 'pane_index', 'pane_active', 'pane_current_path',
             'pane_start_command', 'pane_current_command', 'pane_title'])
        if errors:
            raise WorkspaceException('Error creating pane {}'.format(errors))
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
            session_name+':'+win_name, layout or 'tiled'
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
                session_name+':'+win_name+'.'+str(pane_index),
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
        venv = self._config.get('venv')
        if venv:
            self._venv = [
                ' source "{}"'.format(os.path.join(venv, 'bin/activate'))]

    def create(self):
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
            # Normalize window schema definition
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

            # Normalize post commands
            post_cmds = window.get('post_cmd', [])
            post_cmds = [post_cmds] if isinstance(post_cmds, str) \
                else post_cmds

            self._windows.append(
                self.create_window(
                    name, panes, post_cmds, window.get('layout')))

        return self._windows

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

    def get_session_name(self):
        return self._config.get('name')


class WorkspaceException(Exception):
    def __init__(self, message, errors=''):
        super(WorkspaceException, self).__init__(message)
        self.errors = errors
        self.message = message


class Git(object):
    _config = {}
    _repos = []
    _root = ''

    def __init__(self, config):
        """
        :param config: Dictionary with config schema
        """
        self._config = config
        self._root = self._config.get('dir') or os.getcwd()

        # Collect normalized list of repositories in workspace
        for repo_name in self._config.get('repos', []):
            repo = {
                'name': repo_name,
                'url': 'https://github.com/{}.git'.format(repo_name),
                'dir': repo_name.split('/')[1]
            }
            self._repos.append(repo)

    def fetch(self):
        """
        Iterate through all repositories and run git fetch with rich output
        """
        log.echo(' [blue]::[reset] Fetching git index for project at [white]{}'
                 .format(self._root))
# Debugging:
#        with open('output_example.txt') as f:
#            output = f.read()
#        self._parse_git_fetch(output)
#        return
        for repo in self._repos:
            log.echo(' [blue]::[reset] Fetching [white]{} [boldblack]@ {}'
                     .format(repo['name'], repo['url']))
            os.chdir(self._root)
            os.chdir(repo['dir'])
            output = subprocess.check_output(
                ['git', 'fetch', '--all', '--tags', '--prune'],
                stderr=subprocess.STDOUT
            )
            self._parse_git_fetch(output.decode('utf_8'))

    def _parse_git_fetch(self, output):
        """
        Parse and beautify git's raw fetch summary

        :param output: Git's raw fetch output
        """
        branches = {'created': [], 'updated': []}
        tags = {'created': [], 'updated': []}
        deleted = []
        # Example matches:
        #
        #  * [new branch]      1.34.3     -> gogs/1.34.3
        #  bc23688..8be82ed  develop    -> gogs/develop
        #  * [new tag]         0.9.1      -> 0.9.1
        #  - [tag update]      1.19.0     -> 1.19.0
        #  - [tag update]      1.19.1     -> 1.19.1
        #  - [tag update]      1.19.2     -> 1.19.2
        #  * [new tag]         1.19.3     -> 1.19.3
        #  * [new tag]         1.19.4     -> 1.19.4
        #  x [deleted]         (none)     -> origin/foobar
        regex = re.compile(
            r'^\s+([-+*x\ ])\s+\[?([\w\ \.]+)\]?'
            '\s{2,}([^\s]+)\s{2,}->\s(.*)$',
            flags=re.MULTILINE
        )
        for match in regex.finditer(output):
            remote = match.group(4)
            if match.group(2).find('new') > -1:
                action = 'created'
            else:
                action = 'updated'

            if match.group(2) == 'deleted':
                deleted.append(remote)
            if match.group(2).find('tag') > -1:
                tags[action].append(remote)
            else:
                branches[action].append(remote)

        for action in ['created', 'updated']:
            if tags[action] or branches[action]:
                log.echo('   [{}]::[reset] {}'
                         ' {}[yellow]([boldyellow]{}[yellow])[reset]'
                         ' {}[yellow]([boldred]{}[yellow])[reset]'
                         .format(
                            'green' if action == 'created' else 'yellow',
                            action.title(),
                            'tags: ' if tags[action] else '',
                            ', '.join(tags[action]),
                            'branches: ' if branches[action] else '',
                            ', '.join(branches[action])))
        if deleted:
            log.echo('   [red]::[reset] Deleted:'
                     ' [yellow]([boldred]{}[yellow])[reset]'
                     .format(', '.join(deleted)))

    def status(self):
        """
        Iterate through repositories and display a colorful status
        """
        is_on = tmux.has_session(session_name)
        log.echo(' [blue]::[reset] Session [boldyellow]{}[reset]: {}'
                 .format(session_name,
                         '[boldgreen]on' if is_on else '[boldred]off'))

        for repo in self._repos:
            os.chdir(self._root)
            os.chdir(repo['dir'])

            try:
                output = subprocess.check_output(
                    ['git', 'symbolic-ref', '-q', 'HEAD'],
                    stderr=subprocess.DEVNULL)
                detached = False
            except subprocess.CalledProcessError:
                detached = True

            output = subprocess.check_output(['git', 'diff', '--shortstat'])
            modified = re.match(r'^\s*(\d)', output.decode('utf_8'))
            modified = '≠'+str(modified.group(1)) if modified else ''

            output = subprocess.check_output(
                ['git', 'ls-files', '--others', '--exclude-standard'],
                stderr=subprocess.DEVNULL).decode('utf-8')
            untracked = len(output.split('\n')) - 1
            untracked = '?'+str(untracked) if untracked > 0 else ''

            current = subprocess.check_output([
                'git', 'log', '-1', '--color=always',
                '--format=%C(auto)%D %C(black bold)(%aN %ar)%Creset'
            ]).decode('utf-8').strip()

            position = ''
            if not detached:
                output = subprocess.check_output([
                    'git', 'rev-parse', '--abbrev-ref', 'HEAD'])
                branch = output.decode('utf-8').strip()
                upstream = None
                try:
                    output = subprocess.check_output(
                        ['git', 'rev-parse', '--abbrev-ref', '@{upstream}'],
                        stderr=subprocess.DEVNULL)
                    upstream = output.decode('utf-8').strip()
                except subprocess.CalledProcessError:
                    pass

                if not upstream:
                    upstream = 'origin/{}'.format(branch)

                output = subprocess.check_output([
                    'git', 'rev-list', '--left-right',
                    branch, '...', upstream
                ]).decode('utf-8')
                ahead = len(re.findall(r'\<', output))
                behind = len(re.findall(r'\>', output))
                position = '{}{}'.format(
                    '▲'+str(ahead) if ahead else '',
                    '▼'+str(behind) if behind else '',
                )

            log.echo('   [white]{:>30} '
                     ' [boldred]{:3} [boldblue]{:3} [boldmagenta]{:7}'
                     ' [reset]{}'
                     .format(
                        repo['name'], modified, untracked,
                        position if not detached else 'detach', current))


# Start main program and parse user arguments
parser = argparse.ArgumentParser(description='mux: Orchestrate tmux sessions')
parser.add_argument('action', type=str, default='start',
                    choices=['start', 'fetch', 'stop', 'status'],
                    help='an action for %(prog)s (default: %(default)s)')
parser.add_argument('session', type=str, nargs='?',
                    help='session for %(prog)s to load'
                    ' (default: current directory\'s mux.yml)')
parser.add_argument('--config', type=str, default='mux.yml',
                    help='workspace yml config file (default: %(default)s)')

args = parser.parse_args()

log = Logger()
tmux = Tmux()
cache_dir = os.environ.get('XDG_CACHE_HOME',
                           os.path.join(os.environ.get('HOME'), '.cache'))
pool_dir = os.path.join(cache_dir, 'mux')

if args.session:
    # Load session from cache pool (symlinks)
    cfg_path = os.path.join(pool_dir, args.session+'.yml')
else:
    # Load session from cli option (or default value)
    cfg_path = os.path.realpath(args.config)

if not os.path.isfile(cfg_path):
    log.echo('[red]ERROR: [reset]Unable to find [white]{}'.format(cfg_path))
    sys.exit(2)

with open(cfg_path, 'r') as stream:
    config = yaml.load(stream)
workspace = Workspace(tmux)
workspace.set_config(config)
session_name = workspace.get_session_name()

if args.action == 'start':
    try:
        workspace.create()

        # Save session symlink in cache pool
        if not os.path.isdir(pool_dir):
            os.makedirs(pool_dir)
        link = os.path.join(pool_dir, session_name+'.yml')
        if not os.path.isfile(link):
            os.symlink(cfg_path, link)
    except WorkspaceException as e:
        log.echo('[red]{}: [reset]{}'.format(e.message, e.errors))

elif args.action == 'stop':
    tmux.kill_session(session_name)

elif args.action in ['status', 'fetch']:
    git = Git(config)
    getattr(git, args.action)()
