# -*- coding: cp1250 -*-
import serial
from externals import RS232 #Comparator, Interferometer, Level, Nivel, Thermometer
from externals import strbit2byte, hex2byte
from tkinter import Tk, Button, Frame, Radiobutton, Entry, Label, Grid, IntVar, StringVar, END
import threading

DIMENSIONS = '500x400'
bgcolor = 'khaki'
fgcolor = 'peru'
inputbox = 'lemon chiffon'
buttoncolor = 'goldenrod1'

class testGUI:
    def __init__(self, master):
        """initialize GUI"""
        self.root = master
        self.on = True
        self.connection = None
        Tk().withdraw()
        self.basicframe = Frame(self.root)
        self.basicframe.grid()
        self.basicframe.configure(bg=bgcolor)

        self.fr = Frame(self.basicframe)
        self.fr.grid(row=0, column=0, sticky='new')  # , sticky='W')
        self.fr.configure(bg=bgcolor)
        Grid.columnconfigure(self.root, 0, weight=1)

        self.port = None
        self.baud = None
        # self.inputTypes = ['ascii', 'bin', 'hex', 'mix']
        self.inputType = StringVar()
        self.inputType.set('ascii')
        self.input = 'ascii'

        self.labelPort = Label(self.fr, width=10, text='PORT', justify='left', anchor='w', bg=bgcolor, fg=fgcolor, font=("Calibri", 12))
        self.entryPort = Entry(self.fr, width=20, bd=3, justify='left', bg=inputbox, fg=fgcolor)

        self.labelBaud = Label(self.fr, text='BAUD', justify='left', anchor='w', bg=bgcolor, fg=fgcolor, font=("Calibri", 12))
        self.entryBaud = Entry(self.fr, width=20, bd=3, justify='right', bg=inputbox, fg=fgcolor)

        self.labelType = Label(self.fr, text='TYPE', justify='left', anchor='w', bg=bgcolor, fg=fgcolor, font=("Calibri", 12))
        self.radioType1 = Radiobutton(self.fr, text='ascii', variable=self.inputType, value='ascii', indicatoron=0)
        self.radioType2 = Radiobutton(self.fr, text='bin', variable=self.inputType, value='bin', width=20, indicatoron=0)
        self.radioType3 = Radiobutton(self.fr, text='hex', variable=self.inputType, value='hex', indicatoron=0)
        self.radioType4 = Radiobutton(self.fr, text='mix', variable=self.inputType, value='mix', width=20, indicatoron=0)

        self.labelInput = Label(self.fr, text='INPUT', justify='left', anchor='w', bg=bgcolor, fg=fgcolor, font=("Calibri", 12))
        self.entryInput = Entry(self.fr, width=20, bd=3, justify='left', bg=inputbox, fg=fgcolor)

        self.buttonSend = Button(self.fr, text='SEND', justify='center', bg=buttoncolor, command=self.send)
        self.buttonRead = Button(self.fr, text='READ', justify='center', bg=buttoncolor, command=self.read)
        self.buttonExit = Button(self.fr, text='EXIT', justify='center', bg='red', fg='white', command=self.exit)

        self.response = StringVar()
        self.response.set('')
        self.responseBar = Label(self.fr, textvariable=self.response, justify='left', anchor='w',
                                 bg=bgcolor, fg=fgcolor, font=("Calibri", 12))
        self.status = StringVar()
        self.statusBar = Label(self.fr, textvariable=self.status, justify='left', anchor='nw',
                               bg=bgcolor, fg=fgcolor, font=("Calibri", 10))
        self.status.set('Initialized')


    def emptyRow(self, nrow):
        Label(self.fr, text="", bg=bgcolor).grid(row=nrow, column=0)

    def configure_connection(self):
        self.status.set('Configuring connection')
        self.port = self.entryPort.get()
        self.baud = self.entryBaud.get()
        try:
            self.baud = int(self.baud)
        except:
            self.entryBaud.delete(0, END)
            self.entryBaud.insert(0, '0')
            self.baud = 0

        self.connection = RS232(comport=self.port, baud=self.baud, dictionary={})

        if self.connection and self.connection.conn:
            self.entryPort.configure(state='disabled')
            self.entryBaud.configure(state='disabled')
        else:
            self.status.set('<No connection>')

    def convertInput(self):
        self.status.set('Converting input')
        print ('Converting')
        typ = self.inputType.get()
        self.input = self.entryInput.get()
        print (self.input)
        if typ == 'bin':
            newInput = ''
            for i in self.input:
                if i in ['0', '1']:
                    newInput += i
            z = len(newInput) % 8
            self.input = strbit2byte(('' if not z else (8 - z) * '0') + newInput)
        elif typ == 'hex':
            newInput = ''
            for i in self.input:
                if i in '0123456789ABCDEF':
                    newInput += i
            z = len(newInput) % 2
            self.input = hex2byte(('' if not z else '0') + newInput)
        elif typ == 'mix':
            newInput = self.input
            for i in re.findall('<(\d+?)>', inp):
                newInput = newInput.replace('<{}>'.format(i), chr(int(i)))
            self.input = newInput
        print ('Converted input: {}'.format(self.input))

    def send(self):
        # self.input = self.entryInput.get()
        self.convertInput()
        self.status.set('Sending Data {}...'.format(self.input[:5]))

        if not self.connection or not self.connection.conn:
            self.configure_connection()
        if self.connection and self.connection.conn:
            self.connection.send(self.input)
            self.status.set('')
        else:
            pass
            # self.status.set('<No connection>')

    def read(self):
        self.status.set('Reading Data')
        if not self.connection or not self.connection.conn:
            self.configure_connection()
        # self.input = self.entryInput.get()
        response = self.connection.receive()
        if response:
            self.response.set(response)
        else:
            self.response.set('<No response>')
        # self.status.set('')

    def exit(self):
        # for thread in (self.timerthread, self.connthread, self.statusthread, self.autologthread, self.readexternalsthread):
        #     thread.join()
        # if self.active:
        #     self.startStop()
        self.on = False
        self.root.destroy()
        self.root.quit()

    def mainDialog(self):
        self.labelPort.grid(row=0, column=0, sticky='we', padx=(5, 0))
        self.entryPort.grid(row=0, column=1, sticky='we')
        self.labelBaud.grid(row=1, column=0, sticky='we', padx=(5, 0))
        self.entryBaud.grid(row=1, column=1, sticky='we')
        self.labelType.grid(row=2, column=0, sticky='we', padx=(5, 0))
        self.radioType1.grid(row=2, column=1, sticky='we')
        self.radioType2.grid(row=2, column=2, sticky='we')
        self.radioType3.grid(row=3, column=1, sticky='we')
        self.radioType4.grid(row=3, column=2, sticky='we')
        self.labelInput.grid(row=4, column=0, sticky='we', padx=(5, 0))
        self.entryInput.grid(row=4, column=1)
        self.responseBar.grid(row=5, column=1)
        self.statusBar.grid(row=6, column=1)
        Label(self.fr, text="", bg=bgcolor).grid(row=7, column=0)
        self.buttonSend.grid(row=8, column=0)
        self.buttonRead.grid(row=8, column=1)
        self.buttonExit.grid(row=8, column=2)


if __name__ == '__main__':
    root = Tk()
    root.title('TEST APP')
    root.geometry(DIMENSIONS)
    root.configure(bg=bgcolor)
    g = testGUI(root)
    g.mainDialog()
    root.mainloop()
