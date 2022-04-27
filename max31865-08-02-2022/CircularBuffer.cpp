#include "Arduino.h"
#include "CircularBuffer.h"
//#include <iostream> // used for debugging purposes
// using namespace std; // used for debugging purposes

template <typename T>
CircularBuffer<T>::CircularBuffer(int length)
{
    _length = length;
    _data = new T[length];
    for (int i = 0; i < _length; i++) // initialize
    {
        _data[i] = 0;
    }
}
template <typename T>
void CircularBuffer<T>::push(T element)
{
    if (_count > 0)
        _head = (_head + 1) % _length; // increase the index circularly
    _data[_head] = element;            // insert the element in the array
    if (_head == _tail && _count > 1)
    {
        _tail = (_tail + 1) % _length;
    }
    if (_count < _length)
    {
        _count++; // increase the count of the number of elements
    }
}
template <typename T>
T CircularBuffer<T>::pop()
{
    if (_count > 0)
    {
        T toReturn = _data[_tail]; // get the int to return
        _count--;                  // decrese the count of the number of elements
        if (_count > 0)            // if it is the last element, do not move the _tail pointer
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
template <typename T>
bool CircularBuffer<T>::available()
{
    return _count > 0; // simply return if there is data in the buffer
}
template <typename T>
int CircularBuffer<T>::size() // necessario per spaccare il bit
{
    return _count;
}
template <typename T>
void *CircularBuffer<T>::dump(T *toReturn )
{
    // return at most 64B of data (bytes/2 elements)
    //static T toReturn[32];
    int i = 0;
    while (_count > 0)
    {
        *(toReturn+(i++)) = pop();
    }
   // return toReturn;
}
//!! JUST FOR DEBUGGING PURPOSES
/*template <typename T>
void CircularBuffer<T>::show()
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

// !! Given the fact that main.cpp and CircularBuffer.cpp are compiled separately, it is
// !! necessary to tell the compiler that these are the implemented template or the
// !! linker will not be able to link implementations with the requested instantiation.
// !! ex: CircularBuffer will accept the unspecified type T, if I instantiate the class as
// !! CircularBuffer<byte> the linker will try to find in the implementation of the class
// !! CircularBuffer<byte> but will only find CircularBuffer<T>, failing the compilation:
// !! By specifying that we want the following implementations, the compiler will compile
// !! the class using the specified types (instead of T) and this should let the linker link
// !! the instantiation to the correct compiled implementation finishing the compilation successfully
template class CircularBuffer<uint16_t>;
template class CircularBuffer<byte>;
template class CircularBuffer<int>;
