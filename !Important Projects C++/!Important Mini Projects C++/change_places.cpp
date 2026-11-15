#include <iostream>
#include <Windows.h>
#include <ctime>

using namespace std;


void coop(int *pa, int *pb)
{
	int pcapsul = *pa;

	*pa = *pb;
	*pb = pcapsul;
}


int main()
{

	setlocale(LC_ALL, "ru");

	int a, b;

	cout << "Введите первое число: ";
	cin >> a;
	cout << "Введите второе число: ";
	cin >> b;

	cout << "=========================" << endl;

	coop(&a, &b);

	cout << "Ваши числа наоборот: " << a << " и " << b << endl;

 	system("pause");

}
