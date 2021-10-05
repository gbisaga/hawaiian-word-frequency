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

controlWords = ["_skipped"]

parser = argparse.ArgumentParser()
parser.add_argument('--deck', help="deck file to write")
parser.add_argument('--lookups', help="existing Duolingo lookups file")
parser.add_argument('--force', help="force write to dictionary file")
parser.add_argument('--import', dest='doImport', help="file name to import from; JSON like you'd get from https://preview.duolingo.com/vocabulary/overview")
parser.add_argument('--forcescan', help="force scan of Duolingo pages")
args = parser.parse_args()

deckFileName = args.deck
lookupFileName = args.lookups
chromeDriverLocation = 'C:/src/duolingo-tools/chromedriver.exe'
headless = False
language = 'hawaiian'
jsonfile = f'dl-{language}-words.json'
doForce = args.force == 'true'
importJSON = args.doImport
forcescan = args.forcescan == 'true'

importvocab = None
if importJSON != None:
    print(f'importing from {importJSON}')
    with open(args.doImport, 'r') as f:
        importvocab = json.loads(f.read())
        if "vocab_overview" in importvocab and "language_string" in importvocab:
            language = importvocab["language_string"].lower()
        else:
            print(f'Import file in bad format')
            sys.exit(1)

print(f'Language is {language}')

# Import is JSON format you'd get from https://preview.duolingo.com/vocabulary/overview

words = {}
originalJSON = None
skippedwords = []
with open(jsonfile, 'r') as f:
    originalJSON = f.read()
    words = json.loads(originalJSON)
    if "_skipped" in words:
        skippedwords = words["_skipped"]
    else:
        words["_skipped"] = skippedwords

if importvocab != None:
    for vocab in importvocab["vocab_overview"]:
        word = vocab["word_string"]
        if word not in words and word not in skippedwords:
            print(f'new word: {word}')
            words[word] = { }

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
    if word in controlWords: continue
    
    # See if we need to look it up in Duolingo first
    info = words[word]

    if 'duo' not in info or forcescan:
        print(f'lookup {word}')
        count += 1
        if maxcount != 0 and count > maxcount: break
        url = lookup(word)
        print(f'{word} => {url}')
        info['duo'] = url

    urlword = urlquote(word)
    info["wehe"] = f"https://hilo.hawaii.edu/wehe/?q={stripsuffix(urlword)}"
    info["google"] = f"https://translate.google.com/?sl=haw&tl=en&text={urlword}%0A&op=translate"

    if 'duodef' not in info:
        info['duodef'] = getdef(info['duo'])

    if "english" not in info or info["english"] == "":
        info["english"] = info['duodef']

    if "parts" not in info:
        info["parts"] = ""
    # print(f'{word} => {defn}')

# Write new JSON, but only if it's changed
newJSON = json.dumps(words, indent=2)
if doForce or (originalJSON != newJSON and importJSON == None):
    jsonbak = jsonfile.replace('.json', '.bak')

    print(f'backing up {jsonfile} to {jsonbak}')
    shutil.copyfile(jsonfile, jsonbak)

    print(f'writing to {jsonfile}')
    with open(jsonfile, 'w') as f:
        f.write(newJSON)
else:
    print(f'no change or import without force, not saving to {jsonfile}')

if deckFileName != None:
    print(f'writing deck to {deckFileName}')
    with open(deckFileName, 'w', encoding='utf-8', newline='') as f:
        csvwriter = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        for word in words:
            if word in controlWords: continue
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
