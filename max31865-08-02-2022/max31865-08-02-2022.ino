
#include <Adafruit_MAX31865.h>
#include <SPI.h>
#include "CircularBuffer.h"

// Use software SPI: CS, DI, DO, CLK
//CS => CS //Arduino 10
//MISO => SDO //Arduino 12
//MOSI => SDI //Arduino 11
//SCK => SCK //Arduino 13

Adafruit_MAX31865 thermo = Adafruit_MAX31865( 10, 11, 12, 13);
// use hardware SPI, just pass in the CS pin
//Adafruit_MAX31865 thermo = Adafruit_MAX31865(10);

// The value of the Rref resistor. Use 430.0 for PT100 and 4300.0 for PT1000
#define RREF      430.0
// The 'nominal' 0-degrees-C resistance of the sensor
// 100.0 for PT100, 1000.0 for PT1000
#define RNOMINAL  100.0


#define HIGH_THRESH 0x80
#define LOW_THRESH 0x40
#define REF_IN_LOW 0x20
#define REF_IN_HIGH 0x10
#define RTD_IN_LOW 0x08
#define OVUV 0x04


int ftest=0 ;// da rimuovere

int ind = 0;
const byte drdyPin = 2;
const byte chipSelectPin = 10;

CircularBuffer <uint16_t> cb = CircularBuffer <uint16_t>(32);
CircularBuffer <byte> eb = CircularBuffer <byte>(5);

byte reg1, reg2;
uint16_t fullreg;
byte notch = 0;

int cont = 0; // da eliminare only  for debugging purpose

byte h = 0xC2;
byte l = 0xF7;

bool drdy = false;


void setup() {


  Serial.begin(115200);

  // Adafruit MAX31865 PT100 SENSOR;
  thermo.begin(MAX31865_3WIRE);  // set to 2WIRE or 4WIRE as necessary


  Serial.println();
  //Serial.flush();
  pinMode(drdyPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(drdyPin), IntReady, FALLING);// dopo aver effettuato la prima lettura il pin DRDY va a basso quando è disponibile un nuovo dato, questo sistema funge dopo la prima lettura




}




void loop() {

 sendData(); //  serve a inviare i valori di RTD a Python
  //Serial.println("loop");




}

void IntReady() {
  drdy = true;
}

//la massima frequenza di campionamento 15S/s
void setupTimer() {

  TIMSK1 &= ~(1 << TOIE1); //disabilita l'interrupt del contatore 1
  TCCR1A &= ~((1 << WGM11) | (1 << WGM10)); // imposta la modalità del timer come contatore (funzione Normale )
  TCCR1B &= ~((1 << WGM12) | (1 << WGM13)); // imposta la modalità del timer come contatore (funzione Normale )
  TIMSK1 &= ~(1 << OCIE1A); // abilita l'interrupt del contatore (solo se l'interrupt flag globale (I_flag) è settato a true )
  TCCR1B |= (1 << CS12)  | (1 << CS10); // set dei bit del prescaler a 1 0 1  CS12=1 CS10=1
  TCCR1B &= ~(1 << CS11);           // set dei bit del prescaler a 1 0 1  CS11=0
  TCNT1H = h;  // set up parte alta del registro del punto di partenza del contatore
  TCNT1L = l; // set up parte bassa del registro del punto di partenza del contatore
  TIMSK1 |= (1 << TOIE1); // riabilita l'interrupt del contatore 1

}



// interrupt contatore/timer metodo
ISR(TIMER1_OVF_vect) {

  interrupts();

  TCNT1H = h;
  TCNT1L = l;

  if (drdy) {

    drdy = false;
    uint16_t rtd = readRegister(); //mod
    
    bool faultdet=checkFault();
    
    if ( !faultdet) {
      //uint16_t rtd = readRegister();
      //Serial.println (rtd);
      cb.push(rtd);
    }
    else {
      cb.push(0);
    

    }


  }

}

//timeperiod è da considerarsi in secondi ricordati che il valore massimo possibile è 4 secondi il minimo 0.000064s (1/15625) cioè il valore del clock diviso il prescaler factor  16MHz/1024 = 15,625KZ
void setCounterStartValue( float timePeriod) {


  float  n = (timePeriod * 15625);
  int i = (int) n;
  uint16_t fullvalue = (65536 - i);

  h = fullvalue >> 8;
  l = fullvalue & 0xFF;

}




uint16_t  readRegister()
{

  SPI.beginTransaction(SPISettings(500000, MSBFIRST, SPI_MODE1));
  digitalWrite(chipSelectPin, LOW); // * Chip Select CS: a LOW quando c'è comunicazione (attiva il clock), altrimenti HIGH

  SPI.transfer(0x80); //80h = 128 - config register // *-> questa è l'istruzione che indica che configuriamo il registro
  //SPI.transfer((0xB2) + notch); //B0h = 176 - 10110000.// *: |Bias ON|Conversion normally off|1 shot|3 wire|Fault|Fault|Fault Status clear|60Hz| vedi pagina 13 (prima era B0 per attivare l'autoclear abbiamo settato il bit di riferimento)
  SPI.transfer((0xB0) + notch);
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
  //SPI.transfer((0x92) + notch);  //144 = 10010000 // * |Bias on|Conversion auto|not 1 shot|3 wire|Fault|Fault|Fault Status clear|60Hz| vedi pagina 13 (prima era 144 per attivaqre l'autoclear del fault abbiamo settato il bit)

  SPI.transfer((144) + notch); // da modificare il valore con 0x90
  
  SPI.endTransaction();              // * fine
  digitalWrite(chipSelectPin, HIGH); //* stoppa il SCLK

  //* roba di lettura

  return fullreg;
}


void sendData() {


  if (!cb.available())  return; // se il buffer è vuoto esce dal metodo
  uint16_t dat = 0;
  uint8_t msb, lsb = 0;


  int sz = cb.size(); // restituisce il numero di elementi presenti nel buffer
  uint16_t *pointer = cb.dump(); //ritorna il puntatore dei dati da inviare, cioè del primo elemento del buffer

  for (int i = 0; i < sz; i++) { // per ogni elemento da trasmettere accede ai due byte che compongono il valore di RTD

    dat = *(pointer + i); //prende il valore di RTD (a 16 bit)

    msb = dat >> 8; // insertisce in MSB la parte più significativa del valore di RTD
    lsb = dat & 0xFF; // insertisce in LSB la parte meno significativa del valore di RTD

    // poichè il metodo write invia un byte per volta è necessario suddividere il dato in due Byte
    Serial.write(msb);
    Serial.write(lsb);

    Serial.flush(); // Necessario per  ripulire il canale di comunnicazione
    //Serial.println(); //da togliere
  }


}

void sendErr() {

  if (!eb.available()) return;
  
  byte dat = 0;
  int sz = eb.size();

  byte *pointer = eb.dump();
  
  for (int i = 0; i < sz ; i++) {

    dat = *(pointer + i);

    Serial.write(dat);
    Serial.flush();

  }
  Serial.write(0); // modificato necessario per terminare da phyton l acquisizione degli errori
  Serial.flush();
}


void serialEvent() {

  char *pointer;
  String msg;
  int len;


  msg = Serial.readString();


  // !!!! WARNING : ricorda che quando dichiari una variabile all interno di uno switch case vanno inserire le parentesi attorno al case altrimenti non prosegue
  switch (msg[0]) {

    case 'S': {
        //  inizializziamo  il timer e facciamo la prima richiesta

        int i = 0;
        float t;
        char *pointer;

        len = msg.length();
        char ch [len];
        msg.toCharArray(ch, len);
        pointer = strtok(ch, ":");
        while (pointer != NULL ) {

          switch (i) {

            case 1:
              String ts(pointer);
              t = ts.toFloat();

              break;

            case 2:
              // settare la frequenza di notch
              String freq(pointer);
              if (freq.equals("50")) {
                notch = 0x01;
              } else {
                notch = 0;
              }

              break;


          }

          i++;
          pointer = strtok(NULL, ":");
        }

        setCounterStartValue(t);
        setupTimer();
        uint16_t rtd = readRegister(); // Effettua la prima lettura necessaria all avvio del processo di misurazione
        //Serial.print("WRYYY S");

        break;
      }
    case 'R':
      // vengono inviati i dati
      Serial.print("WRYYY R");
      break;
    case 'T':

      noInterrupts();
      Serial.println("EOT");
      Serial.flush();
      Serial.end();
      break;

    case 'F':

      sendErr();

      break;


  }



  /*String msg =" " ;
    Serial.println("Hai un nuovo messaggio !");
    msg=Serial.readString();
    float t=msg.toFloat();

    if ((t >0) && (t<=4))
    {

    setCounterStartValue(t);
    setupTimer();
    Serial.println("Hai cambiato il tempo di campionamento");
    Serial.println(t);

    }*/



}


bool checkFault() {

      byte err, conf ;
   //Serial.println ("vediamo se ci sono degli errori ");
  
    // Leggere il registro di fault status 0x07 controllare se il bit (D1) è a 1(allora si è verificato un FAULT) c'è leggiamo i rimanenti bit per valutare il tipo di fault 
    // settiamo a 1 il bit del configuration register per pulire il Fault Status Register
   SPI.beginTransaction(SPISettings(500000, MSBFIRST, SPI_MODE1));
  
  
  digitalWrite(chipSelectPin, LOW); // * Chip Select CS: a LOW quand 
  SPI.transfer(0x07);
  err=SPI.transfer(0x00);
  digitalWrite(chipSelectPin, HIGH);

  
  digitalWrite(chipSelectPin, LOW);
  SPI.transfer(0x00);
  conf=SPI.transfer(0x00);
  digitalWrite(chipSelectPin, HIGH);

  
  conf |= 0x02; // Dovrebbe? modificare solo il Auto Clear flag 


  digitalWrite(chipSelectPin, LOW);
  SPI.transfer(0x80);
  SPI.transfer(conf);

  SPI.endTransaction(); 
  digitalWrite(chipSelectPin, HIGH);

  
   if (err!=0){

    eb.push(err);
    return true;
    
   }
 
  

  return  false;
}


// WRYYY