//#include <iostream>
#include "Arduino.h"
#include "CircularBuffer.h"
using namespace std;

CircularBuffer::CircularBuffer(int length)
{
    _length = length;
    _data = new uint16_t[length];
    for (int i = 0; i < _length; i++) // initialize
    {
        _data[i] = 0;
    }
}

void CircularBuffer::push(uint16_t element)
{
    _head = (_head + 1) % _length; // increase the index circularly
    _data[_head] = element;        // insert the element in the array
    if (_head == _tail && _count > 1)
    {
        _tail = (_tail + 1) % _length;
    }
    if (_count < _length)
    {
        _count++; // increase the count of the number of elements
    }
}

uint16_t CircularBuffer::pop()
{
    if (_count > 0)
    {
        uint16_t toReturn = _data[_tail]; // get the int to return
        _count--;                         // decrese the count of the number of elements
        if (_count > 0)                   // if it is the last element, do not move the _tail pointer
        {
            _tail = (_tail + 1) % _length; // decrese the index circularly
        }
        return toReturn;
    }
    return 0;
    // to avoid the use of exceptions and of signed integers,
    // given the fact that the class will be used for RTD readings
    // that are all > 0, 0 can be considered an "invalid" value
}

bool CircularBuffer::available()
{
    return _count > 0; // simply return if there is data in the buffer
}

int CircularBuffer::size() // necessario per spaccare il bit
{
    return _count;
}

uint16_t *CircularBuffer::dump()
{
    // return at most 64B of data (bytes/2 elements)
    int n;
    static uint16_t toReturn[32];
    int i = 0;
    while (_count > 0)
    {
        toReturn[i++] = pop();
    }
    return toReturn;
}
//!! JUST FOR DEBUGGING PURPOSES
/*void CircularBuffer::show()
{
    for (int i = 0; i < _length; i++)
    {
        cout << _data[i] << " ";
    }
    cout << endl
         << "Head:\t" << _head << "; Tail:\t" << _tail << endl;
}*/
//&a = prendi l'indirizzo di a
//*a = a conterrà un indirizzo
