from setuptools import setup, find_packages
from src import mx

MAJOR_VERSION = '0'
MINOR_VERSION = '2'
MICRO_VERSION = '5'
VERSION = '{}.{}.{}'.format(MAJOR_VERSION, MINOR_VERSION, MICRO_VERSION)

setup(
    name='mx',
    version=VERSION,
    description='Project-oriented tmux/git personal assistant.',
    long_description=mx.__doc__,
    author=mx.__author__,
    author_email=mx.__email__,
    license=mx.__license__,
    url='http://github.com/rafi/mx',
    keywords='tmux git workspace project assistant',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=['PyYAML'],
    extras_requires=['pytest', 'mock'],
    platforms='any',
    zip_safe=False,
    entry_points={
        'console_scripts': ['mx = mx.cli:main']
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Customer Service',
        'Intended Audience :: System Administrators',
        'Operating System :: Microsoft',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development',
        'Topic :: Software Development :: Build Tools',
        'Topic :: Software Development :: Debuggers',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Software Distribution',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities'
    ]
)
