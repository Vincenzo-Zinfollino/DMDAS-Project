# DMDAS-Project D'Arcangelo, De Pinto, Zinfollino, Karpczak

La repository qui presente contiene l'implementazione del progetto per il corso Distributed Measurement and Data Acquisition Systems (a.a 2021/2022) degli studenti D'Arcangelo, De Pinto, Zinfollino e Karpczak del Politecnico di Bari. Il progetto prevede la realizzazione di un sistema di misura della temperatura per poter monitorare e correggere la procedura di cottura della vernice applicata ad alcuni elementi di dimensione e forma differenti: l'obbiettivo finale è quello di costruire il profilo termico del bene realizzato, ovvero il tracciamento di una curva che mostra la termperatura del prodotto durante l'intera fase di cottura. Ciò che segue è una descrizione di ciascuna componente del sistema realizzato.

## max31865.ino

Il file _max31865.ino_ contiene lo script utilizzato per la richiesta dei dati di misure di temperatura. Esso sfrutta un buffer circolare (implementato tramite _CircularBuffer.cpp_) per memorizzare le misure con un periodo di campionamento definito dall'utente (ed implementato tramite l'uso di un timer).
**INSERIRE DETTAGLI IMPLEMENTATIVI**

## CircularBuffer.cpp

Il file _CircularBuffer.cpp_ contiene l'implementazione della classe **CircularBuffer**: un buffer circolare usato per memorizzare i dati delle misure prima della trasmissione. Esso ha una lunghezza \_length, un contatore \_count per indicare il numero di elementi inseriti e due indici: \_head che indica l'elemento inserito più di recente e \_tail che indica l'elemento inserito meno recentemente.
![images/push.png](/images/push.png)
Il metodo _push(element)_ permette di inserire all'interno del buffer circolare un elemento, l'elemento sarà inserito in "testa" alla struttura dati, il cui puntatore si sposterà (in modo circolre) in avanti per indicare l'elemento inserito più di recente. Se il puntatore \_head coincide con \_tail quando il numero di elementi inseriti \_count è maggiore di 1, vuol dire che i dati che saranno inseriti successivamente sovrascriveranno quelli più vecchi: è perciò necessario spostare in avanti \_tail.
![images/pop.png](/images/pop.png)
Il metodo _pop()_ permette di leggere e rimuovere l'elemento meno recente dal buffer circolare: l'implementazione prevede solo memorizzare il valore meno recente e di spostare \_tail in avanti di una posizione.
![images/dump.png](/images/dump.png)
Il metodo _dump()_ permette di raccogliere fino a 64kB di dati dal buffer, così che possano essere trasmessi sulla porta seriale in seguito ad una richiesta da parte del calcolatore.

###### NB:

Dato che i valori che saranno memorizzati sono sempre _unsined 16 bit integers (uint16_t)_, ogni elemento del buffer avrà dimensione pari a 2B.

## main.py

**ATTENDO FINALIZZAZIONE DELLO SCRIPT**

## Arduino.py

**ATTENDO FINALIZZAZIONE DELLO SCRIPT**
