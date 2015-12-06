from setuptools import setup, find_packages

setup(
    name='mux2',
    version='0.2',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    scripts=['src/bin/mux'],
    install_requires=['PyYAML'],
    author='Rafael Bodill',
    author_email='justrafi@gmail.com',
    description='Workspace/project-oriented tmux/git personal assistant.',
    license='MIT',
    keywords='tmux git workspace project',
    url='http://github.com/rafi/mux2'
)
