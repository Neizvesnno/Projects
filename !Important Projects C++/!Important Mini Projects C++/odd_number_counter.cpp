#include <iostream>
#include <Windows.h>
using namespace std;

int main()
{

	setlocale(LC_ALL, "ru");

	int a, b, count = 0;
	cout << "Привет, это счётчик нечётных чисел!" << endl;
	cout << "Введите начальное число: ";
	cin >> a;
	cout << "Введите конечное число: ";
	cin >> b;

	while (a < b)
	{
		if (a % 2 != 0)
		{
			count = count + a;
		}
		a++;
	}

	cout << "\nСума нечётных чисел в вашем диапазоне = " << count << endl;
	cout << "\nУдачного времени суток" << endl;
}
