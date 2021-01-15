# Hawaiian word frequency repo
This is a simple project that presents the top X words in Hawaiian, as determined by scanning the corpus of the Hawaiian newspaper archive at http://www.nupepa.org/. Most newspapers are before 1914, most during the Kingdom period. For consistency, I convert everything to the old-style (kahiko) writing, without kahako or ʻokina. However, I have not found this to be a major impediment for using the list as a learning aid.

# How do I use it?
Download the top-X file you want. Go thru the list, starting from the beginning, and see which words you don't know. Look them up on https://hilo.hawaii.edu/wehe/ to find their usages in context. Then put then in anki and learn them. Rinse and repeat.

# Aren't these words too old/specialized?
Technically, this list is most useful if you are planning on writing newspaper articles in the period before 1914. However, I have scanned down the list, and all commonly-used words are present. (This was also done by a friend who is much more fluent in Hawaiian than I am, and he came to the same conclusion.) It is true, words like "au", "ʻoe", etc. would probably come up a bit more in conversational speech than in a newspaper. However, "au" is #38 and "ʻoe" is #50; would it really make much difference if they were #20 and #25?

I also have done some comparison using the top 50k Italian words at https://github.com/hermitdave/FrequencyWords/tree/master/content/2018/it. These were gleaned from the opensubtitles.org project are are subtitles from movies and TV. I scanned the first 500 words, and none of these were particularly "new" or "specialized"; I cannot imagine any of them not being in common use 100 years ago. And aside from some colloquialisms (shortenings, semi-vulgar slang, etc.), any of the top 500 would be as much at home in a newspaper as in colloquial speech.

# Files in repo
* The top-X lists - with ordering and how many of each word were found in the corpus
* hawaiian-texts.yaml - the entire corpus, currently totally 1377 documents. It contains all the text, but before any rules were applied. As you can see, it contains a significant quantity of English text. The basic rule applied was: whenever a word containing non-Hawaiian letters is found, start skipping words and keep skipping until 2 words with only Hawaiian letters is found. All punctuation, HTML entities, and kahako/ʻokina are also stripped. This file also contains (in the `exceptions` element at the front) the list of exceptions to the "non-Hawaiian letters" rule. These are words that are considered Hawaiian, even if they contain other letters, and optionally what word to map them to.
* hawaiian-skipped.yaml - words that were skipped, along with their context.
