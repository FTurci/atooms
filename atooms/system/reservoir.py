"""
Thermodynamic reservoirs to impose temperature, pressure, or
particle numbers in a simulation.

When added to a `System` object, they will determine the statistical
ensemble of a simulation:

    #!python
    system = System()
    system.thermostat = Thermostat(temperature=1.0)
    system.barostat = Barostat(pressure=1.0)
    print system.ensemble == 'NPT'

Note: in an actual simulation backend, these reservoirs will have
additional degrees of freedom, e.g. s and pi in a Nose-like
thermostat.
"""


class Thermostat(object):

    """Thermostat to control the temperature during a simulation."""

    def __init__(self, temperature, name='', mass=1.0, collision_period=-1):
        self.name = name
        self.temperature = temperature
        self.mass = mass
        self.collision_period = collision_period


class Barostat(object):

    """Barostat to control the pressure during a simulation."""

    def __init__(self, pressure, name='', mass=1.0):
        self.name = name
        self.pressure = pressure
        self.mass = mass


class Reservoir(object):

    """Reservoir to control the number of particles during a simulation."""

    def __init__(self, chemical_potential, name='', mass=1.0):
        self.name = name
        self.chemical_potential = chemical_potential
        self.mass = mass
