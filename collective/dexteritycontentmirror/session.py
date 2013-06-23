from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension

Session = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
