"""An abstract Laser class.

Copyright 2014-2015 Mick Phillips (mick.phillips at gmail dot com)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

## This module defines the interface for a laser that can be controlled
# by cockpit.devices.laserpower.
import abc
import Pyro4
import serial
import socket
import threading
import time

# The name of the config section for this device
CONFIG_NAME = 'dummyLaser'
# The name of the class that provides the interface specified below.
CLASS_NAME = 'Laser'


def _storeSetPoint(func):
    def _wrappedSetPower(self, mW):
        self.powerSetPoint_mW = mW
        # self seems to be passed implicitly due to binding.
        func(mW)
    return _wrappedSetPower


## This is a prototype for a class to be used with laser_server.
class Laser(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def __init__(self, *args):
        ## Should connect to the physical device here and set self.connection
        # to a type with read, readline and write methods (e.g. serial.Serial).
        self.connection = None
        self.powerSetPoint_mW = None
        # Wrap derived-classes setPower_mW to store power set point.
        # The __get__(self, Laser) binds the wrapped function to an instance.
        self.setPower_mW = _storeSetPoint(self.setPower_mW).__get__(self, Laser)


    ## Simple passthrough.
    @abc.abstractmethod
    def read(self, numChars):
        return self.connection.read(numChars)


    ## Simple passthrough.
    @abc.abstractmethod
    def readline(self):
        return self.connection.readline().strip()


    ## Send a command.
    @abc.abstractmethod
    def write(self, command):
        # Override if a specific format is required.
        response = self.connection.write(command + '\r\n')
        return response

    
    ## Query and return the laser status.
    @abc.abstractmethod
    def getStatus(self):
        result = []
        # ...
        return result


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @abc.abstractmethod
    def enable(self):
        pass


    ## Turn the laser OFF.
    @abc.abstractmethod
    def disable(self):
        pass


    ## Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    @abc.abstractmethod
    def getIsOn(self):
        pass


    ## Return the max. power in mW.
    @abc.abstractmethod
    def getMaxPower_mW(self):
        pass


    ## Return the current power in mW.
    @abc.abstractmethod
    def getPower_mW(self):
        pass


    ## Return the power set point.
    def getSetPower_mW(self):
        return self.powerSetPoint_mW


    ## Set the power from an argument in mW.
    @abc.abstractmethod
    def setPower_mW(self, mW):
        pass