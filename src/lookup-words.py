import sys
import argparse
import re
from os import path
from html.parser import HTMLParser
import json
import requests
import yaml
import time
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.select import Select, By
import io
import csv
import shutil
import urllib.parse

parser = argparse.ArgumentParser()
parser.add_argument('--deck', help="deck file to write")
parser.add_argument('--lookups', help="existing Duolingo lookups file")
# parser.add_argument('--maxurls', help="maximum number of urls")
# parser.add_argument('--pull', help="if true, pull data; default is process existing data file")
# parser.add_argument('--top', help="only output top X words")
# parser.add_argument('--out', required=True, help="top X words output file")
args = parser.parse_args()

deckFileName = args.deck
lookupFileName = args.lookups
chromeDriverLocation = 'C:/src/duolingo-tools/chromedriver.exe'
headless = False
jsonfile = 'dl-hawaiian-words.json'

words = {}
originalJSON = None
with open(jsonfile, 'r') as f:
    originalJSON = f.read()
    words = json.loads(originalJSON)

lookups = {}
if lookupFileName != None:
    with io.open(lookupFileName, 'r', newline='\n', encoding='UTF-8') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in csvreader:
            # print(row)
            word = row[0]
            if word in words:
                words[word]['duo'] = row[1]
            else:
                print(f'unknown word from lookups: {word}')

browser = None
def openbrowser():
    global browser
    if browser != None: return
    opts = ChromeOptions()
    opts.set_headless(headless)
    browser = Chrome(executable_path=chromeDriverLocation, options=opts)
    browser.implicitly_wait(10)

baseurl = f'https://preview.duolingo.com/dictionary/Hawaiian'
print(baseurl)

def getdef(wordurl):
    openbrowser()
    browser.get(wordurl)
    # //*[@id="root"]/div/div[4]/div/div[2]/div/div[1]/div/div[1]/div[1]/h3
    # /html/body/div[1]/div/div[4]/div/div[2]/div/div[1]/div/div[1]/div[1]/h3
    try:
        translation = browser.find_element(By.XPATH, "//h2[text()='Translation']/../div[1]/h3")
        print(f'trans: {translation} -> {translation.text}')
        if translation != None:
            return translation.text
    except:
        pass
    return None

def lookup(word):
    openbrowser()
    browser.get(baseurl)
    els = browser.find_elements_by_css_selector('input[data-test=dictionary-search-input]')
    textfield = els[0]
    print(textfield)
    textfield.send_keys(word)
    lookupbutton = browser.find_elements_by_css_selector('button[data-test=dictionary-translate]')[0]
    lookupbutton.click()
    try:
        element = browser.find_element(By.XPATH, "//h2[text()='Translation']")
        return browser.current_url
    except:
        return browser.current_url

def stripsuffix(word):
    if '(' not in word: return word
    else: return word.split('(')[0]

def urlquote(word):
    return urllib.parse.quote_plus(word)

# Don't read from deck by default: use jsonfile, already read into `words`
# with io.open(csvfileName, 'r', newline='\n', encoding='UTF-8') as csvfile:
#     csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
#     for row in csvreader:
maxcount = 0
count = 0
for word in words:
    info = words[word]
    urlword = urlquote(word)
    info["wehe"] = f"https://hilo.hawaii.edu/wehe/?q={stripsuffix(urlword)}"
    info["google"] = f"https://translate.google.com/?sl=haw&tl=en&text={urlword}%0A&op=translate"

    if 'duodef' not in info:
        info['duodef'] = getdef(info['duo'])

    if 'duo' not in info:
        print(f'lookup {word}')
        count += 1
        if maxcount != 0 and count > maxcount: break
        url = lookup(word)
        print(f'{word} => {url}')
        info['duo'] = url

    # print(f'{word} => {defn}')

# Write new JSON, but only if it's changed
newJSON = json.dumps(words, indent=2)
if originalJSON != newJSON:
    jsonbak = jsonfile.replace('.json', '.bak')

    print(f'backing up {jsonfile} to {jsonbak}')
    shutil.copyfile(jsonfile, jsonbak)

    print(f'writing to {jsonfile}')
    with open(jsonfile, 'w') as f:
        f.write(newJSON)
else:
    print(f'no change, not saving to {jsonfile}')

if deckFileName != None:
    print(f'writing deck to {deckFileName}')
    with open(deckFileName, 'w', encoding='utf-8', newline='') as f:
        csvwriter = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        for word in words:
            info = words[word]
            csvwriter.writerow([
               word,
               info['english'],
               info['wehe'],
               info['duo'],
               info['parts'],
               info['google'],
               info['duodef']
            ])

if browser != None: browser.close()
sys.exit(0)
