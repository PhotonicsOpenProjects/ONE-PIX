import logging
import os
from logging.handlers import TimedRotatingFileHandler

# Crée le dossier 'logs' à la racine du projet (une fois au-dessus de onepix/)
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(log_dir, exist_ok=True)

# Format des logs : module, fonction, ligne, message
log_format = logging.Formatter(
    fmt="%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Handler fichier avec rotation journalière
file_handler = TimedRotatingFileHandler(
    filename=os.path.join(log_dir, "app.log"),
    when="midnight",
    backupCount=7,
    encoding="utf-8"
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(log_format)

# Handler console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_format)

# Logger racine (root)
root = logging.getLogger()
root.setLevel(logging.DEBUG)
root.addHandler(file_handler)
root.addHandler(console_handler)

# Évite les doublons si plusieurs handlers
root.propagate = False
