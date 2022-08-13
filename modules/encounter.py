import re
import time
import random
import logging
from typing import List

from .platform import windowMP
from .mouse_utils import move_mouse_and_click, move_mouse, mouse_click  # , mouse_scroll

from .image_utils import partscreen, find_ellement, get_resolution
from .constants import UIElement, Button, Action
from .game import countdown, waitForItOrPass
# from .log_board import LogHSMercs
from .settings import settings_dict, mercslist, mercsAbilities, ability_order


log = logging.getLogger(__name__)

class Enemies:
    def __init__(self, red, green, blue, noclass, noclass2, mol):
        self.red = red
        self.green = green
        self.blue = blue
        self.noclass = noclass
        self.noclass2 = noclass2
        self.mol = mol

def select_enemy_to_attack(index):
    """Used to move the mouse over an enemy to attack it
    (after selecting a merc's ability)
    """
    cardWidth = windowMP()[2] // 16
    cardHeight = windowMP()[3] // 6
    retour = False

    if index:
        time.sleep(0.1)
        log.debug(
            f"Move index (index, x, y) : {index}"
            f" {index[0] + (cardWidth // 2)} {index[1] - (cardWidth // 3)}",
        )
        move_mouse_and_click(
            windowMP(), index[0] + (cardWidth // 3), index[1] - (cardHeight // 2)
        )
        retour = True
    return retour


def select_random_enemy_to_attack(enemies=None):
    """look for a random enemy
    (used when blue mercs can't find red enemy,
    green can't find blue or
    red can't find green
    """
    enemies = enemies or []
    log.debug("select_random_enemy_to_attack : %s len=%s", enemies, len(enemies))
    retour = False
    while enemies:
        toAttack = enemies.pop(random.randint(0, len(enemies) - 1))
        if select_enemy_to_attack(toAttack):
            retour = True
            break

    # attacks the middle enemy minion if you don't find any enemy
    if not retour:
        select_enemy_to_attack([windowMP()[2] / 2.01, windowMP()[3] / 2.77])
        # select_enemy_to_attack([windowMP()[2] / 2.1, windowMP()[3] / 3.6])

    # right click added to avoid some problem (if enemy wasn't clickable)
    mouse_click("right")


def priorityMercByType(myMercs, targettype) -> List[int]:
    """
    return merc position list prioritize by the targetType comes first,
        non target type after and minion comes last
    """
    mercs_pos = []
    # add targettype mercs first
    for i in myMercs:
        if myMercs[i] in mercslist:
            if mercslist[myMercs[i]]["type"] == targettype:
                mercs_pos.append(int(i))
    # add non targettype mercs to the end of the list 
    for i in myMercs:
        if myMercs[i] in mercslist:
            mercs_pos.append(int(i))
    # add friendly minion
    for i in myMercs:            
        if targettype == "minion":
            mercs_pos.append(int(i))
    return mercs_pos

def ability_target_friend(targettype, myMercs, enemies: Enemies):
    """Return the X coord of one of our mercenaries"""

    cardSize = int(windowMP()[2] / 12)
    firstOdd = int(windowMP()[2] / 3)
    firstEven = int (windowMP()[2] / 3.6)
    positionOdd = []  # positionOdd=[640,800,960,1120,1280]
    positionEven = []  # positionEven=[560,720,880,1040,1200,1360]
    for i in range(6):
        positionEven.append(int(firstEven + (i * cardSize)))
        if i != 5:
            positionOdd.append(int(firstOdd + (i * cardSize)))

    number = int(sorted(myMercs)[-1])
    if targettype == "friend":
        blueEnemiesLen, greenEnemiesLen, redEnemiesLen = len(enemies.blue), len(enemies.green), len(enemies.red)
        if blueEnemiesLen >= greenEnemiesLen and blueEnemiesLen >= redEnemiesLen:
             # enemies have blue the most so we buff red merc first
            position = priorityMercByType(myMercs, "Protector")[0]
        elif greenEnemiesLen >= blueEnemiesLen and greenEnemiesLen >= redEnemiesLen:
             # enemies have green the most so we buff blue merc first
            position = priorityMercByType(myMercs, "Caster")[0]
        elif redEnemiesLen >= greenEnemiesLen and redEnemiesLen >= blueEnemiesLen:
            # enemies have red the most so we buff green merc first
            position = priorityMercByType(myMercs, "Fighter")[0]
        else:
            position = random.randint(1, number)
    else:
        position = 1
        for i in myMercs:
            if myMercs[i] in mercslist:
                # is a Mercenary
                if mercslist[myMercs[i]]["minion_type"] == targettype:
                    position = int(i)
            else:
                # is a friendly Minion
                if targettype == "minion":
                    position = int(i)

    if number % 2 == 0:  # if mercenaries number is even
        pos = int(2 - (number / 2 - 1) + (position - 1))
        x = positionEven[pos]
    else:  # if mercenaries number is odd
        pos = int(2 - (number - 1) / 2 + (position - 1))
        x = positionOdd[pos]

    return x


def get_ability_for_this_turn(name, minionSection, turn, defaultAbility=0):
    """Get the ability (configured) for this turned for the selected Merc/minion"""

    if minionSection in ability_order and name.lower() in ability_order[minionSection]:
        # in combo.ini, split (with ",") to find the ability to use this turn
        # use first ability if not found
        round_abilities = ability_order[minionSection][name.lower()].split(",")
        abilitiesNumber = len(round_abilities)
        if abilitiesNumber != 0:
            ability = turn % abilitiesNumber
            if ability == 0:
                ability = len(round_abilities)
            ability = round_abilities[ability - 1]
        else:
            ability = defaultAbility
    else:
        ability = defaultAbility

    log.info("%s Ability Selected : %s", name, ability)

    return str(ability)


def parse_ability_setting(ability):
    retour = {"chooseone": 0, "ai": "byColor", "name": None, "miniontype": None}

    if ":" not in ability:
        retour["ability"] = int(ability)
    else:
        retour["ability"] = int(ability.split(":")[0])
        retour["config"] = ability.split(":")[1]
        for i in retour["config"].split("&"):
            key, value = i.split("=")
            if key == "chooseone":
                retour["chooseone"] = int(value) - 1
            elif key == "ai":
                retour["ai"] = value
            elif key == "name":
                retour["name"] = value
            elif key == "miniontype":
                retour["miniontype"] = value
            else:
                log.warning("Unknown parameter")

    return retour


def didnt_find_a_name_for_this_one(name, minionSection, turn, defaultAbility=0):
    abilitiesWidth = windowMP()[2] // 14.2
    abilitiesHeigth = windowMP()[3] // 7.2

    # abilitiesPositionY : Y coordinate to find "abilities" line during battle
    abilitiesPositionY = windowMP()[3] // 2.4
    # abilitiesPositionX :
    #   X coordinates to find the 3 "abilities" during battle
    #   (4 because sometimes, Treasure give you a new abilities
    #   but the bot doesn't support it right now)
    abilitiesPositionX = [
        windowMP()[2] // 2.68,
        windowMP()[2] // 2.17,
        windowMP()[2] // 1.8,
        windowMP()[2] // 1.56,
    ]

    abilityConfig = parse_ability_setting(
        get_ability_for_this_turn(name, minionSection, turn, defaultAbility)
    )
    ability = abilityConfig["ability"]
    if ability == 0:
        log.debug("No ability selected (0)")
    elif ability >= 1 and ability <= 3:
        log.debug(
            f"abilities Y : {abilitiesPositionY} |"
            f" abilities X : {abilitiesPositionX}"
        )
        _, _, _, scale_size = get_resolution()
        partscreen(
            int(abilitiesWidth),
            int(abilitiesHeigth),
            int(windowMP()[1] + abilitiesPositionY),
            int(windowMP()[0] + abilitiesPositionX[0]),
            scale_size=scale_size,
        )
        if (
            find_ellement(UIElement.hourglass.filename, Action.get_coords_part_screen)
            is None
        ):
            move_mouse_and_click(
                windowMP(),
                int(abilitiesPositionX[ability - 1] + abilitiesWidth // 2),
                int(abilitiesPositionY + abilitiesHeigth // 2),
            )
    else:
        log.warning(f"No ability selected for {name}")
        abilityConfig["ability"] = 0

    return abilityConfig


def select_ability(localhero, myBoard, enemies: Enemies):
    """Select an ability for a mercenary.
        Depend on what is available and wich Round (battle)
    Click only on the ability (doesnt move to an enemy)
    """
    global raund

    if localhero in mercsAbilities:
        retour = False
        chooseone2 = [windowMP()[2] // 2.4, windowMP()[2] // 1.7]
        chooseone3 = [windowMP()[2] // 3, windowMP()[2] // 2, windowMP()[2] // 1.5]

        abilitySetting = didnt_find_a_name_for_this_one(
            localhero, "Mercenary", raund, 1
        )
        if abilitySetting["ability"] != 0:
            ability = abilitySetting["ability"]
            if isinstance(mercsAbilities[localhero][str(ability)], bool):
                retour = mercsAbilities[localhero][str(ability)]
            elif mercsAbilities[localhero][str(ability)] == "chooseone3":
                time.sleep(0.2)
                move_mouse_and_click(
                    windowMP(),
                    chooseone3[abilitySetting["chooseone"]],
                    windowMP()[3] // 2,
                )
            elif mercsAbilities[localhero][str(ability)] == "chooseone2":
                time.sleep(0.2)
                move_mouse_and_click(
                    windowMP(),
                    chooseone2[abilitySetting["chooseone"]],
                    windowMP()[3] // 2,
                )
            elif mercsAbilities[localhero][str(ability)].startswith("friend"):
                time.sleep(0.2)
                if ":" in mercsAbilities[localhero][str(ability)]:
                    move_mouse_and_click(
                        windowMP(),
                        ability_target_friend(
                            mercsAbilities[localhero][str(ability)].split(":")[1],
                            myBoard,
                            enemies,
                        ),
                        windowMP()[3] / 1.5,
                    )
                else:
                    move_mouse_and_click(
                        windowMP(),
                        ability_target_friend("friend", myBoard, enemies),
                        windowMP()[3] / 1.5,
                    )
            # elif mercsAbilities[localhero][str(ability)] == "friend:Dragon":
            #     time.sleep(0.2)
            #     move_mouse_and_click(
            #         windowMP(),
            #         ability_target_friend("friend:Dragon", myBoard, enemies),
            #         windowMP()[3] / 1.5,
            #     )
    else:
        localhero = re.sub(r" [0-9]$", "", localhero)
        abilitySetting = didnt_find_a_name_for_this_one(localhero, "Neutral", raund, 0)
        if abilitySetting["ability"] == 0:
            retour = False
        else:
            retour = True

    return retour


def attacks(
    position,
    mercName,
    # number,
    myMercs,
    enemies: Enemies,
):
    """
    Function to attack an enemy (red, green or blue ideally)
    with the selected mercenary
    red attacks green (if exists)
    green attacks blue (if exists)
    blue attacks red (if exists)
    else merc attacks minion with special abilities or neutral
    """
    global raund

    log.debug("Attacks function")

    number = int(sorted(myMercs)[-1])

    cardSize = int(windowMP()[2] / 12)
    firstOdd = int(windowMP()[2] / 3)
    firstEven = int(windowMP()[2] / 3.6)
    positionOdd = []  # positionOdd=[640,800,960,1120,1280]
    positionEven = []  # positionEven=[560,720,880,1040,1200,1360]
    for i in range(6):
        positionEven.append(int(firstEven + (i * cardSize)))
        if i != 5:
            positionOdd.append(int(firstOdd + (i * cardSize)))

    if number % 2 == 0:  # if mercenaries number is even
        pos = int(2 - (number / 2 - 1) + (position - 1))
        x = positionEven[pos]
    else:  # if mercenaries number is odd
        pos = int(2 - (number - 1) / 2 + (position - 1))
        x = positionOdd[pos]
    y = windowMP()[3] / 1.5

    log.info("attack with : %s ( position : %s/%s =%s)", mercName, position, number, x)

    move_mouse_and_click(windowMP(), x, y)
    time.sleep(0.2)
    move_mouse(windowMP(), windowMP()[2] / 3, windowMP()[3] / 2)
    if mercName in mercslist:
        if (
            mercslist[mercName]["type"] == "Protector"
            and select_ability(mercName, myMercs, enemies)
            and not select_enemy_to_attack(enemies.green)
            and not select_enemy_to_attack(enemies.mol)
            and not select_enemy_to_attack(enemies.noclass)
            and not select_enemy_to_attack(enemies.noclass2)
        ):
            select_random_enemy_to_attack([enemies.red, enemies.blue])
        elif (
            mercslist[mercName]["type"] == "Fighter"
            and select_ability(mercName, myMercs, enemies)
            and not select_enemy_to_attack(enemies.blue)
            and not select_enemy_to_attack(enemies.mol)
            and not select_enemy_to_attack(enemies.noclass)
            and not select_enemy_to_attack(enemies.noclass2)
        ):
            select_random_enemy_to_attack([enemies.red, enemies.green])
        elif (
            mercslist[mercName]["type"] == "Caster"
            and select_ability(mercName, myMercs, enemies)
            and not select_enemy_to_attack(enemies.red)
            and not select_enemy_to_attack(enemies.mol)
            and not select_enemy_to_attack(enemies.noclass)
            and not select_enemy_to_attack(enemies.noclass2)
        ):
            select_random_enemy_to_attack([enemies.green, enemies.blue])
    elif select_ability(mercName, myMercs, enemies):
        select_random_enemy_to_attack(
            [enemies.red, enemies.green, enemies.blue, enemies.noclass, enemies.noclass2, enemies.mol]
        )

# Look for enemies
def find_enemies() -> Enemies:
    enemyred = find_red_enemy()
    enemygreen = find_green_enemy()
    enemyblue = find_blue_enemy()
    enemynoclass = find_noclass_enemy()
    enemynoclass2 = find_noclass2_enemy()
    enemymol = find_mol_enemy()

    log.info(
        f"Enemies : red {enemyred}"
        f" - green {enemygreen}"
        f" - blue {enemyblue}"
        f" - noclass {enemynoclass}"
        f" - noclass2 {enemynoclass2}"
        f" - mol {enemymol}"
    )
    return Enemies(enemyred, enemygreen, enemyblue, enemynoclass, enemynoclass2, enemymol)


def find_red_enemy():
    return find_enemy("red")


def find_green_enemy():
    return find_enemy("green")


def find_blue_enemy():
    return find_enemy("blue")


def find_noclass_enemy():
    return find_enemy("noclass")


def find_noclass2_enemy():
    return find_enemy("noclass2")


def find_mol_enemy():
    return find_enemy("sob")


def find_enemy(enemy_type):
    enemy = find_ellement(
        getattr(UIElement, enemy_type).filename, Action.get_coords_part_screen
    )
    # find_element: Can be changed to return None or actual coords if exists
    if enemy:
        enemy = (
            enemy[0],
            enemy[1],
        )
    return enemy


def battle(zoneLog=None):
    """Find the cards on the battlefield (yours and those of your opponents)
    and make them battle until one of yours die
    """
    global raund
    retour = True

    # init the reading of Hearthstone filelog to detect your board / mercenaries
    # zoneLog = LogHSMercs(settings_dict["zonelog"])
    # zoneLog.start()

    raund = 1
    while True:
        move_mouse(
            windowMP(),
            windowMP()[2] // 4,
            windowMP()[3] // 2,
        )

        # we look for the (green) "ready" button because :
        # - sometimes, the bot click on it but it doesn't work very well
        # - during a battle, some enemies can return in hand and
        #   are put back on battlefield with a "ready" button
        #       but the bot is waiting for a victory / defeat /
        #   ... or the yellow button ready
        find_ellement(Button.allready.filename, Action.move_and_click)

        find_ellement(Button.onedie.filename, Action.move_and_click)

        if find_ellement(UIElement.win.filename, Action.screenshot) or find_ellement(
            UIElement.win_final.filename, Action.screenshot
        ):
            retour = "win"
            move_mouse_and_click(windowMP(), windowMP()[2] / 2, windowMP()[3] / 1.3)
            zoneLog.cleanBoard()

            break
        elif find_ellement(UIElement.lose.filename, Action.screenshot):
            retour = "loose"
            move_mouse_and_click(
                windowMP(),
                windowMP()[2] / 2,
                windowMP()[3] / 1.3,
            )
            zoneLog.cleanBoard()
            break
        elif find_ellement(
            Button.fight.filename, Action.screenshot
        ):  # or find_ellement(Button.startbattle1.filename, Action.screenshot):

            # looks for your enemies on board thanks to log file
            enemies = zoneLog.getEnemyBoard()
            log.info(f"Round {raund} : enemy board {enemies}")
            # looks for your Mercenaries on board thanks to log file
            mercenaries = zoneLog.getMyBoard()
            log.info(f"Round {raund} :  your board {mercenaries}")

            # click on neutral zone to avoid problem with screenshot
            # when you're looking for red/green/blue enemies
            move_mouse_and_click(windowMP(), windowMP()[2] // 2, windowMP()[3] // 1.2)

            time.sleep(0.5)

            # tmp = int(windowMP()[3] / 2)
            _, _, _, scale_size = get_resolution()
            partscreen(
                windowMP()[2],
                windowMP()[3] // 2,
                windowMP()[1],
                windowMP()[0],
                scale_size=scale_size,
            )

            enemies = find_enemies()

            # Go (mouse) to "central zone" and click on an empty space
            # move_mouse_and_click(windowMP(), windowMP()[2] // 2, windowMP()[3] // 1.2)
            # time.sleep(1)

            for i in mercenaries:
                # Go (mouse) to "central zone" and click on an empty space
                move_mouse_and_click(
                    windowMP(), windowMP()[2] // 2, windowMP()[3] // 1.2
                )

                attacks(
                    int(i),
                    mercenaries[i],
                    # int(sorted(mercenaries)[-1]),
                    mercenaries,
                    enemies,
                )
                # in rare case, the bot detects an enemy ("noclass" most of the
                #   times) outside of the battlezone.
                # the second click (to select the enemy),
                #   which is on an empty space, doesnt work.
                # next move : instead of selecting the next mercenaries (to choose an
                #   ability), the mercenary is clicked on to be targeted (from
                #   previous ability). Need a "rightclick" to cancel this action.
                mouse_click("right")
                time.sleep(0.1)

            i = 0
            while not find_ellement(Button.allready.filename, Action.move_and_click):
                if i > 5:
                    move_mouse(windowMP(), windowMP()[2] // 1.2, windowMP()[3] // 3)
                    mouse_click("right")
                    find_ellement(Button.fight.filename, Action.move_and_click)
                    break
                time.sleep(0.2)
                i += 1
            time.sleep(3)
            raund += 1

    return retour


def selectCardsInHand(zL=None):
    """Select the cards to put on battlefield
    and then, start the 'battle' function
    Update : actually, the bot doesn't choose it anymore
    since we stopped to use image with mercenaries text
    (so we can easily support multi-language)
        this feature will come back later using HS logs
    """

    log.debug("[ SETH - START]")
    retour = True

    # while not find_ellement(Button.num.filename, Action.screenshot):
    #    time.sleep(2)
    waitForItOrPass(Button.num, 60, 2)

    if find_ellement(Button.num.filename, Action.screenshot):
        # wait 'WaitForEXP' (float) in minutes, to make the battle last longer
        # and win more XP (for the Hearthstone reward track)
        wait_for_exp = settings_dict["waitforexp"]
        log.info(f"WaitForEXP - wait (second(s)) : {wait_for_exp}")
        # time.sleep(wait_for_exp)
        countdown(wait_for_exp, 10, "Wait for XP : sleeping")

        log.debug(f"windowMP = {windowMP()}")
        x1 = windowMP()[2] // 2.6
        y1 = windowMP()[3] // 1.09
        x2 = windowMP()[2] // 10
        y2 = windowMP()[3] // 10

        # let the "while". In future release,
        #   we could add a function to select specifics cards
        while not find_ellement(Button.num.filename, Action.move_and_click):
            move_mouse(windowMP(), x1, y1)
            move_mouse(windowMP(), x2, y2)

        retour = battle(zL)
        log.debug("[ SETH - END]")

    return retour
