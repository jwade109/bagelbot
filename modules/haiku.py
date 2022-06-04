
# for counting syllables for haiku detection
from curses.ascii import isdigit
from nltk.corpus import cmudict
CMU_DICT = cmudict.dict()

import itertools

def detect_haiku(string):

    def count_syllables(word):
        low = word.lower()
        if low not in CMU_DICT:
            return None
        syl_list = [len(list(y for y in x if isdigit(y[-1]))) for x in CMU_DICT[low]]
        syl_list = list(set(syl_list))
        if not syl_list:
            return None
        return syl_list[0]

    string = string.split(" ")
    lens = [count_syllables(x) for x in string]
    if None in lens:
        return None
    cumulative = list(itertools.accumulate(lens))
    if cumulative[-1] != 17 or 5 not in cumulative or 12 not in cumulative:
        return None
    first = " ".join(string[:cumulative.index(5) + 1])
    second = " ".join(string[cumulative.index(5) + 1:cumulative.index(12) + 1])
    third = " ".join(string[cumulative.index(12) + 1:])
    return first, second, third
