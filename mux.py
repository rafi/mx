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
__version__ = "0.1"


class Logger():
    _is_tty = sys.stdout.isatty()

    _colors = {
        'reset': 0, 'black': 30, 'white': 37,
        'cyan': 36, 'magenta': 35, 'blue': 34,
        'yellow': 33, 'green': 32, 'red': 31}

    def echo(self, *args):
        for arg in args:
            msg = re.sub(r'\[(bold)?([a-z]+)\]', self._colorize, arg)
            print(msg, '\x1b[0m')

    def _colorize(self, match):
        if not self._is_tty:
            return ''
        attr = ['1' if match.group(1) == 'bold' else '0']
        attr.append(str(self._colors[match.group(2)]))
        return '\x1b[{}m'.format(';'.join(attr))


class Tmux:
    def command(self, cmd, formats=None, many=False):
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
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.wait()
            stdout = process.stdout.read()
            process.stdout.close()
            stderr = process.stderr.read()
            process.stderr.close()
            if stdout:
                lines = ','.join(stdout.decode('utf_8').split('\n')) \
                    .rstrip(',')
                return json.loads('['+lines+']' if many else lines)
        except subprocess.CalledProcessError:
            print('Error')
        except ValueError:
            print('Error')

    def within_session(self):
        return os.environ.get('TMUX') != ''

    def has_session(self, session_name):
        try:
            cmds = ['tmux', 'has-session', '-t', session_name]
            code = subprocess.check_call(cmds, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            code = e.returncode
        return code == 0


class Workspace(object):
    _config = {}
    _repos = []
    _session = {}
    _windows = []
    _tmux = None

    def __init__(self, config_filepath, tmux, log):
        self._tmux = tmux
        self._log = log
        with open(config_filepath, 'r') as stream:
            self._config = yaml.load(stream)

        for repo_name in self._config.get('repos', []):
            repo = {
                'name': repo_name,
                'url': 'https://github.com/{}.git'.format(repo_name),
                'dir': repo_name.split('/')[1]
            }
            self._repos.append(repo)

        venv = self._config.get('venv')
        self._venv = [' source "{}/bin/activate"'.format(venv)] \
            if venv else []

    def create_windows(self):
        root = self._config.get('dir')
        if root:
            os.chdir(root)
        for win_schema in self._config.get('windows', []):
            # Normalize window schema definition
            if isinstance(win_schema, str):
                win_name = win_schema
            else:
                win_name = next(iter(win_schema.keys()))
                win_schema = win_schema[win_name] or {}

            if isinstance(win_schema, str):
                panes = [win_schema]
                win_schema = {}
            else:
                panes = win_schema.get('panes', [])

            layout = win_schema.get('layout')

            # Normalize post commands
            post_cmds = win_schema.get('post_cmd', [])
            post_cmds = [post_cmds] if isinstance(post_cmds, str) \
                else post_cmds

            window = self._create_window(win_name, panes, post_cmds, layout)
            self._windows.append(window)

        return self._windows

    def _create_window(self, name, panes, post_cmds, layout=None):
        if len(self._windows) > 0:
            window, pane = self._new_window(self._session['name'], name)
        else:
            self._session, window, pane = \
                self._new_session(self._config.get('name'), name)
            if not self._session:
                print('Error creating session buddy.')
                sys.exit(1)

        session_name = self._session['name']
        window['panes'] = []
        for pane_schema in panes:
            if len(window['panes']) > 0:
                pane = self._new_pane(session_name, name, pane['index'])
            window['panes'].append(pane)

            # Run commands+post-commands, and activate virtualenv
            cmds = next(iter(pane_schema.values())) \
                if isinstance(pane_schema, dict) else [pane_schema]
            cmds = self._venv + cmds + post_cmds
            for cmd in cmds:
                self.send_keys(session_name, name, pane['index'], cmd)

        self.set_layout(session_name, name, layout)
        return window

    def _new_session(self, session_name, win_name=''):
        cmds = ['new-session', '-Pd', '-s', session_name]
        if win_name:
            cmds.extend(['-n', win_name])

        output = self._tmux.command(
            cmds,
            ['session_id', 'session_name', 'session_windows',
             'window_id', 'window_index', 'pane_index', 'pane_id'])

        if not output:
            raise Exception('Error creating session')
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

    def _new_window(self, session_name, win_name=''):
        cmds = ['new-window', '-Pd', '-t', session_name]
        if win_name:
            cmds.extend(['-n', win_name])

        output = self._tmux.command(
            cmds,
            ['window_id', 'window_name', 'window_panes', 'window_active',
             'window_index', 'window_layout', 'pane_index', 'pane_id'])

        if not output:
            raise Exception('Error creating window')
        window = {}
        pane = {}
        for k, v in output.items():
            short_name = k.split('_')[1]
            if k.startswith('pane_'):
                pane[short_name] = v
            else:
                window[short_name] = v

        return window, pane

    def _new_pane(self, session_name, window_id, pane_id):
        output = self._tmux.command(
            ['split-window', '-P', '-t',
             ':'.join([session_name, window_id])+'.'+str(pane_id), '-h'],
            ['pane_id', 'pane_index', 'pane_active', 'pane_current_path',
             'pane_start_command', 'pane_current_command', 'pane_title'])
        if not output:
            raise Exception('Error creating pane')
        pane = {}
        for k, v in output.items():
            short_name = k.split('_')[1]
            pane[short_name] = v
        return pane

    def get_session_name(self):
        return self._config.get('name')

    def get_windows(self, session_name):
        return self._tmux.command(
            ['list-windows', '-t', session_name],
            ['window_id', 'window_name', 'window_panes', 'window_active',
             'window_index', 'window_layout'],
            many=True)

    def get_panes(self, session_name, window_name):
        return self._tmux.command(
            ['list-panes', '-t', ':'.join([session_name, window_name])],
            ['pane_id', 'pane_active', 'pane_index', 'pane_start_command',
             'pane_current_command', 'pane_current_path', 'pane_title'],
            many=True)

    def set_layout(self, session_name, win_name, layout=None):
        return self._tmux.command([
            'select-layout', '-t',
            session_name+':'+win_name, layout or 'tiled'
        ])

    def send_keys(self, session_name, win_name, pane_index, cmd, enter=True):
        if cmd:
            return self._tmux.command([
                'send-keys', '-Rt',
                session_name+':'+win_name+'.'+str(pane_index),
                cmd, 'C-m' if enter else ''
            ])

    def attach(self, session_name):
        if session_name:
            cmd = 'switch-client' if self.tmux.within_session() \
                else 'attach-session'
            return self._tmux.command([cmd, '-t', session_name])

    def fetch(self):
        root = self._config.get('dir') or os.getcwd()
        log.echo(' [blue]::[reset] Fetching git index for project at [white]{}'
                 .format(root))
# Debugging:
#        with open('output_example.txt') as f:
#            output = f.read()
#        self._parse_git_fetch(output)
#        return
        for repo in self._repos:
            log.echo(' [blue]::[reset] Fetching [white]{} [boldblack]@ {}'
                     .format(repo['name'], repo['url']))
            os.chdir(root)
            os.chdir(repo['dir'])
            output = subprocess.check_output(
                ['git', 'fetch', '--all', '--tags', '--prune'],
                stderr=subprocess.STDOUT
            )
            output = output.decode('utf_8')
            self._parse_git_fetch(output)

    def _parse_git_fetch(self, output):
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
                         ' {}[yellow]([boldmagenta]{}[yellow])[reset]'
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
        is_on = tmux.has_session(session_name)
        log.echo(' [blue]::[reset] Session [boldyellow]{}[reset]: {}'
                 .format(session_name,
                         '[boldgreen]on' if is_on else '[boldred]off'))

        root = self._config.get('dir') or os.getcwd()
        for repo in self._repos:
            os.chdir(root)
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
if args.session:
    # TODO load workspace yml
    session_name = args.session
    pool_dir = '/'.join([os.environ.get('XDG_CACHE_HOME', '~/.cache'), 'mux'])
    if not os.path.isdir(pool_dir):
        os.makedirs(pool_dir)
else:
    workspace = Workspace(args.config, tmux, log)
    session_name = workspace.get_session_name()

if args.action == 'start':
    windows = workspace.create_windows()
elif args.action == 'stop':
    output = tmux.command(['kill-session', '-t', session_name])
elif args.action == 'status':
    workspace.status()
elif args.action == 'fetch':
    workspace.fetch()
