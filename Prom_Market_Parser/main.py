import requests
from bs4 import BeautifulSoup
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl import Workbook
import random
import math
import time
import os

headers: dict = {"User-Agent": "..."}
canner: bool = True
kol_strs: int = 1
data_len: int = 0
search: str


def every_main(parse_str):
    global search, data_len, canner
    response = requests.get(f"https://prom.ua/ua/search?search_term={search}&page={parse_str}", headers)
    html_content = response.content
    soup = BeautifulSoup(html_content, "html.parser")
    advertisements = soup.find_all("span", class_="_3Trjq htldP _7NHpZ h97_n")
    prices = soup.find_all("span", class_="yzKb6")
    senders = soup.find_all("div", class_="l-GwW js-productad")

    time.sleep(0.1)

    header = ["Назва", "Ціна", "Посилання"]
    links = ["This is HyperLink", "Touch me", "Click here", "Hello, I'm Link!"]
    kkn = 0
    sorted_advertisements = []
    sorted_senders = []
    sorted_prices = []
    data = []

    for adver in advertisements:
        zap_adver = adver.get_text()
        # print(zap_adver)
        sorted_advertisements.append(zap_adver)

    for adver_f in senders:
        adver = str(adver_f)
        href_find = adver.find('url=')
        zap_adver = adver[(href_find + 5)::]
        href_find2 = zap_adver.find('"')
        zap_adver = zap_adver[:href_find2:]
        sorted_senders.append(zap_adver)

    for adver in prices:
        zap_adver = adver.get_text()
        # print(zap_adver)
        sorted_prices.append(zap_adver)

    if len(sorted_senders) == 0:
        canner = False
        return 0

    for name in sorted_advertisements:
        data.append([name, sorted_prices[kkn], sorted_senders[kkn]])
        kkn += 1
        if kkn == len(sorted_advertisements) or kkn == len(sorted_prices) or kkn == len(sorted_senders):
            break

    try:
        workbook = load_workbook('products.xlsx')
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

    last_row = worksheet.max_row - 1

    for row_num, info in enumerate(data, start=2):
        data_len += 1
        for col_num, value in enumerate(info, start=1):
            col_letter = get_column_letter(col_num)
            colip = f'{col_letter}{last_row + row_num}'
            if col_letter == "C":
                worksheet[colip].hyperlink = value
                worksheet[colip].value = random.choice(links)
                worksheet[colip].style = "Hyperlink"
            else:
                worksheet[colip] = value

    workbook.save('products.xlsx')


def main():
    global kol_strs, headers, search, canner, data_len
    try:
        os.remove("products.xlsx")
    except FileNotFoundError:
        print("need make a file \"products.xlsx\"")

    search = str(input("Enter a search query: "))
    search = search.replace(" ", "%20")
    url = f"https://prom.ua/ua/search?search_term={search}"
    response = requests.get(url, headers)
    html_content = response.content
    soup = BeautifulSoup(html_content, "html.parser")
    mb_kol_strs = soup.find_all("span", class_="_3Trjq iX-v2")[0].get_text()
    mb_kol_strs = mb_kol_strs.replace("+", "")
    tov_found = mb_kol_strs.find("товарів")
    mb_kol_strs = math.ceil(float(int(mb_kol_strs[(tov_found + 10)::]))/29)

    def kol_parser(kol_strs_zep):
        global headers
        kol_zapper = kol_strs_zep
        while True:
            response_zepper = requests.get(f"https://prom.ua/ua/search?search_term={search}&page={kol_zapper}", headers)
            html_content_zepper = response_zepper.content
            soup_zepper = BeautifulSoup(html_content_zepper, "html.parser")
            array_with_pages = soup_zepper.find_all("button", class_="VS-Ex vtaL- oBR0- _4-SzE")[0].get_text()
            array_zapper_ch = [1, 2, 3]
            if (kol_zapper not in array_zapper_ch) and (int(array_with_pages) in array_zapper_ch):
                while True:
                    kol_zapper -= 1
                    response_zepper = requests.get(f"https://prom.ua/ua/search?search_term={search}&page={kol_zapper}", headers)
                    html_content_zepper = response_zepper.content
                    soup_zepper = BeautifulSoup(html_content_zepper, "html.parser")
                    array_with_pages = soup_zepper.find_all("button", class_="VS-Ex vtaL- oBR0- _4-SzE")[0].get_text()
                    if int(array_with_pages) != 1:
                        break
                break
            kol_zapper += 3

        return kol_zapper

    kol_strs = kol_parser(mb_kol_strs)
    url = f"https://prom.ua/ua/search?search_term={search}&page={kol_strs}"
    response = requests.get(url, headers)
    html_content = response.content
    soup = BeautifulSoup(html_content, "html.parser")
    kol_tov = soup.find_all("span", class_="_3Trjq iX-v2")[0].get_text()
    findator_kol_st = kol_tov.find("- ")
    kol_tov = kol_tov[(findator_kol_st + 2)::]
    findator_kol_en = kol_tov.find(" товарів")
    kol_tov = kol_tov[:findator_kol_en:]
    print(f"Great, {kol_strs} pages and {kol_tov} products found!")
    need_parse_pages = int(input("Write how many pages need to be parsed: "))

    nummer = 0
    for str_p in range(1, need_parse_pages + 1):
        if canner:
            every_main(str_p)
        else:
            break
        nummer += data_len
        data_len = 0

    print(f"successfully, {nummer} products parsed!")


if __name__ == "__main__":
    main()
