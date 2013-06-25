import logging
import sqlalchemy as rdb
from five import grok
from zope import interface, component
from zope.app.container.interfaces import IContainer
from plone import api

try: # mock test environment compatibility
    from OFS.interfaces import IOrderedContainer
except:
    class IOrderedContainer(interface.Interface): pass

from collective.dexteritycontentmirror import schema
from collective.dexteritycontentmirror import interfaces
from collective.dexteritycontentmirror.session import Session


LOGGER = logging.getLogger('collective.dexteritycontentmirror')


class Serializer(grok.Adapter):

    grok.implements(interfaces.ISerializer)
    grok.context(interfaces.IMirrored)

    def __init__(self, context):
        self.context = context

    def add(self):
        peer = schema.fromUID(self.context.UID())
        if not peer is None:
            return
        registry = component.getUtility(interfaces.IPeerRegistry)
        peer = registry[self.context.portal_type]()
        session = Session()
        session.add(peer)
        self._copy(peer)
        return peer

    def update(self):
        peer = schema.fromUID(self.context.UID())
        if peer is None:
            return self.add()
        self._copy(peer)
        return peer

    def delete(self):
        peer = schema.fromUID(self.context.UID())
        if peer is None:
            return
        session = Session()
        session.delete(peer)
        session.flush()
    
    def _copy(self, peer):
        self._copyPortalAttributes(peer)
        peer.transformer.copy(self.context, peer)
        self._copyContainment(peer)

    def _copyPortalAttributes(self, peer):
        peer.portal_type = self.context.portal_type
        peer.content_uid = self.context.UID()
        peer.id = self.context.id

        peer.path = '/'.join(self.context.getPhysicalPath())
        portal_url = getattr(self.context, 'portal_url', None)
        if portal_url:
            peer.relative_path = "/".join(
                portal_url.getRelativeContentPath(self.context))
        peer.status = api.content.get_state(obj=self.context)

        container = self.context.getParentNode()
        if not IOrderedContainer.providedBy(container):
            return

        peer.folder_position = container.getObjectPosition(
            self.context.getId())

    def _copyContainment(self, peer):
        container = self.context.getParentNode()
        if container is None:
            return
        uid = getattr(container, 'UID', None)
        if uid is None:
            return
        uid = uid()
        container_peer = schema.fromUID(uid)
        if not container_peer:
            serializer = interfaces.ISerializer(container, None)
            if not serializer:
                return
            container_peer = serializer.add()
        peer.parent = container_peer
