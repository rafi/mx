# -*- coding: utf-8 -*-
import yaml
import argparse
import os
import sys
from . import __version__
from .logger import Logger
from .git import Git
from .tmux import TmuxException
from .workspace import Workspace, WorkspaceException

WORKSPACE_COMMANDS = ['attach', 'start', 'stop', 'ls', 'init']
GIT_COMMANDS = ['clone', 'fetch', 'status']


def main():
    """
    Start main program: Parse user arguments and take action
    """
    parser = argparse.ArgumentParser(
        description='mx: Orchestrate tmux sessions and git projects')

    parser.add_argument('action', type=str, nargs='?', default='start',
                        choices=WORKSPACE_COMMANDS + GIT_COMMANDS,
                        help='an action for %(prog)s (default: %(default)s)')
    parser.add_argument('session', type=str, nargs='?',
                        help='session for %(prog)s to load'
                        ' (default: current directory\'s .mx.yml)')
    parser.add_argument('-c', '--config', type=str, default='.mx.yml',
                        help='workspace yml config file'
                             ' (default: %(default)s)')
    parser.add_argument('-v', action='version',
                        version='%(prog)s {}'.format(__version__))

    args = parser.parse_args()

    # Compute cache pool path
    cache_dir = os.environ.get('XDG_CACHE_HOME',
                               os.path.join(os.environ.get('HOME'), '.cache'))
    pool_dir = os.path.join(cache_dir, 'mx')

    if args.session:
        # Load session from cache pool (symlinks)
        cfg_path = os.path.join(pool_dir, '{}.yml'.format(args.session))
    else:
        # Load session from cli option (or default value)
        cfg_path = os.path.realpath(args.config)

    log = Logger()
    if not os.path.isfile(cfg_path):
        if args.action == 'init':
            schema = Workspace.initialize(os.getcwd())
            with open(cfg_path, 'w') as cfg_file:
                cfg_file.write(
                    yaml.safe_dump(schema, default_flow_style=False))
            args.action = 'status'
        else:
            log.echo('[red]ERROR: [reset]Unable to find [white]{}'
                     .format(cfg_path))
            sys.exit(2)

    try:
        # Read configuration and run the requested action
        with open(cfg_path, 'r') as stream:
            config = yaml.load(stream)
        run(config, args.action)

        # Save session symlink in cache pool
        if not os.path.isdir(pool_dir):
            os.makedirs(pool_dir)
        link = os.path.join(pool_dir, '{}.yml'.format(config.get('name')))
        if not os.path.isfile(link):
            os.symlink(cfg_path, link)

    except (WorkspaceException, TmuxException) as e:
        if hasattr(e, '__context__') and e.__context__:
            log.echo(' -> {}'.format(e.__context__))
        if hasattr(e, 'errors'):
            log.echo('[red]{}: [reset]{}'.format(e.message, e.errors))
        else:
            log.echo('[red]Raw error: [reset]{}'.format(str(e)))
        sys.exit(3)


def run(config, action):
    """
    Execute tmux or git workspace related actions
    """
    if action in WORKSPACE_COMMANDS:
        workspace = Workspace(config)
        getattr(workspace, action)()

    # Or, git related actions
    elif action in GIT_COMMANDS:
        git = Git(config)
        getattr(git, action)()
