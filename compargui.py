# -*- coding: cp1250 -*-
#
# CONTROL FOR VERTICAL COMPARATOR
# AT SLOVAK TECHINCAL UNIVERSITY BRATISLAVA
# 
# Works with Python 3.5
#
# Author: Juraj Bezrucka

import codecs
import time
from datetime import datetime
import serial
import os
from externals import Comparator, Interferometer, Level, Nivel, Thermometer
from tkinter import Tk, Button, Frame, Radiobutton, Entry, Label, Grid, IntVar, StringVar
# from tkinter.messagebox import askokcancel, showwarning, showinfo
import threading
import operator
import sys
# import queue

# admin mode serves for testing purposes - communication with externals
ADMIN_MODE = False
args = sys.argv[1:]

if '-a' in args:
    ADMIN_MODE = True

# set up geometry of the root window
DIMENSIONS = '550x550' if not ADMIN_MODE else '550x750'


# separate log file for each session
if not os.path.isdir('log'):
    os.mkdir('log')
logfile = os.path.join('log', time.strftime('%Y%m%d%H%M%S')+'.log')


# logging function, open file, write log and close
def log(text='', filename=logfile):
    f = codecs.open(filename, 'a', encoding='utf-8')
    record = time.strftime('%Y%m%d%H%M%S') + ' ' + text
    print(record)
    f.write(record + '\n')
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

#pdb.set_trace()

# COLOR SETTINGS SCHEME
# http://wiki.tcl.tk/37701
bgcolor = 'khaki'
bgcolor1 = 'DarkOliveGreen1'  # background color of ADD_USER
bgcolor2 = 'light coral'  # EDIT_USER
bgcolor3 = 'deep sky blue'  # ADD_CREDIT
bgcolor4 = 'orange red'  # SUB_CREDIT
buttoncolor = 'goldenrod1'
buttoncolor1 = 'DarkOliveGreen3'
buttoncolor2 = "DarkOrange"
entrycolor = 'lightgoldenrod'
entrycolor1 = 'lightgoldenrod'
labelbgcolor = bgcolor
labelbgcolor1 = bgcolor1
statuscolor = 'peru'
pluscolor = 'blue'
minuscolor = 'red'
diffcolor = 'green'
inputbox = 'lemon chiffon'
# button for start/stop action
startstopbg = {0: 'dark green', 1: 'red'}
startstopfg = {0: 'white', 1: 'yellow'}

# radiobutton MANUAL/ AUTO - when changed, log & status
# when going to low/hi, start button should change to stop
# move a step - change log and button to stop

# GUI for vertical comparator control
class GUI:
    def __init__(self, master):
        """initialize GUI"""
        self.root = master
        self.on = True
        Tk().withdraw()

        self.starttime = datetime.now()

        # status bar, info for user
        self.statusString = StringVar()
        self.statusText = 'Ready'
        self.statusString.set(self.statusText)
        self.comparatorStatus = 'inactive'
        # self.comparatorStatuses = ['inactive', 'active',
        #                            'steady', 'moving', 'paused', 'finished']
                                   # 2 manual statuses + 4 auto statuses

        self.levelStatus = StringVar()
        self.ifmStatus = StringVar()
        self.nivelStatus = StringVar()
        self.thermoStatus = StringVar()

        self.active = 0  # 0 - inactive state, 1 - active (in motion), 2 - steady (waiting while taking data)
        self.auto = 0

        # COMPARATOR MOTION CONTROL
        self.step = StringVar()  # mm
        self.begin = StringVar()  # mm
        self.end = StringVar()  # mm

        self.autoVal = IntVar()

        self.labelTop = StringVar()
        self.labelTop.set('VERTICAL COMPARATOR')

        # LABELS ON BUTTONS
        self.label10 = StringVar()  # initialize
        self.label11 = StringVar()  # start/stop
        self.label12 = StringVar()  # pause/continue
        self.label21 = StringVar()  # manual
        self.label22 = StringVar()  # auto
        self.label31 = StringVar()  # step
        self.label32 = StringVar()  # start
        self.label33 = StringVar()  # stop
        self.label51 = StringVar()  # manual read interferometer
        self.label52 = StringVar()  # manual read digi level
        self.label53 = StringVar()  # manual read nivel (inclinometer)
        self.label54 = StringVar()  # manual read thermometer

        self.autoVal.set(0)

        # init PLC, interferometer and level
        self.plc = Comparator(comsettings['COMPARATOR_PORT'], int(comsettings['COMPARATOR_BAUD']))
        self.conn = self.plc.conn
        self.paused = None
        self.ifm = Interferometer(comsettings['IFM_PORT'], int(comsettings['IFM_BAUD']))
        self.level = Level(comsettings['LEVEL_PORT'], int(comsettings['LEVEL_BAUD']))
        self.nivel = Nivel(comsettings['NIVEL_PORT'], int(comsettings['NIVEL_BAUD']))
        self.thermo = Thermometer(comsettings['THERMO_PORT'], int(comsettings['THERMO_BAUD']))

        self.observer = ''  # operator

        self.label10.set('Initialize')
        self.label11.set({0: 'START', 1: 'STOP', 2:'STOP'}[self.active])  # start/stop
        self.setStatus({0: 'ready', 1: 'active', 2:'steady'}[self.active])

        self.label12.set('PAUSE')

        self.label21.set('MANUAL')  # manual
        self.label22.set('AUTO')  # auto

        self.label31.set('LOW')  # start height
        self.label32.set('HIGH')  # stop height
        self.label33.set('STEP')  # step

        self.label51.set('READ IFM')  # read interferometer
        self.label52.set('READ LVL')  # read digi level
        self.label53.set('READ NVL')  # read inclinometer
        self.label54.set('READ THM')  # read thermometer

        self.chksumText = StringVar()
        self.responseText = StringVar()

        self.timestring = StringVar()
        self.connstring = StringVar()

        # self.queue = queue.Queue()
        self.timerthread = threading.Thread(target=self.timer, name='Timer')
        self.timerthread.start()

        self.readdata = ''
        self.connthread = threading.Thread(target=self.checkConnection, name='ConnChk')
        self.connthread.start()

        self.statusthread = threading.Thread(target=self.checkStatus, name='StatChk')
        self.statusthread.start()

        self.readexternalsthread = threading.Thread(target=self.readExternals, name='ReadExt')
        self.readexternalsthread.start()

        self.autologthread = threading.Thread(target=self.autolog, name='Autolog')
        self.autologthread.start()

        # starttimer()
        # startautolog()
        # startautoserialcheck()

    # def toggleStartStop(self):
    #    # if start then stop else otherwise
    #    # change button and text color if possible
    #    pass

    def timer(self):
        while self.on:
            dt = datetime.now() - self.starttime
            self.timestring.set('%-10s' % str(dt).split('.')[0])
            time.sleep(0.1)

    def autolog(self, timeout=60):
        while self.on:
            print('Autolog')
            (s, low, hi, step, ifm, lvl, nvl, thm, obs) = tuple(['']*9)
            try:
                s = self.statusText
            except BaseException:
                s = 'N/A'
            try:
                low = self.lowEntry.get().strip()
            except BaseException:
                low = 'N/A'
            try:
                hi = self.hiEntry.get().strip()
            except BaseException:
                hi = 'N/A'
            try:
                step = self.stepEntry.get().strip()
            except BaseException:
                step = 'N/A'
            try:
                ifm = self.ifm.getReading()
            except BaseException:
                ifm = 'N/A'
            try:
                lvl = self.level.getReading()
            except BaseException:
                lvl = 'N/A'
            try:
                nvl = self.nivel.getReading()
            except BaseException:
                nvl = 'N/A'
            try:
                thm = self.thermo.getReading()
            except BaseException:
                thm = 'N/A'
            try:
                obs = self.entryObserver.get().strip()
            except BaseException:
                obs = 'N/A'
            log('AUTOLOG! status: %s, low: %s, hi: %s, step: %s, ifm: %s, lvl: %s, nvl:%s, thm: %s, obs: %s' % (
            s, low, hi, step, ifm, lvl, nvl, thm, obs))
            time.sleep(timeout)

    def checkConnection(self):
        connection = False
        while self.on:
            if self.conn:
                try:
                    d = self.conn.read(1)
                    self.readdata += d
                    connection = True
                except:
                    self.conn.close()
                    try:
                        self.connect()
                    except:
                        connection = False
            else:
                try:
                    self.connect()
                except:
                    connection = False
            self.connstring.set({True: 'isConn', False: 'notConn'}[connection])
            time.sleep(0.5)

    def checkStatus(self):
        if self.conn:
            moving = self.plc.query('is_moving')
            if moving is None:
                self.status = 'unknown'
            elif not self.auto:
                if moving:
                    self.status = 'active'
                else:
                    self.status = 'inactive'
            else:
                if moving:
                    self.status = 'moving'
                else:
                    if self.paused:
                        self.status = 'paused'
                    else:
                        self.status = 'steady'
        else:
            self.status = 'not connected'

    def readExternals(self):
        while self.on:
            # self.getIfm()
            # self.getLevel()
            self.getNivel()
            self.getThermo()
            time.sleep(15)

    def evaluateEntries(self):
        s, b, e = self.stepEntry, self.beginEntry, self.endEntry
        res = [None, None, None]
        for i in range(3):
            try:
                res[i] = float([s, b, e][i])
            except:
                pass  # leave it None
        if b > e and s > 0:  # if step is negative, it can move downwards (from hi to low)
            b, e = e, b  # otherwise it begin and end must be changed if b>e
        elif b < e and s < 0:
            b, e = e, b

        # INPUT IN MM !! cannot recognize 0.5mm from 0.5m  step or 3mm vs 3m end
        # input values converted to mm
        # [s,b,e] = [i*1000. if (i is not None and i<5.) else i for i in [s,b,e]]
        return s, b, e

    def emptyRow(self, nrow):
        Label(self.fr, text="", bg=bgcolor).grid(row=nrow, column=0)

    def setStatus(self, text):
        self.statusText = text
        self.statusString.set(self.statusText)

    def setIfmStatus(self, text):
        self.ifmStatus.set(text)

    def setLevelStatus(self, text):
        self.levelStatus.set(text)

    def setNivelStatus(self, text):
        self.nivelStatus.set(text)

    def setThermoStatus(self, text):
        self.thermoStatus.set(text)

    def getIfm(self):
        # log('Get Ifm reading')
        response = self.ifm.getReading() or "No response"
        self.setIfmStatus(response)
        return response

    def getLevel(self):
        # log('Get Level reading')
        response = self.level.getReading() or "No response"
        self.setLevelStatus(response)
        return response

    def getNivel(self):
        # log('Get Nivel reading')
        response = '-'.join(map(str,self.nivel.getReading())) if any(self.nivel.getReading()) else "No response"
        self.setNivelStatus(response)
        return response

    def getThermo(self):
        # log('Get Thermo reading')
        response = self.thermo.getReading() or "No response"
        self.setThermoStatus(response)
        return response

    #    #set stop button
    #    def setStop(self):
    #        pass
    #
    #    #set start
    #    def setStart(self):
    #        pass

    # toggle start stop
    def startStop(self):
        # ask comparator if moving, then set "not response"
        self.active = not self.active
        # self.setStatus({0: 'ready', 1: 'active'}[self.active])
        self.setStatus(self.comparatorStatus)

        self.label10.set({0: 'START', 1: 'STOP'}[self.active])
        self.buttonStartStop.configure(bg=startstopbg[self.active],
                                       fg=startstopfg[self.active])
        print(self.active)

        self.observer = self.entryObserver.get().strip()

        if not self.active:
            log('CMP stopped %s' % self.observer)
        else:
            log('CMP started %s' % self.observer)

        if self.active:
            pass  # action after comparator is stopped
        else:
            pass  # action after comparator is started

    # CURRENT_POSITION, NEXT_POSITION, TARGET_POSITION, ITERATION
    def writePauseParams(self,**params):
        with open('.pause') as f:
            f.write('\n'.join([k+' '+' '.join(vals) for k, vals in params.items()]))
        return True

    def readPauseParams(self):
        params = {}
        with open('.pause','r') as f:
            for line in f.readlines():
                key = line.split()[0]
                vals = line.split()[1:]
                params[key] = vals
        os.remove('.pause')
        return params

    def pauseSession(self):
        self.paused = True
        self.stop()
        self.writePauseParams()

    def continueSession(self):
        self.paused = False
        params = self.readPauseParams()
        self.moveto(params['NEXT_POS'])
        self.session(float(params['NEXT_POS']), float(params['TARGET_POS']),
                          float(params['STEP']), int(params['NEXT_ITER']))

    def session(self, **params):
        start = float(params.get('START_POS'))
        target = float(params.get('TARGET_POS'))
        step = float(params.get('STEP',5))
        iteration = int(params.get('NEXT_ITER',0))
        self.plc.moveto(start)
        self.paused = False
        op = operator.le if step > 0 else operator.ge
        while op(self.plc.getPosition(), target):
            iteration += 1
            self.getMeasurement()
            next_position = self.plc.getPosition() + step
            if next_position < target:
                self.plc.moveto(next_position)


    def initialize(self):
        if not self.plc.isInit():
            log('Initialize')
        else:
            log('Already initialized, reinitialize.')
        self.plc.initialize()

    def pause(self):
        # comparator status:
        # man/inactive, man/active,
        # auto/steady (measurement), auto/active, auto/paused, auto/finished
        #['inactive', 'active', 'steady', 'moving', 'paused', 'finished']
        if self.comparatorStatus in ('moving', 'steady'):
            self.pauseSession()

        elif self.comparatorStatus == 'paused':
            self.continueSession()

        # active / inactive - button should be disabled


    def stop(self):
        self.plc.command('STOP')

    def getEntries(self):
        return self.stepEntry, self.beginEntry, self.endEntry

    def close(self):
        self.on = False
        # for thread in (self.timerthread, self.connthread, self.statusthread, self.autologthread, self.readexternalsthread):
        #     thread.join()
        # TODO CLOSE ALL CONNECTIONS!!
        if self.active:
            self.startStop()
        self.root.destroy()
        self.root.quit()

    def gotoLow(self):
        low = None
        self.setStatus('Going to LOW')
        try:
            low = float(self.lowEntry.get().strip())
        except:
            pass
        pass  # move carriage to set low
        return low

    def gotoHi(self):
        hi = None
        self.setStatus('Going to HIGH')
        try:
            hi = float(self.hiEntry.get().strip())
        except:
            pass
        pass  # move carriage to set low
        return hi

    def moveStep(self):
        pos = self.plc.getPosition() or 0  # remove 0 when connection established
        step = 0
        try:
            step = float(self.stepEntry.get().strip())
        except BaseException:
            log('Cannot determine step entry.')
        targetpos = pos + step
        if step != 0:
            self.setStatus('Moving to %f' % targetpos)
            self.plc.moveto(targetpos)
        return targetpos

    def resetIfmStatus(self):
        self.ifmStatus.set('')

    def resetLevelStatus(self):
        self.levelStatus.set('')

    def resetNivelStatus(self):
        self.nivelStatus.set('')

    def resetThermoStatus(self):
        self.thermoStatus.set('')

    def submit(self):
        calculate_checksum = True

        port = self.portEntry.get().strip()
        message = self.messageEntry.get()
        chksumtyp = self.portChecksumType.get()

        from externals import RS232
        from pycrc import pycrc, crc_algorithms, Crc

        rs = RS232()
        r = rs.connect(port, baud=38400)
        if r:
            print ('Successfully connected to %s' % r.name)


        checksum = ''
        if calculate_checksum:
            from pycrc.crc_algorithm import Crc

            # params = filter(lambda x: x['name']==chksumtyp, cmodels)[0]
            params = {'width': 16, 'poly':0x1021, 'reflect_in':True,
                      'xor_in':0x0000, 'reflect_out':True, 'xor_out':0x0000}

            crc = Crc(**params)
            print("{0:#x}".format(crc.bit_by_bit(message)))
            # crc = Crc(width=16, poly=0x8005,
            #             reflect_in = True, xor_in = 0x0000,
            #             reflect_out = True, xor_out = 0x0000)
            # >> > print("{0:#x}".format(crc.bit_by_bit("123456789")))
            # >> > print("{0:#x}".format(crc.bit_by_bit_fast("123456789")))
            # >> > print("{0:#x}".format(crc.table_driven("123456789")))



        rs.send()


        # self.chksumLabel = (self.fr, textvariable = self.chksumText, anchor = 'w',
        #                                                                       bg = bgcolor, fg = statuscolor, font = (
        # "Calibri", 9))
        # self.chksumLabel.grid(row=23, column=2)
        #
        # buttonSubmit = Button(self.fr, text="SUBMIT", width=15, justify='center',
        #                       bg="black", fg="yellow", command=self.submit,
        #                       font=("Calibri", 14, "bold"))
        # buttonSubmit.grid(row=23, column=0)
        #
        # self.responseLabel = (self.fr, textvariable = self.responseText, anchor = 'w',
        #                                                                           bg = bgcolor, fg = statuscolor, font = (
        # "Calibri", 9))
        # self.responseLabel.grid(row=23, column=1)
        #
        # self.emptyRow(24)



    def mainDialog(self):

        self.basicframe = Frame(self.root)
        self.basicframe.grid()
        self.basicframe.configure(bg=bgcolor)

        self.fr = Frame(self.basicframe)
        self.fr.grid(row=0, column=0, sticky='new')  # , sticky='W')
        self.fr.configure(bg=bgcolor)

        # Grid.rowconfigure(root, 0, weight=1)
        Grid.columnconfigure(root, 0, weight=1)

        self.emptyRow(0)

        Label(self.fr, textvariable=self.labelTop,
              justify='center', bg=bgcolor, font=("Calibri", 24)
              ).grid(row=1, column=0, columnspan=3, sticky='we')

        self.emptyRow(2)

        Label(self.fr, text='STATUS:', justify='left', anchor='w',
              bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
              ).grid(row=3, column=0, sticky='we', padx=(5, 0))

        self.statusLine = Label(self.fr, textvariable=self.statusString,
                                justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                                font=("Calibri", 14, "bold")
                                ).grid(row=3, column=1, columnspan=2, sticky='we')

        self.emptyRow(4)

        # AUTO / MANUAL  self.my_var.set(1)
        self.buttonManual = Radiobutton(self.fr, text="MANUAL",
                                     variable=self.auto,
                                     value=0,
                                     width=15,
                                     justify='center',
                                     # bg=buttoncolor2,
                                     bg="moccasin",
                                     indicatoron=0)  # self.exit_root)
        self.buttonManual.grid(row=5, column=0, sticky='ew', padx=(0, 10))
        # self.buttonManual.configure(state='selected')

        self.buttonAuto = Radiobutton(self.fr, text="AUTO",
                                   variable=self.auto,
                                   value=1,
                                   width=15, justify='center',
                                   # bg=buttoncolor2,
                                   bg="moccasin",
                                   indicatoron=0)  # self.exit_root)
        self.buttonAuto.grid(row=5, column=2, sticky='ew', padx=(10, 0))

        self.emptyRow(6)

        #should be disabled if initialized already
        self.buttonInitialize = Button(self.fr, text='Initialize',
                                   justify='center', bg=buttoncolor, command=self.initialize)
        self.buttonInitialize.grid(row=7, column=0, sticky='nsew')

        self.buttonStartStop = Button(self.fr, textvariable=self.label11,
                                   command=self.startStop,
                                   bg=startstopbg[self.active],
                                   fg=startstopfg[self.active],
                                   font=("Calibri", 16, "bold"),
                                   width=10)
        self.buttonStartStop.grid(row=7, column=1, sticky='nsew')

        self.buttonPause = Button(self.fr, textvariable=self.label12,
                                   justify='center', bg=buttoncolor,
                                   state={0: 'disabled', 1: 'enabled'}[self.auto],
                                   command=self.pause)
        self.buttonPause.grid(row=7, column=2, sticky='nsew')

        self.emptyRow(8)

        # put Labels here

        Label(self.fr, textvariable=self.label31, justify='center',
              bg=bgcolor, fg=statuscolor, font=("Calibri", 10)
              ).grid(row=8, column=0, sticky='we')
        Label(self.fr, textvariable=self.label32, justify='center',
              bg=bgcolor, fg=statuscolor, font=("Calibri", 10)
              ).grid(row=8, column=1, sticky='we')
        Label(self.fr, textvariable=self.label33, justify='center',
              bg=bgcolor, fg=statuscolor, font=("Calibri", 10)
              ).grid(row=8, column=2, sticky='we')

        # input boxes: step start stop (mm)
        self.lowEntry = Entry(self.fr, width=20, bd=3, justify='right',
                              bg=inputbox, fg=statuscolor)
        self.lowEntry.grid(row=9, column=0, sticky='we')  # , columnspan=2)
        # SET DEFAULT LOW
        # self.lowEntry.delete(0,END)
        # self.lowEntry.insert(0, MINPOS)

        self.hiEntry = Entry(self.fr, width=20, bd=3, justify='right',
                             bg=inputbox, fg=statuscolor)
        self.hiEntry.grid(row=9, column=1, sticky='we')  # , columnspan=2)
        # SET DEFAULT HIGH
        # self.hiEntry.delete(0,END)
        # self.hiEntry.insert(0, MAXPOS)

        self.stepEntry = Entry(self.fr, width=20, bd=3, justify='right',
                               bg=inputbox, fg=statuscolor)
        self.stepEntry.grid(row=9, column=2, sticky='we')  # , columnspan=2)

        # put buttons for  GOTO and MOVE
        self.butGotoLow = Button(self.fr, text="Go To Low",
                                 justify='center', bg=buttoncolor, command=self.gotoLow)
        self.butGotoLow.grid(row=10, column=0, sticky='we')

        self.butGotoHi = Button(self.fr, text="Go To High",
                                justify='center', bg=buttoncolor, command=self.gotoHi)
        self.butGotoHi.grid(row=10, column=1, sticky='we')

        self.butMoveStep = Button(self.fr, text="Move a Step",
                                  justify='center', bg=buttoncolor, command=self.moveStep)
        self.butMoveStep.grid(row=10, column=2, sticky='we')

        self.emptyRow(11)

        Label(self.fr, text='EXTERNAL SENSORS', justify='left',
              anchor='w', bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
              ).grid(row=12, column=0, columnspan=3, sticky='we', padx=(5, 0))

        # function buttons


        # RIadok 13-16: Externals
        # Interferometer
        buttonIfm = Button(self.fr, text="Read IFM", width=15, justify='center',
                        bg=buttoncolor, command=self.getIfm)  # self.exit_root)
        buttonIfm.grid(row=13, column=0, sticky='we')

        self.labelIfmStatus = Label(self.fr, textvariable=self.ifmStatus,
                                  justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                                  font=("Calibri", 12))
        self.labelIfmStatus.grid(row=13, column=1, columnspan=2,
                               sticky='we', padx=(15, 0))
        self.labelIfmStatus.bind('<Button-1>', self.resetIfmStatus)

        # Digital level (Leica /Trimble)
        buttonLevel = Button(self.fr, text="Read Level", width=15, justify='center',
                        bg=buttoncolor, command=self.getLevel)  # self.exit_root)
        buttonLevel.grid(row=14, column=0, sticky='we')

        self.labelLevelStatus = Label(self.fr, textvariable=self.levelStatus,
                                  justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                                  font=("Calibri", 12))
        self.labelLevelStatus.grid(row=14, column=1, columnspan=2,
                               sticky='we', padx=(15, 0))
        self.labelLevelStatus.bind('<Button-1>', self.resetLevelStatus)

        # Nivel - inclinometer
        buttonNivel = Button(self.fr, text="Read Nivel", width=15, justify='center',
                        bg=buttoncolor, command=self.getNivel)  # self.exit_root)
        buttonNivel.grid(row=15, column=0, sticky='we')

        self.labelNivelStatus = Label(self.fr, textvariable=self.nivelStatus,
                                  justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                                  font=("Calibri", 12))
        self.labelNivelStatus.grid(row=15, column=1, columnspan=2,
                               sticky='we', padx=(15, 0))
        self.labelNivelStatus.bind('<Button-1>', self.resetNivelStatus)

        # Thermometer line
        buttonThermo = Button(self.fr, text="Read Thermo", width=15, justify='center',
                        bg=buttoncolor, command=self.getThermo)  # self.exit_root)
        buttonThermo.grid(row=16, column=0, sticky='we')

        self.labelThermoStatus = Label(self.fr, textvariable=self.thermoStatus,
                                  justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                                  font=("Calibri", 12))
        self.labelThermoStatus.grid(row=16, column=1, columnspan=2,
                               sticky='we', padx=(15, 0))
        self.labelThermoStatus.bind('<Button-1>', self.resetThermoStatus)

        self.emptyRow(17)

        Label(self.fr, text='OBSERVER:', anchor='w', justify='left',
              bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
              ).grid(row=19, column=0, sticky='we', padx=(5, 0))
        self.entryObserver = Entry(self.fr, textvariable=self.observer,
                                   bg=inputbox, fg=statuscolor, font=("Calibri", 12),
                                   justify='left')
        self.entryObserver.grid(row=19, column=1, columnspan=2, sticky='we')

        # row 18> empty (or test connection)
        self.emptyRow(20)

        if ADMIN_MODE:
            # port, message, checksum_type?, resulting checksum?, submit, response
            self.portEntry = Entry(self.fr, width=20, bd=3, justify='left',
                                   bg=inputbox, fg=statuscolor)
            self.portEntry.grid(row=21, column=0, sticky='we')
            Label(self.fr, text='PORT', anchor='w', justify='left',
                  bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
                  ).grid(row=22, column=0, sticky='we', padx=(5, 0))

            self.messageEntry = Entry(self.fr, width=20, bd=3, justify='left',
                                   bg=inputbox, fg=statuscolor)
            self.messageEntry.grid(row=21, column=1, sticky='we')
            Label(self.fr, text='MESSAGE', anchor='w', justify='left',
                  bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
                  ).grid(row=22, column=1, sticky='we', padx=(5, 0))

            self.portChecksumType = Entry(self.fr, width=20, bd=3, justify='left',
                                   bg=inputbox, fg=statuscolor)
            self.portChecksumType.grid(row=21, column=2, sticky = 'we')
            Label(self.fr, text='CHKSUM TYPE', anchor='w', justify='left',
                        bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
                        ).grid(row=22, column=2, sticky='we', padx=(5, 0))


            self.chksumLabel = Label(self.fr, textvariable=self.chksumText, anchor='w',
                                bg=bgcolor, fg=statuscolor, font=("Calibri", 9))
            self.chksumLabel.grid(row=23, column=2)

            buttonSubmit = Button(self.fr, text="SUBMIT", width=15, justify='center',
                             bg="black", fg="yellow", command=self.submit,
                             font=("Calibri", 14, "bold"))
            buttonSubmit.grid(row=23, column=0)


            self.responseLabel = Label(self.fr, textvariable=self.responseText, anchor='w',
                                bg=bgcolor, fg=statuscolor, font=("Calibri", 9))
            self.responseLabel.grid(row=23, column=1)

            self.emptyRow(24)


        lastLine = 21 if not ADMIN_MODE else 25

        self.timeLabel = Label(self.fr, textvariable=self.timestring,
                               anchor='w', bg=bgcolor, fg=statuscolor,
                               font=("Calibri", 9))
        self.timeLabel.grid(row=lastLine, column=0)

        self.connLabel = Label(self.fr, textvariable=self.connstring,
                               anchor='w', bg=bgcolor, fg=statuscolor,
                               font=("Calibri", 9))
        self.connLabel.grid(row=lastLine, column=1)

        butexit = Button(self.fr, text="EXIT", width=15, justify='center',
                         bg="black", fg="yellow", command=self.close,
                         font=("Calibri", 14, "bold"))
        butexit.grid(row=lastLine, column=2)

if __name__ == '__main__':
    root = Tk()
    root.title('VERTICAL COMPARATOR')
    root.geometry(DIMENSIONS)
    root.configure(bg=bgcolor)
    g = GUI(root)
    g.mainDialog()
    root.mainloop()
