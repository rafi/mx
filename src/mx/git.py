# -*- coding: utf-8 -*-
import re
import os
import subprocess
from .logger import Logger
from .tmux import Tmux

log = Logger()


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
        self._root = os.path.expanduser(self._root)

        # Collect normalized list of repositories in workspace
        for repo_name in self._config.get('repos', []):
            if isinstance(repo_name, str):
                repo = {
                    'name': repo_name,
                    'url': self._parse_repo_url(repo_name),
                    'dir': repo_name.split('/')[1]
                }
            else:
                repo = repo_name
                if 'url' not in repo:
                    repo['url'] = self._parse_repo_url(repo['name'])

            self._repos.append(repo)

    def _parse_repo_url(self, repo_name):
        """
        Complete full URL for short named repositories
        """
        url = None
        if 'github.com' not in repo_name:
            url = 'https://github.com/{}.git'.format(repo_name)
        return url or repo_name

    def clone(self):
        """
        Clone all repositories in project directory
        """
        log.echo(' [blue]::[reset] Fetching git index for project at [white]{}'
                 .format(self._root))
        if not os.path.isdir(self._root):
            os.makedirs(self._root)
        os.chdir(self._root)

        for repo in self._repos:
            log.echo(' [blue]::[reset] Cloning [white]{} [boldblack]@ {}'
                     .format(repo['name'], repo['url']))
            subprocess.check_output(
                ['git', 'clone', repo['url']],
                stderr=subprocess.STDOUT)

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
                stderr=subprocess.STDOUT)
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
        session_name = self._config.get('name')
        is_on = Tmux().has_session(session_name)
        log.echo(' [blue]::[reset] Session [boldyellow]{}[reset]: {}'
                 .format(session_name,
                         '[boldgreen]on' if is_on else '[boldred]off'))

        # Compatibility for python 2.x, doesn't have subprocess.DEVNULL
        DEVNULL = open(os.devnull, 'wb')

        for repo in self._repos:
            os.chdir(self._root)
            os.chdir(repo['dir'])

            try:
                output = subprocess.check_output(
                    ['git', 'symbolic-ref', '-q', 'HEAD'],
                    stderr=DEVNULL)
                detached = False
            except subprocess.CalledProcessError:
                detached = True

            output = subprocess.check_output(['git', 'diff', '--shortstat'])
            modified = re.match(r'^\s*(\d)', output.decode('utf_8'))
            modified = '≠' + str(modified.group(1)) if modified else ''

            output = subprocess.check_output(
                ['git', 'ls-files', '--others', '--exclude-standard'],
                stderr=DEVNULL).decode('utf-8')
            untracked = len(output.split('\n')) - 1
            untracked = '?' + str(untracked) if untracked > 0 else ''

            current = subprocess.check_output([
                'git', 'log', '-1', '--color=always',
                '--format=%C(auto)%D %C(black bold)(%aN %ar)%Creset'
            ]).decode('utf-8').strip()

            if detached:
                position = 'detach'
            else:
                output = subprocess.check_output([
                    'git', 'rev-parse', '--abbrev-ref', 'HEAD'])
                branch = output.decode('utf-8').strip()
                upstream = 'origin/{}'.format(branch)
                try:
                    output = subprocess.check_output(
                        ['git', 'rev-parse', '--abbrev-ref', '@{upstream}'],
                        stderr=DEVNULL)
                    upstream = output.decode('utf-8').strip()
                except subprocess.CalledProcessError:
                    pass

                position = ''
                try:
                    output = subprocess.check_output([
                        'git', 'rev-list', '--left-right',
                        branch, '...', upstream
                    ], stderr=subprocess.STDOUT).decode('utf-8')
                    ahead = len(re.findall(r'\<', output))
                    behind = len(re.findall(r'\>', output))
                    position = '{}{}'.format(
                        '▲' + str(ahead) if ahead else '',
                        '▼' + str(behind) if behind else '',
                    )
                except subprocess.CalledProcessError:
                    position = 'n/a'

            name = repo['name']
            if repo['name'].split('/')[1] != repo['dir']:
                name = repo['dir']

            log.echo('   [white]{:>30} '
                     ' [boldred]{:3} [boldblue]{:3} [boldmagenta]{:7}'
                     ' [reset]{}'
                     .format(
                         name, modified, untracked,
                         position, current))

        DEVNULL.close()

    @staticmethod
    def is_git_repo():
        """
        Check if current directory is a Git repository
        """
        try:
            subprocess.check_output(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            return False

    @staticmethod
    def get_remote_url():
        """
        Returns the current directory's Git repository remote URL
        """
        try:
            url = subprocess.check_output(
                ['git', 'config', '--get', 'remote.origin.url'],
                stderr=subprocess.STDOUT)
            return url.decode('utf-8').strip()
        except subprocess.CalledProcessError:
            return False
