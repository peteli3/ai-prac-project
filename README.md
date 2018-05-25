# Learning the optimal degree of concurrency for performance-critical Python processes

Final project for:  
CS 4701 - Practicum in Artificial Intelligence  
Fall 2017, taught by Bart Selman  

## Abstract
Python threading is (unfortunately) an illusion. At runtime, a Global Interpreter Lock restricts execution to one native thread per process at any given time. Thus, the illusion of multithreading is created by fast context switching, leading to trade-offs between degree of concurrency and runtime performance. Too little concurrency doesn't make full utilization of computational resources while too much concurrency introduces memory bottlenecks that make context switching not worth the overhead.

We aim to figure out where the sweet spot of concurrency is. To tackle this problem, which is applicable to a myriad of Python programs, we will set up an experiment that uses simple machine learning techniques to seek out a degree of concurrency which minimizes runtime and generalizes well.

Our ultimate goal is to have a tangible conclusion or prototype that such a learning tool can be implemented efficiently and that its prediction remains consistent to a wide variety of scenarios encountered in everyday computing.
