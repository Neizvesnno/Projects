import random

count = 0

while True:
    rc = random.randint(11, 32)
    print(rc, "*", rc, "= ?")
    n = int(input())
    if n == rc * rc:
        print("Yes, true!")
        count = count + 1
        print("Your count:", count)
    else:
        print("Nope!")
        print("True result is:", rc * rc)
        break

print("Your result:", count)
