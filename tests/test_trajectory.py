#!/usr/bin/env python

import os
import unittest
import numpy

from atooms.system import System, Particle, Cell
from atooms.trajectory import Unfolded
from atooms.trajectory import TrajectoryXYZ, TrajectorySimpleXYZ, TrajectoryRUMD
import atooms.trajectory as trj

def _equal(system1, system2, ignore=None):
    check = {}
    check['npart'] = len(system1.particle) == len(system2.particle)
    for p1, p2 in zip(system1.particle, system2.particle):
        check['position'] = all(p1.position == p2.position)
        check['mass'] = p1.mass == p2.mass
        check['id'] = p1.id == p2.id
        check['name'] = p1.name.strip() == p2.name.strip()
    check['side'] = all(system1.cell.side == system1.cell.side)
    for key in check:
        if ignore is not None and key in ignore:
            continue
        if not check[key]:
            print key, 'differs'
            return False
    return True


class Test(unittest.TestCase):
    
    def setUp(self):
        import copy
        # TODO: use species instead of separate id and name?
        # TODO: mass is not written by 
        # TODO: rumd changes indexing
        # TODO: hdf5 should strip names
        particle = [Particle(position=[0.0, 0.0, 0.0], id=1, name='A', mass=1.0),
                    Particle(position=[1.0, 1.0, 1.0], id=2, name='B', mass=2.0),
                ]
        cell = Cell([2.0, 2.0, 2.0])
        self.system = []
        self.system.append(System(particle, cell))
        self.system.append(System(particle, cell))
        self.inpfile = '/tmp/testtrj'
        self.inpdir = '/tmp/testtrj.d'
        from atooms.utils import mkdir
        mkdir(self.inpdir)

    def _read_write(self, cls, path=None, ignore=None):
        """Read and write"""
        if path is None:
            path = self.inpfile
        with cls(path, 'w') as th:
            th.write_timestep(1.0)
            for i, system in enumerate(self.system):
                th.write(self.system[i], i)
        with cls(path) as th:
            self.assertEqual(th.timestep, 1.0)
            for i, system in enumerate(th):
                #print system.particle[0].id, system.particle[1].id
                self.assertTrue(_equal(self.system[i], system, ignore))

    def test_xyz(self):
        self._read_write(trj.TrajectoryXYZ, ignore=['mass'])
        self._read_write(trj.TrajectorySimpleXYZ, ignore=['mass'])

    def test_hdf5(self):
        self._read_write(trj.TrajectoryHDF5)

    def test_rumd(self):
        self._read_write(trj.TrajectoryRUMD, ignore=['id', 'name'])
        #self._read_write(trj.SuperTrajectoryRUMD, self.inpdir, ignore=['id', 'name'])

    def tearDown(self):
        os.system('rm -rf /tmp/testtrj')
        os.system('rm -rf /tmp/testtrj.d')

if __name__ == '__main__':
    unittest.main()

