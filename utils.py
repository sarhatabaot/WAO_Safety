from threading import Timer, Event, Lock
from config.config import Config
import logging
import os
import datetime
import platform
from json import JSONEncoder

default_log_level = logging.DEBUG
default_encoding = "utf-8"
default_port = 8000


class RepeatTimer(Timer):
    def __init__(self, name, interval, function):
        super(RepeatTimer, self).__init__(interval=interval, function=function)
        self.name = name
        self.interval = interval
        self.function = function
        self.stopped = Event()

    def run(self):
        while not self.stopped.wait(self.interval):
            self.function(*self.args, **self.kwargs)

    def stop(self):
        self.stopped.set()


class FixedSizeFifo:
    def __init__(self, max_size: int):
        self.max_size = max_size
        self.data = []

    def push(self, item):
        if len(self.data) >= self.max_size:
            self.data.pop(0)
        self.data.append(item)

    def latest(self):
        return self.data[0]

    def get(self):
        return self.data


class SingletonFactory:
    instances: dict = {}
    lock: Lock = Lock()

    @classmethod
    def get_instance(cls, type):
        with cls.lock:
            if type not in cls.instances:
                cls.instances[type] = type()
        return cls.instances[type]


cfg = SingletonFactory.get_instance(Config)


class PathMaker:
    top_folder: str

    def __init__(self):
        self.top_folder = os.path.join('/var', 'log', 'last')
        pass

    @staticmethod
    def make_seq(path: str):
        seq_file = os.path.join(path, '.seq')

        os.makedirs(os.path.dirname(seq_file), exist_ok=True)
        if os.path.exists(seq_file):
            with open(seq_file) as f:
                seq = int(f.readline())
        else:
            seq = 0
        seq += 1
        with open(seq_file, 'w') as file:
            file.write(f'{seq}\n')

        return seq

    def make_daily_log_folder_name(self):
        directory = os.path.join(self.top_folder, datetime.datetime.now().strftime('%Y-%m-%d'))
        os.makedirs(directory, exist_ok=True)
        return directory

    def make_logfile_name(self):
        daily_folder = self.make_daily_log_folder_name()
        return os.path.join(daily_folder, 'log.txt')


path_maker = PathMaker()


class DailyFileHandler(logging.FileHandler):

    filename: str = ''
    path: str

    def make_file_name(self):
        """
        Produces file names for the DailyFileHandler, which rotates them daily at noon (UT).
        The filename has the format <top><daily><bottom> and includes:
        * A top section (either /var/log/mast on Linux or %LOCALAPPDATA%/mast on Windows
        * The daily section (current date as %Y-%m-%d)
        * The bottom path, supplied by the user
        Examples:
        * /var/log/mast/2022-02-17/server/app.log
        * c:\\User\\User\\LocalAppData\\mast\\2022-02-17\\main.log
        :return:
        """
        top = ''
        if platform.platform() == 'Linux':
            top = os.path.join('var', 'log', 'last')
        elif platform.platform().startswith('Windows'):
            top = os.path.join(os.path.expandvars('%LOCALAPPDATA%'), 'mast')
        now = datetime.datetime.now()
        if now.hour < 12:
            now = now - datetime.timedelta(days=1)
        return os.path.join(top, f'{now:%Y-%m-%d}', self.path)

    def emit(self, record: logging.LogRecord):
        """
        Overrides the logging.FileHandler's emit method.  It is called every time a log record is to be emitted.
        This function checks whether the handler's filename includes the current date segment.
        If not:
        * A new file name is produced
        * The handler's stream is closed
        * A new stream is opened for the new file
        The record is emitted.
        :param record:
        :return:
        """
        filename = self.make_file_name()
        if not filename == self.filename:
            if self.stream is not None:
                # we have an open file handle, clean it up
                self.stream.flush()
                self.stream.close()
                self.stream = None  # See Issue #21742: _open () might fail.

            self.baseFilename = filename
            os.makedirs(os.path.dirname(self.baseFilename), exist_ok=True)
            self.stream = self._open()
        logging.StreamHandler.emit(self, record=record)

    def __init__(self, path: str, mode='a', encoding=None, delay=False, errors=None):
        self.path = path
        if "b" not in mode:
            encoding = default_encoding # io.text_encoding(encoding) # python3.10
        logging.FileHandler.__init__(self, filename='', delay=True, mode=mode, encoding=encoding)


def init_log(logger: logging.Logger):
    logger.propagate = False
    logger.setLevel(default_log_level)
    handler = logging.StreamHandler()
    handler.setLevel(default_log_level)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)-8s ' +
        '- {%(name)s:%(funcName)s:%(process)d:%(threadName)s:%(thread)s}' +
        ' -  %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler = DailyFileHandler(path=path_maker.make_logfile_name(), mode='a')
    handler.setLevel(default_log_level)
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        # Let the base class default method raise the TypeError
        return JSONEncoder.default(self, obj)


def datetime_decoder(dct):
    for key, value in dct.items():
        if isinstance(value, str):
            try:
                dct[key] = datetime.datetime.fromisoformat(value)
            except ValueError:
                pass  # Not a datetime string, so we leave it unchanged
    return dct
