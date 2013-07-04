"""
The Model Loader drives the startup bootstrapping, its wired into the
zcml directives, its responsible for loading/generating the tables,
and creating the rdb mapped peer classes.
"""
import logging
from Products.CMFCore.utils import getToolByName
from Products.CMFCore.interfaces import ISiteRoot
from zope import component
from zope.interface import alsoProvides
from zope.component import providedBy
from zope.component import queryUtility
from zope.component.hooks import getSite
from plone.dexterity.utils import createContent
from plone.dexterity.interfaces import IDexterityFTI
from plone.behavior.interfaces import IBehavior
from plone.behavior.interfaces import IBehaviorAssignable

from collective.dexteritycontentmirror import schema
from collective.dexteritycontentmirror import behaviors
from collective.dexteritycontentmirror import interfaces


LOGGER = logging.getLogger('collective.dexteritycontentmirror')


class ModelLoader(object):

    def __init__(self, metadata):
        self.metadata = metadata

    def load(self, klass):
        registry = component.queryUtility(interfaces.IPeerRegistry)
        if klass in registry:
            raise KeyError("Duplicate %r"%klass)

        instance = createContent(klass)
        alsoProvides(instance, interfaces.IMirrored)

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


def _get_portal():
    closest_site = getSite()
    if closest_site is not None:
        for potential_portal in closest_site.aq_chain:
            if ISiteRoot in providedBy(potential_portal):
                return potential_portal
    raise Exception("Unable to get the portal object.")


def _has_behavior(portal_type, klass):
    fti = queryUtility(IDexterityFTI, portal_type, None)
    if not fti is None:
        for behavior_name in fti.behaviors:
            behavior_instance = queryUtility(IBehavior, name=behavior_name)
            if not behavior_instance is None and \
                behavior_instance.interface is klass:
                return True
    return False


def load_models(portal=None):
    if portal is None:
        portal = _get_portal()
    portal_types = getToolByName(portal, "portal_types")
    for portal_type in portal_types:
        if _has_behavior(portal_type, behaviors.IMirroredContent):
            LOGGER.info('LOAD MODEL {0}'.format(portal_type))
            loader.load(portal_type)
