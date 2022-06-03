#! /usr/bin/python3

import sys
from dataclasses import dataclass, field
from typing import List
import wikipediaapi
import yaml
from wiktionaryparser import WiktionaryParser
from bs4 import BeautifulSoup
import requests
wiktionary = WiktionaryParser()
wikipedia = wikipediaapi.Wikipedia('en',
    extract_format=wikipediaapi.ExtractFormat.WIKI)


@dataclass()
class Definition:
    word: str = ""
    part_of_speech: str = ""
    tense_summary: str = ""
    definitions: List[str] = field(default_factory=list)


def pretty_print_definition(d: Definition):
    print(f"{d.word.capitalize()} - {d.part_of_speech}")
    # print(d.tense_summary)
    for entry in d.definitions:
        print(f"-- {entry}")


def do_wiktionary(word) -> List[Definition]:
    defined = wiktionary.fetch(word)
    if not defined:
        return []
    results = []
    for entry in defined:
        # print("======")
        # print(entry.keys())
        definitions = entry["definitions"]
        # print(f"{len(definitions)} definitions.")
        for definition in definitions:
            # print(yaml.dump(definition))
            d = Definition()
            d.word = word # perhaps unnecessary
            d.part_of_speech = definition["partOfSpeech"]
            d.tense_summary = definition["text"][0]
            d.definitions = definition["text"][1:]
            results.append(d)
    return results


def print_section_titles_recursively(section, level=0):
    print(" "*level + section.title)
    for s in section.sections:
        print_section_titles_recursively(s, level+1)


def crop_text_nicely(text: str, n_characters: int) -> str:
    sentences = text.split(" ")
    running_sum = 0
    dotdotdot = False
    to_join = []
    for sentence in sentences:
        running_sum += len(sentence)
        if running_sum + 3 > n_characters:
            dotdotdot = True
            break
        to_join.append(sentence)
    return " ".join(to_join) + ("..." if dotdotdot else "")


@dataclass()
class WikiPage:
    title: str = ""
    url:   str = ""
    text:  str = ""
    is_referral: bool = False
    is_stub:     bool = False
    is_math:     bool = False


def pretty_print_wikipage(w: WikiPage):
    print(f"{w.title} -- {w.url} -- {w.is_math}\n")
    s = crop_text_nicely(w.text, 400)
    print(s)


def do_wikipedia(word):
    page = wikipedia.page(word)
    if not page.exists():
        return None


    ret = WikiPage()
    ret.is_stub = len(page.summary) < 150
    ret.is_referral = "may refer to" in page.summary or "may also refer to" in page.summary
    # print(f"{page.title} -- {page.fullurl} {'WEIRD' if (is_stub or is_referral) else ''}")
    s = page.text if (ret.is_stub or ret.is_referral) else page.summary
    ret.is_math = "\displaystyle" in s
    s = s.replace("(, ", "(").replace(" )", ")") \
         .replace("(; ", "(").replace("() ", "") \
         .replace("(), ", "")
    if ret.is_referral:
        s = "\n~ ".join([x for x in s.split("\n") if x])
    else:
        s = "\n\n".join([x for x in s.split("\n") if x])
    s = crop_text_nicely(s, 800)
    ret.text = s
    ret.title = page.title
    ret.url = page.fullurl
    return ret

    # print(f"\n{s}")
    # return 1
    # print("SECTIONS")
    # for section in page.sections:
    #     print_section_titles_recursively(section)


def main():
    word = " ".join(sys.argv[1:])
    if not word:
        print("Need a word.")
        return 1

    wikipage = do_wikipedia(word)
    wikidefs = do_wiktionary(word)

    if not wikipage and not wikidefs:
        print(f"Couldn't find anything on {word}.")
        return 1

    if not wikipage or wikipage.is_referral:
        for res in wikidefs:
            pretty_print_definition(res)
        print("\n~ ~ ~ ~ ~ ~ ~\n")
    pretty_print_wikipage(wikipage)

if __name__ == "__main__":
    main()


