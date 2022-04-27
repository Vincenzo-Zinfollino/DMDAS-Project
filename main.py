from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from asyncore import read
from base64 import encode
import csv
from distutils.log import error
import math
from multiprocessing.connection import wait
from multiprocessing.sharedctypes import Value
from pickle import NONE
from queue import Empty
from re import S
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


settings = {
    "COMPORT": "COM6",
    "RNOMINAL": 100,
    "BAUDRATE": 115200,
    "REFRESISTOR": 430,
    "STEP": 0,
    "WINDOWSIZE": 100,
    "TIMER": 0.5,
    "NOTCH": 60,
    "ERROR": 5,
    "TARGETTEMP": None
}

fault = {
    "80": "MAX31865_FAULT_HIGHTHRESH: 0x80",
    "40": "MAX31865_FAULT_LOWTHRESH 0x40",
    "20": "MAX31865_FAULT_REFINLOW 0x20",
    "10": "MAX31865_FAULT_REFINHIGH 0x10",
    "08": "MAX31865_FAULT_RTDINLOW 0x08",
    "04": "MAX31865_FAULT_OVUV 0x04",
}

t_time = []
downstream = []
temp = []
delay = 1
i_time = []
errors = [[], []]

f = Figure(figsize=(7.5, 5), dpi=100)
a = f.add_subplot(111)
a.set_xlabel('Time [s]')
a.set_ylabel('Temperature [°C]')


# acquire_data è il metodo utilizzato per ricevere i dati delle misure via SPI
def acquire_data(self):
    self.s_data.port = self.port
    count_err = 0  # necessario per terminare automaticamente il processo di misura se ci sono tropp errori consecutivi

    try:
        self.s_data.open()
    except:
        # se l'apertura della SPI fallisce resetta lo stato del pulsante
        app.start["state"] = "normal"
        return

    if self.s_data.isOpen():
        self.running = True  # inizia il processo di misura
        self.s_data.flush()
        self.s_data.readline()  # prima lettura della SPI (per inizializzare la comunicazione)
        self.s_data.write(
            bytes(f"S:{settings['TIMER']}:{settings['NOTCH']}\n", "ascii"))  # invia il comando di start "S:<time><notch>"
        self.s_data.flush()

    while self.running and self.s_data is not None and self.s_data.isOpen():
        try:
            reading = self.s_data.read(2)  # prova a leggere 2 byte
        except:
            break

        read = reading.hex()  # converti i caratteri in valori hex
        val = []
        for i in range(0, len(read), 4):
            # converti da base 16 (hex) a base 10
            val.append(int(read[i:i+4], 16))

        for rtd in val:  # per ogni valore di rtd ricevuto dalla lettura
            # converti da rtd ad un valore di temperatura
            t = round(self.rtd_to_temp(rtd), 2)
            if rtd > 0:  # se non c'è stato alcun errore
                if len(temp) > 0:
                    # calcola la differenza di temperatura rispetto all'ultimo valore ricevuto
                    dif = abs(t-temp[-1])
                count_err = 0  # azzera il numero di errori consecutivi
                # inserisci la misura appena effettuata all'interno della lista di temperature
                temp.append(t)
                # aggiungi alla lista degli istanti di campionamento l'istante corrente
                i_time.append(float(self.instant))
                if len(temp) > 1:  # se più di un campione è stato raccolto
                    # se è stata impostata una temperatura target e la temperatura corrente l'ha superata
                    if (settings["TARGETTEMP"] is not None) and (t >= settings["TARGETTEMP"]) and (temp[-2] < settings["TARGETTEMP"]):
                        t_time.append([self.instant])
                        # cambia il colore appena supera la soglia
                        app.track_temp_label["bg"] = "#00AC69"
                    elif settings["TARGETTEMP"] is not None and t < settings["TARGETTEMP"] and temp[-2] >= settings["TARGETTEMP"]:
                        # se la temperatura target è stat impostata e la temperatura corrente è al disotto di essa dopo averla superata in precedenza
                        t_time[-1] += [
                            self.instant, self.instant-t_time[-1][0]]
                        # cambia il colore appena supera la soglia
                        app.track_temp_label["bg"] = "#D02C2F"
                elif settings["TARGETTEMP"] is not None and t >= settings["TARGETTEMP"]:
                    # nel caso in cui la temperatura sia al di sopra della soglia impostata fin dall'inizio del processo di misura
                    t_time.append([self.instant])
                if len(temp) > 1 and (dif > 40):  # rileva gli sbalzi di temperatura
                    errors[0].append(temp[-1])
                    errors[1].append(self.instant)
                    logging.warning(
                        f"Salto di temperatura di :{round(dif,2)}° all istante {self.instant}")
                # incrementa l'istante di campionamento e passa al successivo
                self.instant = self.instant + settings["TIMER"]
            else:
                # se un errore è rilevato
                count_err += 1
                self.fault_aq()  # richiedi i codici d'errore
                if len(temp) > 0:
                    # mantieni la l'ultimo valore corretto per evitare "buchi" nei dati
                    temp.append(temp[-1])
                    i_time.append(float(self.instant))
                    errors[0].append(temp[-1])
                    errors[1].append(self.instant)
                    self.instant = self.instant + settings["TIMER"]
                # se il limite di errori consecutivi è stato raggiunto
                if count_err == settings["ERROR"]:
                    # mostra un messaggio d'errore
                    if self.running:
                        if (messagebox.askokcancel("ERRORE", "Sono stati rilevati un numero elevato di errori.\nLe misure potrebbero non essere attendibili.\nVuoi terminare ?")):
                            app.stop_command()  # interrompi il processo di misura
                            self.stop()  # ferma il thread
                        else:
                            return

# reset_offset azzera l'offset memorizzato nella EEPROM di Arduino


def reset_offset(self):
    self.end = False
    self.s_data.port = self.port
    self.s_data.open()  # apri la porta seriale

    if self.s_data.isOpen():  # se la porta seriale è aperta
        self.s_data.flush()
        self.s_data.readline()  # inizializza la comunicazione SPI
        # tramsette il comando `R` per resettare l'offset
        self.s_data.write(bytes("R\n", "ascii"))
        self.s_data.read(size=0)
        self.s_data.flush()

# calibrate richiede 10 campioni dal sensore PT100 e dal sensore LM35 per effettuare la correzione dell'errore dell'offset
# assumendo che i valori letti dall PT100 siano valori di riferimento (e quindi corretti)


def calibrate(self):
    self.end = False
    self.s_data.port = self.port
    self.s_data.open()  # apri la porta seriale

    if self.s_data.isOpen():
        self.s_data.flush()
        self.s_data.readline()  # inizializza la comunicazione SPI
        # trasmetti il comando `C` per iniziare la calibrazione
        self.s_data.write(bytes("C\n", "ascii"))
        self.s_data.flush()
        # converti i primi 10 valori ricevuti in valori esadecimali
        readingPt100 = self.s_data.readline().hex()
        # converti gli ultimi 10 valori ricevuti in valori esadecimali
        readingLM35 = self.s_data.readline().hex()
        self.valPt100 = []
        self.valLM35 = []

        for i in range(0, len(readingPt100)-4, 4):
            # converti da esadecimale a decimale
            self.valPt100.append(int(readingPt100[i:i+4], 16))
            self.valLM35.append(int(readingLM35[i:i+4], 16))

        # converti i valori ricevuti dalla pt100 in temperature
        self.valPt100 = [
            round(x, 2) for x in map(self.rtd_to_temp, self.valPt100)]
        # converti i valori ricevuti da LM35 in temperature
        self.valLM35 = [round(((x*5)/1024)*100, 2) for x in self.valLM35]
        # calcola l'errore di offset
        error = [x-y for x, y in zip(self.valPt100, self.valLM35)]
        self.offset = np.average(error)  # calcola la media
        # converti l'offset in un valore nel range di LM35
        self.offset = (self.offset/500)*1024
        datasend = f"O:{round(self.offset,2)}\n"
        self.s_data.write(bytes(datasend, "ascii"))  # trasmetti il dato
        # da inserire dopo ogni scrittura sulla seriale altrimenti Arduino Soffoca
        self.s_data.read(size=0)
        self.s_data.write(bytes("T\n", "ascii"))  # termina la comunicazione
        # ??
        self.s_data.read(size=0)


# la classe measure estende Thread e permette di utilizzare il multithreading per effettuare le misure
class measure(threading.Thread):
    def __init__(self, port, baudrate, method, *args, **kwargs):
        # invoca il costruttore della superclasse
        super(measure, self).__init__(*args, **kwargs)
        self.instant = 0  # istante iniziale posto a 0
        self._stop_event = threading.Event()  # definisci l'evento di arresto del thread
        self.port = port  # definisci la porta da utilizzare per le comunicazioni
        print("COM port init", self.port)
        self.baudrate = baudrate  # definisci il baudrate da usare
        self.running = False
        # definisci la porta seriale
        self.s_data = sr.Serial(baudrate=self.baudrate)
        self.method = method  # definisci il metodo di cui il thread si occuperà
        self.valPt100 = []  # valori della pt100 per la calibazione
        self.valLM35 = []  # valori di LM35 per la calibazione
        self.end = None
        self.offset = None

    # rtd_to_temp converte i valori di resistenza in valori di temperatura
    def rtd_to_temp(self, rtd: int):
        # definizioni delle costanti
        A = 3.9083e-3
        B = -5.775e-7
        # converte l'encoding binario dell'adc in un valore di resistenza
        Rt = ((rtd/32768)*settings["REFRESISTOR"])
        temp = (
            math.sqrt(
                ((A*A)-(4*B)) +
                ((4*B)/settings["RNOMINAL"])*Rt)
            - A)/(2*B)  # calcolo della temperatura
        if (temp >= 0):
            return temp

        # la funzione di conversione in temperatura è definita a tratti e varia se la temperatura è negativa
        Rt = (Rt/settings["RNOMINAL"])*100
        temp = -242.02 + 2.2228*Rt
        + 2.5859e-3*(math.pow(Rt, 2))
        - 4.8260e-6*(math.pow(Rt, 3))
        - 2.8183e-8*(math.pow(Rt, 4))
        + 1.5243e-10*(math.pow(Rt, 5))
        return temp

    def fault_aq(self):
        if self.s_data.isOpen():
            self.s_data.flush()
            # trasmetti il comando `F` per ricevere i codici di fault
            self.s_data.write(bytes("F\n", "ascii"))
            self.s_data.flush()
            read = ""

            while not (read == "00"):  # il carattere "00" indica la fine della trasmissione
                try:
                    reading = self.s_data.read(1)  # leggi un byte
                    read = reading.hex()  # converti in hex
                    if read != "00":
                        # converti in decimale e memorizza l'errore
                        logging.error(fault[read])
                # inseriamo i fault
                except:
                    return

    # run esegue il metodo assegnato al thread al momento della sua definizione
    def run(self):
        self.method(self)

    # stop termina il processo di misurazione
    def stop(self):
        if (self.s_data.isOpen()):
            # trasmetti il comando `T` di terminazione
            self.s_data.write(b"T\n")
            self.s_data.close()

        self.running = False
        return self.running


# App è la classe che modella l'applicativo e la sua interfaccia grafica
class App:
    def __init__(self, root):
        self.saveData_w = None
        self.is_running = False
        self.measT = None
        self.filepath = ''
        self.avg = None
        self.std = None
        # imposta il titolo
        root.title("Progetto DMDAS")
        # imposta la dimensione della finestra
        width = 1200
        height = 800
        screenwidth = root.winfo_screenwidth()
        screenheight = root.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height,
                                    (screenwidth - width) / 2, (screenheight - height) / 2)
        root.geometry(alignstr)
        root.resizable(width=False, height=False)
        root.option_add('Roboto', '12')
        # menu
        self.menubar = tk.Menu(root)

        # ---------File Menu---------
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

        # left side -------------
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
        # END left side ------

    def start_command(self):
        print("Start")
        self.start["state"] = "disable"

        # dichiarazione thread
        print("start port :", settings["COMPORT"])
        # definisci il thread
        self.measT = measure(
            settings["COMPORT"],
            settings["BAUDRATE"],
            acquire_data)
        self.measT.daemon = True  # SetDiavoletto

        if not self.measT.is_alive():
            self.measT.start()  # avvia il thread
            self.is_running = True

    # stop_command è il metodo che è assegnato al pulsante di stop

    def stop_command(self):
        print("stop")
        self.is_running = self.measT.stop()  # ferma il thread
        ani.pause()
        plt.close()

    # on_closing si avvia automaticamente alla chiusura della finestra
    def on_closing(self):
        if self.is_running:
            # se le misure sono ancora in corso avverti l'utente
            if (messagebox.askokcancel("Esci", "Le misure sono ancora in corso.\nSei Sicuro di voler terminare ?")):
                self.stop_command()
                root.destroy()
            else:
                return
        root.destroy()

    # calibrate controlla il processo di calibrazione (a livello alto: GUI e metodi dei vari pulsanti)
    def calibration(self):
        startcalibratew = ttk.Toplevel(root)

        def start_t():
            # inizializza il thread di calibrazione
            cl = measure(settings["COMPORT"], settings["BAUDRATE"], calibrate)
            cl.deamon = True
            cl.start()
            cl.join()  # attende che il thread abbia completato l'operazione
            # crea la finestra di calibrazione ed in seguito ne definisce tutti gli attributi
            calibratew = ttk.Toplevel(root)
            width = 900
            height = 450
            screenwidth = calibratew.winfo_screenwidth()
            screenheight = calibratew.winfo_screenheight()
            alignstr = '%dx%d+%d+%d' % (width, height,
                                        (screenwidth - width) / 2, (screenheight - height) / 2)
            calibratew.geometry(alignstr)
            calibratew.resizable(width=False, height=False)
            calibratew.title("Calibration Option")
            startcalibratew.destroy()
            valuelabelPT100 = []
            valuelabelLM35 = []

            # motra i valori ricevuti dalla fase di calibrazione
            for i in range(len(cl.valPt100)):
                ft = tkFont.Font(family='Roboto', size=13)
                self.label1 = ttk.Label(
                    calibratew, text="Misure del device di riferimento ", font=ft)
                self.label1.place(x=50, y=70)
                valuelabelPT100.append(tk.Label(calibratew, text='--'))
                valuelabelPT100[-1].place(
                    x=50+i*80,
                    y=105,
                    width=70,
                    height=45)
                ft = tkFont.Font(family='Roboto', size=14)
                valuelabelPT100[-1]["font"] = ft
                valuelabelPT100[-1]["fg"] = "#ffffff"
                valuelabelPT100[-1]["bg"] = "#696969"
                valuelabelPT100[-1].config(text=str(cl.valPt100[i]))

                ft = tkFont.Font(family='Roboto', size=13)
                self.label1 = ttk.Label(
                    calibratew, text="Misure del device da tarare ", font=ft)
                self.label1.place(x=50, y=190)

                valuelabelLM35.append(tk.Label(calibratew, text='--'))
                valuelabelLM35[-1].place(x=50+i*80, y=225, width=70, height=45)
                ft = tkFont.Font(family='Roboto', size=14)
                valuelabelLM35[-1]["font"] = ft
                valuelabelLM35[-1]["fg"] = "#ffffff"
                valuelabelLM35[-1]["bg"] = "#696969"
                valuelabelLM35[-1].config(text=str(cl.valLM35[i]))

            ft = tkFont.Font(family='Roboto', size=13)
            self.label1 = ttk.Label(
                calibratew, text="Il valore di Offset rilevato", font=ft)
            self.label1.place(x=335, y=300)

            self.temp_label = tk.Label(
                calibratew, text=str(round(cl.offset, 2)))
            self.temp_label.place(x=315, y=330, width=250, height=80)
            ft = tkFont.Font(family='Roboto', size=32)
            self.temp_label["font"] = ft
            self.temp_label["fg"] = "#ffffff"
            self.temp_label["bg"] = "#696969"

        # reset_c controlla il processo di reset dell'offset (a livello alto)
        def reset_c():
            cl = measure(
                settings["COMPORT"],
                settings["BAUDRATE"],
                reset_offset)
            cl.deamon = True
            cl.start()
            cl.join()  # attende che il thread abbia completato l'operazione

        if not self.is_running:
            # definisci la finestra a livello grafico
            width = 300
            height = 250
            screenwidth = startcalibratew.winfo_screenwidth()
            screenheight = startcalibratew.winfo_screenheight()
            alignstr = '%dx%d+%d+%d' % (width, height,
                                        (screenwidth - width) / 2, (screenheight - height) / 2)
            startcalibratew.title("Calibration Option")
            startcalibratew.geometry(alignstr)
            startcalibratew.resizable(width=False, height=False)
            ft = tkFont.Font(family='Roboto', size=13)
            self.label1 = ttk.Label(
                startcalibratew, text=" Start calibration ", font=ft)
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

            setz = ttk.Button(startcalibratew)
            setz["bg"] = "#d02c2f"
            ft = tkFont.Font(family='Roboto', size=10)
            setz["font"] = ft
            setz["fg"] = "#ffffff"
            setz["justify"] = "center"
            setz["text"] = "RESET"
            setz["borderwidth"] = 0
            setz.place(x=25, y=190, width=70, height=25)
            setz["command"] = reset_c
        else:
            messagebox.showerror(
                "Esci", "Le misure sono ancora in corso.\nPuoi effettuare il proceso di calibrazione solo prima d'iniziare il processo di misurazione")

    #
    def m_open(self):
        print("open")
        filename = askopenfilename()

    def m_saveData(self):
        print('Save Data')
        # --- definizione del metodo di salvataggio --- #

        def save():
            if len(temp) > 1:
                self.filepath = tk.filedialog.askdirectory()
                FilePosition = self.filepath + '/' + self.filename.get()
                with open(FilePosition, 'w', newline='', encoding='UTF8') as csv_file:
                    write = csv.writer(csv_file)
                    write.writerow(["Time", "Temperature"])
                    for i in range(len(temp)):
                        row = [str(i_time[i]), str(temp[i])]
                        print(row)
                        write.writerow(row)

                if(settings["TARGETTEMP"] is not None):
                    SidecarFilePosition = self.filepath + '/' + \
                        "TIME_INTERVAL" + self.filename.get()
                    with open(SidecarFilePosition, 'w', newline='', encoding='UTF8') as csv_file:
                        write = csv.writer(csv_file)
                        write.writerow(
                            ["Temperature", "Rising", "Falling", " Interval"])
                        for i in range(len(t_time)):
                            row = [settings["TARGETTEMP"], t_time]
                            print(row)
                            write.writerow(row)
            else:
                messagebox.showinfo("Impossibile salvare i dati ",
                                    " Impossibile salvare i dati, non sono stati trovati dati oppure \n il processo di misura potrebbe non essere stato avviato. ")
        # --- dine della definizione del metodo di salvataggio --- #

            saveData_w.destroy()
            print(self.filepath)

        filepath = ''
        # --- Window Declaring
        saveData_w = ttk.Toplevel(root)
        width = 320
        height = 200
        screenwidth = saveData_w.winfo_screenwidth()
        screenheight = saveData_w.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height,
                                    (screenwidth - width) / 2, (screenheight - height) / 2)
        saveData_w.geometry(alignstr)
        saveData_w.resizable(width=False, height=False)
        saveData_w.title("File Option")
        # --- END  Window Declaring

        ft = tkFont.Font(family='Roboto', size=10)
        self.label1 = ttk.Label(
            saveData_w, text="Scegli il nome del file ", font=ft)
        self.label1.place(x=15, y=20)

        self.s_filename = 'TEMPMEAS'+str(datetime.timestamp(datetime.now()))

        self.filename = tk.Entry(saveData_w, textvariable=self.s_filename)
        self.filename.insert(0, self.s_filename + '.csv')
        self.filename.place(x=30, y=50, width=250, height=20)
        print(self.s_filename)

        if ((len(t_time) > 0) and (settings["TARGETTEMP"] is not None)):

            ft = tkFont.Font(family='Roboto', size=10)
            self.label1 = ttk.Label(
                saveData_w, text=" Il traking della temperatura è attivo,\n sarà creato un file sidecar contenente tutti i dati ", font=ft)
            self.label1.place(x=30, y=80)

        self.save_b = ttk.Button(saveData_w)
        self.save_b.place(x=125, y=150, width=70, height=35)

        self.save_b["bg"] = "#00ac69"
        ft = tkFont.Font(family='Roboto', size=12)
        self.save_b["font"] = ft
        self.save_b["fg"] = "#ffffff"
        self.save_b["justify"] = "center"
        self.save_b["text"] = 'SAVE'
        self.save_b["borderwidth"] = 0
        self.save_b["command"] = save

    # stat calcola e mostra nella GUI i valori di media e deviazione standard
    def stat(self):
        obsv = 10
        if len(temp) > 1 and len(temp) < settings["WINDOWSIZE"]:
            self.avg = np.average(temp)
            self.std = np.std(temp)
        # Calcolo della media nella obsv. window pari a 10 samples
        elif len(temp) >= settings["WINDOWSIZE"]:
            self.avg = np.average(temp[-(settings["WINDOWSIZE"]+1):-1])
            self.std = np.std(temp[-(settings["WINDOWSIZE"]+1):-1])

        if self.avg is not None and self.std is not None:
            self.avg_label.config(text=round(self.avg, 2)+"°C")
            self.std_label.config(text=round(self.std, 2)+"°C")

    # m_serial seleziona la porta seriale corretta da usare per le comunicazioni

    def m_serial(self):
        self.comboP = None
        # --- definizione del metodo di selezione della seriale --- #

        def selectser():
            # effettuiamo il salvataggio su un file
            porttest = self.comboP.get()
            if not self.is_running:
                # se non è stato selezionato alcun vaore appare un messaggio di errore.
                if porttest == "Scegli un valore":
                    messagebox.showinfo(
                        "Impossibile salvare la preferenza:", " Selezionare una porta valida")
                else:
                    psel = porttest.split(" ")
                    # poichè potrebbe non essere COM3 ma avere più digit divido la stringa
                    # secondo gli spazi e prendo e dalla lista creata prendo il primo elemento che rappresenta il nominativo della porta
                    settings["COMPORT"] = psel[0]  # modificato
                    print(settings["COMPORT"])
                    serial_w.destroy()
            else:
                messagebox.showinfo(
                    "Impossibile modificare la porta:", " Il processo di misurazione è in corso")
        # --- fine della definizione del metodo di selezione --- #

        portlist = list(sr_list.comports())
        for p in portlist:
            print(p)
        serial_w = ttk.Toplevel(root)

        width = 400
        height = 200
        screenwidth = serial_w.winfo_screenwidth()
        screenheight = serial_w.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height,
                                    (screenwidth - width) / 2, (screenheight - height) / 2)
        serial_w.geometry(alignstr)
        serial_w.resizable(width=False, height=False)
        serial_w.resizable(width=False, height=False)
        serial_w.title("Serial Option")

        self.label1 = ttk.Label(
            serial_w, text="Scegli la porta di comunicazione:")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label1["font"] = ft
        self.label1.place(x=40, y=25)

        # dichiaro la combo box per selezionare la porta seriale
        self.comboP = TTK.Combobox(serial_w, values=portlist, state="readonly")
        self.comboP.set("Scegli un valore")

        self.comboP.place(x=40, y=50, width=280, height=35)  # x=60

        self.saveser_b = ttk.Button(serial_w)
        self.saveser_b.place(x=160, y=120, width=70, height=35)

        self.saveser_b["bg"] = "#00ac69"
        ft = tkFont.Font(family='Roboto', size=12)
        self.saveser_b["font"] = ft
        self.saveser_b["fg"] = "#ffffff"
        self.saveser_b["justify"] = "center"
        self.saveser_b["text"] = 'SAVE'
        self.saveser_b["borderwidth"] = 0
        self.saveser_b["command"] = selectser

    # m_settings permette di definire tutte le impostazioni relative al processo di misura

    def m_settings(self):
        selvar = tk.IntVar()
        if settings["TARGETTEMP"] != None:
            selvar.set(1)

        # --- definizione del metodo di selezione delle impostazioni --- #
        def selectset():
            if not self.is_running:
                var = self.t_Slider.get()
                settings["TIMER"] = var
                settings["NOTCH"] = self.comboN.get()[0:2]

                if selvar.get() == 1:
                    settings["TARGETTEMP"] = self.temp_Slider.get()
                    self.track_temp_label.config(text=settings["TARGETTEMP"])
                    if settings["TARGETTEMP"] >= 0:
                        self.track_temp_label["bg"] = "#F89625"
                    else:
                        self.track_temp_label["bg"] = "#648DE5"
                else:
                    settings["TARGETTEMP"] = None
                    self.track_temp_label.config(text="--")
                    self.track_temp_label["bg"] = "#696969"

                # cambia il colore del riquadro della temperatura monitorata
                print(settings["TARGETTEMP"])
                settingsw.destroy()
            else:
                messagebox.showinfo(
                    "Impossibile modificare le impostazioni:", " Il processo di misurazione è in corso")
        # --- fine della definizione del metodo di selezione --- #

        # --- definizione del metodo di controllo --- #
        # verifica che il controllo della temperatura target sia attivato prima di permettere
        # la modifica della temperatura target
        def check():
            if selvar.get() == 1:
                self.temp_Slider.configure(state="normal")
            else:
                self.temp_Slider.configure(state="disabled")
        # --- fine della definizione del metodo di controllo --- #
        # !! TODO da inserire la condizione per impossibilitare la modifica durante la misurazione
        settingsw = ttk.Toplevel(root)
        width = 320
        height = 425
        screenwidth = settingsw.winfo_screenwidth()
        screenheight = settingsw.winfo_screenheight()
        alignstr = '%dx%d+%d+%d' % (width, height,
                                    (screenwidth - width) / 2, (screenheight - height) / 2)
        settingsw.geometry(alignstr)
        settingsw.resizable(width=False, height=False)
        settingsw.title("Settings Option")

        self.label1 = ttk.Label(
            settingsw, text="Scegli l'intervallo di tempo tra due campioni:")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label1["font"] = ft
        self.label1.place(x=40, y=30)

        # dichiaro lo slider del intervallo di campionamento
        ft = tkFont.Font(family='Roboto', size=8)
        self.t_Slider = tk.Scale(
            settingsw,
            from_=0.1, to=4.0,
            digits=2,
            resolution=0.1,
            orient="horizontal",
            font=ft)
        self.t_Slider.set(1.0)
        self.t_Slider.place(x=40, y=50, width=250)

        self.label2 = ttk.Label(
            settingsw, text="Scegli la frequenza del Notch :")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label2["font"] = ft
        self.label2.place(x=40, y=105)

        # selezione del notch
        notch = ["50 Hz", "60 Hz"]
        self.comboN = TTK.Combobox(settingsw, values=notch, state="readonly")
        self.comboN.set("Scegli un valore")
        self.comboN.place(x=40, y=135, width=200, height=32)

        # dichiaro lo slider della selezione temperatura
        self.select_tempSlider = tk.Checkbutton(
            settingsw, text='Abilita monitoraggio della temperatura', variable=selvar, command=check)
        self.select_tempSlider.place(x=40, y=185)
        self.label2 = ttk.Label(
            settingsw, text="Scegli la temperatura da monitorare [ °C ] :")
        ft = tkFont.Font(family='Roboto', size=10)
        self.label2["font"] = ft
        self.label2.place(x=40, y=225)
        ft = tkFont.Font(family='Roboto', size=8)
        self.temp_Slider = tk.Scale(settingsw, from_=-100.0, to=250.0, digits=4,
                                    resolution=0.5, orient="horizontal", font=ft, state="disabled")
        self.temp_Slider.set(20.0)
        self.temp_Slider.place(x=40, y=250, width=250)

        self.saveset_b = ttk.Button(settingsw)

        self.saveset_b["bg"] = "#00ac69"
        ft = tkFont.Font(family='Roboto', size=12)
        self.saveset_b["font"] = ft
        self.saveset_b["fg"] = "#ffffff"
        self.saveset_b["justify"] = "center"
        self.saveset_b["text"] = 'SAVE'
        self.saveset_b["borderwidth"] = 0
        self.saveset_b["command"] = selectset

        self.saveset_b.place(x=128, y=360, width=70, height=35)

    # animate mostra in tempo reale i dati ricevuti dai sensori su un grafico
    def animate(self, k):
        if self.is_running:
            if len(temp) > 0:
                dat = str(temp[-1])+"°"  # mostra la temperatura corrente
                self.temp_label.config(text=dat)

            self.stat()
            a.autoscale(enable=True, axis='both', tight=None)
            a.clear()
            a.set_xlabel('Time [s]')  # label sugli assi cartesiani
            a.set_ylabel('Temperature [°C]')

            if len(temp) > 0:
                # mostra gli errori come x rosse
                a.plot(i_time, temp, errors[1], errors[0], "rx")
                if(settings["TARGETTEMP"]):
                    a.plot(
                        [0, i_time[-1]],
                        [settings["TARGETTEMP"], settings["TARGETTEMP"]],
                        "r-")  # mostra la temperatura target come una linea rossa

            if len(temp) > 0:
                # imposta i valori presenti sull'asse y
                yticks(np.arange(min(temp), max(temp), step=0.31))


if __name__ == "__main__":
    logging.basicConfig(filename="ErrorLOG.log",
                        format='%(asctime)s - %(levelname)s : %(message)s',
                        filemode='w')
    root = tk.Tk()
    app = App(root)
    ani = an.FuncAnimation(f, app.animate,  interval=50, repeat=False)  # mod
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
