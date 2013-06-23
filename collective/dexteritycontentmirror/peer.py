from sqlalchemy import orm
from five import grok
from zope import interface

from collective.dexteritycontentmirror import schema
from collective.dexteritycontentmirror import interfaces


class PeerFactory(grok.MultiAdapter):

    grok.implements(interfaces.IPeerFactory)
    grok.adapts(interfaces.IMirrored, interfaces.ISchemaTransformer)

    def __init__(self, context, transformer):
        self.context = context
        self.transformer = transformer

    @property
    def name(self):
        return self.context.portal_type + 'Peer'

    def make(self):
        klass = type(self.name, (schema.Content,),
            dict(transformer=self.transformer))

        # With single value references creating additional foreign
        # keys to the content table, we need to distinguish the
        # join condition for the class inheritance.
        if self.transformer.table is not None:
            # unit tests exercise a custom transformer without a table.
            join_clause = (
                self.transformer.table.c.content_id == \
                schema.content.c.content_id)
        else:
            join_clause = None

        orm.mapper(klass,
                   self.transformer.table,
                   properties=dict(self.transformer.properties),
                   inherits=schema.Content,
                   inherit_condition=join_clause,
                   polymorphic_on=schema.content.c.object_type,
                   polymorphic_identity=self.name)
        return klass


class PeerRegistry(grok.GlobalUtility):

    grok.implements(interfaces.IPeerRegistry)

    def __init__(self):
        self._peer_classes = {}

    def __setitem__(self, key, value):
        self._peer_classes[key] = value

    def __getitem__(self, key):
        """
        Lookup the peer class using the content class as the key. If
        not found try find a peer using the content's base classes.
        Either returns a suitable peer class or raises a KeyError.
        """
        if key in self._peer_classes:
            return self._peer_classes[key]

        '''
        TODO:
        for base in key.mro():
            factory = self._peer_classes.get(base, None)
            if factory is not None:
                self._peer_classes[key] = factory # cache
                break
        '''
        factory = self._peer_classes.get(key, None)
        if factory is not None:
            self._peer_classes[key] = factory # cache
        
        return self._peer_classes[key]

    def __contains__(self, key):
        # must not check base classes here
        return key in self._peer_classes

    def items(self):
        return self._peer_classes.items()
