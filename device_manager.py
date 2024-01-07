from weather_device import WeatherDevice
from threading import Event, Thread, Lock
import time
from range_safety_checker import DeviceMeasuringConfig


class DeviceManager:
    """
    This class handles manages the measuring of a device and
    holds last measurements
    """
    def __init__(self, device: WeatherDevice, config: DeviceMeasuringConfig,
                 save_callback: callable):
        self.device = device

        self._queue = list()
        self.queue_size = config.queue_size
        self._queue_lock = Lock()

        self.interval = config.interval

        self._stop_event = Event()
        self._save_callback = save_callback

    def _measuring_loop(self):
        while not self._stop_event.is_set():
            start_time = time.time()
            measurement = self.device.measure_all()

            # if saving of the measurement is required, do it
            if self._save_callback is not None:
                self._save_callback(measurement)

            with self._queue_lock:
                if len(self._queue) == self.queue_size:
                    self._queue.pop(0)

                # add new measurement to the queue
                self._queue.append(measurement)

            end_time = time.time()

            # sleep until an interval elapsed
            remaining_time = self.interval - (end_time - start_time)
            time.sleep(remaining_time)

    def start_measuring(self):
        # start making measurements in a separate thread
        self._stop_event.clear()

        thread = Thread(target=self._measuring_loop)
        thread.start()

    def stop_measuring(self):
        # stop the thread making the measurements
        self._stop_event.clear()

    def get_last_measurements(self):
        # get all measurements
        with self._queue_lock:
            return self._queue.copy()
