import time

import serial as sr
import time as t

class Arduino:
    def __init__( port, baudrate):

        s_data=sr.Serial(port,baudrate,timeout=0)
        for i in range(10):
            print(s_data.readline())
            time.sleep(2)