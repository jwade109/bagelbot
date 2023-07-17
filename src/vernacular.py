import sys
import random
import re
from bblog import log


BAD_CATEGORY_FALLBACK = "CALL_AN_AMBULANCE"


def sarcastify(sentence):
    return ''.join(map(random.choice, zip(sentence.lower(), sentence.upper())))


SENTENCE_ENHANCERS = \
{
    "GREETING":
    [
        "hi",
        "hello",
        "hi there",
        "hello there",
        "howdy",
        "greetings",
        "salutations"
    ],
    "NICE":
    [
        "good",
        "great",
        "nice",
        "terrific"
    ],
    "HEY":
    [
        "hey",
        "hey you",
        "yo",
        "oy",
        "oy mate",
        "ahoy matey",
        "howdy"
    ],
    "APOLOGY":
    [
        "sorry",
        "my apologies",
        "apologies",
        "so sorry",
        "my bad",
        "whoops",
        "hmmmm"
    ],
    "COULD_NOT":
    [
        "could not",
        "couldn't",
        "failed to",
        "wasn't able to",
        "was not able to",
        "couldn't be bothered to",
        "could not be bothered to",
        "just couldn't",
        "just could not"
    ],
    "UNDERSTAND_THAT":
    [
        "understand that",
        "make heads or tails of that",
        "figure that out",
        "figure that one out"
    ],
    "THATS_NOT":
    [
        "that's not",
        "that is not",
        "that isn't"
    ],
    "DONT_KNOW_WHAT_UR_ON_ABOUT":
    [
        "I don't know what you're on about.",
        "Have you gone mad?",
        "Have you got a screw loose?",
        "Are you having a bad day?",
        "Try again later.",
        "Thanks for playing.",
        "Ask Wade for help, maybe.",
        "You want to go home and rethink your life."
    ],
    BAD_CATEGORY_FALLBACK:
    [
        "call an ambulance, I'm having a stroke",
        "wow, something is wrong",
        "something's wrong, I can feel it",
        "do you ever worry that God is real, or that he isn't",
        "all is vanity",
        "hi nothing is wrong I promise"
    ]
}



def enhance_sentence(sentence):
    log.debug(f"Enhancing: {sentence}")
    formatter_regex = r"\(\(([\^\$\&\*])?([\w]+)\)\)"
    match = re.search(formatter_regex, sentence)
    while match:
        category = match.group(2)
        opts = match.group(1)
        if category not in SENTENCE_ENHANCERS:
            print(f"Bad category: {category}")
            category = BAD_CATEGORY_FALLBACK
            opts = "*"
        repl = random.choice(SENTENCE_ENHANCERS[category])
        if opts == "^":
            repl = repl.upper()
        elif opts == "&":
            repl = repl.lower()
        elif opts == "$":
            repl = repl.capitalize()
        elif opts == "*":
            repl = sarcastify(repl)
        elif opts is not None:
            log.error(f"Bad format option: {opts}")
        sentence = sentence[:match.start()] + repl + sentence[match.end():]
        match = re.search(formatter_regex, sentence)
    if random.random() < 0.01:
        sentence = sarcastify(sentence)
    log.debug(f"Returning: {sentence}")
    return sentence


def main():

    # sentence = "(($GREETING)), ((MY_NAME_IS)) Bagelbot. ((^NICE)) to meet you!"

    sentence = "(($APOLOGY)), I ((COULD_NOT)) ((UNDERSTAND_THAT)). "

    if sys.argv[1:]:
        sentence = " ".join(sys.argv[1:])

    print(sentence)
    for i in range(10):
        print(enhance_sentence(sentence))



if __name__ == "__main__":
    main()