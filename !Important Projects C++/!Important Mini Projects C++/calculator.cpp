#include <iostream>
#include <Windows.h>
using namespace std;

int main()
{

	setlocale(LC_ALL, "ru");

	int a, b, r, res;
	cout << "Привет, это калькулятор!" << endl;
	cout << "Введите первое число: ";
	cin >> a;
	cout << "Введите второе число: ";
	cin >> b;

	cout << "Математическую опперации: 1 - сума. 2 - вычетание. 3 - умножение. 4 - деление" << endl;
	cout << "Отлично, а теперь введите математическую опперацию: ";
	cin >> r;

	switch (r)
	{
	case 1:

		res = a + b;
		cout << "Сума ваших чисел: " << res << endl;

		break;

	case 2:

		res = a - b;
		cout << "Результат отнимания ваших чисел: " << res << endl;

		break;

	case 3:

		res = a * b;
		cout << "Результат умножения ваших чисел: " << res << endl;

		break;
	case 4:

		res = a / b;
		cout << "Результат деления ваших чисел: " << res << endl;

		break;

	default:
			cout << "Вы ввели что-то не так!" << endl;
			break;
	}

	cout << "Удачного времени суток!" << endl;

}
