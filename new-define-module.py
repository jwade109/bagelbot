#! /usr/bin/python3

import sys
from dataclasses import dataclass, field
from typing import List
import wikipediaapi
import yaml
from wiktionaryparser import WiktionaryParser
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
    for res in results:
        pretty_print_definition(res)
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


def do_wikipedia(word):
    page = wikipedia.page(word)
    if not page.exists():
        return False
    is_stub = len(page.summary) < 150
    is_referral = "may refer to" in page.summary or "may also refer to" in page.summary
    print(f"{page.title} -- {page.fullurl} {'WEIRD' if (is_stub or is_referral) else ''}")
    s = page.text if (is_stub or is_referral) else page.summary
    s = s.replace("(, ", "(").replace(" )", ")").replace("(; ", "(")
    s = "\n\n".join([x for x in s.split("\n") if x])
    s = crop_text_nicely(s, 800)
    print(f"\n{s}")
    return True
    # print("SECTIONS")
    # for section in page.sections:
    #     print_section_titles_recursively(section)


def main():
    word = " ".join(sys.argv[1:])
    r1 = do_wiktionary(word)
    r2 = do_wikipedia(word)
    if not r1 and not r2:
        print(f"Couldn't find anything on {word}.")

if __name__ == "__main__":
    main()


