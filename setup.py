from setuptools import setup, find_packages

from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='luapatt',
    version='0.9.0b4',
    description='Python implementation of Lua-style pattern matching',
    long_description=long_description,
    url='https://github.com/jcgoble3/luapatt',
    author='Jonathan Goble',
    author_email='jcgoble3@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        # 'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: General'
    ],
    keywords='Lua pattern matching regex regular expressions',
    package_dir={'': 'src'},
    py_modules=["luapatt"],
    install_requires=[],  # no dependencies
    extras_require={'test': ['pytest']}
)
