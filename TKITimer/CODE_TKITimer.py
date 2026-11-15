import tkinter as tk
import time
import sys
from PIL import ImageTk, Image

value1 = 0
value2 = 0
value3 = 0
value4 = 0
value5 = 0
value6 = 0

exc1 = 0
exc2 = 0
exc3 = 0
exc4 = 0
exc5 = 0
exc6 = 0

RB = True

window = tk.Tk()

window.title("TKITimer")
icon = tk.PhotoImage(file="Timer.png")
window.iconphoto(False, icon)

window.config(bg="#BFC0C2")
window.geometry("700x600+800+100")
window.resizable(width=False, height=False)

can1 = tk.Canvas(window, relief=tk.FLAT)
can1.place(x=250, y=275, relwidth=0.35, relheight=0.02)

img = ImageTk.PhotoImage(Image.open("BackGroundSPL.jpg"))
image = can1.create_image(0, 0, anchor="nw", image=img)

tk.Label(window, text="Hello! It\'s TKITimer", bg="#BFC0C2", font=("Arial", 8, "bold")).place(x=0, y=120, relwidth=0.15)
tk.Label(window, text="This is Timer:", bg="#556E29", font=("Arial", 16, "bold")).place(x=300, y=180)

ER1 = tk.Label(window, text="It doesn't work!", bg="#556E29", font=("Arial", 14, "bold"))
ER2 = tk.Label(window, text="You can\'t start with that!", bg="#556E29", font=("Arial", 14, "bold"))
ER3 = tk.Label(window, text="This doesn't work!", bg="#556E29", font=("Arial", 14, "bold"))

SC1 = tk.Label(window, text="OK, Let\'s start!", bg="#556E29", font=("Arial", 14, "bold"))
SC2 = tk.Label(window, text="time is up!", bg="#556E29", font=("Arial", 14, "bold"))

ST1 = tk.Label(window, text="Program is stopped!", bg="#556E29", font=("Arial", 14, "bold"))
RS1 = tk.Label(window, text="Program is reset!", bg="#556E29", font=("Arial", 14, "bold"))
CT1 = tk.Label(window, text="Program has been restored!", bg="#556E29", font=("Arial", 14, "bold"))

colon1 = tk.Label(window, text=":", bg="#BFC0C2", font=("Arial", 30, "bold"))  # H - M
colon2 = tk.Label(window, text=":", bg="#BFC0C2", font=("Arial", 30, "bold"))  # M - S

zero1 = tk.Label(window, text="0", bg="#BFC0C2", font=("Arial", 30, "bold"))  # H1
zero2 = tk.Label(window, text="0", bg="#BFC0C2", font=("Arial", 30, "bold"))  # H2
zero3 = tk.Label(window, text="0", bg="#BFC0C2", font=("Arial", 30, "bold"))  # M1
zero4 = tk.Label(window, text="0", bg="#BFC0C2", font=("Arial", 30, "bold"))  # M2
zero5 = tk.Label(window, text="0", bg="#BFC0C2", font=("Arial", 30, "bold"))  # S1
zero6 = tk.Label(window, text="0", bg="#BFC0C2", font=("Arial", 30, "bold"))  # S2

one1 = tk.Label(window, text="1", bg="#BFC0C2", font=("Arial", 30, "bold"))
one2 = tk.Label(window, text="1", bg="#BFC0C2", font=("Arial", 30, "bold"))
one3 = tk.Label(window, text="1", bg="#BFC0C2", font=("Arial", 30, "bold"))
one4 = tk.Label(window, text="1", bg="#BFC0C2", font=("Arial", 30, "bold"))
one5 = tk.Label(window, text="1", bg="#BFC0C2", font=("Arial", 30, "bold"))
one6 = tk.Label(window, text="1", bg="#BFC0C2", font=("Arial", 30, "bold"))

two1 = tk.Label(window, text="2", bg="#BFC0C2", font=("Arial", 30, "bold"))
two2 = tk.Label(window, text="2", bg="#BFC0C2", font=("Arial", 30, "bold"))
two3 = tk.Label(window, text="2", bg="#BFC0C2", font=("Arial", 30, "bold"))
two4 = tk.Label(window, text="2", bg="#BFC0C2", font=("Arial", 30, "bold"))
two5 = tk.Label(window, text="2", bg="#BFC0C2", font=("Arial", 30, "bold"))
two6 = tk.Label(window, text="2", bg="#BFC0C2", font=("Arial", 30, "bold"))

three1 = tk.Label(window, text="3", bg="#BFC0C2", font=("Arial", 30, "bold"))
three2 = tk.Label(window, text="3", bg="#BFC0C2", font=("Arial", 30, "bold"))
three3 = tk.Label(window, text="3", bg="#BFC0C2", font=("Arial", 30, "bold"))
three4 = tk.Label(window, text="3", bg="#BFC0C2", font=("Arial", 30, "bold"))
three5 = tk.Label(window, text="3", bg="#BFC0C2", font=("Arial", 30, "bold"))
three6 = tk.Label(window, text="3", bg="#BFC0C2", font=("Arial", 30, "bold"))

four1 = tk.Label(window, text="4", bg="#BFC0C2", font=("Arial", 30, "bold"))
four2 = tk.Label(window, text="4", bg="#BFC0C2", font=("Arial", 30, "bold"))
four3 = tk.Label(window, text="4", bg="#BFC0C2", font=("Arial", 30, "bold"))
four4 = tk.Label(window, text="4", bg="#BFC0C2", font=("Arial", 30, "bold"))
four5 = tk.Label(window, text="4", bg="#BFC0C2", font=("Arial", 30, "bold"))
four6 = tk.Label(window, text="4", bg="#BFC0C2", font=("Arial", 30, "bold"))

five1 = tk.Label(window, text="5", bg="#BFC0C2", font=("Arial", 30, "bold"))
five2 = tk.Label(window, text="5", bg="#BFC0C2", font=("Arial", 30, "bold"))
five3 = tk.Label(window, text="5", bg="#BFC0C2", font=("Arial", 30, "bold"))
five4 = tk.Label(window, text="5", bg="#BFC0C2", font=("Arial", 30, "bold"))
five5 = tk.Label(window, text="5", bg="#BFC0C2", font=("Arial", 30, "bold"))
five6 = tk.Label(window, text="5", bg="#BFC0C2", font=("Arial", 30, "bold"))

six1 = tk.Label(window, text="6", bg="#BFC0C2", font=("Arial", 30, "bold"))
six2 = tk.Label(window, text="6", bg="#BFC0C2", font=("Arial", 30, "bold"))
six3 = tk.Label(window, text="6", bg="#BFC0C2", font=("Arial", 30, "bold"))
six4 = tk.Label(window, text="6", bg="#BFC0C2", font=("Arial", 30, "bold"))
six5 = tk.Label(window, text="6", bg="#BFC0C2", font=("Arial", 30, "bold"))
six6 = tk.Label(window, text="6", bg="#BFC0C2", font=("Arial", 30, "bold"))

seven1 = tk.Label(window, text="7", bg="#BFC0C2", font=("Arial", 30, "bold"))
seven2 = tk.Label(window, text="7", bg="#BFC0C2", font=("Arial", 30, "bold"))
seven3 = tk.Label(window, text="7", bg="#BFC0C2", font=("Arial", 30, "bold"))
seven4 = tk.Label(window, text="7", bg="#BFC0C2", font=("Arial", 30, "bold"))
seven5 = tk.Label(window, text="7", bg="#BFC0C2", font=("Arial", 30, "bold"))
seven6 = tk.Label(window, text="7", bg="#BFC0C2", font=("Arial", 30, "bold"))

eight1 = tk.Label(window, text="8", bg="#BFC0C2", font=("Arial", 30, "bold"))
eight2 = tk.Label(window, text="8", bg="#BFC0C2", font=("Arial", 30, "bold"))
eight3 = tk.Label(window, text="8", bg="#BFC0C2", font=("Arial", 30, "bold"))
eight4 = tk.Label(window, text="8", bg="#BFC0C2", font=("Arial", 30, "bold"))
eight5 = tk.Label(window, text="8", bg="#BFC0C2", font=("Arial", 30, "bold"))
eight6 = tk.Label(window, text="8", bg="#BFC0C2", font=("Arial", 30, "bold"))

nine1 = tk.Label(window, text="9", bg="#BFC0C2", font=("Arial", 30, "bold"))
nine2 = tk.Label(window, text="9", bg="#BFC0C2", font=("Arial", 30, "bold"))
nine3 = tk.Label(window, text="9", bg="#BFC0C2", font=("Arial", 30, "bold"))
nine4 = tk.Label(window, text="9", bg="#BFC0C2", font=("Arial", 30, "bold"))
nine5 = tk.Label(window, text="9", bg="#BFC0C2", font=("Arial", 30, "bold"))
nine6 = tk.Label(window, text="9", bg="#BFC0C2", font=("Arial", 30, "bold"))


def numbers_false():
    num_v = [zero1, one1, two1, three1, four1, five1, six1, seven1, eight1, nine1,
             zero2, one2, two2, three2, four2, five2, six2, seven2, eight2, nine2,
             zero3, one3, two3, three3, four3, five3, six3, seven3, eight3, nine3,
             zero4, one4, two4, three4, four4, five4, six4, seven4, eight4, nine4,
             zero5, one5, two5, three5, four5, five5, six5, seven5, eight5, nine5,
             zero6, one6, two6, three6, four6, five6, six6, seven6, eight6, nine6]
    count = len(num_v)
    for delete in range(count):
        num_v[delete].place_forget()


def help_info():
    root = tk.Tk()

    root.title("TKITimer")

    root.config(bg="#BFC0C2")
    root.geometry("200x120+500+100")
    root.resizable(width=False, height=False)

    tk.Label(root, bg="#BFC0C2",
             text="Ex: Hour\'s Minute\'s Second\'s \n sample: 01 00 10 \n" "Ex: Hour\'s Minute\'s Second\'s \n sample: 00 00 00",
             font=("Arial", 10, "bold"), padx=10, pady=20).place(x=0, y=0)

    root.mainloop()


def visible_false():
    ER1.place_forget()
    ER2.place_forget()
    ER3.place_forget()
    SC1.place_forget()
    SC2.place_forget()
    ST1.place_forget()
    RS1.place_forget()
    CT1.place_forget()


def get_exit():
    global RB
    RB = False
    Btn_get_continue.place_forget()
    Btn_get_reset.place_forget()
    visible_false()
    get_zero()
    sys.exit()


def get_stop():
    global RB
    visible_false()
    ST1.place(x=280, y=300)
    Btn_get_stop.place_forget()
    Btn_get_continue.place(x=320, y=340, relwidth=0.15)
    Btn_get_reset.place(x=320, y=370, relwidth=0.15)
    RB = False


def get_continue():
    global RB
    visible_false()
    CT1.place(x=240, y=300)
    Btn_get_continue.place_forget()
    Btn_get_reset.place_forget()
    Btn_get_stop.place(x=320, y=340, relwidth=0.15)
    window.update()
    time.sleep(1)
    RB = True
    start()


def get_reset():
    global RB
    RB = False
    Btn_get_continue.place_forget()
    Btn_get_reset.place_forget()
    visible_false()
    get_zero()
    RS1.place(x=290, y=300)


def get_zero():
    numbers_false()
    zero1.place(x=260, y=220)
    zero2.place(x=290, y=220)
    colon1.place(x=320, y=220)
    zero3.place(x=340, y=220)
    zero4.place(x=370, y=220)
    colon2.place(x=400, y=220)
    zero5.place(x=420, y=220)
    zero6.place(x=450, y=220)


def get_insert():
    get_delete()
    first.insert(0, "00")
    second.insert(0, "00")
    third.insert(0, "00")
    fourth.insert(0, "00")
    fifth.insert(0, "00")
    sixth.insert(0, "00")


def get_delete():
    first.delete(0, tk.END)
    second.delete(0, tk.END)
    third.delete(0, tk.END)
    fourth.delete(0, tk.END)
    fifth.delete(0, tk.END)
    sixth.delete(0, tk.END)


def start():
    global value1, value2, value3, RB
    global exc1, exc2, exc3, exc4, exc5, exc6

    while True:
        exc1 = value1 // 10 % 10
        exc2 = value1 % 10
        exc3 = value2 // 10 % 10
        exc4 = value2 % 10
        exc5 = value3 // 10 % 10
        exc6 = value3 % 10

        if value2 == 0 and value3 == 0 and value1 > value4:
            value1 = value1 - 1
            value2 = value2 + 59
            value3 = value3 + 60
        if value3 == 0 and value2 > value5:
            value2 = value2 - 1
            value3 = value3 + 60

        numbers_false()

        exc1_v = [zero1, one1, two1, three1, four1, five1, six1, seven1, eight1, nine1]
        exc1_v[exc1].place(x=260, y=220)

        exc2_v = [zero2, one2, two2, three2, four2, five2, six2, seven2, eight2, nine2]
        exc2_v[exc2].place(x=290, y=220)

        exc3_v = [zero3, one3, two3, three3, four3, five3, six3, seven3, eight3, nine3]
        exc3_v[exc3].place(x=340, y=220)

        exc4_v = [zero4, one4, two4, three4, four4, five4, six4, seven4, eight4, nine4]
        exc4_v[exc4].place(x=370, y=220)

        exc5_v = [zero5, one5, two5, three5, four5, five5, six5, seven5, eight5, nine5]
        exc5_v[exc5].place(x=420, y=220)

        exc6_v = [zero6, one6, two6, three6, four6, five6, six6, seven6, eight6, nine6]
        exc6_v[exc6].place(x=450, y=220)

        value3 = value3 - 1
        window.update()

        if value3 == value6 - 1 and value2 == value5 and value1 == value4 and RB is True:
            visible_false()
            SC2.place(x=322, y=300)
            Btn_get_continue.place_forget()
            Btn_get_reset.place_forget()
            Btn_get_stop.place_forget()
            if value6 != 0 or value5 != 0 or value4 != 0:
                Btn_get_reset.place(x=320, y=340, relwidth=0.15)
            break
        elif RB is False:
            break

        time.sleep(1)


def get_info():
    global value1, value2, value3, value4, value5, value6, RB

    try:
        value1 = int(first.get())  # H1
        value2 = int(second.get())  # M1
        value3 = int(third.get())  # S1
        value4 = int(fourth.get())  # H2
        value5 = int(fifth.get())  # M2
        value6 = int(sixth.get())  # S2
        if value1 != value4 or value2 != value5 or value3 != value6:
            if value1 >= 0 and 59 >= value2 >= 0 and 59 >= value3 >= 0 and value4 >= 0 and 59 >= value5 >= 0 and 59 >= value6 >= 0:
                RB = True
                if RB is True:
                    Btn_get_continue.place_forget()
                    Btn_get_reset.place_forget()
                    Btn_get_stop.place(x=320, y=340, relwidth=0.15)
                    visible_false()
                    get_delete()
                    SC1.place(x=302, y=300)
                    start()
            else:
                RB = False
                visible_false()
                get_delete()
                ER1.place(x=298, y=300)
        else:
            RB = False
            visible_false()
            get_delete()
            ER2.place(x=258, y=300)
    except ValueError:
        RB = False
        visible_false()
        get_delete()
        ER3.place(x=285, y=300)


FirstTimeText = tk.Label(window, text="enter the time you want to start", font=("Arial", 9, "bold"), bg="#556E29")
FirstTimeText.place(x=280, y=10)

H1 = tk.Label(window, text="Hour\'s: ", bg="#BFC0C2", font=("Arial", 10, "bold"))
H1.place(x=110, y=40)
first = tk.Entry(window, bg="#BFC0C2")
first.place(x=160, y=40)

M1 = tk.Label(window, text="Minute\'s: ", bg="#BFC0C2", font=("Arial", 10, "bold"))
M1.place(x=290, y=40)
second = tk.Entry(window, bg="#BFC0C2")
second.place(x=350, y=40)

S1 = tk.Label(window, text="Second\'s: ", bg="#BFC0C2", font=("Arial", 10, "bold"))
S1.place(x=480, y=40)
third = tk.Entry(window, bg="#BFC0C2")
third.place(x=550, y=40)

SecondTimeText = tk.Label(window, text="enter the time which you want to stop", font=("Arial", 9, "bold"), bg="#556E29")
SecondTimeText.place(x=270, y=70)

H2 = tk.Label(window, text="Hour\'s: ", bg="#BFC0C2", font=("Arial", 10, "bold"))
H2.place(x=110, y=100)
fourth = tk.Entry(window, bg="#BFC0C2")
fourth.place(x=160, y=100)

M2 = tk.Label(window, text="Minute\'s: ", bg="#BFC0C2", font=("Arial", 10, "bold"))
M2.place(x=290, y=100)
fifth = tk.Entry(window, bg="#BFC0C2")
fifth.place(x=350, y=100)

S2 = tk.Label(window, text="Second\'s: ", bg="#BFC0C2", font=("Arial", 10, "bold"))
S2.place(x=480, y=100)
sixth = tk.Entry(window, bg="#BFC0C2")
sixth.place(x=550, y=100)

Btn_help_info = tk.Button(window, text="help", command=help_info, bg="#BFC0C2", font=("Arial", 11))
Btn_help_info.place(x=0, y=0, relwidth=0.15)
Btn_get_delete = tk.Button(window, text="delete", command=get_delete, bg="#BFC0C2", font=("Arial", 11))
Btn_get_delete.place(x=0, y=30, relwidth=0.15)
Btn_get_insert = tk.Button(window, text="insert", command=get_insert, bg="#BFC0C2", font=("Arial", 11))
Btn_get_insert.place(x=0, y=60, relwidth=0.15)
Btn_get_info = tk.Button(window, text="start", command=get_info, bg="#BFC0C2", font=("Arial", 11))
Btn_get_info.place(x=0, y=90, relwidth=0.15)

Btn_get_stop = tk.Button(window, text="stop", command=get_stop, bg="#BFC0C2", font=("Arial", 11))
Btn_get_continue = tk.Button(window, text="continue", command=get_continue, bg="#BFC0C2", font=("Arial", 11))
Btn_get_reset = tk.Button(window, text="reset", command=get_reset, bg="#BFC0C2", font=("Arial", 11))

Btn_get_exit = tk.Button(window, text="exit", command=get_exit, bg="#eb4c40", relief=tk.RIDGE, font=("Arial", 11))
Btn_get_exit.place(x=0, y=570, relwidth=1)

get_zero()

window.mainloop()
