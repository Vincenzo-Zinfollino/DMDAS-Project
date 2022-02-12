#include "Arduino.h"
//#include <iostream> // used for debugging purposes
// using namespace std; // used for debugging purposes

template <typename T>
class CircularBuffer
{
private:
    int _head = 0, _tail = 0; // index that points to the first and last inserted element
    T *_data;                 // data inserted in the buffer

public:
    int _length, _count = 0; // number of elements in the array
    CircularBuffer(int length);
    void push(T element);
    T pop();
    bool available();
    int size();
    // void dump(uint16_t *arr);
    T *dump();
    //   JUST FOR DEBUG PURPOSES
    void show();
};