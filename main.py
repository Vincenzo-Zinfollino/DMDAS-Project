# This is a sample Python script.

# Press Maiusc+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
from asyncore import read
from base64 import encode
import csv
import math
from multiprocessing.connection import wait
from multiprocessing.sharedctypes import Value
from pickle import NONE
from queue import Empty
import sys
import tkinter as tk
import tkinter as ttk
import tkinter.ttk as TTK
from tkinter.ttk import *
import tkinter.font as tkFont
from tkinter import RAISED, Tk, messagebox
from datetime import datetime
from tkinter.filedialog import askopenfilename
import unicodedata
from unittest import skip
import logging 

import matplotlib.pyplot as plt
import serial as sr
import io 
import serial.tools.list_ports as sr_list
import time
import threading

import numpy as np
import matplotlib
import matplotlib.animation as an
#from matplotlib import animation as an
from matplotlib.pyplot import text, yticks



matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure


settings= {"COMPORT":"COM6",
            "RNOMINAL":100,
            "BAUDRATE":115200,
            "REFRESISTOR":430,
            "STEP":0,
            "WINDOWSIZE":100,
            "TIMER":0.5,
            "NOTCH":60,
            "ERROR":5,
            "TARGETTEMP":None
            }

fault = { "80":"MAX31865_FAULT_HIGHTHRESH: 0x80",
          "40":"MAX31865_FAULT_LOWTHRESH 0x40",
          "20":"MAX31865_FAULT_REFINLOW 0x20",  
          "10":"MAX31865_FAULT_REFINHIGH 0x10",
          "08":"MAX31865_FAULT_RTDINLOW 0x08",
          "04":"MAX31865_FAULT_OVUV 0x04",         
        }

t_time=[]
downstream = []
temp = []
delay=1
i_time = []
errors=[[],[]]

f = Figure(figsize=(7.5, 5), dpi=100)
a = f.add_subplot(111)
a.set_xlabel('Time [s]')
a.set_ylabel('Temperature [°C]')


def acquire_data(self):

    self.s_data.port=self.port
    count_err=0

    try :
        self.s_data.open()
    except:  
        app.start["state"] = "normal" 

        return 

    
    
    if self.s_data.isOpen():

        self.running = True
            
        #self.s_data.write(b"\n") 
        self.s_data.flush()
        #time.sleep(0.5)
        self.s_data.readline() 
        

        self.s_data.write(bytes(f"S:{settings['TIMER']}:{settings['NOTCH']}\n","ascii"))
        self.s_data.flush()

    

    while self.running and self.s_data is not None and self.s_data.isOpen():

        try:
            
            reading = self.s_data.read(2)
        except: break
        

        

        
        #print (reading.hex())
        

        read=reading.hex()

        val = []
        
        for i in range(0,len(read),4):
            val.append(int(read[i:i+4],16))
            

        #print(val)

        for rtd in val:

            #print (rtd)
            t=round(self.rtd_to_temp(rtd),2)

            if rtd > 0  :
                
                if len(temp)>0:
                    dif=abs(t-temp[-1])

                    #verifichiamo il target

                #settings["TARGETTEMP"]=25

                
                count_err=0
                #print(t)
                temp.append(t)
                i_time.append(float(self.instant))
                

                if len(temp)>1:
                    
                  

                    if (settings["TARGETTEMP"] is not None) and (t>=settings["TARGETTEMP"]) and (temp[-2]<settings["TARGETTEMP"]):
                        t_time.append([self.instant])

                        #cambia il colore appena supera la soglia 
                        app.track_temp_label["bg"] = "#00AC69"
                        
                    elif settings["TARGETTEMP"] is not None and t<settings["TARGETTEMP"] and temp[-2]>=settings["TARGETTEMP"]:

                        t_time[-1]+=[self.instant,self.instant-t_time[-1][0]]

                        app.track_temp_label["bg"] = "#D02C2F"

                elif settings["TARGETTEMP"] is not None and t>=settings["TARGETTEMP"]:
                        t_time.append([self.instant])

                #print (t_time)
                    

                if len(temp)>1 and (dif>40): #rileva gli sbalzi di temperatura

                    # TO Do: inserire il log
                    errors[0].append(temp[-1])
                    errors[1].append(self.instant)
                    #effettuiamo il logging

                    logging.warning(f"Salto di temperatura di :{round(dif,2)}° all istante {self.instant}")

                self.instant = self.instant + settings["TIMER"]
                
                

            else:

                count_err+=1

                
                self.fault_aq()
                

                if len(temp)>0:
                    temp.append(temp[-1])
                    i_time.append(float(self.instant))
                    errors[0].append(temp[-1])
                    errors[1].append(self.instant)
                    self.instant = self.instant + settings["TIMER"]
                    

                    
                if  count_err==settings["ERROR"]:
                    
                    if  self.running:
                        if (messagebox.askokcancel("ERRORE","Sono stati rilevati un numero elevato di errori.\nLe misure potrebbero non essere attendibili.\nVuoi terminare ?")):
                            app.stop_command()
                            self.stop()
                        else:return



        # print(i_time)
        #print(temp)
        #time.sleep(settings["STEP"])



def calibrate(self):

    self.end=False
    self.s_data.port=self.port
    self.s_data.open()


    if self.s_data.isOpen():
 

      
        self.s_data.flush()
       
        self.s_data.readline() 
        

        self.s_data.write(bytes("C\n","ascii"))
        self.s_data.flush()

        readingPt100=self.s_data.readline().hex()
        readingLM35=self.s_data.readline().hex()


        self.valPt100 = []
        self.valLM35  =[]
        
        for i in range(0,len(readingPt100)-4,4):
            self.valPt100.append(int(readingPt100[i:i+4],16))
            self.valLM35.append(int(readingLM35[i:i+4],16))

        self.valPt100=[round(x,2) for x in map(self.rtd_to_temp,self.valPt100)]
        self.valLM35=[ round(((x*5)/1024)*100,2) for x in self.valLM35]
        
        #print (valPt100,valLM35)

        error=[x-y for x,y in zip(self.valPt100,self.valLM35)]
        self.offset=np.average(error)
        print(self.offset)

    
        self.s_data.write(bytes(f"O:{round(self.offset,2)}\n","ascii"))

        #TODO[ricordatevi d'inviare i dati PUTTANI !!!!!!! ]

        self.s_data.close() #ricordati di chiudere la seriale altrimenti non partono le misurazioni 
        
        


        



   

class measure(threading.Thread):



    def __init__(self, port, baudrate, method, *args, **kwargs):
        #threading.Thread.__init__(self)
        super(measure, self).__init__(*args, **kwargs)
        self.instant =0
        #i_time.append(0)
        self._stop_event = threading.Event()
        self.port = port   
        print ("COM port init", self.port)
        self.baudrate = baudrate
        self.running = False
        #self.s_data = sr.Serial(self.port, self.baudrate, timeout=0)
        self.s_data = sr.Serial( baudrate=self.baudrate) #modificato
        
        self.method=method

        self.valPt100 = []
        self.valLM35  =[]
        self.end=None
        self.offset=None

        

    def rtd_to_temp(self,rtd:int):
       
        A = 3.9083e-3
        B = -5.775e-7
        Rt= ((rtd/32768)*settings["REFRESISTOR"])

        temp=(math.sqrt(((A*A)-(4*B))  +  ((4*B)/settings["RNOMINAL"])*Rt ) -A)/(2*B)
        if (temp>= 0):return temp

        Rt= (Rt/settings["RNOMINAL"])*100

        temp=-242.02 + 2.2228*Rt 
        + 2.5859e-3*(math.pow(Rt,2)) 
        - 4.8260e-6*(math.pow(Rt,3))
        - 2.8183e-8*(math.pow(Rt,4))
        + 1.5243e-10*(math.pow(Rt,5))

        return temp

    def fault_aq(self):

        if self.s_data.isOpen():

            self.s_data.flush()

            
            self.s_data.write(bytes("F\n","ascii"))
            self.s_data.flush()

            read= ""
            
            while not (read == "00"):
                try:
                    reading = self.s_data.read(1)
                    read=reading.hex()

                    if read!="00":
                       logging.error(fault[read])
                    
                   # inseriamo i fault 
                except: return


   

    def run(self):
      
        self.method(self)

        
    
    


    




    def stop(self):
         

        if (self.s_data.isOpen()):

            self.s_data.write(b"T\n")
            self.s_data.close()

        self.running = False
        return self.running
        # self._stop_event.set()
      


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
        #root.iconbitmap("Icona.ico")


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
        self.menu_o.add_cascade(label="Settings", command=self.m_settings)
        self.menu_o.add_cascade(label="Calibration", command=self.calibration)
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



        # Temperature Track --------


        self.l4 = tk.Label(root, text='Temperatura monitorata :')
        self.l4.place(x=110, y=450, width=270, height=20)
        ft = tkFont.Font(family='Roboto', size=10)
        self.l4["font"] = ft
        self.l4["fg"] = "#000000"

        self.track_temp_label = tk.Label(root, text='--')
        self.track_temp_label.place(x=110, y=480, width=270, height=100)
        ft = tkFont.Font(family='Roboto', size=32)
        self.track_temp_label["font"] = ft
        self.track_temp_label["fg"] = "#ffffff"
        self.track_temp_label["bg"] = "#696969"

       






        #END left side ------




    def start_command(self):
        print("Start")

        self.start["state"] = "disable"

        # dichiarazione thread
        print("start port :",settings["COMPORT"])  #modificato
        self.measT = measure(settings["COMPORT"], settings["BAUDRATE"],acquire_data)
        self.measT.daemon=True  # SetDiavoletto
       
        


        if not self.measT.is_alive():
            self.measT.start()
            self.is_running = True

        # print(downstream)

    def stop_command(self):
        print("stop")
        # self.start["state"] = "normal"
        #self.data1.stop()
        self.is_running = self.measT.stop()
        ani.pause()
        plt.close()

        # print("btnstp",self.data1.is_alive())



    def on_closing(self):

      
        if  self.is_running:
            if (messagebox.askokcancel("Esci","Le misure sono ancora in corso.\nSei Sicuro di voler terminare ?")):
                self.stop_command()
                root.destroy()
            else: return

        
        root.destroy()
        


    def calibration(self):

        startcalibratew = ttk.Toplevel(root)
        
        cl=measure(settings["COMPORT"],settings["BAUDRATE"],calibrate)
        cl.deamon=True

        def start_t():

            cl.start()
            print("hello0")
            cl.join() #attende che il thread abbia completato l'operazione
            print (cl.valPt100,cl.valLM35,cl.offset)

            calibratew = ttk.Toplevel(root)

            width = 900
            height = 450
            screenwidth = calibratew.winfo_screenwidth()
            screenheight = calibratew.winfo_screenheight()
            alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
            calibratew.geometry(alignstr)
            calibratew.resizable(width=False, height=False)
            calibratew.title("Calibration Option")
            startcalibratew.destroy()

            valuelabelPT100= [] 
            valuelabelLM35 = [] 




            for i in range(len(cl.valPt100)):

                ft = tkFont.Font(family='Roboto', size=13)
                self.label1 = ttk.Label(calibratew, text="Misure del device di riferimento ",font=ft)
                self.label1.place(x=50, y=70)

                valuelabelPT100.append ( tk.Label(calibratew, text='--'))
                valuelabelPT100[-1].place(x=50+i*80, y=105, width=70, height=45)
                ft = tkFont.Font(family='Roboto', size=14)
                valuelabelPT100[-1]["font"] = ft
                valuelabelPT100[-1]["fg"] = "#ffffff"
                valuelabelPT100[-1]["bg"] = "#696969"
                valuelabelPT100[-1].config(text=str(cl.valPt100[i]))

                ft = tkFont.Font(family='Roboto', size=13)
                self.label1 = ttk.Label(calibratew, text="Misure del device da tarare ",font=ft)
                self.label1.place(x=50, y=190)

                valuelabelLM35.append ( tk.Label(calibratew, text='--'))
                valuelabelLM35[-1].place(x=50+i*80, y=225, width=70, height=45)
                ft = tkFont.Font(family='Roboto', size=14)
                valuelabelLM35[-1]["font"] = ft
                valuelabelLM35[-1]["fg"] = "#ffffff"
                valuelabelLM35[-1]["bg"] = "#696969"
                valuelabelLM35[-1].config(text=str(cl.valLM35[i]))

            ft = tkFont.Font(family='Roboto', size=13)
            self.label1 = ttk.Label(calibratew, text="Il valore di Offset rilevato",font=ft)
            self.label1.place(x=335, y=300)


            self.temp_label = tk.Label(calibratew, text=str(round(cl.offset,2)))
            self.temp_label.place(x=315, y=330, width=250, height=80)
            ft = tkFont.Font(family='Roboto', size=32)
            self.temp_label["font"] = ft
            self.temp_label["fg"] = "#ffffff"
            self.temp_label["bg"] = "#696969"

            




        
        if not self.is_running:
            
            width = 300
            height = 200

            screenwidth =  startcalibratew.winfo_screenwidth()
            screenheight =  startcalibratew.winfo_screenheight()
            alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
            startcalibratew.title("Calibration Option")
           
            startcalibratew.geometry(alignstr)
            
            startcalibratew.resizable(width=False, height=False)
           
            ft = tkFont.Font(family='Roboto', size=13)
            self.label1 = ttk.Label(startcalibratew, text=" Start calibration ",font=ft)
            self.label1.place(x=80, y=50)
            
            start = ttk.Button(startcalibratew)
            start["bg"] = "#00ac69"
            ft = tkFont.Font(family='Roboto', size=18)
            start["font"] = ft
            start["fg"] = "#ffffff"
            start["justify"] = "center"
            start["text"] = "START"
            start["borderwidth"] = 0
            start.place(x=80, y=100, width=140, height=50)
            start["command"] = start_t
               




        else:
            messagebox.showerror("Esci","Le misure sono ancora in corso.\nPuoi effettuare il proceso di calibrazione solo prima d'iniziare il processo di misurazione")
            


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
        #saveData_w.iconbitmap("Icona.ico")
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

        if len(temp)>1 and len(temp)<settings["WINDOWSIZE"]:
            self.avg=np.average(temp)
            self.std=np.std(temp)
        elif len(temp)>=settings["WINDOWSIZE"]:  # Calcolo della media nella obsv. window pari a 10 samples
            self.avg=np.average(temp[-(settings["WINDOWSIZE"]+1):-1])
            self.std=np.std(temp[-(settings["WINDOWSIZE"]+1):-1])
        
        
        if self.avg is not None and self.std is not None:
            self.avg_label.config(text=round(self.avg, 2))
            self.std_label.config(text=round(self.std, 2))



    def m_serial(self):
        
        self.comboP=None

        def selectser():
            #effettuiamo il salvataggio su un file
            porttest=self.comboP.get()
            
            if not self.is_running:
                if porttest=="Scegli un valore": #se non è stato selezionato alcun vaore appare un messaggio di errore.
                    messagebox.showinfo("Impossibile salvare la preferenza:"," Selezionare una porta valida")
                else :
                    #porttest=porttest[0:4]
                    psel=porttest.split(" ") 
                    # poichè potrebbe non essere COM3 ma avere più digit divido la stringa 
                    # secondo gli spazi e prendo e dalla lista creata prendo il primo elemento che rappresenta il nominativo della porta

                    settings["COMPORT"]=psel[0] #modificato
                    print(settings["COMPORT"])
                    serial_w.destroy()
            else:
                messagebox.showinfo("Impossibile modificare la porta:"," Il processo di misurazione è in corso")


 

            


        portlist = list(sr_list.comports())
        for p in portlist:
            print(p)
            
    
        serial_w = ttk.Toplevel(root)

        
        width = 400
        height = 200
        screenwidth = serial_w.winfo_screenwidth()
        screenheight = serial_w.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        serial_w.geometry(alignstr)
        serial_w.resizable(width=False, height=False)
        serial_w.resizable(width=False, height=False)
        serial_w.title("Serial Option")
        #serial_w.iconbitmap("Icona.ico")

        self.label1 = ttk.Label(serial_w, text="Scegli la porta di comunicazione:")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label1["font"] = ft
        self.label1.place(x=40, y=25 )
        
        # dichiaro la combo box per selezionare la porta seriale 
        self.comboP=TTK.Combobox(serial_w, values=portlist, state="readonly")
        self.comboP.set("Scegli un valore")
        
        self.comboP.place(x=40, y=50, width=280, height=35) #x=60

        self.saveser_b=ttk.Button(serial_w)
        self.saveser_b.place(x=160, y=120, width=70, height=35)

        self.saveser_b["bg"] = "#00ac69"
        ft = tkFont.Font(family='Roboto', size=12)
        self.saveser_b["font"] = ft
        self.saveser_b["fg"] = "#ffffff"
        self.saveser_b["justify"] = "center"
        self.saveser_b["text"] = 'SAVE'
        self.saveser_b["borderwidth"] = 0
        self.saveser_b["command"] = selectser

    def m_settings(self):



        selvar = tk.IntVar()
        if settings["TARGETTEMP"]!=None:

            selvar.set(1)

        def selectset():
            if not self.is_running:
                var=self.t_Slider.get()
                settings["TIMER"]=var

                settings["NOTCH"]=self.comboN.get()[0:2]

                if selvar.get()== 1:
                    settings["TARGETTEMP"]=self.temp_Slider.get()
                    self.track_temp_label.config(text=settings["TARGETTEMP"])
                    if settings["TARGETTEMP"]>= 0:
                        self.track_temp_label["bg"] = "#F89625"
                    else:
                        self.track_temp_label["bg"] = "#648DE5"
                    

                else:
                    settings["TARGETTEMP"]= None
                    self.track_temp_label.config(text="--")
                    self.track_temp_label["bg"] = "#696969"


                #cambia il colore del riquadro della temperatura monitorata
                
                print(settings["TARGETTEMP"])


                settingsw.destroy()
            else:
                messagebox.showinfo("Impossibile modificare le impostazioni:"," Il processo di misurazione è in corso")

        def check():
            if selvar.get()== 1:
          
                self.temp_Slider.configure(state="normal")
            else:
                 self.temp_Slider.configure(state="disabled")


        
        #da inserire la condizione per impossibilitare la modifica durante la misurazione 
        settingsw = ttk.Toplevel(root)
        width = 320
        height = 425
        screenwidth = settingsw.winfo_screenwidth()
        screenheight = settingsw.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height, (screenwidth - width) / 2, (screenheight - height) / 2)
        settingsw.geometry(alignstr)
        settingsw.resizable(width=False, height=False)
        settingsw.title("Settings Option")
        #settingsw.iconbitmap("Icona.ico")

        self.label1 = ttk.Label(settingsw, text="Scegli l'intervallo di tempo tra due campioni:")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label1["font"] = ft
        self.label1.place(x=40, y=30 )
      
        # dichiaro lo slider del intervallo di campionamento 
        ft = tkFont.Font(family='Roboto', size=8)
        self.t_Slider = tk.Scale(settingsw, from_=0.1, to=4.0,digits=2, resolution=0.1, orient="horizontal",font=ft)
        self.t_Slider.set(1.0)
        self.t_Slider.place(x=40, y=50, width=250)


        self.label2 = ttk.Label(settingsw, text="Scegli la frequenza del Notch :")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label2["font"] = ft
        self.label2.place(x=40, y=105 )
      

        #selezione del notch
        notch=["50 Hz","60 Hz"]
        self.comboN=TTK.Combobox(settingsw, values=notch, state="readonly")
        self.comboN.set("Scegli un valore")
        self.comboN.place(x=40, y=135, width=200, height=32)



        #dichiaro lo slider della selezione temperatura

        
        self.select_tempSlider=tk.Checkbutton(settingsw, text='Abilita monitoraggio della temperatura', variable=selvar, command=check)
        self.select_tempSlider.place(x=40, y=185 )

        self.label2 = ttk.Label(settingsw, text="Scegli la temperatura da monitorare [ °C ] :")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label2["font"] = ft
        self.label2.place(x=40, y=225 )
        
        ft = tkFont.Font(family='Roboto', size=8)
        self.temp_Slider = tk.Scale(settingsw, from_=-100.0, to=250.0, digits=4, resolution=0.5, orient="horizontal",font=ft ,state="disabled")
        self.temp_Slider.set(20.0)
        self.temp_Slider.place(x=40, y=250, width=250)


        
       

       



        self.saveset_b=ttk.Button(settingsw)
        
        self.saveset_b["bg"] = "#00ac69"
        ft = tkFont.Font(family='Roboto', size=12)
        self.saveset_b["font"] = ft
        self.saveset_b["fg"] = "#ffffff"
        self.saveset_b["justify"] = "center"
        self.saveset_b["text"] = 'SAVE'
        self.saveset_b["borderwidth"] = 0
        self.saveset_b["command"] = selectset

        self.saveset_b.place(x=128, y=360, width=70, height=35)

        #notch frequency

          # dichiaro la combo box per selezionare la notch F
        
      



        



    def animate(self,k):

        if self.is_running:
            #temp_1=[float(i) for i in temp]

            if len(temp)>1:
                dat = str(temp[-1])+"°"
                self.temp_label.config(text=dat)
                #self.temp_label.place(x=10, y=60, width=140, height=50)
                #print("tempdisp =", str(temp[-1]))

            self.stat()

            a.autoscale(enable=True, axis='both', tight=None)
            a.clear()

            a.set_xlabel('Time [s]')
            a.set_ylabel('Temperature [°C]')

          

            if len(temp)>0:
                a.plot( i_time,temp,errors[1],errors[0], "rx")
                if(settings["TARGETTEMP"]):
                    a.plot([0,i_time[-1]],[settings["TARGETTEMP"],settings["TARGETTEMP"]],"r-") 

            if len(temp)>0:
              yticks(np.arange(min(temp), max(temp), step=0.31))




if __name__ == "__main__":

  
    logging.basicConfig(filename="ErrorLOG.log",
                                    format='%(asctime)s - %(levelname)s : %(message)s',
                                    filemode='w' )

    root = tk.Tk()
    app = App(root)
    ani = an.FuncAnimation(f, app.animate,  interval=50, repeat=False) #mod

    root.protocol("WM_DELETE_WINDOW", app.on_closing)



    root.mainloop()
