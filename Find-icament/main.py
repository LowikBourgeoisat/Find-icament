import logging
import re

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


# Fonction permettant de créer nos urls
def create_urls():
    # On récupère les ids de nos médicaments qui sont contenues dans un fichier text
    drugs_ids = open('drugs_ids.txt', 'r').read().replace('\n', '').split(',')
    urls_list = []
    # On créer nos urls et on les met dans une liste que l'on retourne
    for drug_id in drugs_ids:
        url = 'https://base-donnees-publique.medicaments.gouv.fr/affichageDoc.php?specid=' + drug_id + '&typedoc=N'
        urls_list.append(url)
    return urls_list


def main():
    # PENSER A CHECK SI L'ID EXISTE DEJA EN BDD

    # On va sur les urls créés précédemment et on récupère la notice
    for url in create_urls():
        try:
            id = re.search(r'\d+', url).group(0)
            page1 = urllib.request.urlopen(url)
            soup = BeautifulSoup(page1, 'html.parser')
            table = soup.find('div', attrs={'id': 'textDocument'}).get_text()
            page2 = requests.get('https://base-donnees-publique.medicaments.gouv.fr/extrait.php?specid=' + id)
            tree = html.fromstring(page2.content)
            code_cip = tree.xpath('(//h2[@class="titrePresentation"]/following-sibling::text()[contains(., "Code CIP")])[1]')
            code_cip = re.search(r'(\d{5}.+)\'', str(code_cip)).group(1)
            print(code_cip)
            sql = "INSERT INTO medicament2 (id, code_cip, notice) VALUES (%s, %s, %s)"
            mycursor.execute(sql, (str(id), str(code_cip), str(table)))
            mydb.commit()
        except AttributeError:
            logging.warning('No notice for drug')


if __name__ == '__main__':
    main()
