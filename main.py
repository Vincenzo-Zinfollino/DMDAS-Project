# This is a sample Python script.

# Press Maiusc+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
import csv
import math
import sys
import tkinter as tk
import tkinter as ttk
import tkinter.font as tkFont
from tkinter import RAISED, messagebox
from datetime import datetime
from tkinter.filedialog import askopenfilename

import matplotlib.pyplot as plt
import serial as sr
import serial.tools.list_ports as sr_list
import time
import threading

import numpy as np
import matplotlib
import matplotlib.animation as an
#from matplotlib import animation as an
from matplotlib.pyplot import yticks



matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

port = "COM3"
baudrate = 115200
downstream = []
temp = []
delay=1
i_time = []


f = Figure(figsize=(7.5, 5), dpi=100)
a = f.add_subplot(111)


class measure(threading.Thread):



    def __init__(self, port, baudrate, *args, **kwargs):
        #threading.Thread.__init__(self)
        super(measure, self).__init__(*args, **kwargs)
        self.instant =0
        #i_time.append(0)
        self._stop_event = threading.Event()
        self.port = port
        self.baudrate = baudrate
        self.running = False
        self.s_data = sr.Serial(port, baudrate, timeout=0)

    def run(self):

        # print( self.s_data.isOpen())
        try:
            self.s_data.isOpen()
        except IOError:
            self.s_data = sr.Serial(port, baudrate, timeout=0)

        self.running = True
        while self.running and self.s_data.isOpen():
            reading = str(self.s_data.readline())

            reading = reading[2:len(reading) - 5]
            downstream.append(reading)

            var = reading.split(':')[-1]
            if not var == '' and not var.isdecimal() and 'Fault' not in var:
                temp.append(float(var))
                self.instant = self.instant + delay
                i_time.append(float(self.instant))
                print("temp =", temp)
            # print("down =", downstream)

            print("run")

            # print(i_time)
            #print(temp)
            time.sleep(delay+1)

    def stop(self):
        self.running = False
        return self.running
        # self._stop_event.set()
        # self.s_data.close()


class App:
    def __init__(self, root):

        self.saveData_w = None
        self.is_running = False
        self.measT = None  # Prima era commentato
        self.filepath =''
        self.avg= None
        self.std= None

        # setting title
        root.title("Progetto DMDAS")
        # setting window size
        width = 1200
        height = 800
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=False, height=False)
        root.option_add('Roboto', '12')
        root.iconbitmap("icona.ico")


        # menu
        self.menubar = tk.Menu(root)

        '''NB: in tk must be declared first the sub menu element  than the top bar menu '''

        #---------File Menu---------
        self.menu_f = tk.Menu(self.menubar, tearoff=0)
        self.menu_f.add_cascade(label="Open", command=self.m_open)
        self.menu_f.add_cascade(label="Save Data", command=self.m_saveData)
        # ---------End File Menu---------

        # ---------File Open---------
        self.menu_o = tk.Menu(self.menubar, tearoff=0)
        self.menu_o.add_cascade(label="Serial", command=self.m_serial)
        # ---------End File Open---------

        # ---------Main Top Menu Element---------
        self.menubar.add_cascade(label='File', menu=self.menu_f)
        self.menubar.add_cascade(label='Option', menu=self.menu_o)
        # ---------------------------------------

        root.config(menu=self.menubar)




        # start Button
        self.start = ttk.Button(root)
        self.start["bg"] = "#00ac69"
        ft = tkFont.Font(family='Roboto', size=18)
        self.start["font"] = ft
        self.start["fg"] = "#ffffff"
        self.start["justify"] = "center"
        self.start["text"] = "START"
        self.start["borderwidth"] = 0
        self.start.place(x=50, y=715, width=140, height=50)
        self.start["command"] = self.start_command

        # stop button
        self.stop = ttk.Button(root)
        self.stop["bg"] = "#d02c2f"
        ft = tkFont.Font(family='Roboto', size=18)
        self.stop["font"] = ft
        self.stop["fg"] = "#ffffff"
        self.stop["justify"] = "center"
        self.stop["text"] = "STOP"
        self.stop["borderwidth"] = 0
        self.stop.place(x=1010, y=715, width=140, height=50)
        self.stop["command"] = self.stop_command

        # Canvas for the graph
        self.canvas = tk.Canvas(root)
        self.canvas.place(x=500, y=60, width=650, height=530)
        self.canvas["bg"] = "#d02c2f"

        a.plot()



        self.f1 = FigureCanvasTkAgg(f, master=self.canvas)
        self.f1.draw()
        self.f1.get_tk_widget().pack()

        toolbar = NavigationToolbar2Tk(self.f1, self.canvas)
        toolbar.update()
        # self.f1.get_tk_widget().pack()

        #left side -------------

        self.l1 = tk.Label(root, text='La temperatura corrente è:')
        self.l1.place(x=110, y=60, width=270, height=20)
        ft = tkFont.Font(family='Roboto', size=10)
        self.l1["font"] = ft
        self.l1["fg"] = "#000000"

        self.temp_label = tk.Label(root, text='--')
        self.temp_label.place(x=110, y=85, width=270, height=100)
        ft = tkFont.Font(family='Roboto', size=32)
        self.temp_label["font"] = ft
        self.temp_label["fg"] = "#ffffff"
        self.temp_label["bg"] = "#696969"

        self.lavg = tk.Label(root, text='AVG:')
        self.lavg.place(x=113, y=200, width=130, height=20)
        ft = tkFont.Font(family='Roboto Bold', size=10)
        self.lavg["font"] = ft
        self.lavg["fg"] = "#000000"

        self.avg_label = tk.Label(root, text='--')
        self.avg_label.place(x=110, y=225, width=130, height=45)
        ft = tkFont.Font(family='Roboto', size=22)
        self.avg_label["font"] = ft
        self.avg_label["fg"] = "#ffffff"
        self.avg_label["bg"] = "#696969"

        
        self.lstd = tk.Label(root, text='STD:')
        self.lstd.place(x=251, y=200, width=130, height=20)
        ft = tkFont.Font(family='Roboto Bold', size=10)
        self.lstd["font"] = ft
        self.lstd["fg"] = "#000000"

        self.std_label = tk.Label(root, text='--')
        self.std_label.place(x=250, y=225, width=130, height=45)
        ft = tkFont.Font(family='Roboto', size=22)
        self.std_label["font"] = ft
        self.std_label["fg"] = "#ffffff"
        self.std_label["bg"] = "#696969"









        #END left side ------


    def start_command(self):
        print("Start")

        self.start["state"] = "disable"

        # dichiarazione thread
        self.measT = measure(port, baudrate)
        self.measT.setDaemon(True)  # SetDiavoletto
        self.is_running = True



        if not self.measT.is_alive():
            self.measT.start()

        # print(downstream)

    def stop_command(self):
        print("stop")
        # self.start["state"] = "normal"
        # self.data1.stop()
        self.is_running = self.measT.stop()
        ani.pause()
        plt.close()

        # print("btnstp",self.data1.is_alive())

    def m_open(self):
        print("open")
        filename = askopenfilename()


    def m_saveData(self):

        print('Save Data')

        def save():

            if len(temp) > 1:
                self.filepath = tk.filedialog.askdirectory() + '/' + self.filename.get()
                with open(self.filepath, 'w', newline='', encoding='UTF8') as csv_file:
                    write = csv.writer(csv_file)
                    write.writerow(["time", "temperature"])
                    for i in range(len(temp)):
                        row = [str(i_time[i]), str(temp[i])]
                        print(row)
                        write.writerow(row)
            else:
                messagebox.showinfo("Impossibile salvare i dati "," Impossibile salvare i dati, non sono stati trovati dati oppure \n il processo di misura potrebbe non essere stato avviato. ")

            saveData_w.destroy()


            print(self.filepath)


        filepath = ''
        #---Window Declaring
        saveData_w = ttk.Toplevel(root)
        width = 320
        height = 165
        screenwidth = saveData_w.winfo_screenwidth()
        screenheight = saveData_w.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        saveData_w.geometry(alignstr)
        saveData_w.resizable(width=False, height=False)
        saveData_w.title("File Option")
        saveData_w.iconbitmap("icona.ico")
        # --- END  Window Declaring


        self.label1 = ttk.Label(saveData_w, text="Scegli il nome del file ")
        self.label1.place(x=20, y=20 )

        self.s_filename='TEMPMEAS'+str(datetime.timestamp(datetime.now()))

        self.filename=tk.Entry(saveData_w, textvariable=self.s_filename )
        self.filename.insert(0,self.s_filename +'.csv')
        self.filename.place(x=20,y=50, width=250, height=20)
        print(self.s_filename)


        self.save_b=ttk.Button(saveData_w)
        self.save_b.place(x=125, y=110, width=70, height=35)

        self.save_b["bg"] = "#00ac69"
        ft = tkFont.Font(family='Roboto', size=12)
        self.save_b["font"] = ft
        self.save_b["fg"] = "#ffffff"
        self.save_b["justify"] = "center"
        self.save_b["text"] = 'SAVE'
        self.save_b["borderwidth"] = 0
        self.save_b["command"] = save


    def stat(self): #calcolo e aggiorno le label di STD e AVG
        
        obsv=10

        if len(temp)>0 and len(temp)<10:
            self.avg=np.average(temp)
            self.std=np.std(temp)
        elif len(temp)>obsv:  # Calcolo della media nella obsv. window pari a 10 samples
            self.avg=np.average(temp[-(obsv+1):-1])
            self.std=np.std(temp[-(obsv+1):-1])
        
        
        if self.avg is not None and self.std is not None:
            self.avg_label.config(text=round(self.avg, 2))
            self.std_label.config(text=round(self.std, 2))





    def m_serial(self):
        print("serial")
        port = list(sr_list.comports())
        for p in port:
            print(p)

        serial_w = ttk.Toplevel(root)
        serial_w.geometry("400x400")
        serial_w.resizable(width=False, height=False)
        serial_w.title("Serial Option")


    def animate(self,k):

        if self.is_running:
            #temp_1=[float(i) for i in temp]

            if len(temp)>1:
                dat = str(temp[-1])+"°"
                self.temp_label.config(text=dat)
                #self.temp_label.place(x=10, y=60, width=140, height=50)
                print("tempdisp =", str(temp[-1]))

            self.stat()

            a.autoscale(enable=True, axis='both', tight=None)
            a.clear()
            a.plot( i_time,temp)
            if len(temp)>0:
              yticks(np.arange(min(temp), max(temp), step=0.31))




if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    ani = an.FuncAnimation(f, app.animate,  interval=30, repeat=False)
    root.mainloop()
