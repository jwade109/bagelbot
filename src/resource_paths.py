import os
import logging
from ws_dir import WORKSPACE_DIRECTORY

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

# begin filesystem resources
# using absolute filepaths so this can be run via a chron job
FART_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/farts")
RL_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/rl")
UNDERTALE_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/ut")
STAR_WARS_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/sw")
MULANEY_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/jm")
CH_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/ch")
SOTO_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/images/soto.png")
SOTO_PARTY = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/soto_party.mp3")
SOTO_TINY_NUKE = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/tiny_soto_nuke.mp3")
WOW_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/wow.mp3")
GK_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/genghis_khan.mp3")
GUNTER_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/gunter.mp3")
GASGASGAS_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/gasgasgas.mp3")
BILLNYE_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/bill_nye_the_science_guy.mp3")
HELLO_THERE_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sw/obi_wan_kenobi/hello_there.mp3")
SWOOSH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sw/mace_windu/swoosh.mp3")
OHSHIT_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/ohshit.mp3")
YEAH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/yeah.mp3")
GOAT_SCREAM_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/goat.mp3")
SUPER_MARIO_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/super_mario_sussy.mp3")
BUHH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/sounds/buhh.mp3")
DUMB_FISH_PATH = check_exists(WORKSPACE_DIRECTORY + "/media/images/dumb_fish.png")
DOG_PICS_DIR = check_exists(WORKSPACE_DIRECTORY + "/private/dog_pics") # in home dir for privacy -- maybe being paranoid
WII_EFFECTS_DIR = check_exists(WORKSPACE_DIRECTORY + "/media/wii")
PICTURE_OF_BAGELS = check_exists(WORKSPACE_DIRECTORY + "/media/images/bagels.jpg")
MECHANICUS_DIR = check_exists(WORKSPACE_DIRECTORY + "/media/mechanicus")
SIMPSONS_DIRECTORY = check_exists(WORKSPACE_DIRECTORY + "/media/simpsons")
BUG_REPORT_DIR = check_exists(WORKSPACE_DIRECTORY + "/bug-reports")
GENERATED_FILES_DIR = check_exists(WORKSPACE_DIRECTORY + "/generated")
# end filesystem resources
