import datetime, os

class Logger:
    ORANGE = '\033[38;5;214m'
    GREEN = '\033[32m'
    RED = '\033[31m'
    CYAN = '\033[36m'
    RESET = '\033[0m'

    directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    file_name = f"{datetime.datetime.now().strftime('%m-%d-%Y-%H_%M_%S')}.txt"
    file_path = os.path.join(directory, file_name)

    os.makedirs(directory, exist_ok=True)
    print(f"Generated logfile at: {file_path}", flush=True)

    def _timestamp(self):
        now = datetime.datetime.now().strftime('%H:%M:%S')
        return f"{self.ORANGE}[{now}]{self.RESET}"

    def _log_to_file(self, message):
        with open(Logger.file_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}\n")

    def suc(self, message):
        print(f"{self._timestamp()} {self.GREEN}{message}{self.RESET}", flush=True)
        self._log_to_file(message)

    def err(self, message):
        print(f"{self._timestamp()} {self.RED}{message}{self.RESET}", flush=True)
        self._log_to_file(message)

    def info(self, message):
        print(f"{self._timestamp()} {self.CYAN}{message}{self.RESET}", flush=True)
        self._log_to_file(message)

logger = Logger()
