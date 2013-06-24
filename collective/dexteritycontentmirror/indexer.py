import logging
from five import grok
from zope.interface import directlyProvides
from zope import component
from Acquisition import aq_base
from collective.indexing.interfaces import IIndexQueueProcessor
from collective.indexing.indexer import IPortalCatalogQueueProcessor

from collective.dexteritycontentmirror import interfaces
from collective.dexteritycontentmirror import behaviors
from collective.dexteritycontentmirror.loader import load


LOGGER = logging.getLogger('collective.dexteritycontentmirror')


class IndexQueueProcessor(grok.GlobalUtility):

    grok.implements(IIndexQueueProcessor)
    grok.provides(IPortalCatalogQueueProcessor)
    grok.name(u'contentmirrorindexer')

    def _check_peer(self, obj):
        registry = component.queryUtility(interfaces.IPeerRegistry)
        if not obj.portal_type in registry:
            LOGGER.info("Loading model for {0}".format(obj.portal_type))
            load(obj.portal_type)


    def index(self, obj, attributes=[]):
        mirrored = behaviors.IMirroredContent(obj, None)
        if mirrored is None:
            return

        LOGGER.info("INDEX {0}".format('/'.join(obj.getPhysicalPath())))

        self._check_peer(obj)

        directlyProvides(obj, interfaces.IMirrored)
        interfaces.ISerializer(obj).add()

    def reindex(self, obj, attributes=[]):
        mirrored = behaviors.IMirroredContent(obj, None)
        if mirrored is None:
            return

        LOGGER.info("REINDEX {0}".format('/'.join(obj.getPhysicalPath())))

        self._check_peer(obj)

        directlyProvides(obj, interfaces.IMirrored)
        interfaces.ISerializer(obj).update()

    def unindex(self, obj):
        if aq_base(obj).__class__.__name__ == 'PathWrapper':
            # Could be a PathWrapper object from collective.indexing.
            obj = obj.context

        mirrored = behaviors.IMirroredContent(obj, None)
        if mirrored is None:
            return
        
        LOGGER.info("UNINDEX {0}".format('/'.join(obj.getPhysicalPath())))

        self._check_peer(obj)

        directlyProvides(obj, interfaces.IMirrored)
        interfaces.ISerializer(obj).delete()

    def begin(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass
