from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model
from zope import schema
from zope.component import adapts
from zope.interface import alsoProvides, implements

from collective.dexteritycontentmirror import MessageFactory as _
from collective.dexteritycontentmirror.interfaces import IMirroredContent


class MirroredContent(object):
    implements(IMirroredContent)
    adapts(IDexterityContent)

    def __init__(self,context):
        self.context = context
