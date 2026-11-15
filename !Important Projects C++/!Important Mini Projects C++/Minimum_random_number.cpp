#include <iostream>
#include <Windows.h>
#include <ctime>

using namespace std;

int main()
{

	setlocale(LC_ALL, "ru");

	srand(time(NULL));

	bool x = false;

	int const SIZE = 10;

	int res, arr[SIZE]{};

	for (int i = 0; i < SIZE;)
	{
		x = false;
		res = rand() % 20;
		for (int j = 0; j < i; j++)
		{
			if (res == arr[j])
			{
				x = true;
				break;
			}
		}

		if (x == false)
		{
			arr[i] = res;
			i++;
		}
	}

	int min = arr[0];

	for (int i = 0; i < SIZE; i++)
	{
		if (arr[i] < min)
		{
			min = arr[i];
		}
	}

	cout << "Минимальное рандомное число = " << min << endl;

	system("pause");

}
