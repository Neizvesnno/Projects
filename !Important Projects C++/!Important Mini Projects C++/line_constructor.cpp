#include <iostream>
#include <Windows.h>
using namespace std;

int main()
{

	setlocale(LC_ALL, "ru");

	int a, i = 0, man;
	char sim;

	cout << "Привет, это линия!" << endl;
	cout << "Пример: 20" << endl;
	cout << "Введи длину линии: ";
	cin >> a;
	cout << "Пример: a" << endl;
	cout << "Введи символ, с которого будет построенна линия: ";
	cin >> sim;
	cout << "Горизонтально - 1. вертикально - 2" << endl;
	cout << "Пример: 1" << endl;
	cout << "Горизонтально или вертикально: ";
	cin >> man;

	cout << endl;

	while (i < a)
	{
		switch (man)
		{
		case 1:

			i++;
			cout << sim;
			break;

		case 2:

			i++;
			cout << sim << endl;
			break;

		default:
			cout << "Вы ввели что-то не так!" << endl;
			i = a;
			break;
		}
	}

	cout << endl;

	cout << "\nУдачного времени суток!" << endl;

}
