import time
import pyopencl as cl

class PythonPlan(object):
    def __init__(self, function, **kwargs):
        self.function = function
        self.name = kwargs.get('name', "")
        self.tag = kwargs.get('tag', "")
        self.kwargs = kwargs
        self.atime = 0.0
        self.btime = 0.0
        self.ctime = 0.0
        self.n_calls = 0

    def __call__(self, profiling=False):
        if profiling:
            timer = time.time()
        self.function()
        if profiling:
            self.ctime += (time.time() - timer)
            self.n_calls += 1

    def enqueue(self):
        pass

    def __str__(self):
        return '%s{%s %s %s}' % (
            self.__class__.__name__,
            self.name,
            self.tag,
            self.kwargs)

class PythonProg(object):
    def __init__(self, plans):
        self.plans = plans

    def __call__(self, profiling=False):
        for p in self.plans:
            p(profiling=profiling)


class Plan(object):

    def __init__(self, queue, kern, gsize, lsize, **kwargs):
        self.queue = queue
        self.kern = kern
        self.gsize = gsize
        self.lsize = lsize
        self.name = kwargs.get('name', "")
        self.tag = kwargs.get('tag', "")
        self.kwargs = kwargs
        self.atime = 0.0
        self.btime = 0.0
        self.ctime = 0.0
        self.n_calls = 0

    def __call__(self, profiling=False):
        ev = self.enqueue()
        self.queue.finish()
        if profiling:
            self.atime += 1e-9 * (ev.profile.submit - ev.profile.queued)
            self.btime += 1e-9 * (ev.profile.start - ev.profile.submit)
            self.ctime += 1e-9 * (ev.profile.end - ev.profile.start)
            self.n_calls += 1

    def enqueue(self):
        return cl.enqueue_nd_range_kernel(
            self.queue, self.kern, self.gsize, self.lsize)

    def __str__(self):
        return '%s{%s, %s, %s, %s, %s}' % (
            self.__class__.__name__,
            self.queue,
            self.kern,
            self.gsize,
            self.lsize,
            self.kwargs)


class Prog(object):
    def __init__(self, plans):
        self.plans = plans
        self.queues = [p.queue for p in self.plans]
        self.kerns = [p.kern for p in self.plans]
        self.gsizes = [p.gsize for p in self.plans]
        self.lsizes = [p.lsize for p in self.plans]
        self.map_args = (cl.enqueue_nd_range_kernel,
                         self.queues, self.kerns, self.gsizes, self.lsizes)

    def __call__(self, profiling=False):
        if profiling:
            for p in self.plans:
                p(profiling=profiling)
        else:
            map(*self.map_args)
            self.queues[-1].flush()

    def enqueue(self):
        return map(*self.map_args)

    def call_n_times(self, n):
        self.enqueue_n_times(n)
        self.queues[-1].finish()

    def enqueue_n_times(self, n):
        for ii in range(n):
            map(*self.map_args)


class HybridProg(object):
    def __init__(self, python_plans, ocl_plans):
        self.py_prog = PythonProg(python_plans)
        self.ocl_prog = Prog(ocl_plans)

    def __call__(self, profiling=False):
        self.py_prog(profiling=profiling)
        self.ocl_prog(profiling=profiling)
