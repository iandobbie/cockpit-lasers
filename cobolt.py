"""A Laser class implementation for Cobolt lasers.

Copyright 2015 Mick Phillips (mick.phillips at gmail dot com)

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
import Pyro4
import serial
import socket
import threading
import time
import laser
import functools

CONFIG_NAME = 'cobolt'
CLASS_NAME = 'CoboltLaser'

def lockComms(func):
    """A decorator to flush the input buffer prior to issuing a command.

    Locks the comms channel so that a function must finish all its comms
    before another can run.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.commsLock:
            return func(self, *args, **kwargs)

    return wrapper


class CoboltLaser(laser.Laser):
    def __init__(self, serialPort, baudRate, timeout):
        super(CoboltLaser, self).__init__()
        print "Connecting to laser on port",serialPort,"with rate",baudRate,"and timeout",timeout
        self.connection = serial.Serial(port = serialPort,
            baudrate = baudRate, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # Start a logger.
        self.logger = laser.LaserLogger()
        self.logger.open(CLASS_NAME + '_' + serialPort)
        self.write('sn?')
        response = self.readline()
        self.logger.log("Cobolt laser serial number: [%s]" % response)
        # We need to ensure that autostart is disabled so that we can switch emission
        # on/off remotely.
        self.write('@cobas 0')
        self.logger.log("Response to @cobas 0 [%s]" % self.readline())
        self.commsLock = threading.RLock()


    ## Simple passthrough.
    def read(self, numChars):
        return self.connection.read(numChars)


    ## Simple passthrough.
    def readline(self):
        return self.connection.readline().strip()


    ## Send a command. 
    def write(self, command):
        response = self.connection.write(command + '\r\n')
        return response


    ## Send command and retrieve response.
    def send(self, command):
        self.write(str(command))
        return self.readline()


    @lockComms
    def clearFault(self):
        self.write('cf')
        self.readline()
        return self.getStatus()


    def flushBuffer(self):
        line = ' '
        while len(line) > 0:
            line = self.readline()

    @lockComms
    def isAlive(self):
        self.write('l?')
        response = self.readline()
        return response in '01'


    @lockComms
    def getStatus(self):
        result = []
        for cmd, stat in [('l?', 'Emission on?'),
                            ('p?', 'Target power:'),
                            ('pa?', 'Measured power:'),
                            ('f?', 'Fault?'),
                            ('hrs?', 'Head operating hours:')]:
            self.write(cmd)
            result.append(stat + ' ' + self.readline())
        return result


    ## Things that should be done when cockpit exits.
    @lockComms
    def onExit(self):
        # Disable laser.
        self.send('l0')
        self.send('@cob0')
        self.flushBuffer()


    ##  Initialization to do when cockpit connects.
    @lockComms
    def onCockpitInitialize(self):
        self.flushBuffer()
        #We don't want 'direct control' mode.
        self.send('@cobasdr 0')
        # Force laser into autostart mode.
        self.send('@cob1')


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @lockComms
    def enable(self):
        self.logger.log("Turning laser ON at %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
        # Turn on emission.
        response = self.send('l1')
        self.logger.log("l1: [%s]" % response)

        if not self.getIsOn():
            # Something went wrong.
            self.logger.log("Failed to turn on. Current status:\r\n")
            self.loggerl.log(self.getStatus())
            return False
        return True


    ## Turn the laser OFF.
    @lockComms
    def disable(self):
        self.logger.log("Turning laser OFF at %s" % time.strftime('%Y-%m-%d %H:%M:%S'))
        self.write('l0')
        return self.readline()


    ## Return True if the laser is currently able to produce light.
    @lockComms
    def getIsOn(self):
        self.write('l?')
        response = self.readline()
        return response == '1'


    @lockComms
    def getMaxPower_mW(self):
        # 'gmlp?' gets the maximum laser power in mW.
        self.write('gmlp?')
        response = self.readline()
        return float(response)


    @lockComms
    def getPower_mW(self):
        self.write('pa?')
        return 1000 * float(self.readline())


    @lockComms
    def setPower_mW(self, mW):
        mW = min(mW, self.getMaxPower_mW)
        self.logger.log("Setting laser power to %.4fW at %s"  % (mW / 1000.0, time.strftime('%Y-%m-%d %H:%M:%S')))
        return self.send("@cobasp %.4f" % (mW / 1000.0))


    @lockComms
    def getSetPower_mW(self):
        self.write('p?')
        return 1000 * float(self.readline())


if __name__ == "__main__":
    ## Only run when called as a script --- do not run on include.
    #  This way, we can use an interactive shell to test out the class.

    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-p", "--port", type="int", dest="net_port", default=7776, help="TCP port to listen on for service", metavar="PORT_NUMBER")
    parser.add_option("-n", "--name", dest="service_name", default='pyro561CoboltLaser', help="name of service", metavar="NAME")
    parser.add_option("-s", "--serial", type="int", dest="serial_port", default=1, help="serial port number", metavar="PORT_NUMBER")
    parser.add_option("-b", "--baud", type="int", dest="baud_rate", default=9600, help="serial port baud rate in bits/sec", metavar="RATE")
    (options, args) = parser.parse_args()

    laser = CoboltLaser(options.serial_port, options.baud_rate, 2)

    daemon = Pyro4.Daemon(port = options.net_port,
            host = socket.gethostbyname(socket.gethostname()))
    Pyro4.Daemon.serveSimple(
            {laser: options.service_name},
            daemon = daemon, ns = False, verbose = True)
