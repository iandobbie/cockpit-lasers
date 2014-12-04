import Pyro4
import serial
import socket
import threading
import time

CONFIG_NAME = 'cobolt'

class CobaltLaser:
    def __init__(self, serialPort, baudRate, timeout):
        print "Connecting to laser on port",serialPort,"with rate",baudRate,"and timeout",timeout
        self.connection = serial.Serial(port = serialPort,
            baudrate = baudRate, timeout = timeout,
            stopbits = serial.STOPBITS_ONE,
            bytesize = serial.EIGHTBITS, parity = serial.PARITY_NONE)
        self.write('sn?')
        response = self.readline()
        print "Cobalt laser serial number: [%s]" % response


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

    ## Turn the laser ON. Return True if we succeeded, False otherwise.
    def enable(self):
        print "Turning laser ON at %s" % time.strftime('%Y-%m-%d %H:%M:%S')
        #Set power to something small ... < 10% is unstable, though.
        self.setPower_mW(self.getMaxPower_mW() / 10.0)
        response = self.readline()
        print "Set power response: [%s]" % response
        #We don't want 'direct control' mode.
        self.write('@cobasdr 0')
        response = self.readline()
        print "@cobasdr 0 response: [%s]" % response
        #Finally, turn on emission.
        self.write('l1') 
        response = self.readline()
        print "l1: [%s]" % response

        if not self.getIsOn():
            # Something went wrong.
            print "Failed to turn on. Current status:\r\n"
            print self.getStatus()
            return False
        return True


    ## Turn the laser OFF.
    def disable(self):
        print "Turning laser OFF at %s" % time.strftime('%Y-%m-%d %H:%M:%S')
        self.write('l0')
        return self.readline()


    ## Return True if the laser is currently able to produce light.
    def getIsOn(self):
        self.write('l?')
        response = self.readline()
        print "Are we on? [%s]" % response
        return response == '1'


    def getMaxPower_mW(self):
        # 'gmlp?' gets the maximum laser power in mW.
        self.write('gmlp?')
        response = self.readline()
        return float(response)


    def getPower_mW(self):
        self.write('pa?')
        return 1000 * float(self.readline())


    def setPower_mW(self, mW):
        mW = min(mW, self.getMaxPower_mW)
        print "Setting laser power to %.4fW at %s"  % (mW / 1000.0, time.strftime('%Y-%m-%d %H:%M:%S'))
        self.write("p %.4f" % (mW / 1000.0))
        return self.readline()


class Server(object):
    def __init__(self):
        self.run_flag = True
        self.threads = []
        self.daemons = []
        self.devices = []


    def run(self):
        import readconfig
        config = readconfig.config
        sections = [s for s in config.sections() if s.startswith(CONFIG_NAME)]

        for section in sections:
            com = config.get(section, 'comPort')
            baud = config.get(section, 'baud')
            host = config.get(section, 'ipAddress')
            port = config.get(section, 'port')
            try:
                timeout = config.get(section, 'timeout')
            except:
                timeout = 1.

            daemon = Pyro4.Daemon(port=port, host=host)
            device = DeepstarLaser(com, baud, timeout)

            # Start the daemon in a new thread.
            daemon_thread = threading.Thread(
                target=Pyro4.Daemon.serveSimple,
                args = ({server: 'pyro%s' % section}),
                kwargs = {'daemon': daemon, 'ns': False}
                )
            daemon_thread.start()

            self.daemons.append(daemon)
            self.threads.append(daemon_thread)


        # Wait until run_flag is set to False.
        while self.run_flag:
            time.sleep(1)

        # Do any cleanup.
        for daemon in self.daemons():
            daemon.Shutdown()

        for devices in self.devices():
            device.disable()
            del(device)

        for thread in self.threads():
            thread.stop()
            thread.join()


    def shutdown(self):
        self.run_flag = 0


if __name__ == "__main__":
    ## Only run when called as a script --- do not run on include.
    #  This way, we can use an interactive shell to test out the class.

    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-p", "--port", type="int", dest="net_port", default=7776, help="TCP port to listen on for service", metavar="PORT_NUMBER")
    parser.add_option("-n", "--name", dest="service_name", default='pyro561CobaltLaser', help="name of service", metavar="NAME")
    parser.add_option("-s", "--serial", type="int", dest="serial_port", default=1, help="serial port number", metavar="PORT_NUMBER")
    parser.add_option("-b", "--baud", type="int", dest="baud_rate", default=9600, help="serial port baud rate in bits/sec", metavar="RATE")
    (options, args) = parser.parse_args()

    laser = CobaltLaser(options.serial_port, options.baud_rate, 2)

    daemon = Pyro4.Daemon(port = options.net_port,
            host = socket.gethostbyname(socket.gethostname()))
    Pyro4.Daemon.serveSimple(
            {laser: options.service_name},
            daemon = daemon, ns = False, verbose = True)