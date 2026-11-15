import tkinter as tk


def have_acc():
    global answeriti
    answeriti = Entry_acc.get()
    Entry_acc.delete(0, tk.END)
    account_w.quit()
    account_w.destroy()


answeriti = 'Guest'

account_w = tk.Tk()

account_w.title("Account")

account_w.config(bg="#BFC0C2")
account_w.geometry("300x300+750+100")
account_w.resizable(width=False, height=False)

Label_text = tk.Label(account_w, text="Enter your Account Name:", bg="#6BA64F", font=("Arial", 14))
Label_text.place(x=22, y=50, relwidth=0.85)

Entry_acc = tk.Entry(account_w, bg="#BFC0C2")
Entry_acc.place(x=22, y=100, relwidth=0.85)

Btn_succec = tk.Button(account_w, text="Select", command=have_acc, bg="#BFC0C2", relief=tk.RIDGE, font=("Arial", 11))
Btn_succec.place(x=22, y=150, relwidth=0.85)

account_w.mainloop()
