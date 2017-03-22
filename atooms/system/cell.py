# This file is part of atooms
# Copyright 2010-2014, Daniele Coslovich

"""Simulation cell."""

import numpy
from atooms.core import ndim as _ndim

class Cell(object):

    def __init__(self, side, origin=numpy.zeros(_ndim)):
        self.side = numpy.asarray(side)
        self.origin = origin

    @property
    def volume(self):
        return numpy.prod(self.side)
