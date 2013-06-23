from setuptools import setup, find_packages
import os

version = '1.0'

setup(name='collective.dexteritycontentmirror',
      version=version,
      description="Dexterity Content Mirror",
      long_description=open("README.rst").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      classifiers=[
        "Framework :: Plone",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Roman Lacko',
      author_email='backup.rlacko@gmail.com',
      url='https://bitbucket.org/rlacko/collective.dexteritycontentmirror',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'plone.app.dexterity [grok]',
          'plone.namedfile [blobs]',
          'plone.api',
          'collective.indexing',
          'zope.sqlalchemy',
          'SQLAlchemy',
      ],
      entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
