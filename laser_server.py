import serial
import socket
import threading
import time
import Pyro4

CONFIG_NAME = 'laserServer'
Pyro4.config.SERIALIZER = 'pickle'
Pyro4.config.SERIALIZERS_ACCEPTED.add('pickle')

class Server(object):
    def __init__(self):
        self.run_flag = True
        self.devices = {}
        self.daemon_thread = None


    def run(self):
        import readconfig
        config = readconfig.config
        try:
            supported_lasers = config.get(CONFIG_NAME, 'supported').split(' ')
        except:
            raise Exception('No supported laser modules defined in config.')

        loaded_modules = {}
        print "Loading laser modules:"
        for module in supported_lasers:
            try:
                m = __import__(module)
                print "\t%s loaded" % module
            except:
                raise Exception("Could not load module %s." % module)
            loaded_modules.update({module: m})

        # Map lasers defined in config to their driver module.
        lasers = {section: module_name
                    for section in config.sections() 
                    for module_name in supported_lasers
                    if section.startswith(module_name)}

        # Create laser instances and map to Pyro names.
        for section, module_name in lasers.iteritems():
            com = config.get(section, 'comPort')
            baud = config.get(section, 'baud')
            try:
                timeout = config.get(section, 'timeout')
            except:
                timeout = 1.
            # Create an instance of the laser m.CLASS_NAME in module m.
            m = loaded_modules[module_name]
            laser_instance = getattr(m, m.CLASS_NAME)(com, int(baud), int(timeout))
            
            # Add this to the dict mapping lasers to Pyro names.
            self.devices.update({laser_instance: section})

        port = config.get(CONFIG_NAME, 'port')
        host = config.get(CONFIG_NAME, 'ipAddress')

        self.daemon = Pyro4.Daemon(port=int(port), host=host)
        # Start the daemon in a new thread.
        self.daemon_thread = threading.Thread(
            target=Pyro4.Daemon.serveSimple,
            args = (self.devices, ), # our mapping of class instances to names
            kwargs = {'daemon': self.daemon, 'ns': False}
            )
        self.daemon_thread.start()

        # Wait until run_flag is set to False.
        while self.run_flag:
            time.sleep(1)

        # Do any cleanup.
        self.daemon.shutdown()
        self.daemon_thread.join()

        # For each laser ...
        for (device, name) in self.devices.iteritems():
            # ... make sure emission is switched off
            device.disable()
            # ... relase the COM port.
            device.connection.close()


    def stop(self):
        self.run_flag = False

if __name__ == "__main__":
    ## Only run when called as a script --- do not run on include.
    #  This way, we can use an interactive shell to test out the class.
    server = Server()
    server_thread = threading.Thread(target = server.run)
    server_thread.start()

    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        server.stop()
        server_thread.join()