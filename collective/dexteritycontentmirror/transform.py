import logging
from hashlib import md5
from datetime import datetime

import sqlalchemy as rdb
from sqlalchemy import orm
from five import grok
from zope import interface
from zope import component
from zope.schema import getFieldsInOrder
from plone.dexterity.utils import iterSchemata
from plone.app.textfield.value import RichTextValue

from collective.dexteritycontentmirror.session import Session
from collective.dexteritycontentmirror import interfaces
from collective.dexteritycontentmirror import schema


LOGGER = logging.getLogger('collective.dexteritycontentmirror')


class SchemaTransformer(grok.MultiAdapter):
    """
    the schema transformer is stateful and in memory persistent, its
    responsible for parsing the at schema and transforming it to a
    database table.

    its also responsible for copying an object state from an instance to
    a peer.
    """
    grok.implements(interfaces.ISchemaTransformer)
    grok.adapts(interfaces.IMirrored, interfaces.IMetaData)

    def __init__(self, context, metadata):
        self.context = context
        self.metadata = metadata
        self.table = None
        self.properties = {}

    def transform(self):
        columns = list(self.columns())
        self.table = rdb.Table(self.name,
                               self.metadata,
                               useexisting=True,
                               *columns)
        return self.table

    def copy(self, instance, peer):
        for schema in iterSchemata(self.context):
            for name, field in getFieldsInOrder(schema):
                transformer = component.queryMultiAdapter((field, self),
                    interfaces.IFieldTransformer)
                transformer.copy(instance, peer)

    @property
    def name(self):
        return self.context.portal_type

    def filter(self, field):
        # return false if filter, true if ok
        return True

    def columns(self):
        yield rdb.Column("content_id",
            rdb.Integer,
            rdb.ForeignKey('content.content_id',
                ondelete="CASCADE"),
            primary_key=True)

        for schema in iterSchemata(self.context):
            for name, field in getFieldsInOrder(schema):
                if not self.filter(field):
                    continue

                LOGGER.info("TRANSFROM FIELD: {0}".format(name))

                transformer = component.getMultiAdapter((field, self),
                    interfaces.IFieldTransformer)
                result = transformer.transform()

                if isinstance(result, rdb.Column):
                    yield result


class NamedFieldTransform(object):
    """
    Encapsulates database column naming.
    """

    @property
    def name(self):
        name = self.context.__name__.lower()
        return self._get_name(name)

    def _get_name(self, name):
        name = name.replace(' ', '_')
        if name in self._reserved_names:
            name = "dx_" + name
        return name

    @property
    def _reserved_names(self):
        e = self.transformer.metadata.bind
        if e is None:
            return ()
        return e.dialect.preparer.reserved_words


class BaseFieldTransformer(NamedFieldTransform):

    interface.implements(interfaces.IFieldTransformer)

    column_type = rdb.String
    column_args = ()

    def __init__(self, context, transformer):
        self.context = context
        self.transformer = transformer

    def transform(self):
        args, kw = self._extractDefaults()
        column = rdb.Column(self.name,
                            self.column_type(*self.column_args),
                            *args,
                            **kw)

        self.transformer.properties[self.name] = column
        return column

    def copy(self, instance, peer):
        storage = self.context.interface(instance)
        value = self.context.get(storage)
        setattr(peer, self.name, value)

    def _extractDefaults(self):
        args = []
        kwargs = {}
        return args, kwargs


class StringTransform(BaseFieldTransformer):
    component.adapts(interfaces.IStringField, interfaces.ISchemaTransformer)
    column_type = rdb.Text
    column_args = ()

    def copy(self, instance, peer):
        storage = self.context.interface(instance)
        value = self.context.get(storage)

        if isinstance(value, (tuple, list, set)):
            return LinesTransform(self.context, self.transformer).copy(
                instance, peer)
        
        if isinstance(value, RichTextValue):
            value = value.raw
        
        # at least morph it into a value which won't cause further issues.
        if not isinstance(value, basestring):
            value = str(value)

        setattr(peer, self.name, value)


class RichTextTransform(BaseFieldTransformer):
    component.adapts(interfaces.IRichTextField, interfaces.ISchemaTransformer)
    column_type = rdb.Text
    column_args = ()

    def copy(self, instance, peer):
        storage = self.context.interface(instance)
        value = self.context.get(storage)
        
        if isinstance(value, RichTextValue):
            value = value.raw
        
        setattr(peer, self.name, value)


class TextTransform(BaseFieldTransformer):
    component.adapts(interfaces.IStringField, interfaces.ISchemaTransformer)
    column_type = rdb.Text
    column_args = ()


class LinesTransform(StringTransform):
    component.adapts(interfaces.ILinesField, interfaces.ISchemaTransformer)

    def copy(self, instance, peer):
        storage = self.context.interface(instance)
        value = self.context.get(storage)
        if isinstance(value, (list, tuple, set)):
            value = "\n".join(value)
        setattr(peer, self.name, value)


class FileTransform(NamedFieldTransform):
    """
    a file field serializer that utilizes a file peer.
    """
    interface.implements(interfaces.IFieldTransformer)
    component.adapts(interfaces.IFileField, interfaces.ISchemaTransformer)

    def __init__(self, context, transformer):
        self.context = context
        self.transformer = transformer

    def transform(self):
        file_orm = orm.relation(
            schema.File,
            cascade='all',
            uselist=False,
            primaryjoin=rdb.and_(
                schema.files.c.content_id == schema.content.c.content_id,
                schema.files.c.attribute == self.name))

        self.transformer.properties[self.name] = file_orm

    def copy(self, instance, peer):
        storage = self.context.interface(instance)
        value = self.context.get(storage)
        if not value:
            return
        file_peer = self._getPeer(instance, peer)
        if not self._checkModified(value, file_peer):
            return
        self._copyPeer(file_peer, instance, value)
        setattr(peer, self.name, file_peer)

    def new(self):
        return schema.File()

    def _checkModified(self, value, peer):
        checksum = md5(str(value.data)).hexdigest()
        if peer.checksum == checksum:
            return False
        return True

    def _getPeer(self, instance, peer):
        file_peer = getattr(peer, self.name, None)
        if not file_peer:
            return self.new()
        return file_peer

    def _copyPeer(self, file_peer, instance, value):
        file_peer.attribute = self.name
        file_peer.content = str(value.data)
        file_peer.mime_type = value.contentType
        file_peer.file_size = len(file_peer.content)
        file_peer.file_name = value.filename
        file_peer.checksum = md5(file_peer.content).hexdigest()


class ImageTransform(FileTransform):
    component.adapts(interfaces.IImageField, interfaces.ISchemaTransformer)


class BooleanTransform(BaseFieldTransformer):
    component.adapts(interfaces.IBooleanField, interfaces.ISchemaTransformer)
    column_type = rdb.Boolean


class IntegerTransform(BaseFieldTransformer):
    component.adapts(interfaces.IIntegerField, interfaces.ISchemaTransformer)
    column_type = rdb.Integer


class FloatTransform(BaseFieldTransformer):
    component.adapts(interfaces.IFloatField, interfaces.ISchemaTransformer)
    column_type = rdb.Float


class DateTimeTransform(BaseFieldTransformer):
    column_type = rdb.DateTime
    component.adapts(interfaces.IDateTimeField, interfaces.ISchemaTransformer)

    def copy(self, instance, peer):
        storage = self.context.interface(instance)
        value = self.context.get(storage)
        if not value:
            return
        #value = datetime.fromtimestamp(value.timeTime())
        setattr(peer, self.name, value)


class ReferenceTransform(NamedFieldTransform):
    component.adapts(interfaces.IReferenceField, interfaces.ISchemaTransformer)
    interface.implements(interfaces.IReferenceField)

    def __init__(self, context, transformer):
        self.context = context
        self.transformer = transformer

    def transform(self):
        """
        For multi-valued references do nothing, as we'll use the generic
        relation table. For single valued references we'll directly create
        a foreign key reference to the content table.
        """
        if self.context.multiValued:
            return
        column_name = self.name+'_id'
        column = rdb.Column(
            column_name, rdb.Integer(),
            rdb.ForeignKey("content.content_id", ondelete="SET NULL"))
        relation = orm.relation(
            schema.Content,
            uselist=False,
            primaryjoin=(column == schema.content.c.content_id))
        self.transformer.properties[self.name] = relation
        self.transformer.properties[column_name] = column
        return column

    def copySingleValue(self, instance, peer):
        storage = self.context.interface(instance)
        value = self.context.get(storage)
        if isinstance(value, (list, tuple)):
            if len(value) >= 1:
                value = value[0]
            else:
                value = None
        if not value:
            setattr(peer, self.name+'_id', None)
        else:
            reference_peer = self._fetch_peer(value)
            if not reference_peer:
                return
            setattr(peer, self.name, reference_peer)

    def _fetch_peer(self, ob):
        peer_ob = schema.fromUID(ob.UID())
        if peer_ob is None:
            serializer = interfaces.ISerializer(ob, None)
            if serializer is None:
                return None
            peer_ob = serializer.add()
        return peer_ob

    def copy(self, instance, peer):
        single_value = not self.context.multiValued
        if single_value:
            return self.copySingleValue(instance, peer)

        storage = self.context.interface(instance)
        value = self.context.get(storage)
        if not value:
            return

        if not isinstance(value, (list, tuple)):
            value= [value]

        value = filter(None, value) # filter empty values, ie. bad data

        rel_map = dict([((r.relationship, r.target.content_uid), r)
                        for r in peer.relations])
        oids_seen = set() # oids of the current reference values of this field

        for ob in value:
            t_oid = ob.UID()
            oids_seen.add(t_oid)

            # skip if the object is already related
            related = (self.context.relationship, t_oid) in rel_map
            if related:
                continue

            # fetch the remote side's peer
            reference_peer = self._fetch_peer(ob)
            if not reference_peer:
                continue

            # create the relation
            relation = schema.Relation(peer,
                                       reference_peer,
                                       self.context.relationship)

        # delete old values for multi valued relations
        rel_oids = set([oid for rel_type, oid in rel_map
                        if rel_type == self.context.relationship])
        for oid in (rel_oids - oids_seen):
            Session().delete(rel_map[(self.context.relationship, oid)])
