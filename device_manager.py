from weather_device import WeatherDevice
from threading import Event, Thread, Lock
from typing import List
import time
from range_safety_checker import DeviceMeasuringConfig
from weather_measurement import WeatherMeasurement


class DeviceManager:
    """
    This class handles manages the measuring of a device and
    holds last measurements
    """
    def __init__(self, device: WeatherDevice, config: DeviceMeasuringConfig,
                 save_callback: callable):
        self.device = device

        self.interval = config.interval

        self._queue: List[WeatherMeasurement] = list()
        self.queue_size = config.queue_size

        self._queue_lock = Lock()

        self._stop_event = Event()
        self._save_callback = save_callback

        # TODO: check when it is a bug and when it is not
        if self.interval == 0:
            self.interval = 60

        if self.queue_size == 0:
            self.queue_size = 1
        
    def _measuring_loop(self) -> None:
        """
        This function is blocking, so it is must be called in a separate thread.
        Measures every time interval and updates the measurements queue.
        If there is a saving callback, save the measurement
        """
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

    def start_measuring(self) -> None:
        """
        Start measuring loop in another thread
        """
        # start making measurements in a separate thread
        self._stop_event.clear()

        thread = Thread(target=self._measuring_loop)
        thread.start()

    def stop_measuring(self) -> None:
        """
        Stops the measuring loop if running
        """
        # stop the thread making the measurements
        self._stop_event.clear()

    def get_last_measurements(self) -> List[WeatherMeasurement]:
        """
        Copies the measurements queue
        :return: List of last measurements
        """
        # get all measurements
        with self._queue_lock:
            return self._queue.copy()
