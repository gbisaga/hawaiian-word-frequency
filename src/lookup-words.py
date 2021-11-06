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
import os

controlWords = ["_skipped"]

parser = argparse.ArgumentParser()
parser.add_argument('--export', help="CSV export/deck file to write")
parser.add_argument('--lookups', help="existing Duolingo lookups file")
parser.add_argument('--lookup', help="if true (default), lookup in Duolingo; usually used with --import")
parser.add_argument('--force', help="force write to dictionary file")
parser.add_argument('--import', dest='doImport', help="file name to import from; JSON like you'd get from https://preview.duolingo.com/vocabulary/overview")
parser.add_argument('--forcescan', help="force scan of Duolingo pages")
parser.add_argument('--maxcount', help="maximum number of words to scan; still imports all words if doing an import")
parser.add_argument('--language', help="which language (use two-letter abbreviation) to scan for; default is 'hw'")
parser.add_argument('--delay', help="delay between Duolingo lookups; default 10 seconds")
parser.add_argument('--lemma', help="if true (default false), only use lemma (e.g. infinitive) forms for import and/or export")
parser.add_argument('--makelemma', help="if true (default false), convert all vocab into only lemma forms (experimental)")
parser.add_argument('--singlelookup', help="if passed, lookup a single definition in Duolingo")
args = parser.parse_args()

# Note: not stripping 'u' because of all the non-verbs that end in that letter
eoLemmaMap = {
    'i': ['is', 'as', 'os', 'us', 'inta', 'anta', 'onta'],
    'a': ['aj', 'an', 'ajn'],
    'o': ['oj', 'on', 'ojn']
}
nonEOLemmaMapped = ["plus", "minus", "kaj"]

def makeEOLemma(word, info):
    # print(f'makeEOLemma: word={word}')
    if word in nonEOLemmaMapped:
        return word

    for shortEnding in eoLemmaMap:
        for longEnding in eoLemmaMap[shortEnding]:
            if word.endswith(longEnding) and word != longEnding:
                return word[0:len(word) - len(longEnding)] + shortEnding

    return word

def makeConjugatedLemma(word, info):
    ret = word
    # print(f'makeConjugatedLemma: word={word} info={info}')
    if info.get("infinitive") == None or info.get("infinitive") == word:
        pass
    else:
        ret = info.get("infinitive")
    print(f'makeConjugatedLemma: word={word} -> {ret}')
    return ret

# The non-generic row items should all be at the end
languagesInfo = {
    "hw": {
        "tla": "haw", 
        "name": "Hawaiian",
        "rowitems": ["english", "skill", "duo", "parts", "google", "wehe"],
        "makeLemma": lambda word, info: word
    },
    "it": {
        "tla": "it", 
        "name": "Italian",
        "rowitems": ["english", "skill", "duo", "parts", "google"],
        "makeLemma": lambda word, info: makeConjugatedLemma(word, info)
    },
    "eo": {
        "tla": "eo", 
        "name": "Esperanto",
        "rowitems": ["english", "skill", "duo", "parts", "google", ""],
        "makeLemma": lambda word, info: makeEOLemma(word, info)
    },
    "fr": {
        "tla": "fr", 
        "name": "French",
        "rowitems": ["english", "skill", "duo", "parts", "google"],
        "makeLemma": lambda word, info: makeConjugatedLemma(word, info)
    }
}

exportFileName = args.export
lookupFileName = args.lookups
chromeDriverLocation = 'C:/src/duolingo-tools/chromedriver.exe'
headless = False
languageKey = 'hw' if args.language == None else args.language
if languageKey not in languagesInfo:
    print(f'Unknown language key "{languageKey}"; choices are {[key for key in languagesInfo]}')
    sys.exit(1)
else:
    languageInfo = languagesInfo[languageKey]

doForce = args.force == 'true'
importJSON = args.doImport
forcescan = args.forcescan == 'true'
language = languageInfo["name"]
maxcount = 0 if args.maxcount == None else int(args.maxcount)
delay = int(args.delay) if args.delay != None else 10
lemma = args.lemma == 'true'
doLookup = args.lookup != 'false'
makelemma = args.makelemma == 'true'

importvocab = None
if importJSON != None:
    print(f'importing from {importJSON}')
    with open(args.doImport, 'r') as f:
        importvocab = json.loads(f.read())
        if "vocab_overview" in importvocab and "language_string" in importvocab:
            language = importvocab["language_string"]
            languageKey = importvocab["learning_language"]
            if languageKey not in languagesInfo:
                print(f'Unknown language key "{languageKey}"; choices are {[key for key in languagesInfo]}')
                sys.exit(1)
            languageInfo = languagesInfo[languageKey]
        else:
            print(f'Import file in bad format')
            sys.exit(1)

googleLanguageKey = languageInfo["tla"]
rowitems = languageInfo["rowitems"]

jsonfile = f'dl-{language.lower()}-words.json'

if makelemma and languageInfo["makeLemma"] == None:
    print(f'cannot do --makelemma for {language}')
    sys.exit(1)

print(f'Language is: {language}, makelemma={makelemma}, key={languageKey}{f", scanning {maxcount} max records" if maxcount != 0 else ""}')

# Import is JSON format you'd get from https://preview.duolingo.com/vocabulary/overview

words = {}
originalJSON = None
skippedwords = []
hasJsonFile = os.path.exists(jsonfile)
if hasJsonFile:
    with open(jsonfile, 'r') as f:
        originalJSON = f.read()
        words = json.loads(originalJSON)
        if "_skipped" in words:
            skippedwords = words["_skipped"]
        else:
            words["_skipped"] = skippedwords
else:
    print(f'Database file {jsonfile} does not exist, must be new import')

def isLemma(word, info):
    lemmaword = languageInfo["makeLemma"](word, info)
    if word == lemmaword:
        ret = True
    else:
        ret = False

    print(f'isLemma: word={word} vs {lemmaword} => {ret}')
    return ret

newWordsImported = []
if importvocab != None:
    for vocab in importvocab["vocab_overview"]:
        word = vocab["word_string"]
        if word not in words and word not in skippedwords:
            # If in lemma-only mode, only include if it's an infinitive
            if lemma and not isLemma(word, vocab):
                continue
            
            newWordsImported.append(word)
            words[word] = { }

        # Update anything necessary
        if word in words:
            if vocab.get("infinitive") != "" and vocab.get("infinitive") != None:
                words[word]["infinitive"] = vocab["infinitive"]
            if vocab.get("skill_url_title") != "" and vocab.get("skill_url_title") != None:
                words[word]["skill"] = vocab["skill_url_title"]
            if vocab.get("gender") != "" and vocab.get("gender") != None:
                words[word]["gender"] = vocab["gender"]
            if vocab.get("rel") != "" and vocab.get("gender") != None:
                words[word]["gender"] = vocab["gender"]

if len(newWordsImported) > 0:
    print(f'new words imported: {newWordsImported}')

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

baseurl = f'https://preview.duolingo.com/dictionary/{language}'
print(baseurl)

lastrequest = 0
def delayIfNeeded():
    global lastrequest
    curtime = int(time.time())
    timeleft = (lastrequest+delay) - curtime
    if timeleft > 0:
        print(f'waiting {timeleft} seconds')
        while timeleft > 0:
            curtime = int(time.time())
            timeleft = (lastrequest+delay) - curtime
            # print(f'timeleft {timeleft}')
            time.sleep(1)
    lastrequest = curtime

def getdef(wordurl, languageKey):
    openbrowser()
    browser.get(wordurl)
    # //*[@id="root"]/div/div[4]/div/div[2]/div/div[1]/div/div[1]/div[1]/h3
    # /html/body/div[1]/div/div[4]/div/div[2]/div/div[1]/div/div[1]/div[1]/h3
    try:
        translation = browser.find_element(By.XPATH, "//h2[text()='Translation']/../div[1]/h3")
        print(f'trans: -> {translation.text}')
        if translation != None:
            return translation.text
    except:
        # Look for the word-for-word translation
        langAttr = f'en-x-mtfrom-{languageKey}'
        els = browser.find_elements_by_css_selector(f'h2[lang={langAttr}]')
        if len(els) > 0:
            return els[0].text
        pass
    return None

# Single word lookup
if args.singlelookup != None:
    word = args.singlelookup
    print(f'looking up {word}')
    info = words[word]
    print(f'def {getdef(info["duo"], languageKey)}')
    sys.exit(0)

TOO_MANY_REQUESTS = "*************** TOO MANY REQUESTS *******************"
def lookup(word):
    delayIfNeeded()
    openbrowser()
    browser.get(baseurl)
    els = browser.find_elements_by_css_selector('input[data-test=dictionary-search-input]')
    textfield = els[0]
    # print(textfield)
    textfield.send_keys(word)
    lookupbutton = browser.find_elements_by_css_selector('button[data-test=dictionary-translate]')[0]
    lookupbutton.click()
    try:
        element = browser.find_element(By.XPATH, "//h2[text()='Translation']")
        return browser.current_url
    except:
        # See if it's "too many requests"
        pageSource = browser.page_source
        if pageSource != None and "too many requests" in pageSource.lower():
            return TOO_MANY_REQUESTS
        return browser.current_url

def stripsuffix(word):
    if '(' not in word: return word
    else: return word.split('(')[0]

def urlquote(word):
    return urllib.parse.quote_plus(word)

def handleLanguageSpecific(info, word, languageKey):
    if languageKey == 'hw':
        info["wehe"] = f"https://hilo.hawaii.edu/wehe/?q={stripsuffix(urlword)}"

def hydrateInfo(info):
    global count
    changedduo = False
    if ('duo' not in info or forcescan) and doLookup:
        print(f'lookup {word}')
        count += 1
        if maxcount != 0 and count > maxcount: return False
        url = lookup(word)
        if url == TOO_MANY_REQUESTS:
            return False   # Give up - not sure when it will be available again
        print(f'{word} => {url}')
        info['duo'] = url
        changedduo = True

    urlword = urlquote(word)
    handleLanguageSpecific(info, word, languageKey)

    info["google"] = f"https://translate.google.com/?sl={googleLanguageKey}&tl=en&text={urlword}%0A&op=translate"

    if ('duodef' not in info or changedduo) and 'duo' in info:
        info['duodef'] = getdef(info['duo'], languageKey)

    if ("english" not in info or info["english"] == "") and 'duodef' in info:
        info["english"] = info['duodef']

    if "parts" not in info:
        info["parts"] = ""

    return True

# Makelemma mode is special
if makelemma:
    newwords = {}
    for word in words:
        info = words[word]

        if word in controlWords:
            newwords[lemmaform] = json.loads(json.dumps(info))
            continue

        lemmaform = languageInfo["makeLemma"](word, info)
        if word == 'valise':
            print(f'valise: word={word} lemmaform={lemmaform}')
            print(f'words[lemmaform] = {words[lemmaform]}')
            print(f'info={info}')
            print(f'lemmaform in words={lemmaform in words}')
            # sys.exit(0)
        if lemmaform in words:      # The lemma form is already here
            if lemmaform == 'valise':
                print(f'already: for valise, info={info} words[lemmaform]={words[lemmaform]}')
            #     sys.exit(0)
            newwords[lemmaform] = json.loads(json.dumps(words[lemmaform]))
        else:
            if lemmaform == 'valise':
                print(f'new: for valise, info={info}')
            #     sys.exit(0)
            newwords[lemmaform] = json.loads(json.dumps(info))
    # print(words)
    # print(newwords)
    # sys.exit(0)
    # Also copy the controlWords
    for controlWord in controlWords:
        if controlWord in words: newwords[controlWord] = json.loads(json.dumps(words[controlWord]))

    # Only proceed if force=true
    if not doForce:
        print(f'\nmakelemma results (--force true to commit):')
        print(f'word count before {len(words)} after {len(newwords)}')
        added = {}
        removed = {}
        changed = {}
        for word in words:
            info = words[word]
            if word not in newwords: removed[word] = info
            elif info != newwords[word]: changed[word] = info
        for word in newwords:
            info = newwords[word]
            if word not in words: added[word] = info
        print(f'added: {added.keys()}')
        print(f'removed: {removed.keys()}')
        print(f'changed:')
        for word in changed:
            print(f'  {word}')
            print(f'  - {words[word]}')
            print(f'  + {newwords[word]}')
        tempJsonFile = 'lemmas.tmp.json'
        print(f'writing to {tempJsonFile}')
        with open(tempJsonFile, 'w') as f:
            f.write(json.dumps(newwords, indent=2))
        sys.exit(0)
    words = newwords
else:
    # Don't read from deck by default: use jsonfile, already read into `words`
    # with io.open(csvfileName, 'r', newline='\n', encoding='UTF-8') as csvfile:
    #     csvreader = csv.reader(csvfile, delimiter=',', quotechar='"')
    #     for row in csvreader:
    count = 0
    for word in words:
        if word in controlWords: continue
        
        # See if we need to look it up in Duolingo first
        info = words[word]

        if not hydrateInfo(info):
            break
        # print(f'{word} => {defn}')

# Write new JSON, but only if it's changed
newJSON = json.dumps(words, indent=2)
hasChanges = (originalJSON != newJSON)

saveJsonFile = None
if doForce or (hasChanges and importJSON == None):
    saveJsonFile = jsonfile
elif hasChanges:
    saveJsonFile = jsonfile + ".tmp"
    print(f'Import without force, not saving to {jsonfile}')
else:
    print(f'No change, not saving to {jsonfile}')

if saveJsonFile != None:
    if os.path.exists(saveJsonFile):
        jsonbak = saveJsonFile.replace('.json', '.bak')

        print(f'backing up {saveJsonFile} to {jsonbak}')
        shutil.copyfile(saveJsonFile, jsonbak)

    print(f'writing to {saveJsonFile}')
    with open(saveJsonFile, 'w') as f:
        f.write(newJSON)

def makeRow(info):
    global rowitems
    row = [word]
    for item in rowitems:
        if item in info:
            row.append(info[item])
        else:
            row.append("")
    return row

if exportFileName != None:
    print(f'writing deck to {exportFileName}')
    with open(exportFileName, 'w', encoding='utf-8', newline='') as f:
        csvwriter = csv.writer(f, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        for word in words:
            info = words[word]

            if word in controlWords: continue
            print(f'{word} lemma {lemma} info {info.get("infinitive")}')
            if lemma and info.get("infinitive") != None and info["infinitive"] != word:
                print("... skipping")
                # Only skip if the infinitive itself is also being exported
                # infinitive = info["infinitive"]
                # if infinitive in words: 
                continue

            row = makeRow(info)
            csvwriter.writerow(row)

if browser != None: browser.close()
sys.exit(0)
