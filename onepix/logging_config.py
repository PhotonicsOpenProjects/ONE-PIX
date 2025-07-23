import logging, os
from logging.handlers import TimedRotatingFileHandler

os.makedirs("logs", exist_ok=True)

# Handler principal : rotation journalière, conserve 7 fichiers
file_handler = TimedRotatingFileHandler(
    "logs/app.log",
    when="midnight",
    backupCount=7,
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "%Y-%m-%d %H:%M:%S"
))

# Handler console (niveau INFO+)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "%H:%M:%S"
))

# Logger racine
root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(file_handler)
root.addHandler(console_handler)
