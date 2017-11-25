
#   File name: setup.py
#   Author: Peter Li
#   Date created: 03/03/17
#   Date last modified: 03/13/17
#   Python Version: 2.7
#   External Dependencies: pycurl, validators, crcmod.predefined

import pip

if __name__ == '__main__':
	pip.main(['install', 'pycurl'])
	pip.main(['install', 'validators'])
	pip.main(['install', 'crcmod'])
	pip.main(['install', 'humanize'])

	