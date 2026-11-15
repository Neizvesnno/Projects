#include <iostream>
#include <string>

using namespace std;

long long solve(string &n)
{

	string new_str;
	char n_zap;
	char a = 'A', b = 'B';

	while (true) 
	{
		if (n.empty())
		{
			break;
		}

		n_zap = n[0];

		while (true)
		{
			if (n.empty())
			{
				break;
			}

			if (n_zap == a || n_zap == b)
			{
				new_str += n_zap;
				n.erase(0, 1);
				break;
			}

			n.erase(0, 1);

			if (n.empty())
			{
				break;
			}
			
			n_zap = n[0];

		}

	}

	int counter = 0, kk = 0, kkn = 0;
	char Ac, Bc;
	string zap_new_str1, zap_new_str2;
	string zapi = new_str;

	for (int A = 0; A < new_str.size(); A++)
	{
		Ac = new_str[A];
		if (Ac == a)
		{
			kkn = kk + 1;
			zapi = new_str;
			zap_new_str1 = zapi.erase(0, kk);
				for (int B = 0; B < zap_new_str1.size(); B++)
				{
					Bc = zap_new_str1[B];
					if (Bc == b)
					{
						zapi = new_str;
						zap_new_str2 = (zapi.erase(0, kkn));
						for (int A2 = 0; A2 < zap_new_str2.size(); A2++)
						{
							Ac = zap_new_str2[A2];
							if (Ac == a)
							{
								counter += 1;
							}
						}

					}

					kkn += 1;
					zapi = new_str;
					zap_new_str2 = (zapi.erase(0, kkn));

				}
		}

		kk += 1;

	}

	return counter;

}

int main() 
{
	
	string n;

	cin >> n;

	int res = solve(n);

	cout << res << endl;

	return 0;

}
