# -*- coding: utf-8 -*-
import sys

from setuptools import setup

PACKAGE = 'tracaccesstoken'
with open('VERSION') as f:
    VERSION = f.read().rstrip()

REQUIRES = [
    'Trac>=0.11'
]

if sys.version_info[:4] < (2, 6):
    REQUIRES.append('simplejson')

CLASSIFIERS = [
    'Framework :: Trac',
    'Development Status :: Development',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development',
]

setup(name=PACKAGE,
      version=VERSION,
      description='This plugin allows you to index your wiki and ticket data '
                  'in a full text search engine and search it from a button '
                  'in the main navbar.',
      classifiers=CLASSIFIERS,
      keywords=['trac plugin', 'access token'],
      author='Wusung Peng',
      author_email='wusungpeng@kkbox.com',
      url="https://gitlab.com/wusung/tracauthtokenplugin.git",
      license='SEE LICENSE',
      platforms=['linux', 'osx', 'unix', 'win32'],
      packages=[PACKAGE],
      entry_points={'trac.plugins': '%s = tracaccesstoken' % PACKAGE},
      package_data={
          'tracaccesstoken/': [
              'templates/*.html',
              'htdocs/css/*.css',
              'htdocs/js/*.js'
          ]
      },
      include_package_data=True,
      install_requires=REQUIRES,
      )
