# -*- coding: utf-8 -*-
"""
Media tools
"""
import os
import logging
import pipes
from collections import defaultdict
from datetime import datetime
from time import sleep
from subprocess import check_output, CalledProcessError

from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, event, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.orm.exc import NoResultFound


CONFIG_DIR = os.path.expanduser(os.path.join('~/.config/clitoolkit', ''))
os.makedirs(CONFIG_DIR, exist_ok=True)

EXTENSIONS = ['.asf', '.avi', '.divx', '.f4v', '.flc', '.flv', '.m4v', '.mkv',
              '.mov', '.mp4', '.mpa', '.mpeg', '.mpg', '.ogv', '.wmv']
MINIMUM_VIDEO_SIZE = 10 * 1000 * 1000  # 10 megabytes
VIDEO_ROOT_PATH = os.path.join(os.environ.get('VIDEO_ROOT_PATH', ''), '')
APPS = ['vlc.Vlc', 'feh.feh', 'google-chrome', 'Chromium-browser.Chromium-browser']
PIPEFILE = 'pipefile.tmp'
TIME_FORMAT = '%H:%M:%S'

logger = logging.getLogger(__name__)
engine = create_engine('sqlite:///{}'.format(os.path.join(CONFIG_DIR, 'media.sqlite')))
Base = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()


@event.listens_for(Engine, "connect")
def enable_foreign_keys(dbapi_connection, connection_record):
    """Enable foreign keys in SQLite.
    See http://docs.sqlalchemy.org/en/rel_0_9/dialects/sqlite.html#sqlite-foreign-keys

    :param dbapi_connection:
    :param connection_record:
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def check_video_root_path():
    """Check if there is an environment variable with the video root path.

    :return:
    """
    if not VIDEO_ROOT_PATH:
        raise ValueError('The environment variable VIDEO_ROOT_PATH must contain the video root directory')


class Video(Base):
    """Video file, with path and size."""
    __tablename__ = 'video'

    video_id = Column(Integer, primary_key=True)
    path = Column(String, nullable=False, unique=True)
    size = Column(Integer, nullable=False)

    def __repr__(self):
        return "<Video(path='{}', size='{}')>".format(self.path, self.size)


class WindowLog(Base):
    """Log entry for an open window."""
    __tablename__ = 'window_log'

    window_id = Column(Integer, primary_key=True)

    start_dt = Column(DateTime, nullable=False)
    end_dt = Column(DateTime, nullable=False)
    app_name = Column(String, nullable=False)
    title = Column(String, nullable=False)

    video_id = Column(Integer, ForeignKey('video.video_id'))

    def __repr__(self):
        diff = self.end_dt - self.start_dt
        return "<WindowLog({start} to {end} ({diff}) {app}: '{title}' ({id}))>".format(
            app=self.app_name, title=self.title, diff=diff, id=self.video_id,
            start=self.start_dt.strftime(TIME_FORMAT),
            end=self.end_dt.strftime(TIME_FORMAT))


def scan_video_files():
    """Scan all video files in subdirectories, ignoring videos with less than 10 MB.
    Save the videos in SQLite.

    :return: None
    """
    check_video_root_path()
    # http://stackoverflow.com/questions/18394147/recursive-sub-folder-search-and-return-files-in-a-list-python
    for partial_path in [os.path.join(root, file).replace(VIDEO_ROOT_PATH, '')
                         for root, dirs, files in os.walk(VIDEO_ROOT_PATH)
                         for file in files if os.path.splitext(file)[1].lower() in EXTENSIONS]:
        full_path = os.path.join(VIDEO_ROOT_PATH, partial_path)
        # http://stackoverflow.com/questions/2104080/how-to-check-file-size-in-python
        size = os.stat(full_path).st_size
        if size > MINIMUM_VIDEO_SIZE:
            session.add(Video(path=partial_path, size=size))
            session.commit()


def list_windows():
    """List current windows from selected applications.
    Always return at least one element in each application list, even if it's an empty title.
    This is needed by the window monitor to detect when an application was closed,
        and still log a title change.

    :return: Window titles grouped by application.
    :rtype dict
    """
    grep_args = ' -e '.join(APPS)
    t = pipes.Template()
    t.prepend('wmctrl -l -x', '.-')
    t.append('grep -e {}'.format(grep_args), '--')
    with t.open_r(PIPEFILE) as f:
        lines = f.read()

    windows = {app: [] for app in APPS}
    for line in lines.split('\n'):
        words = line.split()
        if words:
            app = words[2]
            if app not in windows.keys():
                windows[app] = []
            title = ' '.join(words[4:])
            if app.startswith('vlc'):
                title = ''
                open_files = list_vlc_open_files(False)
                if open_files:
                    windows[app].extend(open_files)
                    continue
            windows[app].append(title)
    return {key: value if value else [''] for key, value in windows.items()}


def list_vlc_open_files(full_path=True):
    """List files opened by VLC in the root directory.

    :param full_path: True to show full path, False to strip the video root path.
    :return: Files currently opened.
    :rtype list
    """
    check_video_root_path()
    t = pipes.Template()
    t.prepend('lsof -F n -c vlc 2>/dev/null', '.-')
    t.append("grep '^n{}'".format(VIDEO_ROOT_PATH), '--')
    with t.open_r(PIPEFILE) as f:
        files = f.read()
    return [file[1:].replace(VIDEO_ROOT_PATH, '') if not full_path else file[1:]
            for file in files.strip().split('\n') if file]


def window_monitor(save_logs=True):
    """Loop to monitor open windows of the selected applications.
    An app can have multiple windows, each one with its title.

    :param save_logs: True to save logs (default), False to only display what would be saved (dry run).
    :return:
    """
    last = {}
    monitor_start_time = datetime.now()
    print('Starting the window monitor now ({})...'.format(monitor_start_time.strftime(TIME_FORMAT)))
    try:
        while True:
            sleep(.2)

            for app, new_titles in list_windows().items():
                assert isinstance(app, str)
                assert isinstance(new_titles, list)

                if app not in last.keys():
                    last[app] = defaultdict(tuple)

                for index, new_title in enumerate(new_titles):
                    if last[app][index] and last[app][index][1] == new_title:
                        continue

                    last_info = last[app][index]
                    # Time since last saved time, or since the beginning of the monitoring
                    start_time = last_info[0] if last_info else monitor_start_time
                    end_time = datetime.now()
                    # Save time info for the next change of window title
                    last[app][index] = (end_time, new_title)
                    if new_title:
                        print("{} Open window in {}: {}".format(end_time.strftime(TIME_FORMAT), app, new_title))

                    # Save logs only after the first change of title
                    old_title = last_info[1] if last_info else ''
                    if not old_title:
                        continue

                    try:
                        video = session.query(Video).filter(Video.path == old_title).one()
                        video_id = video.video_id
                    except NoResultFound:
                        video_id = None

                    window_log = WindowLog(start_dt=start_time, end_dt=end_time, app_name=app,
                                           title=old_title, video_id=video_id)
                    print(window_log)
                    if save_logs:
                        session.add(window_log)
                        session.commit()
    except KeyboardInterrupt:
        return


def is_vlc_running():
    """Check if VLC is running.

    :return: True if VLC is running.
    :rtype bool
    """
    try:
        check_output(['pidof', 'vlc'])
        return True
    except CalledProcessError:
        return False


def add_to_playlist(videos):
    """Add one or more videos to VLC's playlist.

    :param videos: One or more video paths.
    :type videos list|str
    :return: True if videos were added to the playlist.
    :rtype bool
    """
    if not is_vlc_running():
        logger.error('VLC is not running, please open it first.')
        return False

    videos = [videos] if isinstance(videos, str) else videos
    t = pipes.Template()
    t.append('xargs -0 vlc --quiet --no-fullscreen --no-auto-preparse --no-playlist-autostart', '--')
    with t.open_w(PIPEFILE) as f:
        f.write('\0'.join(videos))
    print('{} videos added to the playlist.'.format(len(videos)))
    return True


def query_videos_by_path(search=None):
    """Return videos from the database based on a query string.
    All spaces in the query string will be converted to %, to be used in a LIKE expression.

    :param search: Optional query strings to search; if not provided, return all videos.
    :type search str|list
    :return:
    """
    sa_filter = session.query(Video)
    if search:
        conditions = []
        search = [search] if isinstance(search, str) else search
        for query_string in search:
            clean_query = '%{}%'.format('%'.join(query_string.split()))
            conditions.append(Video.path.like(clean_query))
        sa_filter = sa_filter.filter(or_(*conditions))
    return query_to_list(sa_filter)


def query_to_list(sa_filter):
    """Output a SQLAlchemy Video query as a list of videos with full path.

    :param sa_filter: SQLAlchemy query filter.
    :type sa_filter sqlalchemy.orm.query.Query
    :return: List of videos with full path.
    """
    check_video_root_path()
    return [os.path.join(VIDEO_ROOT_PATH, video.path) for video in sa_filter.all()]


def query_not_logged_videos():
    """Return videos that were not yet logged.

    :return:
    :rtype list
    """
    return query_to_list(session.query(Video).outerjoin(
        WindowLog, Video.video_id == WindowLog.video_id).filter(
        WindowLog.video_id.is_(None)))


Base.metadata.create_all(engine)
# TODO: Convert data from $HOME/.gtimelog/window-monitor.db