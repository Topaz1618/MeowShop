import sys
import re
import logging.handlers
import time
import os


class MyTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    def __init__(self):
        formatter = logging.Formatter(fmt='[%(levelname)s] [%(asctime)s] %(message)s', datefmt='%Y_%m_%d %H:%M:%S')
        self.setFormatter(formatter)
        self.dir_log = "logfiles/"
        filename = self.dir_log + time.strftime("%Y_%m_%d") + ".log"
        logging.handlers.TimedRotatingFileHandler.__init__(self, filename, when='D', interval=1, backupCount=180)

    def doRollover(self):
        self.stream.close()
        self.baseFilename = self.dir_log + time.strftime("%Y_%m_%d") + ".log"
        self.stream = open(self.baseFilename, 'w')
        self.rolloverAt = self.rolloverAt + self.interval
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

    def getFilesToDelete(self):
        dirName, baseName = os.path.split(self.baseFilename)
        fileNames = os.listdir(dirName)
        result = []
        prefix, suffix = baseName.split(".")
        for fileName in fileNames:
            if self.extMatch.match(prefix):
                result.append(os.path.join(dirName, fileName))
        if self.backupCount == 0:
            result = []

        if len(result) < self.backupCount:
            result = []
        else:
            result.sort()
            result = result[:len(result) - self.backupCount]
        return result


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(fmt='[%(levelname)s] [%(asctime)s] %(message)s', datefmt='%Y_%m_%d %H:%M:%S')

log_file_handler = MyTimedRotatingFileHandler()
log_file_handler.extMatch = r"^\d{4}_\d{2}_\d{2}$"
log_file_handler.extMatch = re.compile(log_file_handler.extMatch)
log_file_handler.setFormatter(formatter)
log_file_handler.setLevel(logging.DEBUG)
logger.addHandler(log_file_handler)

