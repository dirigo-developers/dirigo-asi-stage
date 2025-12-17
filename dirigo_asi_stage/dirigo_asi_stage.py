import time
from typing import Optional
from dataclasses import dataclass
from functools import cached_property

from pyvisa import ResourceManager

from dirigo import units
from dirigo.hw_interfaces.stage import MultiAxisStage, LinearStage, StageInfo
from .ms2000_lowlevel import MS2000


@dataclass
class ASILinearMotorInfo(StageInfo):
    """Stage info for ASI linear motor axes."""
    serial_number: str
    resource_name: str


class ASILinearMotor(LinearStage):
    """
    ASI linear motor stage axis (X, Y, or Z).
    
    The ASI MS2000 uses units of tenths of microns (0.1 μm) internally.
    This class converts to/from Dirigo's Position units (typically mm).
    """
    HOME_TIMEOUT = units.Time('30 s')
    MOVE_TIMEOUT = units.Time('30 s')
    POLLING_PERIOD = units.Time('50 ms')
    
    # # Conversion factor: ASI uses tenths of microns, Dirigo uses mm
    # # 1 mm = 10000 tenths of microns
    # TENTHS_OF_MICRONS_PER_MM = 10000.0

    def __init__(self, stage_controller: 'MS2000Stage', 
                 axis: str,
                 position_limits: dict = None, **kwargs):
        super().__init__(axis=axis, **kwargs)
        
        self._controller = stage_controller
        self._axis_upper = axis.upper()  # ASI uses uppercase X, Y, Z
        
        # Position limits may be set manually in system_config.toml, or omitted
        if position_limits is None:
            self._position_limits = None  # Will read from device
        else:
            self._validate_limits_dict(position_limits)
            self._position_limits = units.PositionRange(**position_limits)
        
        # Store previous position to handle edge cases
        time.sleep(0.1)  # Wait for axis to stabilize
        self._prev_position = self.position

    @cached_property
    def device_info(self) -> ASILinearMotorInfo:
        """Returns an object describing permanent properties of the stage."""
        return ASILinearMotorInfo(
            manufacturer="ASI",
            model="MS2000",
            serial_number=self._controller._resource_name,
            resource_name=self._controller._resource_name
        )

    @cached_property
    def position_limits(self) -> units.PositionRange:
        """Get position limits from device or use configured limits."""
        if self._position_limits is None:
            # Query limits from device
            # Always request all axes from the device and then select ours
            limits = self._controller._stage.limits(x=True, y=True, z=True)
            # Limits are returned as (lower, upper) tuples in tenths of microns,
            # in the order (x, y, z)
            axis_idx = {'x': 0, 'y': 1, 'z': 2}[self.axis]
            lower_tenths_um, upper_tenths_um = limits[axis_idx]
            # Convert to mm
            # lower_mm = lower_tenths_um / self.TENTHS_OF_MICRONS_PER_MM
            # upper_mm = upper_tenths_um / self.TENTHS_OF_MICRONS_PER_MM
            return units.PositionRange(lower_tenths_um/10e6, upper_tenths_um/10e6)
        else:
            return self._position_limits
    
    @property
    def position(self) -> units.Position:
        """The current spatial position in mm."""
        # Always request all axes and then take the one we care about
        pos_tenths_um = self._controller._stage.position(x=True, y=True, z=True)
        # Position returns tuple (x, y, z) in tenths of microns
        axis_idx = {'x': 0, 'y': 1, 'z': 2}[self.axis]
        pos_tenths_um = pos_tenths_um[axis_idx]
        # Convert to mm
        # pos_mm = pos_tenths_um / self.TENTHS_OF_MICRONS_PER_MM
        position = units.Position(pos_tenths_um/10e6)
        
        # Store for potential bug workarounds
        self._prev_position = position
        return position

    def move_to(self, position: units.Position, blocking: bool = False):
        """
        Initiate move to specified spatial position.
        
        Choose whether to return immediately (blocking=False, default) or to
        wait until finished moving (blocking=True).
        """
        # Validate move position
        if not self.position_limits.within_range(position):
            raise ValueError(
                f"Requested move ({position}) beyond limits, "
                f"min: {self.position_limits.min}, max: {self.position_limits.max}"
            )
        
        # Convert to tenths of microns
        #pos_tenths_um = round(position * self.TENTHS_OF_MICRONS_PER_MM, 3)
        pos_tenths_um = round(position * 10e6, 3) # TODO is rounding needed/OK?
        
        # Build move command
        move_kwargs = {self.axis: pos_tenths_um}
        self._controller._stage.move(**move_kwargs, relative=False)
        
        if blocking:
            # Wait until move is complete
            start_time = time.perf_counter()
            while self.moving:
                if time.perf_counter() - start_time > self.MOVE_TIMEOUT:
                    raise TimeoutError(f"Move timed out after {self.MOVE_TIMEOUT}")
                time.sleep(self.POLLING_PERIOD)
        
        self._last_move_timestamp = time.perf_counter()

    @property
    def moving(self) -> bool:
        """Return True if the stage axis is currently moving."""
        # ASI status returns True if not moving, False if moving
        # So we invert it
        return not self._controller._stage.status()

    def move_velocity(self, velocity: units.Velocity):
        """
        Initiates movement at a constant velocity until stopped.
        
        Note: ASI MS2000 doesn't have native continuous velocity control.
        This implementation sets the speed and initiates a large relative move
        in the direction of the velocity. The move will continue until stop() is called.
        """
        if not isinstance(velocity, units.Velocity):
            raise ValueError("velocity must be given in units.Velocity")
        
        # Do NOT change the device's speed setting here; assume it has been
        # configured elsewhere. We only use the sign of the requested
        # velocity to choose direction, matching the behaviour in the
        # standalone ASI StageControl tests.
        direction = 1 if velocity > 0 else -1
        # Large relative move in tenths of microns so motion continues
        # at the preconfigured device speed until stop() is called.
        large_distance_tenths_um = direction * 10000000  # 1000 mm in the direction
        move_kwargs = {self.axis: large_distance_tenths_um}
        self._controller._stage.move(**move_kwargs, relative=True)

    def stop(self):
        """
        Halts motion.
        
        Note: ASI MS2000 doesn't have a direct stop command. This implementation
        sends a move command to the current position, which effectively stops
        any ongoing movement.
        """
        # Get current position and move to it (no-op that stops movement)
        current_pos_tenths_um = self._controller._stage.position(x=True, y=True, z=True)
        axis_idx = {'x': 0, 'y': 1, 'z': 2}[self.axis]
        current_pos_tenths_um = current_pos_tenths_um[axis_idx]
        move_kwargs = {self.axis: current_pos_tenths_um}
        try:
            self._controller._stage.move(**move_kwargs, relative=False)
        except RuntimeError:
            # If device is busy, wait a bit and try again
            time.sleep(0.1)
            current_pos_tenths_um = self._controller._stage.position(x=True, y=True, z=True)
            axis_idx = {'x': 0, 'y': 1, 'z': 2}[self.axis]
            current_pos_tenths_um = current_pos_tenths_um[axis_idx]
            move_kwargs = {self.axis: current_pos_tenths_um}
            self._controller._stage.move(**move_kwargs, relative=False)

    def home(self, blocking: bool = False):
        """
        Initiate homing (move to origin).
        
        Choose whether to return immediately (blocking=False, default) or to
        wait until finished homing (blocking=True).
        """
        self._controller._stage.home()
        
        if blocking:
            # Wait until move is complete
            start_time = time.perf_counter()
            while self.moving:
                if time.perf_counter() - start_time > self.HOME_TIMEOUT:
                    raise TimeoutError(f"Homing timed out after {self.HOME_TIMEOUT}")
                time.sleep(self.POLLING_PERIOD)

    @property
    def homed(self) -> bool:
        """
        Return whether the stage has been homed.
        
        Note: ASI stages don't have a homed status, so we check if
        position is near zero (within 1 mm).
        """
        current_pos = self.position
        # Position is a units.Position (UnitQuantity subclass), whose float
        # value is in millimeters, so we can compare directly.
        return abs(float(current_pos)) < 1.0

    @property
    def max_velocity(self) -> units.Velocity:
        """
        Return the current maximum velocity setting.
        
        Note that this is the imposed velocity limit for moves. It is not
        necessarily the maximum attainable velocity for this stage.
        """
        speeds = self._controller._stage.getSpeed(
            x=(self.axis == 'x'),
            y=(self.axis == 'y'),
            z=(self.axis == 'z')
        )
        axis_idx = {'x': 0, 'y': 1, 'z': 2}[self.axis]
        speed_mm_per_s = speeds[axis_idx]
        return units.Velocity(speed_mm_per_s)

    @max_velocity.setter
    def max_velocity(self, new_velocity: units.Velocity):
        """Set the maximum velocity."""
        velocity_mm_per_s = float(new_velocity.with_unit("mm/s"))
        self._controller._stage.speed(**{self.axis: velocity_mm_per_s})

    @property
    def acceleration(self) -> units.Acceleration:
        """
        Return the acceleration used during ramp up/down phase of move.
        
        Note: ASI MS2000 doesn't expose acceleration settings via the API.
        This returns a default value.
        """
        # ASI doesn't provide acceleration control, return a reasonable default
        return units.Acceleration("1 mm/s²")

    @acceleration.setter
    def acceleration(self, new_acceleration: units.Acceleration):
        """
        Set the acceleration.
        
        Note: ASI MS2000 doesn't support acceleration control via API.
        This is a no-op but doesn't raise an error for compatibility.
        """
        # ASI doesn't support acceleration control
        pass


class MS2000Stage(MultiAxisStage):
    """
    Communicate with ASI MS2000 stage controller via VISA.
    
    The MS2000 is a 3-axis (X, Y, Z) linear motor stage controller.
    
    https://www.asiimaging.com/products/ms-2000/
    """
    
    def __init__(self, 
                 x_config: dict = None,
                 y_config: dict = None,
                 z_config: dict = None,
                 resource_name: Optional[str] = None,
                 **kwargs):
        """
        Initialize ASI MS2000 stage.
        
        Args:
            x_config: Configuration dict for X axis (e.g., position_limits)
            y_config: Configuration dict for Y axis (e.g., position_limits)
            z_config: Configuration dict for Z axis (e.g., position_limits)
            resource_name: VISA resource name (e.g., 'ASRL1::INSTR').
                           If None, will auto-detect.
        """
        # Initialize VISA connection via the low-level MS2000 helper, which
        # provides the high-level API (position, limits, move, etc.) that
        # ASILinearMotor expects.
        rm = ResourceManager()
        self._stage = MS2000(resource_name=resource_name, resource_manager=rm)
        self._resource_name = getattr(self._stage, "resource_name", resource_name or "unknown")
        
        # Initialize axes with configs
        x_config = x_config or {}
        y_config = y_config or {}
        z_config = z_config or {}
        
        self._x_axis = ASILinearMotor(self, axis='x', **x_config)
        self._y_axis = ASILinearMotor(self, axis='y', **y_config)
        self._z_axis = ASILinearMotor(self, axis='z', **z_config)
        
        # Home axes if not already homed
        if not self._x_axis.homed:
            self._x_axis.home(blocking=False)
        if not self._y_axis.homed:
            self._y_axis.home(blocking=False)
        if not self._z_axis.homed:
            self._z_axis.home(blocking=False)
    
    @property
    def x(self) -> LinearStage:
        """Returns reference to x axis motor."""
        return self._x_axis
    
    @property
    def y(self) -> LinearStage:
        """Returns reference to y axis motor."""
        return self._y_axis
    
    @property
    def z(self) -> LinearStage:
        """Returns reference to z axis motor."""
        return self._z_axis
    
    def close(self):
        """Close the VISA connection."""
        if hasattr(self, '_stage'):
            self._stage.close()

