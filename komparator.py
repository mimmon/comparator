# -*- coding: cp1250 -*-
#
# CONTROL FOR VERTICAL COMPARATOR
# AT SLOVAK TECHINCAL UNIVERSITY BRATISLAVA
# 
# Works with Python 3.5
#
# Author: Juraj Bezrucka

import os, sys, codecs
import time
from datetime import datetime
import serial
from tkinter import Tk, Button, Frame, Radiobutton
from tkinter import Entry, Label, Grid
from tkinter import IntVar, StringVar
from tkinter.messagebox import askokcancel, showwarning, showinfo
import threading
import queue


# this is for test purposes only, allows start/stop commands for carriage
# if set to False, it is a TESTMODE and it runs and stops carriage
# without connecting via COM port
# if set to True, it is "for real" - sending commands and queries via COM 
REALMODE = False

# from tkFileDialog import 

# maximum and minimum position of the carriage
MAXPOS = 3000
MINPOS = -3000

# port for PLC
PLCCOM = "COM1"
PLCBAUD = 9600

# port for interferometer
IFMCOM = "COM2"
IFMBAUD = 9600

# port for level
LVLCOM = "COM3"
LVLBAUD = 9600

# this converts string zeros and ones to actual bytes
# you can divide 8-bit chunks with space: '10001100 01110001'
def strbit2byte(s):
	bs = ''.join(['0' if i=='0' else '1' for i in s.replace(' ','')]) # kontrola 1 a 0
	bs = bs.zfill((len(bs)//8 +1)*8) # doplnenie prazdnych miest
	return u''.join(map(lambda x: str(chr(int(x,2))),
                        [bs[i*8:i*8+8] for i in range(len(bs)//8)]))


ACTIVE  = strbit2byte('11111111')
INACTIVE= strbit2byte('10000000')
STATUS  = strbit2byte('00001000 00000000 00000000')
STOP    = strbit2byte('00010000 00000000 00000000')
START   = strbit2byte('00000001')
STEP    = strbit2byte('00000011')
MOVETO  = strbit2byte('00000111')
FROM    = strbit2byte('00010100')
TO      = strbit2byte('00010010')
GETPOS  = strbit2byte('10000010')
GETSTAT = strbit2byte('10000100')

# COLOR SETTINGS SCHEME
# http://wiki.tcl.tk/37701
bgcolor = 'khaki'
bgcolor1 = 'DarkOliveGreen1' # background color of ADD_USER
bgcolor2 =  'light coral'  # EDIT_USER
bgcolor3 =  'deep sky blue'  # ADD_CREDIT
bgcolor4 =  'orange red'  # SUB_CREDIT
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


# separate log file for each session
logfile = time.strftime('%Y%m%d%H%M%S')+'.log'

# logging function, open file, write log and close
def log(text='',filename=logfile):
    f = codecs.open(filename,'a',encoding='utf-8')
    f.write(time.strftime('%Y%m%d%H%M%S')+' '+text+'\n')
    f.close()

# class for reading interferometer
class IFM():  
    def __init__(self,comport=IFMCOM,baud=IFMBAUD):
        if comport and baud:
            pass

    def read(self):
        response = None
        pass # commands to get response (measurmenet)
        return response

		
# class for reading level
class LVL():  
    def __init__(self, comport=LVLCOM, baud=LVLBAUD):
        if comport and baud:
            pass

    def read(self):
        response = None
        pass # commands to get response (measurmenet)
        return response
    
# class for communication with PLC
class PLC():

    # should connect to PLC during init
    def __init__(self,comport=None,baud=None):
        self.position = None
        self.auto = False
        self.conn = False
        self.comport = comport
        self.baud = baud
        if comport and baud:
            self.connect(self.comport, self.baud)

# these commands/queries must be changed according to the PLC settings
    def translate(self,q,number=None):
        emptybyte = '00000000'
        plusbytes = emptybyte*2
        
        d = {'status': STATUS,
             'stop':   STOP,
             'start':  START,
             'step':   STEP,
             'moveto': MOVETO,
             'from':   FROM,
             'to':     TO,
             'getpos': GETPOS,
             'getstat':GETSTAT
            }

        if q in ['start','step','moveto','from','to']:
            if number is not None:
                try:
                    plusbytes = bin(number).lstrip('0b').zfill(16)[-16:]
                except:
                    print('Cannot convert %s' % str(number))
                    plusbytes = emptybytes*2
                d[q] += plusbytes

        return d.get(q,None)         
        

    def query(self,q,additional=None):
        if self.conn:
            try:
                self.conn.write(self.translate(q))
                self.read(3)
            except:
                log('%s: Query unresolved or not sent' %q)
                return None
        else:
            log('Connection not established, query unsuccessful: %s' %q)
            return None

    def command(self, q):
        if self.conn:
            try:
                self.conn.write(self.translate(q))
            except:
                log('%s: Command unresolved or not sent' %q)
                return None
        else:
            log('Connection not established, command unsuccessful: %s' %q)
            return None
        

    def getPos(self):
        return self.query('getpos')

    def connect(self,comport, baud):
        try:
            self.conn = serial.Serial(comport, baud)
            return self.conn
        except:
            resp = 'Cannot connect to %s at %s' % (str(comport),str(baud))
            print(resp)
            log(resp)
            return None
		
    def close(self):
        try:
            self.conn.close()
        except:
            resp = 'Cannot connect to %s at %s' % (str(comport),str(baud))
            print(resp)
            log(resp)

    def send(self, data, timeout=15):
        if self.conn:
            self.conn.write(data, timeout=15)
        else:
            log('Cannot send data to serial')
            

    def receive(self,buffer=3, timeout=15):
        received = ''
        now = time.time()
        then = now + timeout
        while time.time() < then or (length(received)>=3):
            received += self.conn.read()

    def setManual(self):
        self.auto = False

    def setAuto(self):
        self.auto = True

    def position(self):
        self.send(self.getpositionstring)
		
        #wait until timeout
        response = self.receive()
        # get position from PLC (if possible)
        #self.position 
        return self.position

    # CONTROLS FOR PLC
    def moveto(self, position):
        pass
        # send instruction to move to position "position"
        log('move to %s' % position)
        self.position = position
        return self.position

    def move(self,step):
        if MINPOS < self.position+step < MAXPOS:
            data = '000'
            self.send(data)
            return 1
        else:
            self.auto = False
            self.stop()
            return 0
        
        # send instructions to move of "step" mm

    def start(self,step):
        if self.auto:
            #automatic
            pass
        else:
            move(step)

    def stop(self):
        if self.auto:
            self.auto = False
        data = '100'
        self.send(data)
                



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


        self.lvlStatus = StringVar()
        self.ifmStatus = StringVar()

        self.active = 0  # 0 - inactive state, 1 - active (in motion)
        self.auto = 0
       
        # COMPARATOR MOTION CONTROL
        self.step  = StringVar() # mm
        self.begin = StringVar() # mm
        self.end   = StringVar() # mm

        self.autoVal = IntVar()


        self.labelTop = StringVar()
        self.labelTop.set('VERTICAL COMPARATOR')

        # LABELS ON BUTTONS
        self.label10 = StringVar() # start/stop
        self.label21 = StringVar() # manual 
        self.label22 = StringVar() # auto
        self.label31 = StringVar() # step
        self.label32 = StringVar() # start
        self.label33 = StringVar() # stop
        self.label51 = StringVar() # read interferometer
        self.label52 = StringVar() # read digi level

        self.autoVal.set(0)
        
        #print self.label12

        # init PLC, interferometer and level
        self.plc = PLC(PLCCOM, PLCBAUD)
        self.conn = self.plc.conn
        self.ifm = IFM(IFMCOM, IFMBAUD)
        self.lvl = LVL(LVLCOM, LVLBAUD)

        self.observer = '' # operator
        
        #self.printData()
        self.label10.set({0:'START',1:'STOP'}[self.active])  # start/stop
        self.setStatus({0:'ready',1:'active'}[self.active])
        self.label21.set('MANUAL')   # manual 
        self.label22.set('AUTO')     # auto

        self.label31.set('LOW')    # start height
        self.label32.set('HIGH')      # stop height
        self.label33.set('STEP')     # step

        self.label51.set('READ IFM') # read interferometer
        self.label52.set('READ LVL') # read digi level

        self.timestring = StringVar()
        self.connstring = StringVar()


        #self.queue = queue.Queue()
        self.timerthread = threading.Thread(target=self.timer)
        self.timerthread.start()

        self.readdata = ''
        self.connthread = threading.Thread(target=self.checkconnection)
        self.connthread.start()

        self.statusthread = threading.Thread(target = self.checkstatus)
        self.statusthread.start()

        self.autologthread = threading.Thread(target = self.autolog)
        self.autologthread.start()

        #starttimer()
        #startautolog()
        #startautoserialcheck()

    #def toggleStartStop(self):
    #    # if start then stop else otherwise
    #    # change button and text color if possible
    #    pass

    #def printData(self):   
    #    pass
    def timer(self):
        while self.on:
            dt = datetime.now() - self.starttime
            self.timestring.set('%-10s' % str(dt).split('.')[0])
            time.sleep(1)

    def autolog(self,timeout = 60):
        while self.on:
            print('Autolog')
            s,low,hi,step,ifm,lvl,obs = '','','','','','',''
            try:
                s = self.statusText
                low = self.lowEntry.get().strip()
                hi = self.hiEntry.get().strip()
                step = self.stepEntry.get().strip()
                ifm = IFM().read()
                lvl = LVL().read()
                obs = self.entryObserver.get().strip()
            except:
                print('problem with values')
            log('AUTOLOG! status: %s, low: %s, hi: %s, step: %s, ifm: %s, lvl: %s, obs: %s' % (s,low,hi,step,ifm,lvl,obs))
            time.sleep(timeout)


    def checkconnection(self):
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
            self.connstring.set({True:'isConn',False:'notConn'}[connection])   
            time.sleep(0.5)

    def checkstatus(self):
        st = None
        if self.conn:
            try:
                st = self.query('status')
                if st == ACTIVE:
                    self.status = 'active'
                elif st == INACTIVE:
                    self.status = 'ready'
                else:
                    self.status = 'unknown'
            except:
                self.status = 'unknown'
        else:
            self.status = 'not connected'


        
    def evaluateEntries(self):
        s,b,e = self.stepEntry, self.beginEntry, self.endEntry
        res = [None,None,None]
        for i in range(3):
            try: res[i] = float([s,b,e][i])
            except: pass # leave it None
        if b>e and s>0: # if step is negative, it can move downwards (from hi to low)
            b,e = e,b # otherwise it begin and end must be changed if b>e
        elif b<e and s<0: 
            b,e = e,b 

        # INPUT IN MM !! cannot recognize 0.5mm from 0.5m  step or 3mm vs 3m end
        # input values converted to mm
        #[s,b,e] = [i*1000. if (i is not None and i<5.) else i for i in [s,b,e]] 
        return s,b,e

    def emptyRow(self,nrow):
        Label(self.fr, text="", bg=bgcolor).grid(row=nrow,column=0)

    def setStatus(self,text):
        self.statusText = text
        self.statusString.set( self.statusText )

    def setLvlStatus(self, text):
        self.lvlStatus.set( text )
        
    def setIfmStatus(self, text):
        self.ifmStatus.set( text )

    def getIfm(self):
        ifm = IFM()
        response = ifm.read()
        if not response: response = "No response"
        self.setIfmStatus(response)
        return response

    def getLevel(self):
        lvl = LVL()   # možno načítať pri __init__
        response = lvl.read()
        if not response: response = "No response"
        self.setLvlStatus(response)
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
        self.active = not self.active
        self.label10.set({0:'START',1:'STOP'}[self.active])
        self.setStatus({0:'ready',1:'active'}[self.active])

        self.butStartStop.configure(bg = startstopbg[self.active],
                                    fg = startstopfg[self.active])

        self.observer = self.entryObserver.get().strip()
        
        if not self.active: log('CMP stopped %s' % self.observer)
        else: log('CMP started %s' % self.observer)

        if self.active:
            pass # action after comparator is stopped
        else:
            pass # action after comparator is started

    def getEntries(self):
        return self.stepEntry, self.beginEntry, self.endEntry

    def close(self):
        self.on = False
        if self.active:
            self.startStop()
        self.root.quit()
        self.root.destroy()

    def gotoLow(self):
        low = None
        self.setStatus('Going to LOW')
        try: low = float(lowEntry.get().strip())
        except: pass
        pass # move carriage to set low
        return low

    def gotoHi(self):
        hi = None
        self.setStatus('Going to HIGH')
        try: hi = float(hiEntry.get().strip())
        except: pass
        pass # move carriage to set low
        return hi

    def moveStep(self):
        pos = self.ifm.getPos()
        step= 0
        try:
            step = float(stepEntry.get().strip())
        except:
            pass
        targetpos = pos+step
        
        if step!=0:
            self.setStatus('Moving to %f' % targetpos)
            self.ifm.moveto(targetpos)
        return targetpos

    def resetLvlStatus(self):
        lvlStatus.set('')

    def resetIfmStatus(self):
        ifmStatus.set('')

    def mainDialog(self):

        self.basicframe = Frame(self.root)
        self.basicframe.grid()
        self.basicframe.configure(bg=bgcolor)

        self.fr = Frame(self.basicframe)
        self.fr.grid(row = 0, column = 0, sticky='new') #, sticky='W')
        self.fr.configure(bg=bgcolor)

        #Grid.rowconfigure(root, 0, weight=1)
        Grid.columnconfigure(root, 0, weight=1)

        self.emptyRow(0)

        Label(self.fr, textvariable = self.labelTop,
              justify='center', bg=bgcolor, font=("Calibri", 24)
            ).grid(row = 1, column=0, columnspan=3, sticky='we')

        self.emptyRow(2)
        
        Label(self.fr, text='STATUS:', justify='left', anchor='w',
              bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
              ).grid(row = 3, column=0, sticky='we', padx=(5,0))

        self.statusLine = Label(self.fr, textvariable = self.statusString,
                           justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                           font=("Calibri", 14, "bold")
                        ).grid(row = 3, column=1, columnspan=2, sticky='we')

        self.emptyRow(4)

        self.butStartStop = Button(self.fr, textvariable = self.label10,
                              command = self.startStop,
                              bg=startstopbg[self.active],
                              fg=startstopfg[self.active],
                              font=("Calibri", 16, "bold"),
                              width=10)
        self.butStartStop.grid(row=5, column=1, sticky='nsew')


        # AUTO / MANUAL  self.my_var.set(1)
        self.butManual = Radiobutton(self.fr, text = "MANUAL",
                                variable = self.auto,
                                value = 0,
                                width=15,
                                justify='center',
                                #bg=buttoncolor2,
                                bg = "moccasin",
                                indicatoron=0) #self.exit_root)
        self.butManual.grid(row=5, column=0, sticky='ew', padx=(0,10))
        #self.butManual.configure(state='selected')

        self.butAuto = Radiobutton(self.fr, text = "AUTO",
                             variable=self.auto,
                             value = 1,
                             width=15, justify='center',
                             #bg=buttoncolor2,
                             bg = "moccasin",
                             indicatoron=0) #self.exit_root)
        self.butAuto.grid(row=5, column=2, sticky='ew', padx=(10,0))

        self.emptyRow(6)
        self.emptyRow(7)

        # put Labels here

        Label(self.fr, textvariable = self.label31, justify='center',
                  bg=bgcolor, fg=statuscolor, font=("Calibri", 10)
                  ).grid(row = 8, column=0, sticky='we')
        Label(self.fr, textvariable = self.label32, justify='center',
                  bg=bgcolor, fg=statuscolor, font=("Calibri", 10)
                  ).grid(row = 8, column=1, sticky='we')
        Label(self.fr, textvariable = self.label33, justify='center',
                  bg=bgcolor, fg=statuscolor, font=("Calibri", 10)
                  ).grid(row = 8, column=2, sticky='we')

        # input boxes: step start stop (mm)
        self.lowEntry = Entry(self.fr, width=20, bd=3, justify='right',
                              bg = inputbox, fg = statuscolor)
        self.lowEntry.grid(row=9, column=0, sticky='we') #, columnspan=2)
        #SET DEFAULT LOW
        #self.lowEntry.delete(0,END)
        #self.lowEntry.insert(0, MINPOS)

        self.hiEntry = Entry(self.fr, width=20, bd=3, justify='right',
                             bg = inputbox, fg = statuscolor)
        self.hiEntry.grid(row=9, column=1, sticky='we') #, columnspan=2)
        #SET DEFAULT HIGH
        #self.hiEntry.delete(0,END)
        #self.hiEntry.insert(0, MAXPOS)

        self.stepEntry = Entry(self.fr, width=20, bd=3, justify='right',
                               bg = inputbox, fg = statuscolor)
        self.stepEntry.grid(row=9, column=2, sticky='we') #, columnspan=2)


        #put buttons for  GOTO and MOVE
        self.butGotoLow = Button(self.fr, text = "Go To Low",
                    justify='center', bg=buttoncolor, command = self.gotoLow)
        self.butGotoLow.grid(row=10, column=0, sticky='we')
        
        self.butGotoHi = Button(self.fr, text = "Go To High",
                    justify='center', bg=buttoncolor, command = self.gotoHi)
        self.butGotoHi.grid(row=10, column=1, sticky='we')

        self.butMoveStep = Button(self.fr, text = "Move a Step",
                    justify='center', bg=buttoncolor, command = self.moveStep)
        self.butMoveStep.grid(row=10, column=2, sticky='we')
        

        self.emptyRow(11)



        Label(self.fr, text = 'EXTERNAL SENSORS', justify='left',
                anchor='w', bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
                ).grid(row = 12, column=0, columnspan=3, sticky='we', padx=(5,0))

        # function buttons

        
        # RIadok 12: Externals
        butIFM = Button(self.fr, text = "Read IFM", width=15, justify='center',
                        bg=buttoncolor, command = self.getIfm) #self.exit_root)
        butIFM.grid(row=13, column=0, sticky='we')

        self.labIfmStatus = Label(self.fr, textvariable = self.ifmStatus,
                    justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                    font=("Calibri", 12))
        self.labIfmStatus.grid(row = 13, column = 1, columnspan = 2,
                               sticky = 'we', padx=(15,0))
        self.labIfmStatus.bind('<Button-1>',self.resetIfmStatus)

        butLVL = Button(self.fr, text = "Read level", width=15, justify='center',
                          bg=buttoncolor, command = self.getLevel) #self.exit_root)
        butLVL.grid(row=14, column=0, sticky='we')

        self.labLvlStatus = Label(self.fr, textvariable = self.lvlStatus,
                    justify='left', anchor='w', bg=bgcolor, fg=statuscolor,
                    font=("Calibri", 12))
        self.labLvlStatus.grid(row = 14, column = 1, columnspan = 2,
                               sticky = 'we', padx=(15,0))
        self.labLvlStatus.bind('<Button-1>',self.resetLvlStatus)


        self.emptyRow(15)

        Label(self.fr, text = 'OBSERVER:', anchor='w', justify='left',
                  bg=bgcolor, fg=statuscolor, font=("Calibri", 12)
                  ).grid(row = 16, column=0, sticky='we', padx=(5,0))
        self.entryObserver = Entry(self.fr, textvariable = self.observer,
                bg=inputbox, fg=statuscolor, font=("Calibri", 12),
                justify='left')
        self.entryObserver.grid(row = 16, column=1, columnspan=2, sticky='we')
        

        #row 18> empty (or test connection)
        self.emptyRow(18)
        self.timeLabel = Label(self.fr, textvariable = self.timestring,
                               anchor='w', bg=bgcolor, fg=statuscolor,
                    font=("Calibri", 9))
        self.timeLabel.grid(row=19,column=0)

        self.connLabel = Label(self.fr, textvariable = self.connstring,
                               anchor='w', bg=bgcolor, fg=statuscolor,
                    font=("Calibri", 9))
        self.connLabel.grid(row=19,column=1)

        butexit = Button(self.fr, text = "EXIT", width=15, justify='center',
                         bg="black", fg="yellow", command = self.close,
                         font=("Calibri", 14, "bold"))
        butexit.grid(row=19, column=2)





root = Tk()
root.title('VERTICAL COMPARATOR')
root.geometry('450x500')
root.configure(bg = bgcolor)
g = GUI(root)
g.mainDialog()
root.mainloop()

