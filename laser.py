
import Pyro4
import serial
import socket
import threading
import time

# The name of the config section for this device
CONFIG_NAME = 'dummyLaser'
# The name of the class that provides the interface specified below.
CLASS_NAME = 'Laser'


## This is a prototype for a class to be used with laser_server.
class Laser:
    def __init__(self, serialPort, baudRate, timeout):
        # Should connect to the physical device here.
        pass


    ## Simple passthrough.
    def read(self, numChars):
        return self.connection.read(numChars)


    ## Simple passthrough.
    def readline(self):
        return self.connection.readline().strip()


    ## Send a command.
    def write(self, command):
        # Override if a specific format is required.
        response = self.connection.write(command + '\r\n')
        return response

    
    ## Query and return the laser status.
    def getStatus(self):
        result = []
        # ...
        return result


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    def enable(self):
        pass


    ## Turn the laser OFF.
    def disable(self):
        pass


    ## Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    def getIsOn(self):
        pass


    ## Set the laser power in native units.
    def setPower(self, level):
        pass


    ## Return the max. power in mW.
    def getMaxPower_mW(self):
        pass


    ## Return the current power in native units.
    def getPower(self):
        pass


    ## Return the current power in mW.
    def getPower_mW(self):
        pass


    ## Set the power from an argument in mW.
    def setPower_mW(self, mW):
        pass