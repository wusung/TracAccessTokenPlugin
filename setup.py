# -*- coding: utf-8 -*-
import sys

from setuptools import setup

PACKAGE = 'TracAccessTokenPlugin'
SOURCE = 'tracaccesstoken'
with open('VERSION') as f:
    VERSION = f.read().rstrip()

REQUIRES = [
    'Trac>=1.0.0'
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
      description='This plugin allows you to maintain the auth token in trac web. '
                  'in the personal preferences.',
      classifiers=CLASSIFIERS,
      keywords=['trac plugin', 'access token'],
      author='Wusung Peng',
      author_email='wusungpeng@kkbox.com',
      url="https://gitlab.com/wusung/TracAccessTokenPlugin.git",
      license='SEE LICENSE',
      platforms=['linux', 'osx', 'unix', 'win32'],
      packages=[SOURCE],
      entry_points={'trac.plugins': '%s = %s' % (PACKAGE, SOURCE)},
      package_data={
          SOURCE: [
              'templates/*.html',
              'htdocs/css/*.css',
              'htdocs/js/*.js'
          ]
      },
      include_package_data=True,
      install_requires=REQUIRES,
      )
