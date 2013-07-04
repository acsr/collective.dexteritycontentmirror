"""
./bin/instance run /path/to/ddl.py [options] portal_path

Create the database structure for a content mirror.
"""

import optparse
import sqlalchemy as rdb
from zope.site.hooks import setHooks
from zope.site.hooks import setSite
from Acquisition import aq_inner

from collective.dexteritycontentmirror import schema
from collective.dexteritycontentmirror import loader


def setup_parser():
    parser = optparse.OptionParser(
        usage="usage: ./bin/instance run /path/to/ddl.py [options] portal_path")
    parser.add_option('-d', '--drop', dest="drop",
        action="store_true", default=False,
        help="Drop Tables")
    parser.add_option('-n', '--nocreate', dest="no_create",
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
    loader.load_models(site)

    if options.drop:
        schema.metadata.drop_all()
    if not options.no_create:
        schema.metadata.create_all()


# Detect if run as a bin/instance run script
if "app" in locals():
    #sys.argv = sys.argv[2:]
    run_ddl_as_script()
