# Command line tool for the TI INA219 current/power measurement chip
# Copyright (c) 2015 Colin Dietrich
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from ina219 import INA219

import os
import sys
from getopt import getopt, GetoptError
from time import time, sleep, strftime
from atexit import register


# get relevant commands
args_in = sys.argv[1:]

# terminal use defaults
inf = False
dt = 1.0
n = 4
min_dt = 0.05
print_dt = ""
pn = ""
file_path = ""
f = None
fp = None
f_save = False
instanced = False
extras = ""


def usage():
    """Usage command"""
    print("use command argument -h or --help for details")


def print_help():
    """Print to screen help commands"""
    print("Tool for collecting electrical current data from the\n"
          " TI INA219 ic2 chip\n"
          "\n"
          "Usage:\n"
          " terminal.py -n 20 -i 0.5 -u 'kW' -s 'test_file.txt'\n"
          " terminal.py -n inf -s 'test_file.csv'\n"
          "\n"
          "Options:\n"
          " -h --help          This help screen.\n"
          " -n --number <x>    Number of samples to take,\n"
          "                        int or 'inf' [default: 4].\n"
          " -i --interval <t>  Time in seconds between samples [default: 1.0]\n"
          " -u --units <y>     Units to report [default: 'J']\n"
          "                        available: 'J', 'Wh', 'kW'\n"
          " -s --save <name>   Save data to specified directory.\n"
          " -a --address <b>   I2C/IIC address of INA219 on bus.\n"
          "                        [default: 0x40]\n")


def save_start(d):
    """Check the location for file saving is ok, in lew of more complete solutions
    i.e.
    http://stackoverflow.com/questions/9532499/check-whether-a-path-is-valid-in-python-without-creating-a-file-at-the-paths-ta/34102855#34102855
    """

    global f
    global fp
    global f_save

    fp = strftime('%Y_%m_%d_%H_%M_%S')
    fp = d + "/" + fp + "_INA219.csv"
    fp = os.path.normpath(fp)

    f_save = True
    f = open(fp, 'w')


def save_end():
    """Close open files"""
    try:
        f.close()
    except AttributeError:
        pass

# register file close
register(save_end)

# handle command arguments
try:
    opts, args = getopt(args_in,
                        "hn:i:u:s:a:",
                        ["help", "number", "interval",
                         "units", "save", "address"])
except GetoptError:
    print("unknown argument passed")
    usage()
    sys.exit()

for opt, arg in opts:

    if opt in ("-h", "--help"):
        print_help()
        sys.exit()

    elif opt in ("-n", "--number"):
        if arg == "inf":
            inf = True
        else:
            try:
                n = int(arg)
            except ValueError:
                usage()
                sys.exit()
            if n < 1:
                inf = True

    elif opt in ("-i", "--interval"):
        try:
            arg = float(arg)
        except ValueError:
            usage()
            sys.exit()
        if arg < min_dt:
            print("Sample interval %s seconds too low" % arg)
            usage()
            sys.exit()
        else:
            dt = arg

    elif opt in ("-a", "--address"):
        # non-default address used, instance ina219 class
        # tested only by passing default "0x40" as arg
        _address = int(arg, 16)
        i = INA219(address=_address)
        instanced = True
        extras += "Using I2C address %s\n" % hex(_address)

    elif opt in ("-u", "--units"):
        if arg in i.available_units:
            i.set_energy_units(arg)
        else:
            print("Unknown unit passed")
            usage()
            sys.exit()

    elif opt in ("-s", "--save"):
        save_start(arg)
        if not f_save:
            usage()
            sys.exit()
        # print("Saving to = %s" % _fp)

# no address given, instance ina219 at default
if not instanced:
    i = INA219()
    extras += "Using default I2C address 0x40\n"

# print data header
if inf:
    pn = "infinity"
    pdt = ""
else:
    pn = n
    pdt = "Energy use over " + str(dt*n) + " seconds\n"

if fp is not None:
    extras += "Saving to: %s\n" % fp

header0 = ("INA219 Voltage, Power & Energy Measurement\n"
           "%sNumber of samples = %s\n"
           "Sample interval = %s\n"
           "Energy units = %s\n"
           "%s"
           "------------------------------------------"
           % (extras, pn, dt, i.units, pdt))
header1 = ("unix time (s),elapsed time (s),"
           "bus voltage (V),shunt current (A),"
           "power (W),sample_energy (%s),total_energy (%s)"
           % (i.units, i.units))
print(header0)
print(header1)

# take initial measurements
i.get_energy_simple()
t0 = time()
_n = 1

# begin regular sampling
while True:
    try:
        if not inf:
            if _n > n:
                break
        _n += 1
        sleep(dt)
        i.get_energy_simple()
        t = time()
        t_elapsed = t - t0
        s = ("%s,%0.3f,%0.5f,%0.5f,%0.5f,%0.5f,%0.5f"
             % (t, t_elapsed, i.bus_voltage, i.i, i.p, i.e, i.e_total))
        if f_save:
            if _n == 2:
                f.write(header1 + "\n")
            f.write(s + "\n")
        print(s)
    except KeyboardInterrupt:
        break
