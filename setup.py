from setuptools import find_packages, setup

version = '0.1.16'

setup(name='RepositoryHookSystem',
      version=version,
      description="plugin to make repository commit events iterable and accessible to other plugins",
      author='Jeff Hammel',
      author_email='jhammel@openplans.org',
      url='http://trac-hacks.org/wiki/k0s',
      keywords='trac plugin',
      license="GPL",
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests*']),
      include_package_data=True,
      package_data={'repository_hook_system': ['templates/*']},
      zip_safe=False,
      install_requires=['python-dateutil', 'Trac >= 1.0.0'],
      entry_points={'trac.plugins':
        ['repository_hook_system.neoticketchanger = repository_hook_system.neoticketchanger',
         'repository_hook_system.ticket_validator = repository_hook_system.ticket_validator',
         'repository_hook_system.listener = repository_hook_system.listener',
         'repository_hook_system.admin = repository_hook_system.admin',
         'repository_hook_system.svnhooksystem.svnhooksystem = repository_hook_system.svnhooksystem.svnhooksystem']
      })
