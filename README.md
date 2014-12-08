# cockpit-lasers
This package defines classes used to remotely control lasers in cockpit. It can be started from the command line, or controlled by CockpitWindowsService.

The package relies on having readconfig.py in the same folder: 
    git@github.com:mickp/readconfig.git

Lasers are each defined in their own section, of the form [module]uniqueID, e.g. _deepstar488_ .

The lasers are served via Pyro, with server parameters (supported laser modules, bound interface / address, port number) defined in the _laserServer_ section of the config file. 

The server interface and port are set in the _laserServer_ section of the config file.

The package also provides an abstract _laser.Laser_ base class from which other lasers may be derived.