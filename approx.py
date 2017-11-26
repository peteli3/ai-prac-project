import scipy as sp
import numpy as np
import os
import matplotlib.pyplot as plt
import pickle as pk

def experiment(filename):
	result = []
	for i in range(1, 10):
		time = os.system('python2 video.py https://storage.googleapis.com/vimeo-test/work-at-vimeo-2.mp4 5 ' + str(i))
		result.append(time)
	for i in range(10, 30, 2):
		time = os.system('python2 video.py https://storage.googleapis.com/vimeo-test/work-at-vimeo-2.mp4 5 ' + str(i))
		result.append(time)
	for i in range(30, 60, 3):
		time = os.system('python2 video.py https://storage.googleapis.com/vimeo-test/work-at-vimeo-2.mp4 5 ' + str(i))
		result.append(time)
	for i in range(60, 80, 4):
		time = os.system('python2 video.py https://storage.googleapis.com/vimeo-test/work-at-vimeo-2.mp4 5 ' + str(i))
		result.append(time)
	for i in range(80, 101, 5):
		time = os.system('python2 video.py https://storage.googleapis.com/vimeo-test/work-at-vimeo-2.mp4 5 ' + str(i))
		result.append(time)

	with open(filename, 'w') as file:
		for i in result:
			file.write(str(i) + '\n')

def load_data(filename):
	with open(filename, 'r') as file:
		return [float(line.rstrip('\n')) for line in file]

def fit_and_plot(results):
	print(results)
	# calculate polynomial function with two degrees
	z = np.polyfit(range(50), np.array(results), 2)
	function = np.poly1d(z)

	x_new = np.linspace(0, 49, 50)
	y_new = function(x_new)

	plt.plot(range(50), results, 'o', x_new, y_new)
	plt.show()

def main():
	filename = 'results.txt'
	experiment(filename)
	results = load_data(filename)
	fit_and_plot(results)

if __name__ == "__main__":
	main()