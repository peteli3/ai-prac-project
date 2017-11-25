
#   File name: progress.py
#   Author: shichao-en from Github
#   Date created: Unk date, 2014
#   Python Version: 2.7
#   External Dependencies: humanize

import sys
import time
from humanize import naturalsize

START_TIME = None

def progress(download_t, download_d, upload_t, upload_d):
	""" 
		* Implemented by shichao-an's python_download_progress.py for pycurl *
		Functionality: 	prints the live progress of download on the console
		Precondition:	n/a, closure to be fed into pycurl.PROGRESSFUNCTION
		Returns: 		n/a
	"""
	global START_TIME

	if int(download_t) == 0:
		return

	if START_TIME is None:
		START_TIME = time.time()

	duration = time.time() - START_TIME + 1
	speed = download_d / duration
	speed_s = naturalsize(speed, binary=True)
	speed_s += '/s'

	if int(download_d) == 0:
		download_d == 0.01
	p = '%s/%s (%.2f%%) %s %s\r' % (naturalsize(download_d, binary=True),
									naturalsize(download_t, binary=True),
									(download_d / download_t) * 100, speed_s, ' ' * 10)
	sys.stderr.write(p)
	sys.stderr.flush()

	