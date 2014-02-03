"""
RepositoryHookAdmin:
admin panel interface for controlling hook setup and listeners
"""

from pkg_resources import resource_filename
from repository_hook_system.interface import IRepositoryHookAdminContributer
from trac.admin.api import IAdminPanelProvider
from trac.core import *
from trac.web.chrome import ITemplateProvider


class RepositoryHookAdmin(Component):

    """webadmin panel for hook configuration"""

    implements(ITemplateProvider, IAdminPanelProvider)

    listeners = []

    systems = ExtensionPoint(IRepositoryHookAdminContributer)

    def system(self):
        """returns the IRepositoryHookSystem appropriate to the repository"""
        # XXX could abstract this, as this is not specific to TTW functionality
        for system in self.systems:
            if self.env.config.get('trac', 'repository_type') in system.type():
                return system

    # methods for ITemplateProvider
    """Extension point interface for components that provide their own
    ClearSilver templates and accompanying static resources.
    """

    def get_htdocs_dirs(self):
        """Return a list of directories with static resources (such as style
        sheets, images, etc.)

        Each item in the list must be a `(prefix, abspath)` tuple. The
        `prefix` part defines the path in the URL that requests to these
        resources are prefixed with.

        The `abspath` is the absolute path to the directory containing the
        resources on the local file system.
        """
        return []

    def get_templates_dirs(self):
        """Return a list of directories containing the provided template
        files.
        """
        return [resource_filename(__name__, 'templates')]

    # methods for IAdminPanelProvider

    """Extension point interface for adding panels to the web-based
    administration interface.
    """

    def get_admin_panels(self, req):
        """Return a list of available admin panels.

        The items returned by this function must be tuples of the form
        `(category, category_label, page, page_label)`.
        """
        if req.perm.has_permission('TRAC_ADMIN'):
            system = self.system()
            if system is not None and self.env.config.get('trac',
                                                          'repository_dir'):
                for hook in system.available_hooks():
                    yield ('repository_hooks', 'Repository Hooks', hook, hook)

    def render_admin_panel(self, req, category, page, path_info):
        """Process a request for an admin panel.

        This function should return a tuple of the form `(template, data)`,
        where `template` is the name of the template to use and `data` is the
        data to be passed to the template.
        """
        hookname = page
        system = self.system()
        data = {}
        data['hook'] = hookname
        data['snippet'] = system.render(hookname, req)

        return ('repositoryhooks.html', data)
