# This file is part of atooms
# Copyright 2010-2014, Daniele Coslovich

"""Trajectory decorators."""

import random
import numpy


# Callbacks

def center(system):
    """Center particles in the simulation cell.
    It wont check if that is done multiple times.
    """
    for p in system.particle:
        p.position -= system.cell.side / 2.0
    return system

def normalize_id(system, alphabetic=False):
    """Change species id's so as to start from 1 (fortran
    convention). Species names can be reassigned alphabetically.
    """
    map_ids = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E'}
    pid = [p.id for p in system.particle]
    id_min = numpy.min(pid)
    if id_min == 0:
        for p in system.particle:
            p.id += 1
    if alphabetic:
        for p in system.particle:
            p.name = map_ids[p.id]
    return system

def sort(system):
    """Sort particles by species id."""
    return sorted(system.particle, key=lambda a: a.id)

def filter_id(system, species):
    """Only return particles with given species."""
    system.particle = [p for p in system.particle if p.id == species]
    return system

def set_density(system, rho):
    """Set density of system to rho by rescaling the cell."""
    rho_old = system.density
    x = (rho_old / rho)**(1./3)
    system.cell.side *= x
    for p in system.particle:
        p.position *= x
    return system

def set_temperature(system, T):
    """Set system temperature by reassigning velocities."""
    from atooms.system.particle import cm_velocity
    for p in system.particle:
        p.maxwellian(T)
    v_cm = cm_velocity(system.particle)
    for p in system.particle:
        p.velocity -= v_cm
    return system

# Class decorators

# To properly implement decorators in python see
# http://stackoverflow.com/questions/3118929/implementing-the-decorator-pattern-in-python
# asnwer by Alec Thomas. if we don't subclass at runtime we won't be able to use the decorated
# mathod in other non-subclassed methods.

class Centered(object):

    """Center positions in the box on the fly."""

    def __new__(cls, component):
        cls = type('Centered', (Centered, component.__class__), component.__dict__)
        return object.__new__(cls)

    def __init__(self, component):
        # Internal list of samples that were already centered.
        self.__done = []

    def read_sample(self, sample):
        # If we have subtracted it yet, we return immediately
        if sample in self.__done:
            return
        self.__done.append(sample)
        s = super(Centered, self).read_sample(sample)
        for p in s.particle:
            p.position -= s.cell.side / 2.0
        return s


class Sliced(object):

    """Only return a slice of a trajectory."""

    # This is still necessary. slicing via __getitem__ has a large memory fingerprint
    # since we couldnt write it as a generator (maybe it is possible?)
    # TODO: adjust uslice to pick up blocks without truncating them

    def __new__(cls, component, uslice):
        cls = type('Sliced', (Sliced, component.__class__), component.__dict__)
        return object.__new__(cls)

    def __init__(self, component, uslice):
        self._sliced_samples = range(len(self.steps))[uslice]
        self.steps = self.steps[uslice]

    def read_sample(self, sample):
        i = self._sliced_samples[sample]
        return super(Sliced, self).read_sample(i)


class Unfolded(object):

    """Decorate Trajectory to unfold particles positions on the fly."""

    def __new__(cls, component):
        cls = type('Unfolded', (Unfolded, component.__class__), component.__dict__)
        return object.__new__(cls)

    def __init__(self, component):
        self._initialized_read = False

    def read_init(self):
        s = super(Unfolded, self).read_init()
        # Cache the initial sample and cell
        s = super(Unfolded, self).read_sample(0)
        self._old = numpy.array([p.position for p in s.particle])
        self._last_read = 0

    def read_sample(self, sample):
        # Return here if first sample
        if sample == 0:
            return super(Unfolded, self).read_sample(sample)

        # Compare requested sample with last read
        delta = sample - self._last_read
        if delta < 0:
            raise ValueError('cannot unfold jumping backwards (delta=%d)' % delta)
        if delta > 1:
            # Allow to skip some samples by reading them internally
            # We read delta-1 samples, then delta is 1
            for i in range(delta-1):
                self.read_sample(self._last_read+1)

        s = super(Unfolded, self).read_sample(sample)
        self._last_read = sample

        # Unfold positions
        # Note that since L can be variable we get it at each step
        # TODO: I am not entirely sure this is correct with NPT.
        # The best thing in this case is to get unfolded positions
        # from the simulation.
        L = s.cell.side
        pos = numpy.array([p.position for p in s.particle])
        dif = pos - self._old
        dif = dif - numpy.rint(dif/L) * L
        self._old += dif

        # Return unfolded system
        for i in xrange(len(pos)):
            s.particle[i].position = self._old[i][:]
        return s


# TODO: see if we can avoid reading anything on construction
# TODO: how to better handle conversions between subclasses? We cannot use _convert() because we rely on close() method being called

class MatrixFix(object):

    # Subclass component at runtime
    def __new__(cls, component, matrix_species):
        cls = type('MatrixFix', (MatrixFix, component.__class__), component.__dict__)
        return object.__new__(cls)

    # Object initialization
    def __init__(self, component, matrix_species):
        self._component = component  # actually unnecessary
        self.matrix_species = matrix_species

    # def _init_read(self):
    #     s = super(MatrixFix, self)._init_read()
    #     matrix = []
    #     fluid = []
    #     for p in s.particle:
    #         if p.id in self.matrix_species:
    #             matrix.append(p)
    #         else:
    #             fluid.append(p)
    #     s.particle = fluid
    #     s.matrix = matrix
    #     return s

    def read_sample(self, *args, **kwargs):
        s = super(MatrixFix, self).read_sample(*args, **kwargs)
        # Get rid of matrix particles in trajectory
        s.particle = [p for p in s.particle if p.id not in self.matrix_species]
        return s


class NormalizeId(object):

    """Make sure all chemical ids start from 1"""

    def __new__(cls, component):
        cls = type('NormalizeId', (NormalizeId, component.__class__), component.__dict__)
        return object.__new__(cls)

    def __init__(self, component):
        pass

    def _normalize(self, pl):
        pid = [p.id for p in pl]
        id_min = numpy.min(pid)
        if id_min == 0:
            for p in pl:
                p.id += 1
        return pl

    def read_sample(self, *args, **kwargs):
        s = super(NormalizeId, self).read_sample(*args, **kwargs)
        s.particle = self._normalize(s.particle)
        return s


class Sorted(object):

    """Sort by species"""

    def __new__(cls, component):
        cls = type('Sorted', (Sorted, component.__class__), component.__dict__)
        return object.__new__(cls)

    def __init__(self, component):
        pass

    def read_sample(self, *args, **kwargs):
        s = super(Sorted, self).read_sample(*args, **kwargs)
        s.particle.sort(key=lambda a: a.id)
        return s


class MatrixFlat(object):

    # Subclass component at runtime
    def __new__(cls, component):
        cls = type('MatrixFlat', (MatrixFlat, component.__class__), component.__dict__)
        return object.__new__(cls)

    # Object initialization
    def __init__(self, component):
        self._component = component  # actually unnecessary
        self._matrix = None

    def __setup_matrix(self, s):

        if self._matrix is not None:
            return

        infinite_mass = 1e20
        max_isp = max([p.id for p in s.particle])

        self._matrix = []
        for m in s.matrix:
            self._matrix.append(m)
            self._matrix[-1].mass = infinite_mass
            self._matrix[-1].id += max_isp

        # Sort matrix particles by index
        self._matrix.sort(key=lambda a: a.id)

    def read_sample(self, *args, **kwargs):
        s = super(MatrixFlat, self).read_sample(*args, **kwargs)
        self.__setup_matrix(s)
        for m in self._matrix:
            s.particle.append(m)
        return s


class Filter(object):

    """Apply a filter that transforms each read sample in a trajectory"""

    def __new__(cls, component, filt, *args, **kwargs):
        cls = type('Filter', (Filter, component.__class__), component.__dict__)
        return object.__new__(cls)

    def __init__(self, component, filt, *args, **kwargs):
        """filt is a function that receives a System and returns a modified version of it"""
        import copy
        self.filt = filt
        self._args = args
        self._kwargs = kwargs

    def read_sample(self, sample):
        sy = super(Filter, self).read_sample(sample)
        # Apply filter to the system, that's all
        # HACK!: when further decorating the class, the referenced
        # function becomes a bound method of the decorated class and
        # therefore passes the first argument (self). Workaround is
        # to always expect a trajectory and forcibly add self if no
        # further decorators are added.
        # TODO: we should catch the right exception here, otherwise errors from the callbacks are caught here as well
        try:
            return self.filt(sy, *self._args, **self._kwargs)
        except:
            return self.filt(self, sy, *self._args, **self._kwargs)


class AffineDeformation(object):

    def __new__(cls, component, scale):
        cls = type('AffineDeformation', (AffineDeformation, component.__class__),
                   component.__dict__)
        return object.__new__(cls)

    def __init__(self, component, scale=0.01):
        self.component = component
        self.scale = scale

    def read_sample(self, *args, **kwargs):
        s = super(AffineDeformation, self).read_sample(*args, **kwargs)
        # Note this random scaling changes every time read is called,
        # even for the same sample
        scale = 1 + (random.random()-0.5)*self.scale
        s.cell.side *= scale
        for p in s.particle:
            p.position *= scale
        return s
