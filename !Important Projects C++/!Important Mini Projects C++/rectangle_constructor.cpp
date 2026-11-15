#include <iostream>
#include <Windows.h>
using namespace std;

int main()
{

	setlocale(LC_ALL, "ru");

	int a, b, i, j;

	cout << "Привет, это конструктор прямоугольников!" << endl;

	cout << "Введите длину прямоугольника: ";
	cin >> a;
	cout << "Введите ширину прямоугольника : ";
	cin >> b;

	for (int i = 0; i < a; i++)
	{
		for (int j = 0; j < b; j++)
		{
			cout << "*";
		}

		cout << endl;
	}

	cout << "Удачного дня!" << endl;

	system("pause");

}
