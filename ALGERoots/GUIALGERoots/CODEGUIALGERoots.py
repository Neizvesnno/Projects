import sqlite3 as sql
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import random
import sys
import Settings
import Account

start_hard = 10
last_hard = 20
last_un = 0
random_count = random.randint(start_hard, last_hard)
name_user = 'Guest'
window_open = False
old_user = False
lose = False
Stop_Bar = False
End_Timer = False
stop_music = False
count_un = 20
count = 0
answer_un = 0
doubler = 0
account_password = str()
win_count = 0
timen = 0
max_result = 0

Settings.music()


def sql_start():
    global old_user
    with sql.connect("Results.db") as con:
        cur = con.cursor()  # Cursor

        #  cur.execute("DROP TABLE IF EXISTS players")
        cur.execute("""CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT 'Guest',
            score INTEGER NOT NULL DEFAULT 0
            )""")

        def prof():
            global old_user
            cur.execute("SELECT name FROM players")
            massive = cur.fetchone()
            massive_big = cur.fetchall()
            for i in range(len(massive)):
                if massive[i] == name_user:
                    old_user = True
                #  print(massive[i])
                for j in range(len(massive_big)):
                    if massive_big[j][0] == name_user and j != len(massive_big) - 1:
                        old_user = True
                    #  print(massive_big[j][0])

        prof()

        if not old_user:
            sql_respawn = "INSERT INTO players (name, score) VALUES(:new_name, 0)"
            cur.execute(sql_respawn, {'new_name': name_user})

        prof()

        if old_user:
            cur.execute('SELECT * FROM players ORDER BY user_id DESC LIMIT 1')
            cur.execute(
                'DELETE FROM players WHERE user_id = (SELECT user_id FROM players ORDER BY user_id DESC LIMIT 1)')

        cur.execute("SELECT * FROM players ORDER BY user_id")


def game():
    global old_user, count, window_open, random_count

    def delete():
        Btn_submit.place_forget()
        Entry_answer.place_forget()
        Label_task.place_forget()

    window = tk.Tk()

    window.title("GUIALGERoots")

    window.config(bg="#BFC0C2")
    window.geometry("300x300+800+100")
    window.resizable(width=False, height=False)

    Label_task = tk.Label(window, text=f"{random_count} * {random_count} = ?", bg="#6BA64F", font=("Arial", 14))
    Label_count = tk.Label(window, text=f"Score: {count}", bg="#6BA64F", font=("Arial", 14))
    Entry_answer = tk.Entry(window, bg="#BFC0C2")

    window_open = True

    def userstats():
        global name_user, count
        stats = tk.Tk()

        stats.title("Profile")

        stats.config(bg="#BFC0C2")
        stats.geometry("300x300+450+100")
        stats.resizable(width=False, height=False)

        with sql.connect("Results.db") as con:
            cur = con.cursor()  # Cursor

            pb_count = "SELECT score FROM players WHERE name = :name_user"
            cur.execute(pb_count, {'name_user': name_user})
            pb = cur.fetchone()
            pb_res = pb[0]

            cur.execute("SELECT * FROM players ORDER BY user_id")

            cur.close()

        Label_Profile_Name = tk.Label(stats, text=f"Name: {name_user}", bg="#6BA64F", font=("Arial", 11))
        Label_Profile_Name.place(x=90, y=100, relwidth=0.4)

        Label_Profile_Count = tk.Label(stats, text=f"Max Score: {pb_res}", bg="#6BA64F", font=("Arial", 11))
        Label_Profile_Count.place(x=90, y=150, relwidth=0.4)

        stats.mainloop()

    def check():
        global random_count, count, answer_un, win_count, last_un, Stop_Bar, timen, End_Timer

        try:
            answer_un = int(Entry_answer.get())
        except ValueError:
            #  print("ValueError!")
            score_update()
            Stop_Bar = True
            End_Timer = True
            #  print(f'Lose: {Stop_Bar}')
            delete()
            # PB!!!!!!!!!!!!!!!!!!!!!!!
        finally:
            #  print(random_count, "*", random_count, "= ?")
            if answer_un == random_count * random_count:
                #  print("Yes, true!")
                count += count_un
                win_count += 1
                #  print("Your count:", count)
                timen = 10
                #  Stop_Bar = True
                #  timer
            else:
                Stop_Bar = True
                End_Timer = True
                #  print(f'Lose: {Stop_Bar}')
                delete()
                score_update()
                # PB!!!!!!!!!!!!!!!!!!!!!
                win_count = -1
                count = 0
                #  print("Nope!")
                #  print("True result is:", random_count * random_count)
                #  Settings.get_exit()
        difficulty()
        Entry_answer.delete(0, tk.END)
        random_count = random.randint(start_hard, last_hard)
        last_un = random_count
        Label_task.configure(text=f"{random_count} * {random_count} = ?")
        if not Stop_Bar:
            Label_count.configure(text=f"Score: {count}")

    Btn_submit = tk.Button(window, text="Submit", command=check, bg="#BFC0C2", font=("Arial", 11))

    def get_exit():
        global stop_music
        score_update()
        stop_music = True
        sys.exit(0)

    def score_update():
        global name_user, count
        with sql.connect("Results.db") as con:
            cur = con.cursor()  # Cursor

            pb_count = "SELECT score FROM players WHERE name = :name_user"
            cur.execute(pb_count, {'name_user': name_user})
            pb = cur.fetchone()
            pb_res = pb[0]

            cur.execute("SELECT * FROM players ORDER BY user_id")

            if pb_res <= count:
                sql_respawn_score = "UPDATE players SET score = :new_score WHERE name = :name_user"
                cur.execute(sql_respawn_score, {'new_score': count, 'name_user': name_user})

            cur.execute("SELECT * FROM players ORDER BY user_id")

    def ScrollBaren():
        global timen
        timen = 10
        arr_Bar = ['Stages/TimerBar0.png', 'Stages/TimerBar1.png', 'Stages/TimerBar2.png', 'Stages/TimerBar3.png',
                   'Stages/TimerBar4.png', 'Stages/TimerBar5.png', 'Stages/TimerBar6.png', 'Stages/TimerBar7.png',
                   'Stages/TimerBar8.png', 'Stages/TimerBar9.png', 'Stages/TimerBar10.png']

        def station():
            global timen, lose, Stop_Bar, End_Timer, max_result
            if timen >= 0:
                if timen == 0:
                    Stop_Bar = True
                    End_Timer = True
                    #  print(f'Lose: {Stop_Bar}')
                    # PB!!!!!!!!!!!!!!!!!!!!!!
                if Stop_Bar:
                    timen = 10
                    Stop_Bar = False

                img_obj = Image.open(arr_Bar[timen])
                box = 350
                wide_size = (box / float(img_obj.size[0]))
                height_size = int((float(img_obj.size[1]) * float(wide_size)))
                img_obj = img_obj.resize((box, height_size), Image.LANCZOS)
                img_obj = ImageTk.PhotoImage(img_obj)
                our_label2 = tk.Label(image=img_obj, bg="#BFC0C2")
                our_label2.image = img_obj
                if not End_Timer:
                    our_label2.place_forget()
                    our_label2.place(x=180, y=10, relheight=0.3, relwidth=0.6)
                    window.after(1000, station)
                else:
                    our_label2.image = 'Stages/ScrolBar_0.png'
                    our_label2.place_forget()
                    delete()
                    score_update()
                    our_label2.place(x=180, y=10, relheight=0.3, relwidth=0.6)
                    Label_GameOver = tk.Label(window, text="Game Over!", bg='#eb4c40', font=("Arial", 40))
                    Label_GameOver.place(x=180, y=140, relheight=0.25, relwidth=0.5)

                    def print_max():
                        global name_user, count, max_result
                        with sql.connect("Results.db") as con:
                            cur = con.cursor()  # Cursor

                            pb_count = "SELECT score FROM players WHERE name = :name_user"
                            cur.execute(pb_count, {'name_user': name_user})
                            pb_forever = cur.fetchone()
                            max_result = pb_forever[0]

                    def restart_main():
                        global timen, Stop_Bar, End_Timer, window_open, win_count, count, count_un, start_hard, last_hard, random_count
                        score_update()
                        timen = 10
                        win_count = 0
                        count = 0
                        count_un = 20
                        start_hard = 10
                        last_hard = 20
                        random_count = random.randint(start_hard, last_hard)
                        Stop_Bar = False
                        End_Timer = False
                        Btn_Restart.place_forget()
                        Label_max.place_forget()
                        Label_GameOver.place_forget()
                        window.destroy()
                        game()

                    score_update()
                    print_max()

                    Label_max = tk.Label(window, text=f"Max score: {max_result}", bg='#6BA64F', font=("Arial", 20))
                    Btn_Restart = tk.Button(window, text="Restart", command=restart_main, bg="#6BA64F",
                                            font=("Arial", 15))
                    Label_max.place(x=250, y=340, relheight=0.1, relwidth=0.3)
                    Btn_Restart.place(x=220, y=440, relwidth=0.4)

                timen -= 1

        station()

    def difficulty():
        global start_hard, last_hard, win_count, count_un
        if win_count <= -1:
            pass
        elif 0 <= win_count <= 4:
            count_un = 20
            start_hard = 10
            last_hard = 20
        elif 5 <= win_count <= 10:
            count_un = 50
            start_hard = 20
            last_hard = 32
        elif 10 <= win_count <= 20:
            count_un = 100
            start_hard = 32
            last_hard = 50
        else:
            count_un = 200
            start_hard = 50
            last_hard = 100
        return start_hard, last_hard

    def play():
        global random_count, count, answer_un, start_hard, last_hard, last_un

        window.geometry("700x600+350+100")

        # Hide Elements There!!!

        Btn_Play.place_forget()
        Btn_Settings.place_forget()
        Label_Hello.place_forget()
        Btn_stats.place_forget()

        ScrollBaren()

        Label_count.place(x=20, y=20, relwidth=0.2)
        Label_task.place(x=290, y=210, relwidth=0.25)
        Entry_answer.place(x=290, y=300, relwidth=0.25)
        Btn_submit.place(x=290, y=330, relwidth=0.25)

        Btn_get_exit.place(x=0, y=570, relwidth=1)

    Label_Hello = tk.Label(window, text="Welcome to GUIALGERoots!", bg="#6BA64F", font=("Arial", 14))
    Label_Hello.place(x=22, y=50, relwidth=0.85)

    Btn_Play = tk.Button(window, text="Play", command=play, bg="#BFC0C2", font=("Arial", 11))
    Btn_Play.place(x=90, y=100, relwidth=0.4)

    Btn_Settings = tk.Button(window, text="Settings", command=Settings.menu, bg="#BFC0C2", font=("Arial", 11))
    Btn_Settings.place(x=90, y=140, relwidth=0.4)

    Btn_stats = tk.Button(window, text="Profile", command=userstats, bg="#BFC0C2", font=("Arial", 11))
    Btn_stats.place(x=90, y=180, relwidth=0.4)

    Btn_get_exit = tk.Button(window, text="exit", command=get_exit, bg="#eb4c40", relief=tk.RIDGE, font=("Arial", 11))
    Btn_get_exit.place(x=0, y=270, relwidth=1)

    window.mainloop()


def main():
    global name_user
    #  run_music()
    name_user = Account.answeriti
    if name_user == '' or name_user == ' ':
        name_user = 'Guest'
    sql_start()
    #  print(f"You\'r account: {name_user}")
    #  print(f'Old User: {old_user}')
    game()


if __name__ == '__main__':
    main()
    #  Score import
