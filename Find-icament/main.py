import logging
import os
import queue
import re
import threading
from bs4 import BeautifulSoup
import urllib.request
import mysql.connector
from lxml import html
import requests


mydb = mysql.connector.connect(
  host="",
  user="",
  password="",
  database=""
)

mycursor = mydb.cursor()
sql = "INSERT INTO medicament2 (id, code_cip, name, notice) VALUES (%s, %s, %s, %s)"
threads = list()
q = queue.Queue()
sema = threading.Semaphore(value=os.cpu_count()*4)
logging.getLogger().setLevel(logging.INFO)


# Fonction permettant de créer nos urls
def create_urls():
    # On récupère les ids de nos médicaments qui sont contenues dans un fichier text
    drugs_ids = open('drugs_ids.txt', 'r').read().splitlines()
    urls_list = []
    # On créer nos urls et on les met dans une liste que l'on retourne
    for drug_id in drugs_ids:
        url = 'https://base-donnees-publique.medicaments.gouv.fr/affichageDoc.php?specid=' + drug_id + '&typedoc=N'
        urls_list.append(url)
    return urls_list


def get_info(url, current_queue):
    sema.acquire()
    try:
        med_id = re.search(r'\d+', url).group(0)
        page1 = urllib.request.urlopen(url)
        soup = BeautifulSoup(page1, 'html.parser', from_encoding="iso-8859-1")
        table = soup.find("div", id="textDocument").get_text()
        name = soup.find("h1", class_="textedeno").get_text().replace('- Notice patient', '')
        print(name)
        page2 = requests.get('https://base-donnees-publique.medicaments.gouv.fr/extrait.php?specid=' + med_id)
        tree = html.fromstring(page2.content)
        code_cip = tree.xpath('(//h2[@class="titrePresentation"]/following-sibling::text()[contains(., "Code CIP")])[1]')
        cip_match = re.search(r'(\d{5}.+)\'', str(code_cip))
        if cip_match:
            code_cip = cip_match.group(1)
        else:
            page_cip2 = requests.get('https://base-donnees-publique.medicaments.gouv.fr/affichageDoc.php?specid=' + med_id + '&typedoc=R')
            tree = html.fromstring(page_cip2.content)
            code_cip = tree.xpath('//p[contains(text(),"34009")][1]')
            code_cip = re.search(r'(\d{5} \d{3} \d{3} \d \d)', str(code_cip)).group(1)
        current_queue.put((med_id, code_cip, name, table))
    except AttributeError:
        current_queue.put(None)
    sema.release()


def main():
    # PENSER A CHECK SI L'ID EXISTE DEJA EN BDD
    # On va sur les urls créés précédemment et on récupère la notice
    for url in create_urls():
        threads.append(threading.Thread(target=get_info, args=(url, q)))
        threads[-1].start()
    for t in threads:
        t.join()
        t_result = q.get()
        logging.info(str(t_result))
        if t_result:
            mycursor.execute(sql, (str(t_result[0]), str(t_result[1]), str(t_result[2]), str(t_result[3])))
            mydb.commit()


if __name__ == '__main__':
    main()
