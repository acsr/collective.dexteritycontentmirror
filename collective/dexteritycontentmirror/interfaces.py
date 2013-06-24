from plone.autoform.interfaces import IFormFieldProvider
from plone.dexterity.interfaces import IDexterityContent
from plone.supermodel import model
from zope import schema
from zope.component import adapts
from zope.interface import alsoProvides
from zope.interface import implements
from zope.interface import interface

from collective.dexteritycontentmirror import MessageFactory as _


class IMirrored(interface.Interface):
    """
    Marker interface, signifying that the content should be mirrored
    to a database
    """


class IDatabaseEngine(interface.Interface):
    """
    Configuration and access to a sqlalchemy pooled database connection.
    """


class IMetaData(interface.Interface):
    """
    Marker interface for sqlalchemy metadata, to allow for use
    in adaptation.
    """


class ISchemaTransformer(interface.Interface):
    """ translate an schema to a relational schema """

    metadata = interface.Attribute("metadata")

    def transform():
        """
        return a sqlalchemy database table representation
        """


class IFieldTransformer(interface.Interface):
    """ transforms an field into a sqlalchemy field """

    def transform():
        """
        returns the equivalent sqlalchemy field
        """

    def copy(instance, peer):
        """
        copies the field value from the instance to the peer.
        """


########################################
## Content Peers
########################################

class IContentPeer(interface.Interface):
    """
    A relational persisted class that has a mirror of attributes
    of a portal content class.
    """

    transformer = schema.Object(ISchemaTransformer)


class IContentFile(interface.Interface):
    """A File."""


class IPeerFactory(interface.Interface):
    """An object can make peer classes."""

    def make():
        """
        create a peer class, with a mapper, returns the mapped orm class
        """


class IPeerRegistry(interface.Interface):
    """ a registry mapping a content class to its orm peer class """


class ISerializer(interface.Interface):

    def add():
        """
        add the object to the database
        """

    def delete():
        """
        delete the object from the database
        """

    def update():
        """
        update the object state in the database
        """


######################################
## Interface Specifications for Fields
######################################

class IStringField(interface.Interface):
    """String Field"""


class IBooleanField(interface.Interface):
    """Boolean Field"""


class IIntegerField(interface.Interface):
    """Integer Field"""


class IFloatField(interface.Interface):
    """Float Field"""


class IReferenceField(interface.Interface):
    """Reference Field """


class ILinesField(interface.Interface):
    """Lines Field """


class IFileField(interface.Interface):
    """Field Field """


class IImageField(interface.Interface):
    """Image Field """


class ITextField(interface.Interface):
    """Text Field """


class IRichTextField(interface.Interface):
    """Rich Text Field """


class IDateTimeField(interface.Interface):
    """DateTime Field """
