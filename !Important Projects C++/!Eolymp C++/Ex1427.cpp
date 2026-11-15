#include <iostream>
#include <vector>
#include <string>

using namespace std;


void solve(string &b, long long &y, long long &x, long long &q)
{

    q = 1;
    x = 0;

    for (long long i = b.size() - 1; i >= 0; i--)
    {
        y = static_cast<long long>(b[i]) - 48;
        x = x + y * q;
        q *= 10;
    }

}


int main()
{

    string a, b = "", c;
    long long q = 1, res = 0, y = 0, x, k = 0;
    vector <int> vec;

    cin >> a;

    for (int i = 0; i < a.size(); i++)
    {
        if (char(a[i]) != '+' and char(a[i]) != '-')
        {   
            b += a[i];
        }
        else 
        {

            solve(b, y, x, q);

            b = "";
            vec.push_back(x);
        }
    }

    solve(b, y, x, q);

    vec.push_back(x);

    for (int i = 0; i < a.size(); i++) 
    {
        if (char(a[i]) == '+' or char(a[i]) == '-')
        {
            c += a[i];
        }
    }

    res = res + vec[0];

    for (int i = 0; i < c.size(); i++) 
    {

        k = static_cast<long long>(i) + 1;

        if (char(c[i]) == '+')
        {
            res = res + vec[k];
        }
        else
        {
            res = res - vec[k];
        }

    }

    cout << res << endl;

    return(0);

}