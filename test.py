import math
settings = {"REFRESISTOR": 430, "RNOMINAL": 100}


def rtd_to_temp(rtd):

    A = 3.9083e-3
    B = -5.775e-7
    Rt = ((rtd/32768)*settings["REFRESISTOR"])

    temp = (math.sqrt(((A*A)-(4*B)) +
            ((4*B)/settings["RNOMINAL"])*Rt) - A)/(2*B)
    if (temp >= 0):
        return temp

    Rt = (Rt/settings["RNOMINAL"])*100

    temp = -242.02 + 2.2228*Rt
    + 2.5859e-3*(math.pow(Rt, 2))
    - 4.8260e-6*(math.pow(Rt, 3))
    - 2.8183e-8*(math.pow(Rt, 4))
    + 1.5243e-10*(math.pow(Rt, 5))

    return temp


for i in range(12000, 13000):
    print(f'{i}:{rtd_to_temp(i)}')
