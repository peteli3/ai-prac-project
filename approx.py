import scipy as sp
import numpy as np
import os
import matplotlib.pyplot as plt
import pickle as pk
import video
from collections import OrderedDict
from scipy import interpolate

FILENAME = 'results11-29.txt'
LINK = 'https://storage.googleapis.com/vimeo-test/work-at-vimeo-2.mp4'
MEGA_BYTES = 5

def experiment(filename):
	result = OrderedDict({})
	# 5 runs
	for _ in range(5):
		for i in range(1, 3):
			result.setdefault(i, []).append(video.main([None, LINK, str(MEGA_BYTES), str(i)]))
		for i in range(10, 30, 2):
			result.setdefault(i, []).append(video.main([None, LINK, str(MEGA_BYTES), str(i)]))
		for i in range(30, 60, 3):
			result.setdefault(i, []).append(video.main([None, LINK, str(MEGA_BYTES), str(i)]))
		for i in range(60, 80, 4):
			result.setdefault(i, []).append(video.main([None, LINK, str(MEGA_BYTES), str(i)]))
		for i in range(80, 101, 5):
			result.setdefault(i, []).append(video.main([None, LINK, str(MEGA_BYTES), str(i)]))

	# save the raw results
	with open('rawdata.txt', 'w') as file:
		for t, lst in result.items():
			vals = ','.join(str(i) for i in lst)
			file.write(str(t) + ',' + vals + '\n')

	# average the results
	avgs = []
	for t, v in result.items():
		avg = sum(v) / len(v)
		avgs.append(avg)

	# save the averaged results
	with open(filename, 'w') as file:
		for t, v in zip(result.keys(), avgs):
			file.write(str(t) + ',' + str(v) + '\n')

	return result

def load_data(filename):
	result = OrderedDict({})
	with open(filename, 'r') as file:
		for line in file:
			line = line.rstrip('\n')
			threads, runtime = line.split(",")
			result[int(threads)] = float(runtime)
		
	return result

def fit_and_plot(result):
	# calculate polynomial function with two degrees
	z = np.polyfit(result.keys(), np.array(result.values()), 8)
	function = np.poly1d(z)
	print(function)
	print(function.deriv())

	x_new = np.linspace(1, max(result.keys()), len(result))
	y_new = function(x_new)
	error = 0.0
	for t, v in result.items():
		error += (function(t) - v) ** 2
	print('original plot curve error ' + str(error))


	# f = interpolate.interp1d(result.keys(), result.values(), kind='cubic')
	# x_new = np.linspace(1, max(result.keys()), len(result))
	# y_new = f(x_new)
	# error = 0.0
	# print(y_new)
	# for i, v in enumerate(result.values()):
	# 	print(v, y_new[i])
	# 	error += (v - y_new[i]) ** 2
	# print(error)

	plt.xlabel('# Threads (theta)')
	plt.ylabel('Runtime (sec)')
	plt.title('Polynomial fit over 5 runs averaged')

	plt.plot(result.keys(), result.values(), 'o', x_new, y_new)
	plt.show()
	return function, function.deriv()

def plot_curves(function, filename):
	""" Validates the polynomial curve on 5 new runs by plotting """
	data = OrderedDict({})
	with open(filename, 'r') as file:
		for line in file:
			line = line.rstrip('\n')
			threads, r1, r2, r3, r4, r5 = line.split(",")
			data[int(threads)] = map(float, [r1,r2,r3,r4,r5])

	for i in range(5):
		x_new = np.linspace(1, 100, 32)
		y_new = function(x_new) - 15
		values = [x[i] for x in data.values()]
		error = 0.0
		for j, t in enumerate(data.keys()):
			error += (function(t) - 15 - values[j]) ** 2
		print('plot ' + str(i) + ' ' + str(error))
		plt.xlabel('# Threads (theta)')
		plt.ylabel('Runtime (sec)')
		plt.plot(data.keys(), values, 'o', x_new, y_new)
		plt.show()

def gradient_desc(df):
	cur_x = 1 # The algorithm starts at x=1
	gamma = 0.01 # step size multiplier
	precision = 0.00001
	previous_step_size = cur_x
	num_iterations = 0

	while previous_step_size > precision and num_iterations < 10000:
	    prev_x = cur_x
	    cur_x += -gamma * df(prev_x)
	    previous_step_size = abs(cur_x - prev_x)
	    num_iterations += 1

	print("The local minimum occurs at %f" % cur_x)

def main():
	# result = experiment(FILENAME)
	result = load_data(FILENAME)
	f, df = fit_and_plot(result)
	gradient_desc(df)
	plot_curves(f, 'rawdata.txt')

if __name__ == "__main__":
	main()