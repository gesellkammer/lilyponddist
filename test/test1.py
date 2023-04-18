import logging
import subprocess

logger = logging.getLogger('lilyponddist')
logger.setLevel('DEBUG')

import lilyponddist

subprocess.call([lilyponddist.lilypondbin(), "test1.ly"])
