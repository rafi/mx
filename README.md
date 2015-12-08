mx
===
Workspace/project-oriented tmux/git personal assistant.

Features
---
Working on multiple git repositories and juggling tmux sessions can be tedious.
`mx` tries to help with that:

- Custom config per project
- Recurse repos to show stats and fetch git index
- Manage pre-configure tmux sessions

Dependencies
---
- [git]
- [tmux]
- [PyYAML]

Install
---
via pip:
```sh
pip install --user rafi.mx
```

Usage
---
```sh
  mx [-h] [--config CONFIG] [-v]
     {attach,start,stop,ls,fetch,status} [session]
```

1. In a project, create a `.mx.yml` file, see [config-examples] for reference
1. Run `mx` in the same directory, with one of its [commands]

`mx` will remember yours projects, so you could reference it anywhere later.

For example:

- Display the status of all git repositories in a directory
  containing `.mx.yml`:
```sh
mx status
```

- Start working on a project, regardless of your current dir:
```sh
mx start funyard
```

- See a colorful summary of git repository stats:
```sh
mx stats
```

Commands
---
- `start` - Create a new Tmux session with pre-configured windows &amp; panes.
- `stop` - Kill the entire Tmux session of a project
- `attach` - Attach to project
- `ls` - List a session's windows and panes
- `fetch` - Run `git fetch --all --prune --tags` on all git repositories
- `stats` - Display git repositories' index and dir stats

Configuration
---
In each project you want `mx`'s powers, create a `.mx.yml` file with your
configuration relating to the project. For example

### Config Examples
```yml
name: funyard
root: /srv/code/
venv: /srv/venvs/funyard
repos:
  - torvalds/linux
  - vim/vim
  - tmux/tmux
  - facebook/react
  - twbs/bootstrap
windows:
  - dev: ls
  - commit:
      post_cmd: git status -sb && git log -1 --color=always --oneline --decorate
      panes:
        - cd linux
        - cd vim
        - cd tmux
        - cd react
        - cd bootstrap
- db:
    layout: even-horizontal
    panes:
    - ipython
    - pgcli:
      - pgcli -U postgres -h localhost -d funyard
- box:
    panes:
    - eval "$(docker-machine env fun)" && docker-compose up
```

License
---
The MIT License (MIT)

Copyright (c) 2015 Rafael Bodill

[config-examples]: #config-examples
[commands]: #commands
[git]: https://git-scm.com/
[tmux]: https://tmux.github.io/
[PyYAML]: http://pyyaml.org/wiki/PyYAML
