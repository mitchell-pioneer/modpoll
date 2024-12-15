import threading

class RepeatingTimer:
    def __init__(self, interval, function, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.timer = None
        self.running = False

    def _run(self):
        if self.running:
            self.function(*self.args, **self.kwargs)
            self.start()

    def start(self):
        self.running = True
        self.timer = threading.Timer(self.interval, self._run)
        self.timer.start()

    def stop(self):
        self.running = False
        if self.timer:
            self.timer.cancel()