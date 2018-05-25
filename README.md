# Learning the optimal degree of concurrency for performance-critical Python processes

Final project for:
CS 4701 - Practicum in Artificial Intelligence
Fall 2017, taught by Bart Selman

## Abstract
Python threading is (unfortunately) an illusion. At runtime, a Global Interpreter Lock restricts ex- ecution to one native thread per process at any given time. Thus, the illusion of multithreading is created by a lot of fast context switching which di- rectly results in trade-offs between degree of con- currency and runtime performance. Too little con- currency doesnt make full utilization of computa- tional resources while too much concurrency in- troduces memory bottlenecks that make context switching not worth the expenditure on handling overhead.

We aim to figure out where the sweet spot of concurrency is. To tackle this problem, which is applicable to a myriad of Python programs, we will set up an experiment that uses machine learning techniques to seek out a degree of concurrency which minimizes runtime and generalizes well.

Our ultimate goal is to have a tangible conclu- sion or prototype that such a learning tool can be implemented efficiently and that its predic- tion remains consistent to a wide variety of sce- narios that users encounter in everyday comput- ing.