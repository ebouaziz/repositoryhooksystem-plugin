# -*- coding: utf-8 -*-

"""
RepositoryHookAdmin:
admin panel interface for controlling hook setup and listeners
"""

from pkg_resources import resource_filename
from repository_hook_system.interface import IRepositoryHookAdminContributer
from trac.admin.api import IAdminPanelProvider
from trac.core import *
from trac.env import IEnvironmentSetupParticipant
from trac.util.translation import _
from trac.web.chrome import ITemplateProvider, add_script, add_warning
from db import Db

class RepositoryHookAdmin(Component):

    """webadmin panel for hook configuration"""

    implements(ITemplateProvider, IAdminPanelProvider,
               IEnvironmentSetupParticipant)

    listeners = []

    # methods for ITemplateProvider
    """Extension point interface for components that provide their own
    ClearSilver templates and accompanying static resources.
    """

    # IEnvironmentSetupParticipant methods
    def environment_created(self):
        pass

    def environment_needs_upgrade(self, db):
        return not self.db.verify()

    def upgrade_environment(self, db):
        self.db.upgrade()

    def __init__(self):
        self.db = Db(self.env)


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
        self.env.log.debug(">>>>>>>>> get_admin_panels <<<<<<<<<<")
        if req.perm.has_permission('TRAC_ADMIN'):
            yield ('repository_hooks', 'Repository Hooks',
                   'milestones', 'Milestones')

    def render_admin_panel(self, req, category, page, path_info):
        req.perm.require('TICKET_ADMIN')
        """Process a request for an admin panel.

        This function should return a tuple of the form `(template, data)`,
        where `template` is the name of the template to use and `data` is the
        data to be passed to the template.
        """
        self.env.log.debug(">>>>>>>>> render_admin_panel <<<<<<<<<<")
        self.env.log.debug("category: '%s'" % category)
        self.env.log.debug("page: '%s'" % page)
        self.env.log.debug("path_info: '%s'" % path_info)

        if req.method == 'POST':
            # Add association
            if req.args.get('add') and req.args.get('name'):
                assoc = {'name': req.args.get('name','').encode('utf-8'),
                         'prefix': req.args.get('prefix','').encode('utf-8')}
                if not assoc['name'] or not assoc['prefix']:
                    add_warning(req, _('Empty value not allowed'))
                else:
                    self.db.add_association(assoc)
                req.redirect(req.href.admin(category, page))
            # Remove association
            elif req.args.get('remove') and req.args.get('sel'):
                sel = req.args.get('sel')
                sel = isinstance(sel, list) and sel or [sel]
                if not sel:
                    raise TracError(_("No custom field selected"))
                for name in sel:
                    assoc = {'name': name}
                    self.db.remove_association(assoc)
                req.redirect(req.href.admin(category, page))

        # data to display
        add_script(req, 'common/js/suggest.js')
        return 'repositoryhooks.html', {'aslist': self.db.list_associations()}
