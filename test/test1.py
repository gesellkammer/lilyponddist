import logging
import subprocess
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--output', default='test1')
args = parser.parse_args()

logger = logging.getLogger('lilyponddist')
logger.setLevel('DEBUG')

import lilyponddist

subprocess.call([lilyponddist.lilypondbin(), "-o", args.output, "test1.ly"])
