//#include <iostream>

#include "Arduino.h"
using namespace std;

class CircularBuffer
{
private:
    int _head = -1, _tail = 0; // index that points to the first and last inserted element
    uint16_t *_data;           // data inserted in the buffer

public:
    int _length, _count = 0; // number of elements in the array
    CircularBuffer(int length);
    void push(uint16_t element);
    uint16_t pop();
    bool available();
    int size();
    uint16_t *dump();
    // JUST FOR DEBUG PURPOSES
    void show();
};