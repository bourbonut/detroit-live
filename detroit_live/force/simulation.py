from collections.abc import Callable
from detroit.force.simulation import ForceSimulation
from detroit.types import SimulationNode
from typing import TypeVar
from ..dispatch import dispatch
from ..timer import timer

TLiveForceSimulation = TypeVar("LiveForceSimulation", bound="LiveForceSimulation")

class LiveForceSimulation(ForceSimulation):

    def __init__(self, nodes: list[SimulationNode]):
        super().__init__(nodes)
        self._event = dispatch("tick", "end")
        self._stepper = timer(self._step)

    def _step(self, elapsed: float, stop: Callable[[None], None]):
        self.tick()
        self._event("tick", self)
        if self._alpha < self._alpha_min:
            stop()
            self._event("end", self)

    def restart(self) -> TLiveForceSimulation:
        """
        Restarts the simulation's internal timer and returns the simulation. In
        conjunction with :code:`alpha_target` or :code:`alpha`, this method can
        be used to "reheat" the simulation during interaction, such as when
        dragging a node, or to resume the simulation after temporarily pausing
        it with :code:`simulation.stop`.

        Returns
        -------
        LiveForceSimulation
            Itself
        """
        self._stepper.restart(self._step)
        return self

    def stop(self) -> TLiveForceSimulation:
        """
        Stops the simulation's internal timer, if it is running, and returns
        the simulation. If the timer is already stopped, this method does
        nothing. This method is useful for running the simulation manually; see
        :code:`simulation.tick`.

        Returns
        -------
        LiveForceSimulation
            Itself
        """
        self._stepper.stop()
        return self

    def on(self, typename: str, listener: Callable[[TLiveForceSimulation], None]) -> TLiveForceSimulation:
        """
        Sets the event listener for the specified typenames and returns this
        simulation.

        When a specified event is dispatched, each listener will be invoked
        with the this context as the simulation.

        The :code:`typename` must be one of the following:

        * :code:`tick` - after each tick of the simulation's internal timer.
        * :code:`end` - after the simulation's timer stops when :code:`alpha <
        alpha_min`.

        Parameters
        ----------
        typename : str
            
        listener : Callable[[LiveForceSimulation], None]
            Listener

        Returns
        -------
        LiveForceSimulation
            Itself

        Notes
        -----
        Tick events are not dispatched when :code:`simulation.tick` is called
        manually; events are only dispatched by the internal timer and are
        intended for interactive rendering of the simulation. To affect the
        simulation, register forces instead of modifying nodes' positions or
        velocities inside a tick event listener.
        """
        self._event.on(typename, listener)
        return self

def force_simulation(nodes: list[SimulationNode] | None = None) -> LiveForceSimulation:
    """
    A force simulation implements a velocity Verlet numerical integrator for
    simulating physical forces on particles (nodes). The simulation assumes a
    constant unit time step :math:`\\Delta t = 1` for each step and a constant
    unit mass :math:`m = 1` for all particles. As a result, a force :math:`F`
    acting on a particle is equivalent to a constant acceleration a over the
    time interval :math:`\\Delta t`, and can be simulated simply by adding to
    the particle's velocity, which is then added to the particle's position.

    Parameters
    ----------
    nodes : list[SimulationNode] | None
        List of nodes

    Returns
    -------
    LiveForceSimulation
        Simulation object
    """
    if nodes is None:
        nodes = []
    return LiveForceSimulation(nodes)
