  /*************************************************** 
  This is a library for the Adafruit PT100/P1000 RTD Sensor w/MAX31865

  Designed specifically to work with the Adafruit RTD Sensor
  ----> https://www.adafruit.com/products/3328

  This sensor uses SPI to communicate, 4 pins are required to  
  interface
  Adafruit invests time and resources providing this open source code, 
  please support Adafruit and open-source hardware by purchasing 
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit Industries.  
  BSD license, all text above must be included in any redistribution
 ****************************************************/

#include <Adafruit_MAX31865.h>
#include <SPI.h>

// Use software SPI: CS, DI, DO, CLK
Adafruit_MAX31865 thermo = Adafruit_MAX31865( 10, 11, 12, 13);
// use hardware SPI, just pass in the CS pin
//Adafruit_MAX31865 thermo = Adafruit_MAX31865(10);

// The value of the Rref resistor. Use 430.0 for PT100 and 4300.0 for PT1000
#define RREF      430.0
// The 'nominal' 0-degrees-C resistance of the sensor
// 100.0 for PT100, 1000.0 for PT1000
#define RNOMINAL  100.0
 int ind=0;
 const byte drdyPin=2;
 const byte chipSelectPin=10;

 
 byte reg1,reg2;
 uint16_t fullreg;



 byte h=0xC2;
 byte l=0xF7;
 
 bool drdy=false;
 int index=0;
       
void setup() {
  
  Serial.begin(115200);
  thermo.begin(MAX31865_3WIRE);  // set to 2WIRE or 4WIRE as necessary
  
   // Adafruit MAX31865 PT100 SENSOR;
  
   uint16_t rtd = thermo.readRTD();
   pinMode(drdyPin, INPUT);
   attachInterrupt(digitalPinToInterrupt(drdyPin), IntReady, FALLING);// dopo aver effettuato la prima lettura il pin DRDY va a basso quando è disponibile un nuovo dato, questo sistema funge dopo la prima lettura 

   setCounterStartValue(1);  
   setupTimer();
  
   
 

}


void loop() {
   
   //uint16_t rtd = thermo.readRTD();

   //Serial.print ("il valore della libreria RTD :");
   //Serial.println (rtd);
   //Serial.println();
   //readRegister();
    //uint16_t mamt=0xC2F7;
    //Serial.print(*(&mamt));
    
 // delay(1000);
  }

void IntReady(){
  drdy=true;
}

void setupTimer(){
  
  TIMSK1 &= ~(1<<TOIE1);  //disabilita l'interrupt del contatore 1
  TCCR1A &= ~((1<<WGM11) | (1<<WGM10));  // imposta la modalità del timer come contatore (funzione Normale )
  TCCR1B &= ~((1<<WGM12) | (1<<WGM13));  // imposta la modalità del timer come contatore (funzione Normale )
  TIMSK1 &= ~(1<<OCIE1A);  // abilita l'interrupt del contatore (solo se l'interrupt flag globale (I_flag) è settato a true )
  TCCR1B |= (1<<CS12)  | (1<<CS10); // set dei bit del prescaler a 1 0 1  CS12=1 CS10=1 
  TCCR1B &= ~(1<<CS11);             // set dei bit del prescaler a 1 0 1  CS11=0
  TCNT1H = h;  // set up parte alta del registro del punto di partenza del contatore
  TCNT1L = l; // set up parte bassa del registro del punto di partenza del contatore
  TIMSK1 |= (1<<TOIE1);  // riabilita l'interrupt del contatore 1
    
}




    ISR(TIMER1_OVF_vect) {  
      
      interrupts();
      
      TCNT1H = h;  
      TCNT1L = l;
      //uint16_t rtd = thermo.readRTD();
      //uint16_t rtd=readRegister();
       //Serial.println (rtd);
      if (drdy){
        drdy=false;
        Serial.print (index);
        Serial.print (":");
       //uint16_t rtd = thermo.readRTD();
       uint16_t rtd=readRegister();
       Serial.println (rtd);
       //Serial.println();
       index++;
      }
    
    } 


 //timeperiod è da considerarsi in secondi ricordati che il valore massimo possibile è 4 secondi 
 
  void setCounterStartValue(unsigned int timePeriod){ 

      int n=(timePeriod*15625);
     
      uint16_t fullvalue=(65536-n);
     
      h=fullvalue>>8;
      l=fullvalue&0xFF;
    
    
    
    }
  



uint16_t  readRegister()
{
    SPI.beginTransaction(SPISettings(500000, MSBFIRST, SPI_MODE1));
    digitalWrite(chipSelectPin, LOW); // * Chip Select CS: a LOW quando c'è comunicazione (attiva il clock), altrimenti HIGH

    SPI.transfer(0x80); //80h = 128 - config register // *-> questa è l'istruzione che indica che configuriamo il registro
    SPI.transfer(0xB0); //B0h = 176 - 101100000.// *: |Bias ON|Conversion normally off|1 shot|3 wire|Fault|Fault|Fault Status clear|60Hz| vedi pagina 13
    digitalWrite(chipSelectPin, HIGH);

    digitalWrite(chipSelectPin, LOW);
    SPI.transfer(1);           // !! Registro da leggere 
    reg1 = SPI.transfer(0xFF); // !! leggi MSB
    
    reg2 = SPI.transfer(0xFF); // !! leggi LSB
    
    digitalWrite(chipSelectPin, HIGH);
   

    
    // * dato che i registri sono a 8 bit e che il numero è un intero a 16 bit, l'unico modo per memorizzare l'intero dato
    // * è dividerlo in 2 registri, quando i registri sono letti bisogna concatenarli
    fullreg = reg1;       //read MSB // * prende la prima parte del numero a 16 bit
    fullreg <<= 8;        //Shift to the MSB part // * lo sposta all'inizio del numero (per lasciare spazio a LSB)
    fullreg |= reg2;      //read LSB and combine it with MSB // * concatena MSB con LSB
    fullreg >>= 1;        //Shift D0 out. // !! L'adc è a 15 bit, quindi uno dei bit è in realtà inutilizzato
    //rtdSPI= fullreg; //pass the value to the resistance variable
    //note: this is not yet the resistance of the RTD!

    digitalWrite(chipSelectPin, LOW);

    SPI.transfer(0x80);                //80h = 128 // * di nuovo la configurazione
    SPI.transfer(144);                 //144 = 10010000 // * |Bias on|Conversion auto|not 1 shot|3 wire|Fault|Fault|Fault Status clear|60Hz| vedi pagina 13
    SPI.endTransaction();              // * fine
    digitalWrite(chipSelectPin, HIGH); //* stoppa il SCLK

    //* roba di lettura
   
   return fullreg;
}
