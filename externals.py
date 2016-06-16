# -*- coding: cp1250 -*-
#
# CONTROL FOR VERTICAL COMPARATOR AND EXTERNAL SENSORS
# AT SLOVAK TECHINCAL UNIVERSITY BRATISLAVA
#
# Works with Python 3.5
#
# Author: Juraj Bezrucka, juraj.bezrucka@nuviel.sk
#

import codecs
import time
from datetime import datetime
import serial
import pdb
import os.path
import threading
import re

# import queue


# separate log file for each session
logfile = os.path.join('log', time.strftime('%Y%m%d%H%M%S')+'.log')

# logging function, open file, write log and close
def log(text='', filename=logfile):
    f = codecs.open(filename, 'a', encoding='utf-8')
    f.write(time.strftime('%Y%m%d%H%M%S') + ' ' + text + '\n')
    f.close()


# this is for test purposes only, allows start/stop commands for carriage
# if set to False, it is a TESTMODE and it runs and stops carriage
# without connecting via COM port
# if set to True, it is "for real" - sending commands and queries via COM
REALMODE = False


# this converts string zeros and ones to actual bytes
# you can divide 8-bit chunks with space: '10001100 01110001'
def strbit2byte(s):
    bs = ''.join(['0' if i == '0' else '1' for i in s.replace(' ', '')])  # kontrola 1 a 0
    bs = bs.zfill((len(bs) // 8 + 1) * 8)  # doplnenie prazdnych miest
    return u''.join(map(lambda x: str(chr(int(x, 2))),
                        [bs[i * 8:i * 8 + 8] for i in range(len(bs) // 8)]))


comsettings = {}
with open('com.cfg', 'r') as f:
    for line in filter(lambda x: x.strip() and x.strip()[0] != '#', f.read().split('\n')):
        if len(line.split())==1:
            comsettings[line.split()[0]] = None
        elif len(line.split())==2:
            comsettings[line.split()[0]] = line.split()[1]
        else:
            comsettings[line.split()[0]] = line.split()[1:]
# MAXPOS, MINPOS, PLCCOM, PLCBAUD, IFMCOM, IFMBAUD, LVLCOM, LVLBAUD


commands = {}
with open('commands.cfg', 'r') as f:
    for line in filter(lambda x: x.strip() and x.strip()[0] != '#', f.read().split('\n')):
        try:
            commands[line.split()[0]] = strbit2byte(''.join(line.split()[1:]))
        except TypeError as te:
            print('Cannot convert %s' % ''.join(line.split()[1:]))
# ACTIVE, INACTIVE, STOP, START, STEP, MOVETO, FROM, TO, GETPOS, GETSTAT


# radiobutton MANUAL/ AUTO - when changed, log & status
# when going to low/hi, start button should change to stop
# move a step - change log and button to stop


## PYSERIAL SNIPPET

"""port = "COM1"
baud = 38400

ser = serial.Serial(port,baud,timeout=0.5)
print(ser.name + ' is open.')

sys.exit()

while True:
    input = raw_input("Enter HEX cmd or 'exit'>> ")
    if input == 'exit':
        ser.close()
        print(port+' is closed.')
        exit()

    elif len(input) == 8:
    # user enters new register value, convert it into hex
        newRegisterValue = bits_to_hex(input)
        ser.write(newRegisterValue.decode('hex')+'\r\n')
        print('Saving...'+newRegisterValue)
        print('Receiving...')
        out = ser.read(1)
        for byte in out:
            print(byte) # present ascii

    else:
        cmd = input
        print('Sending...'+cmd)
        ser.write(cmd.decode('hex')+'\r\n')
        print('Receiving...')
        out = ser.read(1)
        for byte in out:
            print(byte) # present ascii
"""


class RS232(object):
    """
    Generic serial class, defines basic methods to connect, read, write
    Simple external sensors can simply inherit methods and their dictionary
    only contains query 'READING'
    More complex require more commands and queries
    .send() and .receive() - sophisticated read and write to serial conn
    .command() send command and return True or None if fails
    .query() send query, read response and return response or None if fails
    .translate() uses self.dictionary to translate command/query
    """
    _name = 'RS232'

    def __init__(self, comport=None, baud=None, dictionary=None):
        self.comport, self.baud = comport, baud
        self.timeout = 3
        self.buffer = 3
        self.conn = None
        self.dictionary = dictionary if dictionary is not None else {}
        if comport and baud:
            pass
        else:
            self.comport, self.baud = comsettings['PLCPORT'], int(comsettings['PLCBAUD'])

    def receive(self, timeout=None, buffer=None):
        if timeout is None:
            timeout = self.timeout
        if buffer is None:
            buffer = self.buffer
        received = ''
        now = time.time()
        then = now + timeout
        while time.time() < then or (len(received) == buffer):
            received += self.conn.read() if self.conn else ''
        return received

    def connect(self, comport = None, baud = None):
        if comport is None:
            comport = self.comport
        if baud is None:
            baud = self.baud
        try:
            self.conn = serial.Serial(comport, baud)
            return self.conn
        except serial.SerialException:
            resp = 'Cannot connect to %s at %s' % (str(comport), str(baud))
            print(resp)
            log(resp)
            return None

    def disconnect(self):
        try:
            self.conn.close()
        except AttributeError:
            print('Connection probably does not exist')
        except serial.SerialException:
            print('Cannot close connection.')

    def send(self, data, timeout=None):
        if timeout is None:
            timeout = self.timeout
        if self.conn:
            self.conn.write(data, timeout)
            return True
        else:
            log('Cannot send data to serial')

    def translate(self, key, *params):
        return ' '.join([self.dictionary.get(key,'')] + map(str, params))

    def query(self, q, *params):
        if self.conn:
            try:
                self.send(self.translate(q, params))
                log('{}: Query sent'.format(q))
                return self.receive()
            except:
                log('%s: Query unresolved or not sent' % q)
                return None
        else:
            log('Connection not established, query unsuccessful: %s' % q)
            return None

    def command(self, q, *params):
        if self.conn:
            try:
                self.send(self.translate(q, params))
                return True
            except:
                log('%s: Command unresolved or not sent' % q)
                return None
        else:
            log('Connection not established, command unsuccessful: %s' % q)
            return None

    def isOn(self):
        return True if self.conn else False

    def getReading(self, *params):
        return self.query('READING', params) or ''


# class for reading interferometer
class Interferometer(RS232):
    _name = 'Interferometer'

    def __init__(self, comport=None, baud=None, dictionary=None):
        self.comport, self.baud = comport, baud
        self.timeout = 3
        self.buffer = 3
        self.conn = None
        # add IFM translation for reading query
        dictionary = dictionary or {'READING':'IFM_READING'}
        if comport and baud:
            self.baud = int(baud)
        else:
            self.comport, self.baud = comsettings['IFM_PORT'], int(comsettings['IFM_BAUD'])


# class for reading level
# may have different dictionaries depending on the type,
# in case it cannot be detected automatically, a selection should be made prior the measurement
# in order to set up a correct dictionary for the digital level
class Level(RS232):
    _name= 'Level'

    def __init__(self, comport=None, baud=None, dictionary=None):
        self.comport, self.baud = comport, baud
        self.timeout = 3
        self.buffer = 3
        self.conn = None
        self.dictionary = dictionary or {'READING':'LEVEL_READING', 'GET_NAME':'LEVEL_GETNAME'}
        if comport and baud:
            self.baud = int(baud)
        else:
            self.comport, self.baud = comsettings['LEVEL_PORT'], int(comsettings['LEVEL_BAUD'])

    def get_name(self):
        return self.query('GET_NAME')


class Nivel(RS232):
    _name= 'Nivel'

    def __init__(self, comport=None, baud=None, dictionary=None):
        self.comport, self.baud = comport, baud
        self.timeout = 3
        self.buffer = 3
        self.conn = None
        self.dictionary = dictionary or {'READING':'NIVEL_READING'}
        if comport and baud:
            self.baud = int(baud)
        else:
            self.comport, self.baud = comsettings['NIVEL_PORT'], int(comsettings['NIVEL_BAUD'])

    def convertResponse(self, response):
        crd = ''
        val = None
        if re.match('222C1N1 .\:.*\d+.\d{3}3\\x02\\xd1'):
            r = response.lstrip('222C1N1 ').rstrip('3\x02\xd1')
            crd = r[0]
            val = float(r.split(':')[1])
        return val, crd

    def getReading(self,*params):
        queryx = '<22><2>N1C1 G X<3><13><10>'
        queryy = '<22><2>N1C1 G Y<3><13><10>'
        queryz = '<22><2>N1C1 G Z<3><13><10>'

        self.send(queryx, timeout=1)
        responsex = self.receive(buffer=20)
        self.send(queryy, timeout=1)
        responsey = self.receive(buffer=20)
        self.send(queryz, timeout=1)
        responsez = self.receive(buffer=20)

        return map(lambda x: self.convertResponse(x)[0], [responsex, responsey, responsez])

    def reset(self):
        self.send('<22><2>N1C1 RES SYS<3><13><10>', timeout=1)


class Thermometer(RS232):
    _name= 'Thermometer'

    def __init__(self, comport=None, baud=None, dictionary=None):
        self.comport, self.baud = comport, baud
        self.timeout = 3
        self.buffer = 3
        self.conn = None
        self.dictionary = dictionary or {'READING':'THERMO_READING'}
        if comport and baud:
            self.baud = int(baud)
        else:
            self.comport, self.baud = comsettings['THERMO_PORT'], int(comsettings['THERMO_BAUD'])

# class for communication with PLC
class Comparator(RS232):
    _name = 'Comparator'

    # should connect to PLC during init
    def __init__(self, comport=None, baud=None, dictionary=None):
        self.position = None
        self.auto = False
        self.conn = False
        self.comport = comport
        self.baud = baud
        self.position = None
        self.dictionary = dictionary or {}
        self.statustext = ''
        self.status = ''
        if comport and baud:
            self.connect(self.comport, int(self.baud))
        else:
            try:
                self.comport = comsettings.get('COM1', 'PLCPORT')
                self.baud = int(comsettings.get('9600', 'PLCBAUD'))
                self.conn = self.connect(self.comport, self.baud)
            except serial.SerialTimeoutException as ste:
                print('%s > Cannot connect to %s @ %d, timeout.' % (ste, self.comport, self.baud))

    def isInit(self):
        return self.query('is_init')

    def getPosition(self):
        return self.query('get_position')

    def close(self):
        self.disconnect()

    def setManual(self):
        self.auto = False

    def setAuto(self):
        self.auto = True

    def initialize(self):
        return self.command('init')

    # CONTROLS FOR PLC
    def moveto(self, position):
        log('moveto %s' % position)
        # here, position should be translated to units understandable by comparator
        converted_position = position
        self.command('moveto', position)
        while self.conn and not self.checkMovedTo(position):
            time.sleep(0.05)
        return self.getPosition()

    def move(self, step):
        self.position = self.getposition()
        new_position = self.position + step
        if float(comsettings['MINPOS']) < new_position < float(comsettings['MAXPOS']):
            # data = '000'  # THIS SHOULD BE CHANGED WHEN DATA EXCHANGE FORMAT IS DETERMINED
            self.moveto(new_position)
            return True
        else:
            self.auto = False
            self.stop()
            # self.stopSession()
            return False

    def checkMovedTo(self, position):
        return self.getPosition() == position

    def isSteady(self):
        return self.query('is_steady')

    def isMoving(self):
        return self.query('is_moving')

    # def start(self, step):
    #     if self.isSteady():
    #         if self.auto:
    #             # automatic
    #             self.startSession(**params)
    #         else:
    #             self.move(step)

    # if session, pause and ask
    def stop(self):
        # send stop command immediately, then add some logic
        self.command('stop')
        # if self.session:
        #     self.write_params_in_use() # to allow continue processing when pressed CONTINUE
        return self.getPosition()

