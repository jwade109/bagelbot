import os
import logging
from ws_dir import WORKSPACE_DIRECTORY
from datetime import datetime
import hashlib


log = logging.getLogger("resources")
log.setLevel(logging.DEBUG)


# this entire block below is for populating a LOT of resource paths,
# and making it very obvious if (due to negligence, malfeasance, etc)
# the path does not exist, because that's bad
def check_exists(path):
    if not os.path.exists(path):
        print(f"WARNING: required path {path} doesn't exist!")
        log.warning(f"Required path {path} doesn't exist!")
    return path


def ckws(path):
    return check_exists(WORKSPACE_DIRECTORY + path)


# begin filesystem resources
# using absolute filepaths so this can be run via a chron job
FART_DIRECTORY = ckws("/media/farts")
RL_DIRECTORY = ckws("/media/rl")
UNDERTALE_DIRECTORY = ckws("/media/ut")
STAR_WARS_DIRECTORY = ckws("/media/sw")
SPONGEBOB_DIRECTORY = ckws("/media/sb")
MULANEY_DIRECTORY = ckws("/media/jm")
CH_DIRECTORY = ckws("/media/ch")
SOTO_PATH = ckws("/media/images/soto.png")
SOTO_PARTY = ckws("/media/sounds/soto_party.mp3")
SOTO_TINY_NUKE = ckws("/media/sounds/tiny_soto_nuke.mp3")
WOW_PATH = ckws("/media/sounds/wow.mp3")
GK_PATH = ckws("/media/sounds/genghis_khan.mp3")
GUNTER_PATH = ckws("/media/sounds/gunter.mp3")
GASGASGAS_PATH = ckws("/media/sounds/gasgasgas.mp3")
BILLNYE_PATH = ckws("/media/sounds/bill_nye_the_science_guy.mp3")
HELLO_THERE_PATH = ckws("/media/sw/obi_wan_kenobi/hello_there.mp3")
SWOOSH_PATH = ckws("/media/sw/mace_windu/swoosh.mp3")
OHSHIT_PATH = ckws("/media/sounds/ohshit.mp3")
YEAH_PATH = ckws("/media/sounds/yeah.mp3")
GOAT_SCREAM_PATH = ckws("/media/sounds/goat.mp3")
SUPER_MARIO_PATH = ckws("/media/sounds/super_mario_sussy.mp3")
HOME_DEPOT_PATH = ckws("/media/sounds/home_depot.mp3")
BUHH_PATH = ckws("/media/sounds/buhh.mp3")
DUMB_FISH_PATH = ckws("/media/reactions/dumb_fish.png")
MONKEY_PATH = ckws("/media/reactions/monkey_typewriter.jpg")
DOG_PICS_DIR = ckws("/private/dog_pics") # in home dir for privacy -- maybe being paranoid
WII_EFFECTS_DIR = ckws("/media/wii")
PICTURE_OF_BAGELS = ckws("/media/images/bagels.jpg")
MECHANICUS_DIR = ckws("/media/mechanicus")
SIMPSONS_DIRECTORY = ckws("/media/simpsons")
BUG_REPORT_DIR = ckws("/bug-reports")
GENERATED_FILES_DIR = ckws("/generated")
# end filesystem resources


# returns a unique filename stamped with the current time.
# good for files we want to look at later
def stamped_fn(prefix, ext, dir=GENERATED_FILES_DIR):
    if not os.path.exists(dir):
        os.mkdir(dir)
    return f"{dir}/{prefix}-{datetime.now().strftime('%Y-%m-%dT%H-%M-%S.%f')}.{ext}"


# returns a unique filename in /tmp; for temporary work
# which is not intended to persist past reboots
def tmp_fn(prefix, ext):
    return stamped_fn(prefix, ext, "/tmp/bagelbot")


# returns a unique filename in /tmp; for temporary work
# which is not intended to persist past reboots
def hashed_fn(prefix, hashable, ext, dir="/tmp/bagelbot"):
    h = hashlib.md5(hashable).hexdigest()
    if not os.path.exists(dir):
        os.mkdir(dir)
    return f"{dir}/{prefix}-{h}.{ext}"
