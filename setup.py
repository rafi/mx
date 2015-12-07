from setuptools import setup, find_packages

MAJOR_VERSION = '0'
MINOR_VERSION = '2'
MICRO_VERSION = '5'
VERSION = '{}.{}.{}'.format(MAJOR_VERSION, MINOR_VERSION, MICRO_VERSION)

setup(
    name='mux2',
    version=VERSION,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    install_requires=['PyYAML'],
    extras_requires=['pytest', 'mock'],
    platforms='any',
    author='Rafael Bodill',
    author_email='justrafi@gmail.com',
    description='Workspace/project-oriented tmux/git personal assistant.',
    license='MIT',
    keywords='tmux git workspace project assistant',
    url='http://github.com/rafi/mux2',
    zip_safe=False,
    entry_points={
        'console_scripts': ['mux = mux.cli:main']
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
