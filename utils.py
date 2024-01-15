from threading import Timer, Event, Lock
from config.config import Config
# from db_access import DbManager


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
    _instances = {}
    _lock = Lock()

    @staticmethod
    def get_instance(class_type):
        with SingletonFactory._lock:
            if class_type not in SingletonFactory._instances:
                SingletonFactory._instances[class_type] = class_type()
        return SingletonFactory._instances[class_type]


cfg = SingletonFactory.get_instance(Config)
