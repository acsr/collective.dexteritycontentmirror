"""
The Model Loader drives the startup bootstrapping, its wired into the
zcml directives, its responsible for loading/generating the tables,
and creating the rdb mapped peer classes.
"""
from zope import component
from zope.interface import directlyProvides
from plone.dexterity.utils import createContent

from collective.dexteritycontentmirror import schema
from collective.dexteritycontentmirror import interfaces


class ModelLoader(object):

    def __init__(self, metadata):
        self.metadata = metadata

    def load(self, klass):
        registry = component.queryUtility(interfaces.IPeerRegistry)
        if klass in registry:
            raise KeyError("Duplicate %r"%klass)

        instance = createContent(klass)
        directlyProvides(instance, interfaces.IMirrored)

        transformer = self.transform(instance)
        peer_class = self.peer(instance, transformer)

        registry[klass] = peer_class

    def transform(self, instance):
        transformer = component.getMultiAdapter((instance, self.metadata),
            interfaces.ISchemaTransformer)
        transformer.transform()
        return transformer

    def peer(self, instance, transformer):
        factory = component.getMultiAdapter((instance, transformer),
            interfaces.IPeerFactory)
        return factory.make()

loader = ModelLoader(schema.metadata)
load = loader.load
