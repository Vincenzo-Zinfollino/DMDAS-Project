
#include <Adafruit_MAX31865.h>
#include <SPI.h>
#include "CircularBuffer.h"
#include <EEPROM.h>

// Use software SPI: CS, DI, DO, CLK
// CS => CS //Arduino 10
// MISO => SDO //Arduino 12
// MOSI => SDI //Arduino 11
// SCK => SCK //Arduino 13

Adafruit_MAX31865 thermo = Adafruit_MAX31865(10, 11, 12, 13);
#define RREF 430.0
#define RNOMINAL 100.0

// definizione degli codici di fault
#define HIGH_THRESH 0x80
#define LOW_THRESH 0x40
#define REF_IN_LOW 0x20
#define REF_IN_HIGH 0x10
#define RTD_IN_LOW 0x08
#define OVUV 0x04

int ind = 0;
const byte drdyPin = 2;        // pin di dataready
const byte chipSelectPin = 10; // pin di chip selection

CircularBuffer<uint16_t> cb = CircularBuffer<uint16_t>(32); // buffer di valori
CircularBuffer<byte> eb = CircularBuffer<byte>(32);          // buffer di fault
CircularBuffer<uint16_t> dt_b= CircularBuffer<uint16_t>(32);


byte reg1, reg2; // MSB e LSB del registro RTD
uint16_t fullreg;
byte notch = 0; // valore di notch

uint16_t prevT=0;
uint16_t currT=0;

byte h = 0xC2;
byte l = 0xF7;

bool drdy = false; // bit di dataready

// Valori di setup dei registri del max31865
byte config1S = 0xB0;
byte configN1S = 0x90;

float offset;

void setup()
{
  Serial.begin(115200);
  thermo.begin(MAX31865_3WIRE); // imposta a 3Wire
  Serial.println();             // print di inizializzazione della seriale
  pinMode(drdyPin, INPUT);
  attachInterrupt(digitalPinToInterrupt(drdyPin), IntReady, FALLING); // dopo aver effettuato la prima lettura il pin DRDY va a basso quando è disponibile un nuovo dato, questo sistema funziona dopo la prima lettura
  EEPROM.get(0, offset);                                              // prendi l'offset dalla EEPROM dall'indirizzo 0
}

void loop()
{
  sendData(); //  serve a trasmettere i valori di RTD al sistema di monitoraggio (PC)
}

void IntReady()
{
  drdy = true;
}

// setupTimer effettua il setup del timer ed inizializza il valore del contatore basandosi sull'intervallo impostato dall'utente
void setupTimer()
{
  TIMSK1 &= ~(1 << TOIE1);                  // disabilita l'interrupt del contatore 1
  TCCR1A &= ~((1 << WGM11) | (1 << WGM10)); // imposta la modalità del timer come contatore (funzione Normale )
  TCCR1B &= ~((1 << WGM12) | (1 << WGM13)); // imposta la modalità del timer come contatore (funzione Normale )
  TIMSK1 &= ~(1 << OCIE1A);                 // abilita l'interrupt del contatore (solo se l'interrupt flag globale (I_flag) è settato a true )
  TCCR1B |= (1 << CS12) | (1 << CS10);      // set dei bit del prescaler a 1 0 1  CS12=1 CS10=1
  TCCR1B &= ~(1 << CS11);                   // set dei bit del prescaler a 1 0 1  CS11=0
  TCNT1H = h;                               // set up parte alta del registro del punto di partenza del contatore
  TCNT1L = l;                               // set up parte bassa del registro del punto di partenza del contatore
  TIMSK1 |= (1 << TOIE1);                   // riabilita l'interrupt del contatore 1
}

// Routine di gestione dell'interrupt del timer
ISR(TIMER1_OVF_vect)
{
  interrupts(); // permette che altri interrupt avvengano
  // resetta il valore del contatore del timer in modo che ricominci
  TCNT1H = h;
  TCNT1L = l;
  if (drdy)
  {
    uint16_t rtd = readRegister(); // leggi il valore di rtd dal registro
    if(prevT>0){

      dt_b.push(currT-prevT); // memorizza nell'apposito buffer l'intervallo di tempo trascorso dall' ultimo campionamento 
     
      }else{
          dt_b.push(0); // inserisce l'istante di tempo della prima misura 
        }
    prevT=currT; // sostituisce l'istante  precedente con il successivo per effettuare la nuova differenza 
    
    drdy = false;                  // poni il bit di dataready a false
    bool faultdet = checkFault();  // verifica la presenza di fault
    if (!faultdet)
    {
      cb.push(rtd); // inserisci il valore corretto
    }
    else
    {
      cb.push(0); // inserisci 0 come valore invalido
    }
  }
}

// timeperiod è da considerarsi in secondi ricordati che il valore massimo possibile è 4 secondi il minimo 0.000064s (1/15625) cioè il valore del clock diviso il prescaler factor  16MHz/1024 = 15,625kHz
// setCounterStartValue imposta il valore iniziale del contatore utilizzato per il timer
void setCounterStartValue(float timePeriod)
{
  float n = (timePeriod * 15625);
  int i = (int)n;
  uint16_t fullvalue = (65536 - i);
  h = fullvalue >> 8;
  l = fullvalue & 0xFF;
}

// readRegister legge il valore di rtd dal registro
uint16_t readRegister()
{
  SPI.beginTransaction(SPISettings(500000, MSBFIRST, SPI_MODE1));
  // ------------------------
  digitalWrite(chipSelectPin, LOW); // * Chip Select CS: a LOW quando c'è comunicazione (attiva il clock), altrimenti HIGH
  SPI.transfer(0x80);               // 80h = 128 - config register // *-> questa è l'istruzione che indica che configuriamo il registro
  SPI.transfer(config1S);
  digitalWrite(chipSelectPin, HIGH);
  // ------------------------
  digitalWrite(chipSelectPin, LOW);
  SPI.transfer(1);           // !! Registro da leggere
  reg1 = SPI.transfer(0xFF); // !! leggi MSB
  reg2 = SPI.transfer(0xFF); // !! leggi LSB
  digitalWrite(chipSelectPin, HIGH);
  currT=millis();
  // ------------------------
  // * dato che i registri sono a 8 bit e che il numero è un intero a 16 bit, l'unico modo per memorizzare l'intero dato
  // * è dividerlo in 2 registri, quando i registri sono letti bisogna concatenarli
  fullreg = reg1;  // read MSB // * prende la prima parte del numero a 16 bit
  fullreg <<= 8;   // Shift to the MSB part // * lo sposta all'inizio del numero (per lasciare spazio a LSB)
  fullreg |= reg2; // read LSB and combine it with MSB // * concatena MSB con LSB
  fullreg >>= 1;   // Shift D0 out. // !! L'adc è a 15 bit, quindi uno dei bit è in realtà inutilizzato
  digitalWrite(chipSelectPin, LOW);
  // ------------------------
  SPI.endTransaction();              // * fine
  digitalWrite(chipSelectPin, HIGH); //* ferma il clock seriale
  
  return fullreg;
}

// sendData trasmette i dati di misura al software di monitoraggio
void sendData()
{
  if (!cb.available())
    return; // se il buffer è vuoto esce dal metodo
  uint16_t dat = 0;
 
  int sz = cb.size();            // restituisce il numero di elementi presenti nel buffer
  uint16_t point[32];
  cb.dump(point); // ritorna il puntatore dei dati da inviare, cioè del primo elemento del buffer
  uint8_t msb, lsb , msbi, lsbi = 0;
  uint16_t istant[32];
  dt_b.dump(istant);
  uint16_t ist=0;
  

  for (int i = 0; i < sz; i++)
  {                       
    ist = *(istant + i);
    msbi = ist >> 8;
    lsbi = ist & 0xFF;
    Serial.write(msbi);
    Serial.write(lsbi);
    //Serial.flush(); // Necessario per  ripulire il canale di comunnicazione

    // per ogni elemento da trasmettere accede ai due byte che compongono il valore di RTD
    dat = *(point + i); // prende il valore di RTD (a 16 bit)
    msb = dat >> 8;       // insertisce in MSB la parte più significativa del valore di RTD
    lsb = dat & 0xFF;     // insertisce in LSB la parte meno significativa del valore di RTD
    // poichè il metodo write invia un byte per volta è necessario suddividere il dato in due Byte
    Serial.write(msb);
    Serial.write(lsb);
   
  
    Serial.flush(); // Necessario per  ripulire il canale di comunnicazione
    
  }
}

// sendErr trasmette i codici di fault al software di monitoraggio
void sendErr()
{
  if (!eb.available())
    return;
  byte dat = 0;
  int sz = eb.size();
  byte pointer[32];
  eb.dump(pointer); // prendi i valori da trasmettere
  for (int i = 0; i < sz; i++)
  {
    dat = *(pointer + i);
    Serial.write(dat); // trasmetti (un valore alla volta consecutivamente)
    Serial.flush();
  }
  Serial.write(0); // necessario per terminare da phyton l'acquisizione degli errori
  Serial.flush();
}

// serialEvent è la routine di gestione dell'interrupt generato dalla trasmisione di un messaggio sulla seriale
void serialEvent()
{
  char *pointer;
  String msg;
  int len;
  msg = Serial.readString();
  // !!!! WARNING : ricorda che quando dichiari una variabile all interno di uno switch case vanno inserire le parentesi attorno al case altrimenti non prosegue
  switch (msg[0]) // utilizzando il carattere iniziale della stringa possiamo capire che comando è stato trasmesso
  {
  case 'O':
  {
    setOffset(msg);
    break;
  }
  case 'S':
  {
    //  inizializziamo  il timer e facciamo la prima richiesta
    int i = 0;
    float t;
    char *pointer;

    len = msg.length();
    char ch[len];
    msg.toCharArray(ch, len);
    pointer = strtok(ch, ":");
    while (pointer != NULL)
    {
      switch (i)
      {
      case 1:
      {
        // il primo valore è il periodo del timer
        String ts(pointer);
        t = ts.toFloat();
        break;
      }
      case 2:
      {
        // settare la frequenza di notch
        String freq(pointer);
        if (freq.equals("50"))
        {
          config1S = 0xB1;
          configN1S = 0x91;
        }
        else
        {
          config1S = 0xB0;
          configN1S = 0x90;
        }
        break;
      }
      }
      i++;
      pointer = strtok(NULL, ":");
    }
    setCounterStartValue(t);
    setupTimer();
    uint16_t rtd = readRegister(); // Effettua la prima lettura necessaria all avvio del processo di misurazione
    currT=0;
    break;
  }
  case 'R':
  {
    // viene azzerato loffset
    offset = 0;
    EEPROM.put(0, offset);
    break;
  }
  case 'T':
    // interrompi tutte le comunicazioni
    // noInterrupts(); ?? modificato
    Serial.println("EOT");
    TIMSK1 &= ~(1 << OCIE1A); // serve a disabilitare l'interrupt del timer
    Serial.flush();
    Serial.end();
    break;
  case 'F':
  {
    // trasmetti i codici di fault
    sendErr();
    break;
  }
  case 'C':
  {
    // avvia la procedura di calibrazione
    calibrate();
    break;
  }
  }
}

// setOffset memorizza il valore di offset ricevuto dal software di monitoraggio nella EEPROM di arduino
void setOffset(String msg)
{
  // manipolazione di stringhe
  int len = msg.length();
  char ch[len];
  msg.toCharArray(ch, len);
  char *pointer = strtok(ch, ":");
  pointer = strtok(NULL, ":");
  String ts(pointer);
  // fine manipolazione di stringhe
  offset += ts.toFloat();
  EEPROM.put(0, offset); // memorizza nella EEPROM
}

// calibrate è il metodo usato per raccogliere i campioni necessari per la calibrazione
void calibrate()
{
  CircularBuffer<uint16_t> t_LM_35b = CircularBuffer<uint16_t>(10); // buffer di valori da LM35
  CircularBuffer<uint16_t> t_PT100b = CircularBuffer<uint16_t>(10); // buffer di valori da PT100

  uint16_t bOff = (uint16_t)abs(offset);
  analogRead(A1);
  for (int i = 0; i < 11; i++)
  { // poichè la prima misura potrebbe essere soggetta a transitori ignoti non la consideriamo nel processo di taratura
    uint16_t dataRTD = readRegister();
    t_PT100b.push(dataRTD);
    uint16_t dataADC = analogRead(A1);
    // somma offset
    if (offset < 0)
    {
      dataADC -= bOff;
    }
    else
    {
      dataADC += bOff;
    }
    t_LM_35b.push(dataADC);
    delay(100);
  }

  int sz = t_PT100b.size();            // restituisce il numero di elementi presenti nel buffer
  uint16_t pointer[32];
  t_PT100b.dump(pointer); // ritorna il puntatore dei dati da inviare, cioè del primo elemento del buffer
  for (int j = 0; j < 2; j++)
  {
    uint16_t dat = 0;
    uint8_t msb, lsb = 0;
    for (int i = 0; i < sz; i++)
    {                       // per ogni elemento da trasmettere accede ai due byte che compongono il valore di RTD
      dat = *(pointer + i); // prende il valore di RTD (a 16 bit)
      msb = dat >> 8;       // insertisce in MSB la parte più significativa del valore di RTD
      lsb = dat & 0xFF;     // insertisce in LSB la parte meno significativa del valore di RTD
      // poichè il metodo write invia un byte per volta è necessario suddividere il dato in due Byte
      Serial.write(msb);
      Serial.write(lsb);
      Serial.flush(); // Necessario per  ripulire il canale di comunicazione
    }
    Serial.println();
    Serial.flush();
    sz = t_LM_35b.size();      // restituisce il numero di elementi presenti nel buffer
    t_LM_35b.dump(pointer); // ritorna il puntatore dei dati da inviare, cioè del primo elemento del buffer
  }
}

// checkFault legge il FaultStatus Register per ottenere il codice di Fault
bool checkFault()
{
  byte err, conf;
  // Leggere il registro di fault status 0x07 controllare se il bit (D1) è a 1(allora si è verificato un FAULT) c'è leggiamo i rimanenti bit per valutare il tipo di fault
  // settiamo a 1 il bit del configuration register per pulire il Fault Status Register
  SPI.beginTransaction(SPISettings(500000, MSBFIRST, SPI_MODE1));
  // -------------------------- lettura del fault register
  digitalWrite(chipSelectPin, LOW); // * Chip Select CS: a LOW quand
  SPI.transfer(0x07);
  err = SPI.transfer(0x00);
  digitalWrite(chipSelectPin, HIGH);
  // -------------------------- lettura dello status register
  digitalWrite(chipSelectPin, LOW);
  SPI.transfer(0x00);
  conf = SPI.transfer(0x00);
  digitalWrite(chipSelectPin, HIGH);
  // --------------------------
  conf |= 0x02; // modifica solo il flag di Auto Clear
  // -------------------------- scrittura dello status register (per settare il flag di autoclear)
  digitalWrite(chipSelectPin, LOW);
  SPI.transfer(0x80);
  SPI.transfer(conf);
  // --------------------------
  SPI.endTransaction(); // fine delle comunicazioni
  digitalWrite(chipSelectPin, HIGH);

  if (err != 0)
  {
    eb.push(err); // inserisci l'errore nel buffer degli errori
    return true;
  }
  return false;
}

// WRYYY
