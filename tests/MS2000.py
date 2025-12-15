from pyvisa import ResourceManager

# Reference: https://www.asiimaging.com/downloads/manuals/Operations_and_Programming_Manual.pdf
class MS2000:
  """
  Controls an ASI-MS2000 stage via VISA.
  """
  def __init__(self, resourceName=None, resourceManager=None):
    if resourceManager is None:
      rm = ResourceManager()
    else:
      rm = resourceManager

    def configure(device):
      device.baud_rate = 9600
      device.read_termination = '\r'
      device.write_termination = '\r'

    if resourceName is None:
      found = False
      for resource in rm.list_resources():
        try:
          device = rm.open_resource(resource)
          configure(device)
          idn = device.query("WHO")
          if True:  
            resourceName = resource
            self.stage = device
            print("Found", idn, "at:", resourceName)
            found = True
            break
          device.close()
        except:
          continue
      if not found:
        raise RuntimeError(f"Instrument not found, idn = {idn}")

    else:
      if resourceName in rm.list_resources():
        self.stage = rm.open_resource(resourceName)
        configure(self.stage)
        if not ("ASI-MS2000" in self.stage.query("WHO")):
          raise ValueError("Not an ASI MS2000 stage controller.")
      else:
        raise ValueError("Instrument address not found,,")

  def status(self):
    """Return true if the stage is not moving."""
    return not bool("B" in self.stage.query("STATUS").strip())

  def limits(self, x=True, y=True, z=True):
    """Get current limits for the given axes."""
    if not (x or y or z):
      raise ValueError("Must specify at least one axis")

    instruction = "SETLOW"
    if x: instruction += " X?"
    if y: instruction += " Y?"
    if z: instruction += " Z?"
    responsesLow = self.stage.query(instruction).split()
    lowerLims = [float(coord[2:]) for coord in responsesLow[1:]]

    instruction = "SETUP"
    if x: instruction += " X?"
    if y: instruction += " Y?"
    if z: instruction += " Z?"
    responsesHigh = self.stage.query(instruction).split()
    upperLims = [float(coord[2:]) for coord in responsesHigh[1:]]

    return *((coordLow, coordHigh) for coordLow, coordHigh in zip(lowerLims, upperLims)),

  def setLimit(self, axis="X", lower=None, upper=None):
    """Changes the limit of operation for the given axis"""
    if axis not in ("X", "Y", "Z"):
      raise ValueError("Axis must be X, Y or Z")
    if not (lower or upper):
      raise ValueError("Must specify at least an upper or lower limit")

    if lower is not None:
      if not isinstance(lower, (int, float)):
          raise TypeError(axis + " limit must be numeric type!")
      self.stage.query(f"SETLOW {axis}={lower}")

    if upper is not None:
      if not isinstance(upper, (int, float)):
          raise TypeError(axis + " limit must be numeric type!")
      self.stage.query(f"SETUP {axis}={upper}")


  def home(self):
    """Move to origin (0, 0, 0)"""
    self.move(x=0, y=0, z=0, relative=False)

  def zero(self):
    """Set the current position as the origin"""
    self.stage.query("ZERO")

  def position(self, x=True, y=True, z=True):
    """Return the positions on the given axes. Units are in tenths of microns."""
    if not (x or y or z):
      raise ValueError("Must specify at least one axis")

    instruction = "WHERE"
    if x: instruction += " X"
    if y: instruction += " Y"
    if z: instruction += " Z"
 
    responses = self.stage.query(instruction).split()
    coords = *(float(coord) for coord in responses[1:]),

    if len(coords) == x + y + z:
      return coords
    else: # try again
      return self.position()
  

  def move(self, x=None, y=None, z=None, relative=False):
    """
    Move the stage to the given coordinates.
    Units are in tenths of microns. E.g. if x = 1234, x axis will go to 123.4 microns
    Anything beyond the limits (typically +- 110mm) will stop at the limit.
    Specify relative for relative motion from given position.
    """
    if not (x is not None or y is not None or z is not None):
      raise ValueError("Must specify at least one axis")

    instruction = "MOVE" if not relative else "MOVREL"

    for axis, coord in zip(("X", "Y", "Z"), (x, y, z)):
      if coord is not None:
        if not isinstance(coord, (int, float)):
          raise TypeError(axis + " coordinate must be numeric type!")
        instruction += f" {axis}={round(coord,3)}"
    if not self.status():
      raise RuntimeError("Device is busy moving!")
    self.stage.query(instruction)

  def getSpeed(self, x=True, y=True, z=True):
    """
    Request the speed, given in millimeters per second.
    """
    if not (x or y or z):
      raise ValueError("Must specify at least one axis")

    instruction = "SPEED"
    if x: instruction += " X?"
    if y: instruction += " Y?"
    if z: instruction += " Z?"

    responses = self.stage.query(instruction).split()
    return *(float(coord[2:]) for coord in responses[1:]),

  def speed(self, x=None, y=None, z=None):
    """
    Sets the maximum speed at which the stage will move.
    Speed is set in millimeters per second.
    Standard maximum speed is = 7.5 mm/s
    """
    if not (x or y or z):
      raise ValueError("Must specify at least one axis")

    instruction = "SPEED"

    for axis, coord in zip(("X", "Y", "Z"), (x, y, z)):
      if coord is not None:
        if not isinstance(coord, (int, float)):
          raise TypeError(axis + " coordinate must be numeric type!")
        instruction += f" {axis}={coord}"

    if not self.status():
      raise RuntimeError("Device is busy moving!")

    self.stage.query(instruction)


  def close(self):
     self.stage.close()

  def open(self):
     self.stage.open()

