import sys
from string import ascii_lowercase

VOWELS = "aeiou"
CONSONANTS = ''.join([c for c in ascii_lowercase if c not in VOWELS])

VOWELS += VOWELS.upper()
CONSONANTS += CONSONANTS.upper()


def clength(word):
    if not word:
        return 0
    i = 0
    while i < len(word) and word[i] in CONSONANTS:
        i += 1
    return i


def spoonerify(left, right):

    print(left, right)

    cll = clength(left)
    clr = clength(right)

    if not cll or not clr:
        return

    a = left[:cll]
    b = left[cll:]
    c = right[:clr]
    d = right[clr:]

    print(c + b, a + d)



def main():
    left, right = sys.argv[1:3]
    spoonerify(left, right)


if __name__ == "__main__":
    main()
