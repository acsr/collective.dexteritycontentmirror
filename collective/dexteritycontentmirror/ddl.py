"""
./bin/instance run /path/to/ddl.py [options] portal_path

Create the database structure for a content mirror.
"""

import optparse
import sqlalchemy as rdb
from zope.site.hooks import setHooks
from zope.site.hooks import setSite
from zope.component import queryUtility
from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from plone.dexterity.interfaces import IDexterityFTI
from plone.behavior.interfaces import IBehavior
from plone.behavior.interfaces import IBehaviorAssignable

from collective.dexteritycontentmirror import interfaces
from collective.dexteritycontentmirror import behaviors
from collective.dexteritycontentmirror import session
from collective.dexteritycontentmirror import schema
from collective.dexteritycontentmirror import loader


def setup_parser():
    parser = optparse.OptionParser(
        usage="usage: ./bin/instance run /path/to/ddl.py [options] portal_path")
    parser.add_option('-d', '--drop', dest="drop",
        action="store_true", default=False,
        help="Drop Tables")
    parser.add_option('-n', '--nocreate', dest="create",
        action="store_true", default=False,
        help="Do Not Create Tables")
    return parser


def spoof_request(app):
    """
    http://developer.plone.org/misc/commandline.html
    """
    from AccessControl.SecurityManagement import newSecurityManager
    from AccessControl.SecurityManager import setSecurityPolicy
    from Products.CMFCore.tests.base.security import PermissiveSecurityPolicy, OmnipotentUser
    _policy = PermissiveSecurityPolicy()
    setSecurityPolicy(_policy)
    newSecurityManager(None, OmnipotentUser().__of__(app.acl_users))
    return app


def has_behavior(portal_type, klass):
    fti = queryUtility(IDexterityFTI, portal_type, None)
    if not fti is None:
        for behavior_name in fti.behaviors:
            behavior_interface = None
            behavior_instance = queryUtility(IBehavior, name=behavior_name)
            if not behavior_instance is None and \
                behavior_instance.interface is klass:
                return True
    return False


def run_ddl_as_script():
    parser = setup_parser()
    options, args = parser.parse_args()

    if len(args) != 1:
        parser.print_help()
        sys.exit(1)
        return

    instance_path = args[0]

    global app

    # Enable Faux HTTP request object
    app = spoof_request(app)

    # Get Plone site object from Zope application server root
    site = app.unrestrictedTraverse(instance_path)
    setHooks()
    setSite(site)
    site.setupCurrentSkin(app.REQUEST)

    # Load portal types with enabled IMirroredContent behavior
    context = aq_inner(site)
    portal_types = getToolByName(context, "portal_types")
    for portal_type in portal_types:
        if has_behavior(portal_type, behaviors.IMirroredContent):
            print('Loading model for {0}'.format(portal_type))
            loader.load(portal_type)

    if options.drop:
        schema.metadata.drop_all()
    if not options.create:
        schema.metadata.create_all()


# Detect if run as a bin/instance run script
if "app" in locals():
    sys.argv = sys.argv[2:]
    run_ddl_as_script()
