from zope import schema
from zope.component import adapts
from zope.interface import alsoProvides
from zope.interface import implements
from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model

from collective.dexteritycontentmirror import MessageFactory as _


class IMirroredContent(model.Schema):
    """
    Marker/Form interface for MirroredContent behavior
    """

alsoProvides(IMirroredContent, IFormFieldProvider)


class MirroredContent(object):
    implements(IMirroredContent)
    adapts(IDexterityContent)

    def __init__(self,context):
        self.context = context
