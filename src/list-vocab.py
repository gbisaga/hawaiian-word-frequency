import sys
import argparse
import re
from os import path
from html.parser import HTMLParser
import AdvancedHTMLParser
import json
import requests
import yaml
import time

html = AdvancedHTMLParser.AdvancedHTMLParser()

parser = argparse.ArgumentParser()
parser.add_argument('--file', required=True, help="file to read or write raw data")
parser.add_argument('--url', help="base url")
parser.add_argument('--maxurls', help="maximum number of urls")
parser.add_argument('--pull', help="if true, pull data; default is process existing data file")
parser.add_argument('--top', help="only output top X words")
parser.add_argument('--out', required=True, help="top X words output file")
args = parser.parse_args()

url = args.url if args.url != None else "http://nupepa.org/gsdl2.5/cgi-bin/nupepa?e=p-0nupepa--00-0-0--010---4-----text---0-1l--1haw-Zz-1---20-about---0003-1-0000utfZz-8-00&a=d&cl=CL1"
max_url_count = int(args.maxurls) if args.maxurls != None else -1
datafilename = args.file
pull = args.pull == "true"
outfilename = args.out
topx = int(args.top) if args.top != None else -1

entities = [ "&quot;", "&nbsp;"]

def getSubLinks(url, matcher, prevLinks):
    sublinks = []
    baseresponse = requests.get(url)
    basedata = baseresponse.content
    # print("basedata", basedata, "<<-- basedata")

    # Find all the links
    html.parseStr(basedata)
    for link in html.getElementsByTagName('a'):
        href = link.href
        if href != None:
            href = f'http://nupepa.org{href}'
            if matcher in href and href not in prevLinks and not href.endswith('.pr'):  # 
                sublinks.append(href)
    
    return sublinks

def cleanhtml(raw_html):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext.lower()

def replaceKahako(text):
    if "ā" in text:
        text = text.replace("ā", "a")
    if "ē" in text:
        text = text.replace("ē", "e")
    if "ī" in text:
        text = text.replace("ī", "i")
    if "ō" in text:
        text = text.replace("ō", "o")
    if "ū" in text:
        text = text.replace("ū", "u")
    return text

non_hawaiian_words = {}     # All the words deemed "not Hawaiian" after applying the exceptions; value is a list of the skipped text, keyed by first word found
hawaiian_exceptions = {}    # All the words otherwise determined to be Hawaiian (lowercased); if a value other than "true", what they map to
NUM_HAWAIIAN_WORDS_AFTER_BREAK = 2

def processText(text, words, title, year):
    non_processed_words = ""
    non_hawaiian_count = 0
    skip_words = []
    for word in text.split(" "):
        if word == "": continue

        # Reject words with any non-Hawaiian letters, as well as some words
        # in their context. This will take some tweaking, but we'll say:
        # * start skipping words when we see a non-hawaiian letter
        # * after it starts skipping, we have to see NUM_HAWAIIAN_WORDS_AFTER_BREAK words with only
        #   Hawaiian letters to stop skipping
        # * all the words in the meantime will be logged
        # print('check re', word, "=>", (non_hawaiian_pattern.match(word)))
        is_exception = hawaiian_exceptions.get(word)
        non_hawaiian = non_hawaiian_pattern.match(word) != None and is_exception == None
        # print(f'{word} is_exception {is_exception} ({type(is_exception)}) non_hawaiian {non_hawaiian}')
        if non_hawaiian:
            skip_words.append(word)
            # print(f'non-hawaiian in {word}, starting/continuing skip')
            non_hawaiian_count = NUM_HAWAIIAN_WORDS_AFTER_BREAK
            non_processed_words += word + " "
        elif non_hawaiian_count > 0:
            # print(f'only hawaiian in {word}, decrementing skip {non_hawaiian_count}')
            non_hawaiian_count -= 1
            non_processed_words += word + " "
        else:
            if non_processed_words != "":
                for skip_word in skip_words:
                    skiplist = non_hawaiian_words.get(skip_word)
                    if skiplist == None:
                        skiplist = []
                        non_hawaiian_words[skip_word] = skiplist
                    skiplist.append(non_processed_words)
                skip_words = []
                non_processed_words = ""

            # Transform if necessary
            if is_exception != None and is_exception != True:
                word = is_exception
                # print(f'transform {word} to {is_exception}')

            cur = words.get(word.strip())
            cur = 1 if cur == None else cur + 1
            words[word.strip()] = cur

texts = {
    'texts': []
}

existing_text_urls = []

# See if read in existing
if path.exists(datafilename):
    print(f'reading existing {datafilename}')
    with open(datafilename) as file:
        texts = yaml.load(file, Loader=yaml.FullLoader)
        print(f'read {len(texts["texts"])} existing texts')
        existing_text_urls = [text["src"] for text in texts["texts"]]

        # Process exceptions, if any
        if "exceptions" in texts:
            for exception in texts["exceptions"]:
                v = texts["exceptions"][exception]
                e = True if v == "true" else v
                hawaiian_exceptions[exception.lower()] = e
            print(f'exceptions: {hawaiian_exceptions}')

print(f'existing urls: {existing_text_urls}')

def processTextURL(url):
    global texts

    sleep_time = 1
    for cur_try in range(max_tries):
        try:
            response = requests.get(url)
            str_data = response.content

            html.parseStr(str_data)
            # print(str_data)
            title = "unknown"
            title_els = html.getElementsByTagName('title')
            # print(title_els)
            for title_el in title_els:
                title = title_el.innerHTML
            print(f'title: {title}')

            text = ""
            for section in html.getElementsByClassName('Section1'):
                # print('type: ', type(section))    
                # print('innerhtml: ', section.innerHTML, "<<-- innerHTML")
                # print('innerText: ', section.innerText, "<<-- innerText")
                ttext = cleanhtml(section.innerHTML)
                for entity in entities:
                    ttext = ttext.replace(entity, '')
            
                # In case any kahakos snuck in
                ttext = replaceKahako(ttext)

                ttext = re.sub(r'[^a-zA-Z ]', '', ttext.replace("\n", " "))
                text += ttext + " "

            text = text.replace("  ", " ")

            # # Pre-process the text by removing the words that are obviously not Hawaiian
            # raw_words = text.split(" ")
            # text = ""
            # for word in raw_words:
            #     if word == "": continue

            #     # Reject words with any non-Hawaiian letters
            #     # print('check re', word, "=>", (non_hawaiian_pattern.match(word)))
            #     if non_hawaiian_pattern.match(word) == None:
            #         word = word.strip()
            #         text = text + word + " "

            texts['texts'].append({
                'src': url,
                'title': title,
                'text': text
            })

            return
        except:
            print(f'exception fetching, re-try {cur_try+1}/{max_tries} after sleep {sleep_time} sec')
            time.sleep(sleep_time)
            sleep_time *= 2

non_hawaiian_pattern = re.compile(r'.*[^aeiouhklmnpw].*')
max_tries = 5

if pull:
    print('pulling data from nupepa.org')
    toplinks = getSubLinks(url, 'c=nupepa', {})

    print('toplinks', toplinks, '<<-- toplinks\n\n')

    textlinks = []

    url_count = 0
    all_done = False

    for toplink in toplinks:
        if all_done: break

        print(f'\ngetting from top-level link: {toplink}')
        l2links = getSubLinks(toplink, 'c=nupepa', toplinks)

        for l2link in l2links:
            if all_done: break
            print(f'getting from l2 link: {l2link}')
            l3links = getSubLinks(l2link, 'gg=text', toplinks)

            for l3link in l3links:
                url_count += 1
                if max_url_count > 0 and url_count > max_url_count:
                    all_done = True
                    break

                # Don't process URL if we already did
                if l3link in existing_text_urls:
                    print(f'already read text URL: {l3link}')
                else:
                    textlinks.append(l3link)

    print(f'total files: {len(textlinks)}')

    url_count = 0
    for url in textlinks:
        print(f'url', url)
        url_count += 1
        processTextURL(url)

    # Have all the texts, write them
    with open(datafilename, 'w') as file:
        documents = yaml.dump(texts, file)

print(f'processing words from {len(texts["texts"])} texts')
words = {}
url_count = 0
for text in texts["texts"]:
    # Also process max url count
    url_count += 1
    if max_url_count > 0 and url_count > max_url_count:
        break

    title = text["title"]
    year = ""
    yearmatches = re.findall(r'[^0-9]([0-9][0-9][0-9][0-9])([^0-9]|$)', title)
    if yearmatches:
        for tyear in yearmatches[0]:
            tyear = int(tyear)
            if tyear >= 1800 and tyear <= 2000:
                year = tyear
                break

    print(f'processing title: {title} (year {year})')
    processText(text["text"], words, title, year)

word_list = [{'w': w, 'c': words[w]} for w in words]
sorted_words = sorted(word_list, key=lambda el: el['c'], reverse=True)
cnt = 1
with open(outfilename, 'w') as file:
    for el in sorted_words:
        if topx > 0 and cnt > topx: break

        file.write(f"{cnt},{el['w']},{el['c']}\n")
        cnt += 1

skipfilename = 'hawaiian-skipped.yaml'
print(f'generating skipfile {skipfilename}')
with open(skipfilename, 'w') as file:
    yaml.dump(non_hawaiian_words, file)
    # for nhw in non_hawaiian_words:
    #     print(f'skipped: {nhw}')
    #     for ex in non_hawaiian_words[nhw]:
    #         print(f' in: {ex}')

