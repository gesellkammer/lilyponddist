import logging
import subprocess
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--output', default='test1')
args = parser.parse_args()

logger = logging.getLogger('lilyponddist')
logger.setLevel('DEBUG')

import lilyponddist

subprocess.call([lilyponddist.lilypondbin(), "test1.ly", '-o', args.output])
