# Hawaiian word frequency repo
This is a simple project that presents the top X words in Hawaiian, as determined by scanning the corpus of the Hawaiian newspaper archive at http://www.nupepa.org/. Most newspapers are before 1914, most during the Kingdom period. For consistency, I convert everything to the old-style (kahiko) writing, without kahako or ʻokina. However, I have not found this to be a major impediment for using the list as a learning aid.

# How do I use it?
Download the top-X file you want. Go thru the list, starting from the beginning, and see which words you don't know. Look them up on https://hilo.hawaii.edu/wehe/ to find their usages in context. Then put then in anki and learn them. Rinse and repeat.

# Aren't these words too old/specialized?
Technically, this list is most useful if you are planning on writing newspaper articles in the period before 1914. However, I have scanned down the list, and all commonly-used words are present. (This was also done by a friend who is much more fluent in Hawaiian than I am, and he came to the same conclusion.) It is true, words like "au", "ʻoe", etc. would probably come up a bit more in conversational speech than in a newspaper. However, "au" is #38 and "ʻoe" is #50; would it really make much difference if they were #20 and #25?

I also have done some comparison using the top 50k Italian words at https://github.com/hermitdave/FrequencyWords/tree/master/content/2018/it. These were gleaned from the opensubtitles.org project are are subtitles from movies and TV. I scanned the first 500 words, and none of these were particularly "new" or "specialized"; I cannot imagine any of them not being in common use 100 years ago. And aside from some colloquialisms (shortenings, semi-vulgar slang, etc.), any of the top 500 would be as much at home in a newspaper as in colloquial speech.

# Files in repo
* The top-X lists - with ordering and how many of each word were found in the corpus. Note that it gives you the sequence numbering for each word. I find this very useful in language learning. "They" say you need about 2000 words to achieve B1 proficiency on the CEFR scale. I suspect the number in Hawaiian is lower than that, but it gives you a comparison.
* hawaiian-texts.yaml - the entire corpus, currently totally 1377 documents. It contains all the text, but before any rules were applied. As you can see, it contains a significant quantity of English text. The basic rule applied was: whenever a word containing non-Hawaiian letters is found, start skipping words and keep skipping until 2 words with only Hawaiian letters is found. All punctuation, HTML entities, and kahako/ʻokina are also stripped. This file also contains (in the `exceptions` element at the front) the list of exceptions to the "non-Hawaiian letters" rule. These are words that are considered Hawaiian, even if they contain other letters, and optionally what word to map them to.
* hawaiian-skipped.yaml - words that were skipped, along with their context.

# Making Duolingo flashcards

There's a separate function, `lookup-words.py`, which builds and maintains Duolingo vocab decks in Anki. The process is automated and (theoretically anyway) works for any language. The decks I've built are available at 

https://ankiweb.net/shared/byauthor/2085481698

Currently, the following languages are supported, but you can (fairly) easily add more by modifying `lookup-words.py`. Let me know if you want help with this.

|Abbrev|Language|
|------|--------|
|hw|Hawaiian|
|it|Italian|
|eo|Esperanto|
|fr|French|
|es|Spanish|

Prerequisites on your local computer are:
* Have python 3.6 or higher installed
* Have Chromedriver.exe installed in the local directory that matches the version of Chrome you are using
* Install Selenium with `pip install selenium`

To build decks, here's an outline of steps:
1. Choose a language that you've done. The decks will only consist of words you've seen in the language(s) you're studying. Select that language in Duolingo as your "studying" language. If it's not one of the above, contact me.
2. In a browser, go to https://preview.duolingo.com/vocabulary/overview It will result in a JSON file, which you should save to local disk. I usually call these files `xx-overview.json` where `xx` is the two letter abbreviation for the language.
3. Run the command `python src\lookup-words.py --language xx --import xx-overview.json --makelemma true --force true`. This will create the JSON file `dl-xxxxx-words.json`, where `xxxxx` is the full name (not the abbreviation) of the language. This file has all the words, but not the definitions.
4. Lookup the definitions in Duolingo using the command `python src\lookup-words.py --language xx`. This will look up the words in the Duolingo dictionary and fill in default definitions in the same file. It has built-in time delays so Duolingo doesn't lock you out, and there are a bunch of other parameter you might want to use. The most common would be `maxcount`, which limits how many words it looks up in one go. I usually limit this to around 500, just to make sure if something goes south I don't lose everything.
5. Tweak the definitions if you want by editing `dl-xxxxx-words.json`. The `duodef` element is the Duolingo definition, while the `english` element is your definition. They start out the same, but you can tweak the `english` if you want.
6. Create a CSV file using `python src\lookup-words.py --export xx.csv --language xx --lemma true`.
7. Now you're ready to import into Anki! Importing into Anki is a little complex, but here is an outline.
  * You'll need to have a note type created. If it's one of the languages I already have in https://ankiweb.net/shared/byauthor/2085481698, download the deck and use the corresponding note type, e.g. `Duolingo Italian`. Otherwise, I recommend that you download one of my decks like https://ankiweb.net/shared/info/43682733 and edit the `Duolingo Italian` note type for your own use as follows.
  * Change the note type name to match your language.
  * Change the name of the `Italian` field to whatever you want. Do NOT change the order of the fields.
  * Go into the card definitions and change the list of links at the end. I usually create a bunch of links to go to google, wiktionary, and whatever other language-specific reference sites I can think of.