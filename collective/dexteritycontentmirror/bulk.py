"""
./bin/instance run /path/to/bulk.py [options] portal_path

A content mirror bulk importer.
"""

import time
import sys
import optparse
import transaction
import sqlalchemy as rdb
from zope.site.hooks import setHooks
from zope.site.hooks import setSite
from zope.interface import alsoProvides
from zope import component
from DateTime import DateTime

from collective.dexteritycontentmirror import interfaces
from collective.dexteritycontentmirror import behaviors
from collective.dexteritycontentmirror import session
from collective.dexteritycontentmirror import schema
from collective.dexteritycontentmirror.interfaces import IPeerRegistry
from collective.dexteritycontentmirror.loader import load


# pyflakes
session


def expunge(obj):
    try:
        obj._p_deactivate()
    except:
        pass


def setup_parser():
    parser = optparse.OptionParser(
        usage="usage: ./bin/instance run /path/to/bulk.py [options] portal_path")
    parser.add_option(
        '-i', '--incremental', dest="incremental", action="store_true",
        help="serialize content modified/created since last run",
        default=False)
    parser.add_option(
        '-t', '--types', dest="types", default="",
        help="only serialize specified types (comma separated)")
    parser.add_option(
        '-p', '--path', dest="path", default="",
        help="serialize content from the specified path")
    parser.add_option(
        '-q', '--quiet', dest='verbose', action='store_false',
        help="quiet/silent output", default=True)
    parser.add_option(
        '-b', '--batch', dest='threshold', type="int",
        help="batch commit every N objects (default %s)"%(500), default=500)
    return parser


def setup_query(options):
    """
    Setup a site catalog query based on query parameters.

    Any filtering of content will still automatically pull in containers and
    referenced items of matched content regardless of whether they match
    the query to maintain consistency.
    """
    # sorting on created, gets us containers before children
    query = {'sort_on': 'created'}

    # sync by type
    if options.types:
        types = filter(None, [t.strip() for t in options.types.split(',')])
        if types:
            query['portal_type'] = {'query': types, 'operator': 'or'}

    # sync by folder
    if options.path:
        path = filter(None, [p.strip() for p in options.path.split(',')])
        if path:
            query['path'] = {'query': path, 'depth': 0, 'operator': 'or'}

    # incremental sync, based on most recent database content date.
    if options.incremental:
        last_sync_query = rdb.select(
            [rdb.func.max((schema.content.c.modification_date))])
        last_sync = last_sync_query.execute().scalar()
        if last_sync: # increment 1s
            time_tuple = list(last_sync.timetuple())
            time_tuple[4] = time_tuple[4]+1
            last_sync = DateTime(time.mktime(tuple(time_tuple)))
            query['modified'] = {'query': last_sync, 'range': 'min'}

    return query


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


def check_peer(obj):
    registry = component.queryUtility(IPeerRegistry)
    if not obj.portal_type in registry:
        print("Loading model for {0}".format(obj.portal_type))
        load(obj.portal_type)


def run_bulk_as_script(threshold=500):
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

    count = 0 # how many objects have we processed

    start_time = time.time()
    batch_time = start_time # we track the time for each batch
    # sorting on created, gets us containers before children
    query = {'sort_on': 'created'}

    query = setup_query(options)
    for brain in site.portal_catalog.unrestrictedSearchResults(**query):
        try:
            obj = brain.getObject()
            # skip broken objects
            if not obj.UID():
                continue
        except: # got to keep on moving
            continue

        mirrored = behaviors.IMirroredContent(obj, None)
        if mirrored is None:
            expunge(obj)
            continue

        check_peer(obj)

        count += 1

        # the object may have been processed by as a dependency
        # so we use update, which dispatches to add if no db
        # state is found.
        print("Importing object {0}".format('/'.join(obj.getPhysicalPath())))
        if not interfaces.IMirrored.providedBy(obj):
            alsoProvides(obj, interfaces.IMirrored)
        interfaces.ISerializer(obj).update()
        expunge(obj)

        if count % threshold == 0:
            transaction.commit()
            if options.verbose:
                output = ("Processed ", str(count), "in",
                          "%0.2f s"%(time.time()-batch_time))
                print(" ".join(output)+"\n")
            obj._p_jar._cache.incrgc()
            batch_time = time.time()

    # commit the last batch
    transaction.commit()

    if options.verbose:
        output = ("Processed ", str(count), "in",
                  "%0.2f s"%(time.time()-batch_time))
        print(" ".join(output)+"\n")

    if options.verbose:
        output = ("Finished in", str(time.time()-start_time))
        print(" ".join(output)+"\n")

# If this script lives in your source tree, then we need to use this trick so that
# five.grok, which scans all modules, does not try to execute the script while
# modules are being loaded on the start-up
if "app" in locals():
    run_bulk_as_script()
