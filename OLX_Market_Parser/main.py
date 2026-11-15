import requests
from bs4 import BeautifulSoup
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl import Workbook
import random
import os

'''
            modeDict = {'r' : 'rb', 'w': 'w+b', 'x': 'x+b', 'a' : 'r+b',
                        'r+b': 'w+b', 'w+b': 'wb', 'x+b': 'xb'} 
                                    filemode = modeDict[mode]
'''

data_len: int = 0
row_numo: int = 0
search: str


def every_main(kols):
    global data_len, row_numo, search
    header = ["Назва", "Ціна", "Посилання"]
    links = ["This is HyperLink", "Touch me", "Click here", "Hello, I'm Link!"]
    trueltor = False
    data = []
    mega_sorted_senders = []
    mega_sorted_advertisements = []
    mega_sorted_price = []
    sorted_price = []
    sorted_advertisements = []
    sorted_senders = []
    findator_name = []
    zepper_name = -1
    kk = 0
    kk_zep = 0

    url = f"https://www.olx.ua/d/uk/list/q-{search}/?page={kols}"
    response = requests.get(url)
    html_content = response.content
    soup = BeautifulSoup(html_content, "html.parser")
    advertisements = soup.find_all("h6", class_="css-16v5mdi er34gjf0")
    senders = soup.find_all("a", class_="css-rc5s2u")
    prices = soup.find_all("p", class_="css-10b0gli er34gjf0")

    for i in advertisements:
        zap_adver = str(i).replace("<h6 class=\"css-16v5mdi er34gjf0\">", "")
        zap_adver = zap_adver.replace("</h6>", "")
        if zap_adver.find('емонт') != -1 and zap_adver.find('аміна') != -1 and zap_adver.find('становка') != -1 and zap_adver.find('итяжка') != -1:
            findator_name.append(kk_zep)
            zepper_name = kk_zep
        sorted_advertisements.append(zap_adver)
        kk_zep += 1

    for i in prices:
        i = i.find(string=True)
        sorted_price.append(i)

    for i in senders:
        zap_adver = str(i).replace("<a class=\"css-rc5s2u\" href=\"", "")
        zap_adver = "https://www.olx.ua" + str(zap_adver[:(zap_adver.find(".html") + 5):])
        sorted_senders.append(zap_adver)

    if zepper_name != -1:
        for i in range(0, len(sorted_price)):
            if i in findator_name:
                pass
            else:
                mega_sorted_price.append(sorted_price[i])
    else:
        mega_sorted_price = sorted_price

    if zepper_name != -1:
        for i in range(0, len(sorted_senders)):
            if i in findator_name:
                pass
            else:
                mega_sorted_senders.append(sorted_senders[i])
    else:
        mega_sorted_senders = sorted_senders

    if zepper_name != -1:
        for i in range(0, len(sorted_advertisements)):
            if i in findator_name:
                pass
            else:
                mega_sorted_advertisements.append(sorted_advertisements[i])
    else:
        mega_sorted_advertisements = sorted_advertisements

    sorted_advertisements = mega_sorted_advertisements
    sorted_senders = mega_sorted_senders
    sorted_price = mega_sorted_price

    if zepper_name != -1:
        sorted_advertisements = sorted_advertisements[1::]
        sorted_senders = sorted_senders[1::]

    for name in sorted_advertisements:
        data.append([name, sorted_price[kk], sorted_senders[kk]])
        kk += 1
        if kk == len(sorted_advertisements) or kk == len(sorted_price) or kk == len(sorted_senders):
            break

    data_len = len(data)

    try:
        workbook = load_workbook('results.xlsx')
    except FileNotFoundError:
        workbook = Workbook()

    worksheet = workbook.active

    worksheet.column_dimensions['A'].width = 50
    worksheet.column_dimensions['B'].width = 15
    worksheet.column_dimensions['C'].width = 20

    if worksheet['A1'].value != header[0] or worksheet['B1'].value != header[1] or worksheet['C1'].value != header[2]:
        for col_num, value in enumerate(header, start=1):
            col_letter = get_column_letter(col_num)
            worksheet[f'{col_letter}1'] = value
    else:
        trueltor = True

    last_row = worksheet.max_row

    if trueltor:
        last_row -= 1

    for row_num, info in enumerate(data, start=2):
        for col_num, value in enumerate(info, start=1):
            col_letter = get_column_letter(col_num)
            colip = f'{col_letter}{last_row + row_num}'
            if col_letter == "C":
                worksheet[colip].hyperlink = value
                worksheet[colip].value = random.choice(links)
                worksheet[colip].style = "Hyperlink"
            else:
                if value == '.css-1c0ed4l{display:inline-block;}':
                    value = "Error"
                worksheet[colip] = value

    workbook.save('results.xlsx')

    return data_len


def main():
    global row_numo, search, data_len

    try:
        os.remove("results.xlsx")
    except FileNotFoundError:
        print("need make a file \"results.xlsx\"")

    search = str(input("Введіть пошуковий запит: "))
    search = search.replace(" ", "-")

    url_first = f"https://www.olx.ua/d/uk/list/q-{search}/"
    response_first = requests.get(url_first)
    html_content_first = response_first.content

    soup_first = BeautifulSoup(html_content_first, "html.parser")

    kol_strs = soup_first.find_all("a", class_="css-1mi714g")[-1].get_text()

    for ssp in range(1, int(kol_strs) + 1):
        data_len = every_main(ssp)
        row_numo += data_len

    print(f"Excellent, I found {row_numo} products!")


if __name__ == "__main__":
    main()
