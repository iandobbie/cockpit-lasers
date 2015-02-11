import Pyro4
import serial
import socket
import threading
import time
import functools

CONFIG_NAME = 'deepstar'
CLASS_NAME = 'DeepstarLaser'

def flushBuffer(func):
    """A decorator to flush the input buffer prior to issuing a command.

    There have been problems with the DeepStar lasers returning junk characters
    after the expected response, so it is advisable to flush the input buffer
    prior to running a command and subsequent readline.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        self.connection.flushInpu()
        return func(self, *args, **kwargs)

    return wrapper


class LaserLogger(object):
    def __init__(self):
        self.fh = None

    def log(self, message):
        if self.fh:
            self.fh.write(time.strftime('%Y-%m-%d %H:%M:%S:  '))
            self.fh.write(message + '\n')
            self.fh.flush()

    def open(self, filename):
        path = os.path.dirname(os.path.abspath(__file__))
        self.fh = open(os.path.join(path, str(filename) + '.txt'), 'w')

    def close(self):
        self.fh.close()
        self.fh = None


class DeepstarLaser:
    def __init__(self, serialPort, baudRate, timeout):
        print "Connecting to laser on port",serialPort,"with rate",baudRate,"and timeout",timeout
        self.connection = serial.Serial(port = serialPort,
            baudrate = baudRate, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        # Start a logger.
        self.logger = LaserLogger()
        self.logger.open('DeepStar_' + serialPort)
        # If the laser is currently on, then we need to use 7-byte mode; otherwise we need to
        # use 16-byte mode.
        self.write('S?')
        response = self.readline()
        self.logger.log("Current laser state: [%s]" % response)
        

    ## Simple passthrough.
    def read(self, numChars):
        return self.connection.read(numChars)


    ## Simple passthrough.
    def readline(self):
        return self.connection.readline().strip()


    ## Send a command.
    def write(self, command):
        # We'll need to pad the command out to 16 bytes. There's also a 7-byte mode but
        # we never need to use it.
        commandLength = 16
        # CR/LF count towards the byte limit, hence the -2.
        command = command + (' ' * (commandLength - 2 - len(command)))
        response = self.connection.write(command + '\r\n')
        return response


    ## Get the status of the laser, by sending the
    # STAT0, STAT1, STAT2, and STAT3 commands.
    @flushBuffer
    def getStatus(self):
        result = []
        for i in xrange(4):
            self.write('STAT%d' % i)
            result.append(self.readline())
        return result


    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    @flushBuffer
    def enable(self):
        self.logger.log("Turning laser ON.")
        self.write('LON')
        response = self.readline()
        #Set power to something small
        self.setPower(0.01)
        #Turn on deepstar mode with internal voltage ref
        self.logger.log("Enable response: [%s]" % response)
        self.write('L2')
        response = self.readline()
        self.logger.log("L2 response: [%s]" % response)
        #Enable internal peak power
        self.write('IPO')
        response = self.readline()
        self.logger.log("Enable-internal peak power response [%s]" % response)
        #Set MF turns off internal digital and bias modulation
        self.write('MF')
        response = self.readline()
        self.logger.log("MF response [%s]" % response)

        if not self.getIsOn():
            # Something went wrong.
            self.write('S?')
            response = self.readline()
            self.logger.log("Failed to turn on. Current status: %s" % response)
            return False
        return True


    ## Turn the laser OFF.
    @flushBuffer
    def disable(self):
        self.logger.log("Turning laser OFF.")
        self.write('LF')
        return self.readline()


    ## Return True if the laser is currently able to produce light. We assume this is equivalent
    # to the laser being in S2 mode.
    @flushBuffer
    def getIsOn(self):
        self.write('S?')
        response = self.readline()
        self.logger.log("Are we on? [%s]" % response)
        return response == 'S2'


    @flushBuffer
    def setPower(self, level):
        if (level > 1.0) :
            return
        self.logger.log("level=%d" % level)
        power=int (level*0xFFF)
        self.logger.log("power=%d" % power)
        strPower = "PP%03X" % power
        self.logger.log("power level=%s" %strPower)
        self.write(strPower)
        response = self.readline()
        self.logger.log("Power response [%s]" % response)
        return response


    @flushBuffer
    def getMaxPower_mW(self):
        # Max power in mW is third token of STAT0.
        self.write('STAT0')
        response = self.readline()
        return int(response.split()[2])


    @flushBuffer
    def getPower(self):
        self.write('PP?')
        response = self.readline()
        return int('0x' + response.strip('PP'), 16)


    @flushBuffer
    def getPower_mW(self):
        maxPower = self.getMaxPower_mW()
        power = self.getPower()
        return maxPower * float(power) / float(0xFFF)


    @flushBuffer
    def setPower_mW(self, mW):
        maxPower = self.getMaxPower_mW()
        level = float(mW) / maxPower
        self.setPower(level)


if __name__ == "__main__":
    ## Only run when called as a script --- do not run on include.
    #  This way, we can use an interactive shell to test out the class.

    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-p", "--port", type="int", dest="net_port", default=7776, help="TCP port to listen on for service", metavar="PORT_NUMBER")
    parser.add_option("-n", "--name", dest="service_name", default='pyro488DeepstarLaser', help="name of service", metavar="NAME")
    parser.add_option("-s", "--serial", type="int", dest="serial_port", default=1, help="serial port number", metavar="PORT_NUMBER")
    parser.add_option("-b", "--baud", type="int", dest="baud_rate", default=9600, help="serial port baud rate in bits/sec", metavar="RATE")
    (options, args) = parser.parse_args()

    laser = DeepstarLaser(options.serial_port, options.baud_rate, 2)

    daemon = Pyro4.Daemon(port = options.net_port,
            host = socket.gethostbyname(socket.gethostname()))
    Pyro4.Daemon.serveSimple(
            {laser: options.service_name},
            daemon = daemon, ns = False, verbose = True)
