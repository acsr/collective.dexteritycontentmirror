import logging
from five import grok
from plone import api
from plone.dexterity.utils import iterSchemata
from zope.interface import Interface
from zope.interface import implements
from zope.interface import directlyProvides
from zope import component
from zope.schema import getFieldsInOrder
from Acquisition import aq_base
from collective.indexing.interfaces import IIndexQueueProcessor
from collective.indexing.indexer import IPortalCatalogQueueProcessor

from collective.dexteritycontentmirror.interfaces import IMirroredContent
from collective.dexteritycontentmirror.interfaces import IMirrored
from collective.dexteritycontentmirror.interfaces import ISerializer
from collective.dexteritycontentmirror.interfaces import IPeerRegistry
from collective.dexteritycontentmirror.loader import load


LOGGER = logging.getLogger('collective.dexteritycontentmirror')


class IndexQueueProcessor(grok.GlobalUtility):

    grok.implements(IIndexQueueProcessor)
    grok.provides(IPortalCatalogQueueProcessor)
    grok.name(u'contentmirrorindexer')

    def _check_peer(self, obj):
        registry = component.queryUtility(IPeerRegistry)
        if not obj.portal_type in registry:
            LOGGER.info("Loading model for {0}".format(obj.portal_type))
            load(obj.portal_type)


    def index(self, obj, attributes=[]):
        mirrored = IMirroredContent(obj, None)
        if mirrored is None:
            return

        LOGGER.info("INDEX {0}".format('/'.join(obj.getPhysicalPath())))

        self._check_peer(obj)

        directlyProvides(obj, IMirrored)
        ISerializer(obj).add()

    def reindex(self, obj, attributes=[]):
        mirrored = IMirroredContent(obj, None)
        if mirrored is None:
            return

        LOGGER.info("REINDEX {0}".format('/'.join(obj.getPhysicalPath())))

        self._check_peer(obj)

        directlyProvides(obj, IMirrored)
        ISerializer(obj).update()

    def unindex(self, obj):
        if aq_base(obj).__class__.__name__ == 'PathWrapper':
            # Could be a PathWrapper object from collective.indexing.
            obj = obj.context

        mirrored = IMirroredContent(obj, None)
        if mirrored is None:
            return
        
        LOGGER.info("UNINDEX {0}".format('/'.join(obj.getPhysicalPath())))

        self._check_peer(obj)

        directlyProvides(obj, IMirrored)
        ISerializer(obj).delete()

    def begin(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass
