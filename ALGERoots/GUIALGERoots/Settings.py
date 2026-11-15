import sqlite3 as sql
import tkinter as tk
import playsound
import sys


def music():
    playsound.playsound('audio.wav', block=False)


def cleaner():
    with sql.connect("Results.db") as con:
        cur = con.cursor()  # Cursor

        cur.execute("DROP TABLE IF EXISTS players")
        cur.execute("""CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT NEIZVESNNO,
            score INTEGER NOT NULL DEFAULT 0
            )""")

        sql_respawn = "INSERT INTO players (name, score) VALUES(:new_name, :new_score)"
        cur.execute(sql_respawn, {'new_name': 'NEIZVESNNO', 'new_score': 0})

        cur.execute("SELECT * FROM players ORDER BY user_id")


def menu():
    count = 0

    def check():
        try:
            Result = int(Entry_password.get())
            if Result == 2552:
                Entry_password.place_forget()
                Btn_submit.place_forget()
                Label_task.place_forget()
                Btn_cleaner = tk.Button(roots, text="Clean Data Base", command=cleaner, bg="#eb4c40", font=("Arial", 11))
                Btn_cleaner.place(x=145, y=125, relwidth=0.3)
        except ValueError:
            pass
        finally:
            Entry_password.delete(0, tk.END)

    if count < 1:
        count += 1
        roots = tk.Tk()

        roots.title("Program Settings")

        roots.config(bg="#BFC0C2")
        roots.geometry("400x300+500+80")
        roots.resizable(width=False, height=False)

        Label_task = tk.Label(roots, text="Enter the password: ", bg="#6BA64F", font=("Arial", 11))
        Label_task.place(x=135, y=75, relwidth=0.35)

        Entry_password = tk.Entry(roots, bg="#BFC0C2")
        Entry_password.place(x=145, y=125, relwidth=0.3)

        Btn_submit = tk.Button(roots, text="Submit", command=check, bg="#BFC0C2", font=("Arial", 11))
        Btn_submit.place(x=145, y=175, relwidth=0.3)

        roots.mainloop()
    else:
        pass
