
# python standard libraries

import os
import sys
import re
import shutil
import cStringIO
import binascii
import base64
import hashlib
import time
import threading
from Queue import Queue

# external libraries/modules

import pycurl
import validators
import crcmod.predefined
import progress as p

# global constants

MEGA_BYTE = 2 ** 20
MAX_PARALLELISM = 2 ** 16
DEFAULT_PARALLELISM = 2 ** 8

SECS_PER_MIN = 60
SERIAL_TIMEOUT = 30 * SECS_PER_MIN
CHUNK_TIMEOUT = 5 * SECS_PER_MIN

MAX_FILES_OPEN = 100
MAX_RETRIES = 3

# global sync primitives

tempfiles_open = 0
tempfiles_lock = threading.Lock()
can_open_tempfiles = threading.Condition(tempfiles_lock)

#################################### v SCRIPT BODY v ####################################

def md5_func(file_name):
	"""
		Functionality:  calculate the MD5 hash for our newly downloaded file
		Preconditions:  - file_name is a file in the current directory and can be read as a
						binary string
		Returns:        the hexdigest() of file_name's MD5 hash
	"""

	# calculate the MD5 of file, 1MB at a time since file might be too big to fit in memory
	hash_md5 = hashlib.md5()
	with open(file_name, 'rb') as f:
		for chunk in iter(lambda: f.read(MEGA_BYTE), b""):
			hash_md5.update(chunk)

	return hash_md5.hexdigest()


def validate_download(file_name, crc, md5):
	"""
		Functionality:  calculate the crc32c checksum for our newly downloaded file, compare
						with the checksum obtained from https header
		Preconditions:  - file_name is a file in the current directory and can be read as a
						binary string
						- crc is a valid x-goog-hash crc32c checksum,
						- md5 is a valid x-goog-hash message digest 5
		Returns:        boolean indicating whether the checksum of downloaded file matches
						the one specified in the http header, throws exception otherwise
	"""

	# calculate checksum using google cloud's CRC32C algorithm
	crc32c_func = crcmod.predefined.mkCrcFun('crc-32c')
	byte_rep = open(file_name, 'rb').read()
	checksum_hex = crc32c_func(byte_rep)

	# do some weird stuff to get the checksum in right format, thanks @ Tanin Na Nakorn from Google Cloud Storage
	hex_str = '%08x' % checksum_hex
	binary_rep = binascii.unhexlify(hex_str)
	final_checksum = base64.b64encode(binary_rep)

	# do the same for MD5
	hex_str_md5 = str(md5_func(file_name))
	binary_rep_md5 = binascii.unhexlify(hex_str_md5)
	final_md5 = base64.b64encode(binary_rep_md5)

	# if either checksum failed, file is corrupted
	if final_checksum.strip() != crc.strip() or final_md5.strip() != md5.strip():
		raise Exception('File corrupted')


def build_ranges_queue(file_size, chunk_size):
	"""
		Functionality:  build the ranges of chunks, associated with the chunk_id
		Precondition:   - file_size is an int indicating the download size
						- chunk_size is an int specifying size of each concurrent chunk
						chunk_size < file_size
		Returns:        FIFO Queue containing tuple (chunk_id, chunk byte range in a
						format that pycurl can use)
	"""

	# initialize sync-safe Queue, track start/end, track chunk_id for later
	queue = Queue()
	start = 0
	chunk_id = 0
	end = chunk_size

	# add (chunk_id, range) tuples to the FIFO Queue
	while start < file_size:
		range = str(start) + '-' + str(end)
		queue.put( (chunk_id, range) )
		start = 1 + end
		end = min( start + chunk_size, int(file_size) + 1 )
		chunk_id += 1

	return queue


def inc_tempfiles_open():
	"""
		Functionality:  make sure we dont open more than MAX_FILES_OPEN tmp at a time
	"""

	global tempfiles_open, tempfiles_lock, can_open_tempfiles
	with tempfiles_lock:
		while tempfiles_open >= MAX_FILES_OPEN:
			can_open_tempfiles.wait()
		tempfiles_open += 1


def dec_tempfiles_open():
	"""
		Functionality:  make sure we dont open more than MAX_FILES_OPEN tmp at a time
	"""

	global tempfiles_open, tempfiles_lock, can_open_tempfiles
	with tempfiles_lock:
		tempfiles_open -= 1
		if (tempfiles_open < MAX_FILES_OPEN):
			can_open_tempfiles.notify()


def download_chunk(target_url, queue, temp_map, temp_dir, num_chunks):
	"""
		Functionality:  MULTIPROCESSING - the function body for each worker thread, will
						take the first chunk from Queue, download it to a numbered temp
						file, map the chunk_id to temp_file_name in temp_map
		Precondition:   - target_url is a valid URL that can be accessed via HTTP/HTTPS,
						- queue is a Python Queue containing (chunk_id, chunk byte range
						string in pycurl format) tuples,
						- temp_map is a dictionary mapping chunk_id to temp_file_name,
						- temp_dir is a subdirectory containing all temp files,
						- num_chunks is the number of total chunks to be downloaded
		Returns:        a dictionary as {chunk_id : temp_file_name}
	"""

	while True:

		# if chunks left on queue, start downloading chunk
		if queue.qsize() > 0:
			(chunk_id, dl_range) = queue.get()

			# try to download chunk
			for attempt in range(MAX_RETRIES):
				try:
					# extract info from queue
					chunk_name = 'output_tmp' + str(chunk_id)
					chunk_path = os.path.join(temp_dir, chunk_name)

					# progress tracker, ***** MAY NEED TO REVISIT THIS
					back = '\b' * 30
					progress = back + 'Downloading chunk ' + str(chunk_id + 1) + ' of ' + str(num_chunks)
					sys.stdout.write(progress)
					sys.stdout.flush()

					# write to temp file if < 100 open already
					inc_tempfiles_open()
					with open(chunk_path, 'wb') as tmp:
						c = pycurl.Curl()
						c.setopt(c.URL, target_url)
						c.setopt(c.WRITEDATA, tmp)
						c.setopt(c.RANGE, dl_range)
						c.setopt(c.TIMEOUT, CHUNK_TIMEOUT)
						c.perform()
						c.close()
					dec_tempfiles_open()

					# set hashmap, notify queue that task completed
					temp_map[chunk_id] = chunk_path
					queue.task_done()

				# failed download chunk attempt, try again
				except Exception as e:
					continue

				# chunk successfully downloaded, can break out now
				else:
					break

			# if we don't break from loop, then chunk download failed 3x
			else:
				raise Exception('Could not download chunk %d' % chunk_id)

		# no work left, break foreverloop -> end thread execution
		else:
			break


def download_in_chunks(target_url, file_size, num_parallel, chunk_size):
	"""
		Functionality:  download the file in chunks, and then combine the chunks into a
						single playable file
		Precondition:   - target_url is a valid URl that can be accessed via HTTP/HTTPS,
						- file_size is an int that represents the size of the download
						- num_parallel is an int limiting the number of concurrent chunks
						being downloaded at any given time,
						- chunk_size is an int limiting the size of each concurrent chunk
						to be downloaded
		Returns:        name of the file that was written to
	"""

	# build ranges Queue, returns FIFO Queue (thread-safe)
	queue = build_ranges_queue(file_size, chunk_size)

	# initialize temp_map, get # chunks (to iterate), get/set directories for writing
	temp_map = dict()
	num_chunks = int((file_size / chunk_size) + 1)
	write_to = target_url.split('/')[-1]
	write_to_tmp = os.path.join(os.getcwd(), 'dl_tmp')
	if not os.path.exists(write_to_tmp):
		os.makedirs(write_to_tmp)

	# start up the threads, reap them when Queue has been fully processed
	for i in range(num_parallel):
		worker = threading.Thread( target=download_chunk, args=(target_url, queue, temp_map, write_to_tmp, num_chunks) )
		worker.setDaemon(True)
		worker.start()
	queue.join()

	# write all temps into 1 file
	with open(write_to, 'wb') as file:

		# take each ordered chunk, write to file
		for i in range(int(num_chunks)):
			with open(temp_map[i], 'rb') as write_from:
				contents = write_from.read()
				file.write(contents)

	# delete all temps
	shutil.rmtree(write_to_tmp)

	return write_to


def download_whole(target_url):
	"""
		Functionality:  download the entire file at once
		Precondition:   - target_url is a valid URL that can be accessed via HTTP/HTTPS
		Returns:        name of the file that was written to
	"""

	# initialize curl, extract filename
	c = pycurl.Curl()
	write_to = target_url.split('/')[-1]

	with open(write_to, 'wb') as file:
		c.setopt(c.URL, target_url)
		c.setopt(c.WRITEDATA, file)
		c.setopt(c.NOPROGRESS, 0)
		c.setopt(c.PROGRESSFUNCTION, p.progress)
		c.setopt(c.TIMEOUT, SERIAL_TIMEOUT)

		# try the download 3 times, if any fail, prompt user before trying again
		attempt = 0
		while attempt < MAX_RETRIES:

			# attempt to download the file
			try:
				c.perform()

			# if fail, try again when prompted
			except Exception as e:
				if raw_input('Download failed. Try again? (enter y to retry): ') == 'y':
					attempt += 1
					continue
				else:
					attempt = MAX_RETRIES

			# download success, leave loop
			else:
				c.close()
				break

		# if never reach break (success), abort download
		else:
			print 'Download aborted.'
			# os.remove('./' + write_to)    # uncomment this to delete file upon failure

	return write_to


def extract_from_url(target_url, num_parallel, chunk_size):
	"""
		Functionality:  checks if the server accepts byte-range GET, if so, download
						in chunks of size no greater than _____, and at most _____
						chunks in parallel, write to a file of the same name as source
		Precondition:   - target_url is a valid URl that can be accessed via HTTP/HTTPS,
						- num_parallel is an int limiting the number of concurrent chunks
						being downloaded at any given time,
						- chunk_size is an int limiting the size of each concurrent chunk
		Returns:        n/a
	"""

	# get file size to figure out number of concurrent chunks
	c = pycurl.Curl()
	header = cStringIO.StringIO()

	# retrieve content length
	c.setopt(c.URL, target_url)
	c.setopt(c.HEADERFUNCTION, header.write)
	c.setopt(c.NOBODY, 1)
	c.perform()
	content_length = c.getinfo(c.CONTENT_LENGTH_DOWNLOAD)
	c.close()

	# get header text, extract info from header (supports byte ranges, crc32c checksum)
	header_text = header.getvalue()
	accepts_byte_ranges = bool(re.search('Accept-Ranges:\s+bytes', header_text))
	crc = re.search('\nx-goog-hash: crc32c=(.*)\n', header_text).group(1)
	md5 = re.search('\nx-goog-hash: md5=(.*)\n', header_text).group(1)

	# download parallel in chunks if allowed
	if accepts_byte_ranges:

		# attempt parallel download first
		try:
			print 'Attempting parallel download... happy waiting!'
			file_name = download_in_chunks(target_url, content_length, num_parallel, chunk_size)

		# download in series if parallel fails
		except:
			print 'Parallel download failed, will attempt serial download...'
			file_name = download_whole(target_url)

	# otherwise download whole
	else:
		print 'Download starting... happy waiting!'
		file_name = download_whole(target_url)

	# validate the download via hashed crc32c checksum
	print '\nValidating download now...'
	try:
		validate_download(file_name, crc, md5)
		print 'Download successful! %s is intact and ready to view.' % file_name
	except:
		print 'Download corrupted. Try again later.'


def main(argv):
	"""
		Functionality:  driver function, executes extract_from_url()
		Precondition:   - argv[1] contains the URL to be downloaded from (must be valid)
						- argv[2] contains the chunk_size in bytes (must be a digit)
						- argv[3] contains the num_parallel threads to run (must be a digit)
		Returns:        n/a
	"""

	# invalid inputs handling
	if not argv[1]:
		raise Exception('Error: No input URL')
	elif not validators.url(argv[1]):
		raise Exception('Error: Invalid input URL')
	elif not argv[1][-4:] == '.mp4':
		raise Exception('Error: URL content doesn\'t match video/mp4 type') # check MIME instead, this isn't standard enough
	elif len(argv) == 3:
		raise Exception('Error: Missing chunk_size')
	elif len(argv) == 4 and not (argv[2].isdigit() or argv[3].isdigit()):
		raise Exception('Error: Invalid input num_parallel or chunk_size')

	# otherwise, set chunk_size and num_parallel, then download video
	elif len(argv) == 2:
		chunk_size = 5 * MEGA_BYTE
		num_parallel = DEFAULT_PARALLELISM
	elif len(argv) == 4:
		chunk_size = int(argv[2]) * MEGA_BYTE
		num_parallel = min( int(argv[3]), MAX_PARALLELISM )

	start = time.time()
	extract_from_url(argv[1], num_parallel, chunk_size)
	end = time.time()
	print '\ntime elapsed: %f' % (end - start)
	return end - start
	
#################################### ^ SCRIPT BODY ^ ####################################



#################################### v DRIVER BODY v ####################################

if __name__ == "__main__":
	main(sys.argv)

#################################### ^ DRIVER BODY ^ ####################################

