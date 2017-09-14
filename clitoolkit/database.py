# -*- coding: utf-8 -*-
"""Database models, connection and events."""
import os

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String,
                        create_engine, event)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from clitoolkit import CONFIG_DIR, TIME_FORMAT

ENGINE = create_engine('sqlite:///{}'.format(os.path.join(CONFIG_DIR, 'database.sqlite')))
BASE_MODEL = declarative_base()
SESSION_CLASS = sessionmaker(bind=ENGINE)
SESSION_INSTANCE = SESSION_CLASS()

# SQLAlchemy models don't need __init__()
# pylint: disable=no-init


@event.listens_for(ENGINE, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign keys in SQLite.

    See http://docs.sqlalchemy.org/en/rel_0_9/dialects/sqlite.html#sqlite-foreign-keys

    :param dbapi_connection:
    :param connection_record:
    """
    assert connection_record
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Video(BASE_MODEL):
    """Video file, with path and size."""

    __tablename__ = 'video'

    video_id = Column(Integer, primary_key=True)
    path = Column(String, nullable=False, unique=True)
    size = Column(Integer, nullable=False)

    def __repr__(self):
        """Represent a video as a string."""
        return "<Video(path='{}', size='{}')>".format(self.path, self.size)


class WindowLog(BASE_MODEL):
    """Log entry for an open window."""

    __tablename__ = 'window_log'

    window_log_id = Column(Integer, primary_key=True)

    start_dt = Column(DateTime, nullable=False)
    end_dt = Column(DateTime, nullable=False)
    app_name = Column(String, nullable=False)
    title = Column(String, nullable=False)

    video_id = Column(Integer, ForeignKey('video.video_id'))

    def __repr__(self):
        """Represent a window log as a string."""
        diff = self.end_dt - self.start_dt
        return "<WindowLog({start} to {end} ({diff}) {app}: '{title}' ({id}))>".format(
            app=self.app_name, title=self.title, diff=diff, id=self.video_id,
            start=self.start_dt.strftime(TIME_FORMAT),
            end=self.end_dt.strftime(TIME_FORMAT))


# After all models are declared, create them.
BASE_MODEL.metadata.create_all(ENGINE)