import os
import random
import json
import urllib.request
import urllib.error

from typing import List, Dict, Callable
from datetime import datetime
# from tkinter import *

from discord_funcs import discord_input, discord_stutter


__version__ = '0.1.0'


# TODO: more comprehensive refactor, oop etc.


# need to make this dynamic
LANG = 'en'
# load strings
with open(os.path.join('strings', f'{LANG}.json')) as strings_file:
    STRINGS = json.load(strings_file)
# strings shortcuts
STRS_GAME = STRINGS['game']
STRS_ITEMS = STRS_GAME['items']
STRS_ROOMS = STRS_GAME['rooms']


class ZaryaItem:
    """Class for items.

    An item has a name and can be inspected for a description. It may be used, which will invoke usefunc, or taken.

    Attrs:
        name
        desc -- description of item
        can_use
        can_take
        usefunc -- function to be run when the item is used
    """
    desc_stem = STRS_ITEMS['desc_stem']

    def __init__(self, name: str, desc: str, can_use: bool = False, can_take: bool = False, usefunc: Callable = None):
        self.name = name
        if desc.startswith(self.desc_stem):
            desc = desc.removeprefix(self.desc_stem)
        self.desc = desc.strip()
        self.can_use = can_use
        self.can_take = can_take
        if self.can_use and usefunc is not None:
            self.usefunc = usefunc


# TODO: allow giving an identifier to the constructor to automatically get the name and desc from the strings file
class ZaryaContainer:
    """Class for containers.

    A container has a name, and a description which will be used when you `look` while inside it.
    It may be entered and exited, and contain items.

    Attrs:
        name
        desc -- look message of container
        can_leave -- whether you can leave the container, used in the ZaryaRoom subclass
        items -- items in the container, a list of ZaryaItems or None
    """

    desc_stem = STRS_GAME['containers']['desc_stem']

    def __init__(self, name: str, desc: str, can_leave: bool = True, items: List[ZaryaItem] = None):
        self.name = name
        if desc.startswith(self.desc_stem):
            desc = desc.removeprefix(self.desc_stem)
        self.desc = desc.strip()
        self.can_leave = can_leave
        self.items = items


class ZaryaPort:
    """Class for ports connecting two modules of the station (rooms).

    A port has a name, which should correspond to a direction in orbit, like the ones used to describe ISS ports.
    A port will be open or closed. If open, it may have a room which you will enter by going through it.

    Attrs:
        name
        port_open
        room -- if applicable, the ZaryaRoom which you will enter by going through the port
    """
    def __init__(self, name: str, port_open: bool, room=None):
        self.name = name
        self.port_open = port_open
        if self.port_open and room is not None:
            self.room = room


class ZaryaRoom(ZaryaContainer):
    """Class for rooms I.E. station modules.

    A room has all of a container's attributes. It may also have containers within it, and ports connecting it
    to other rooms.

    Attrs:
        desc -- look message of room
        can_leave -- whether you can leave the room, should be False
        has_windows -- determines whether the camera can be used in this room
        items -- items in the room, a list of ZaryaItems or None
        containers -- a list of ZaryaContainers which you can enter, or None
        ports -- a list of ZaryaPorts which may be open or closed, or None
    """
    def __init__(self, name: str, desc: str, can_leave: bool = False, has_windows: bool = False,
                 items: List[ZaryaItem] = None, containers: List[ZaryaContainer] = None, ports: List[ZaryaPort] = None):
        super().__init__(name, desc, can_leave, items)

        self.has_windows = has_windows
        self.containers = containers
        self.ports = ports


class ZaryaPlayer:
    """Class for the player character.

    Attrs:
        name
        inventory --  a list of ZaryaItem's
        wearing -- outfit
        sleep -- how much sleep as a float
    """
    name = STRS_GAME['player']['name_default']

    def __init__(self, name: str, inventory: List[ZaryaItem], wearing, sleep: float = 5):
        self.name = name
        self.inventory = inventory
        self.wearing = wearing
        self.sleep = sleep


class ZaryaGame:
    def __init__(self, discord_client, send_channel, req_channel_name=None):
        self.discord_client = discord_client
        self.send_channel = send_channel
        if req_channel_name is None:
            self.req_channel_name = ''
        else:
            self.req_channel_name = req_channel_name

    async def run(self):
        async def n():
            await discord_stutter('', channel=self.send_channel, skip=True)

        skip = False

        # typing output effects
        async def stutter(text, delay=lambda: random.randint(1, 3)/100):
            await discord_stutter(text, channel=self.send_channel, delay=delay, skip=skip)

        async def stutters(text):
            await stutter(text, delay=lambda: random.randint(5, 10)/100)

        async def stutterf(text):
            await stutter(text, lambda: 0.01)

        async def stutterl(text):
            nonlocal skip
            skip_cached = skip
            skip = False
            await stutter(text)
            skip = skip_cached

        inventory = dict()

        # list of commands for help
        help_info = [
            'help -Shows a list of commands',
            'skip -Toggles stuttering off',
            'noskip -Toggles stuttering on',
            'look around -Tells you what is in the room',
            'show inventory -Tells you what is in your inventory',
            'search [object] -Tells you what is in a container',
            'take [item] -Puts an item in your inventory',
            'take all -Puts all available items in your inventory',
            'use [item] -Lets you exercise the functionality of an item',
            'leave [place] -Lets you leave where you are',
            'go through [direction] port -Travel into adjacent modules',
            'drop [item] -Removes an item from your inventory',
            'quit -Ends the game',
            'Note:',
            'You can also use abbreviations for some commands.',
        ]

        functions = list()

        # npc interact subroutines
        async def talktocrewmate():
            await stutter('Hello there! Glad to see you got that malfunctioning hatch open.')

        # item use subroutines
        async def usepaper():
            await stutter('The strip of paper has a password on it.')
            await stutter("'Pa$$word123'")
            await stutter('You wonder what it is the password to.')
            await stutter("(That's your cue to wonder what it is the password to)")

        async def usedrive():
            if 'laptop' in inventory or 'laptop' in Room['Items']:
                if 'Files' in Drive:
                    await stutter('You transfer all the files on the usb stick to the laptop.')
                    Laptop['Files'] = Drive['Files']
                    del Drive['Files']
                else:
                    await stutter('There are no files on the usb stick.')
            else:
                await stutter('You have to laptop to use it with.')

        async def usejumpsuit():
            await stutter('You put on the jumpsuit.')
            Player['Wearing'] = 'RussianJumpsuit'
            await stutter('You were already wearing one, however, so you are now wearing two jumpsuits.')
            await stutter('Good job.')

        async def usegreenhouse():
            await stutter('You watch the sprouts.')
            await stutters('Nothing interesting happens.')

        # TODO: fix bug with KeyError taking the camera
        # TODO: fix bug with using camera
        # TODO: combine string literals to help with rate limiting
        # TODO: move todos into relevant places :p
        async def usecamera():
            if 'Windows' in Room:
                await stutterl('You take the camera to a window and, after fiddling with '
                               'lenses and settings for\na few minutes, take a ')
                picture_quality = random.randint(1, 10)
                if picture_quality <= 2:
                    picture_type = 'rubbish'
                elif picture_quality <= 5:
                    picture_type = 'nice'
                else:
                    picture_type = 'beautiful'
                picture_name = f'{picture_type} picture'
                await stutter(f'{picture_name}.')
                inventory[picture_name] = picture_quality
            else:
                await stutter('There are no windows to take pictures out of in this module.')

        async def usetoilet():
            await stutter("You do your business in the space toilet. Don't ask an astronaut "
                          "how this \nhappens if you meet one, they're tired of the question.")

        async def usebed():
            await stutter("You get in the 'bed'.")
            if Player['Sleep'] > 8:
                await stutter('You sleep until you are no longer tired.')
                nonlocal FicEpoch
                FicEpoch += Player['Sleep'] * 3600
                Player['Sleep'] = 0
                await stutter('Date: ' + datetime.fromtimestamp(FicEpoch).strftime('%d.%m.%Y'))
            else:
                await stutter('You are not tired enough to get to sleep.')

        async def uselaptop():
            if Laptop['Tutorial'] == 'Pending':
                await stutter('There is a sticker on the laptop that lists things you can do with it.')
                await stutterf('browse web')
                await stutterf('use messenger app')
                await stutterf('read files')
                await stutterf('play text game')
                await stutterf('control station module')
                Laptop['Tutorial'] = 'Complete'
                await n()
            await stutter('You turn on the laptop.')
            Laptop['State'] = 'On'
            while Laptop['State'] == 'On':
                await n()
                task = await discord_input(self.discord_client, self.req_channel_name)
                self.log(task)
                await n()

                if task in 'turn off laptop':
                    await stutter('You turn off the laptop.')
                    Laptop['State'] = 'Off'

                elif task in ['browse web', 'browse', 'web']:
                    await stutter('A browser window opens. Where do you want to go?')
                    url = await discord_input(self.discord_client, self.req_channel_name)
                    self.log(url)
                    try:
                        response = urllib.request.urlopen(url)
                        html = response.read()
                        print(html)
                        await stutter("Hmm, looks like there's no GUI.")
                        await stutter('Oh well.')
                    except ValueError:
                        await stutter("That's not a valid URL.")
                    except urllib.error.URLError:
                        await stutter('You have no internet connection.')

                elif task in ['read files', 'read', 'files']:
                    if Laptop['Files'] == 'None':
                        await stutter('You have no files to read!')
                    else:
                        await stutter('The files say: ')
                        await stutter(Laptop['Files'])

                elif task in ['use messenger app', 'messenger app', 'messenger']:
                    contacts = ['nasa social media team']
                    await stutter('In your contacts list are: ')
                    for contact in contacts:
                        await stutterf(contact)

                    await stutter('Who would you like to message?')
                    invalid_input = True
                    while invalid_input:
                        contact = await discord_input(self.discord_client, self.req_channel_name)
                        self.log(contact)
                        if contact in contacts:
                            invalid_input = False
                            if contact in 'nasa social media team':
                                await stutter('You can send pictures to NASA to be posted online.')
                                await stutter('What picture would you like to send?')
                                picture = await discord_input(self.discord_client, self.req_channel_name)
                                self.log(picture)
                                if 'picture' in picture:
                                    if picture in inventory:
                                        await stutter('You send the picture.')
                                        likes = inventory[picture] * random.randint(10, 1000)
                                        await stutter('Your picture gets ' + str(likes) + ' likes.')
                                        del inventory[picture]
                                    else:
                                        await stutter("You don't have that picture.")
                                else:
                                    await stutter("That's not a picture!")
                        else:
                            await stutter("They aren't in your contacts list.")

                elif task in 'play text game':
                    await ZaryaGame(self.discord_client, self.send_channel, self.req_channel_name).run()

                elif task in 'control station module':
                    await stutter('A window opens with a few readouts and options.')
                    await stutter('periapsis: 390km')
                    await stutter('apoapsis: 390km')
                    await stutter('inclination: 51.6°')
                    await stutter('orbital period: 93 minutes')
                    await stutter('thruster statuses: nominal')
                    await stutter('alignment: retrograde')
                    await stutter("There is a button that says 'fire main engines'.")
                    await stutter('Would you like to press it?')
                    choice = await discord_input(self.discord_client, self.req_channel_name)
                    self.log(choice)
                    if 'yes' in choice:
                        await stutter('You press the button and tons of Gs force you against the back of the module.')
                        await stutter("This is a cargo module, which means there's no seat to help you.")
                        await stutter('Your orbit is rapidly falling deeper into the atmosphere.')
                        await stutter('The remains of the module hits the ground at terminal velocity.')
                        await stutter("But it's ok, because you were already obliterated "
                                      'when its unshielded mass burnt up violently in the atmosphere.')
                        await stutters('GAME OVER')
                        Carry['On'] = False
                        await discord_input(self.discord_client, self.req_channel_name)
                        break
                    else:
                        await stutter('That was probably a sensible choice.')

                else:
                    await stutter("The laptop can't do that!")

        # items
        laptop = ZaryaItem(
            name=STRS_ITEMS['laptop']['name'], desc=STRS_ITEMS['laptop']['desc'],
            can_use=True, can_take=False, usefunc=uselaptop
        )
        laptop.state = 'off'
        laptop.tutorial = 'Pending'
        laptop.files = []

        paper = ZaryaItem(
            name=STRS_ITEMS['paper'], desc=STRS_ITEMS['paper']['desc'],
            can_use=True, can_take=True, usefunc=usepaper
        )

        drive = ZaryaItem(
            name=STRS_ITEMS['drive']['name'], desc=STRS_ITEMS['drive']['desc'],
            can_use=True, can_take=True, usefunc=usedrive
        )
        drive.files = {'program.py': "'print('hello world!')'"}

        jumpsuit = ZaryaItem(
            name=STRS_ITEMS['jumpsuit']['name'], desc=STRS_ITEMS['jumpsuit']['desc'],
            can_use=True, can_take=True, usefunc=usejumpsuit
        )

        greenhouse = ZaryaItem(
            name=STRS_ITEMS['greenhouse']['name'], desc=STRS_ITEMS['greenhouse']['desc'],
            can_use=True, usefunc=usegreenhouse
        )

        camera = ZaryaItem(
            name=STRS_ITEMS['camera']['name'], desc=STRS_ITEMS['camera']['desc'],
            can_use=True, can_take=True, usefunc=usecamera
        )

        toilet = ZaryaItem(
            name=STRS_ITEMS['toilet']['name'], desc=STRS_ITEMS['toilet']['desc'],
            can_use=True, usefunc=usetoilet
        )

        bed = ZaryaItem(
            name=STRS_ITEMS['bed']['name'], desc=STRS_ITEMS['bed']['desc'],
            can_use=True, usefunc=usebed
        )

        # containers
        zarya_boxes_items = [paper, drive, jumpsuit]
        zarya_boxes = ZaryaContainer(
            name=STRS_GAME['containers']['zarya_boxes']['name'], desc=STRS_GAME['containers']['zarya_boxes']['desc'],
            can_leave=True, items=containers_items
        )

        # rooms
        zarya = ZaryaRoom(
            name=STRS_ROOMS['zarya']['name'], desc=STRS_ROOMS['zarya']['desc'],
            can_leave=False, items=[laptop], containers=[zarya_boxes], ports=['TODO ADD PORTS HERE']
        )
        ZaryaPorts = {'front': 'open', 'nadir': 'closed', 'aft': 'open'}
        ZaryaNear = {'front': 'Unity', 'aft': 'Zvezda'}

        unity = ZaryaRoom(
            name=STRS_ROOMS['unity']['name'], desc=STRS_ROOMS['unity']['desc'],
            can_leave=False, ports=['TODO ADD PORTS HERE']
        )
        UnityPorts = {
            'front': 'closed', 'nadir': 'closed',
            'port': 'closed', 'zenith': 'closed',
            'starboard': 'closed', 'aft': 'open'
        }
        UnityNear = {'aft': 'Zarya'}

        zvezda = ZaryaRoom(
            name=STRS_ROOMS['zvezda']['name'], desc=STRS_ROOMS['zvezda']['desc'],
            can_leave=False, has_windows=True, items=[greenhouse, camera, toilet, bed], ports=['TODO ADD PORTS HERE']
        )
        ZvezdaPorts = {
            'front': 'open', 'nadir': 'closed',
            'zenith': 'closed', 'aft': 'closed'
        }
        ZvezdaNear = {'front': 'Zarya'}

        # player
        player = ZaryaPlayer(
            name=STRS_GAME['player']['name_default'], inventory=[], wearing='jumpsuit'
        )

        # def helpwindow():
        #     helpw = Tk()
        #     helpw.title('help')
        #     helpc = Canvas(helpw, height=(len(help_info)*20)+20, width=650)
        #     helpc.pack()
        #     text = list()
        #     for help_info_item in help_info:
        #         text.append(helpc.create_text(325, (i*20)+20, text=help_info_item))

        # TODO: get this from some module instead?
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]

        # start game
        Room = Zarya
        FicEpoch = 968716800
        await stutterf(f'Zarya-Discord v{__version__}')
        await stutterf('© Joel McBride 2017, 2021')
        await stutterf("Remember to report any bugs or errors to 'JMcB#7918' - @ or DM me.")
        await n()
        await stutter('Date: ' + datetime.fromtimestamp(FicEpoch).strftime('%d.%m.%Y'))
        await stutter("For a list of commands, type 'help'.")

        # command reader
        Carry = {'On': True}
        while Carry['On']:
            Player['Sleep'] += 1
            FicEpoch += 3600
            await n()
            Do = str.lower(await discord_input(self.discord_client, self.req_channel_name))
            self.log(Do)
            await n()

            if Do in ['help', 'h']:
                for help_info_item in help_info:
                    await stutterf(help_info_item)
                await stutter('For the uninitiated: ')
                await stutter('In text-based adventure games, a good first command when '
                              "starting out or \nentering a new place is 'look around'.")

            elif Do in ['info', 'background', 'b']:
                await stutterf(f'Zarya-Discord v{__version__}')
                await stutterf('© Joel McBride 2017, 2021')
                await stutterf("Remember to report any bugs or errors to 'JMcB#7918' - @ or DM me.")
                await stutter('I made this game as one of my first reasonably large projects about four years ago '
                              '(2016). It was very poorly coded but I worked quite a while on it, although after I '
                              "finished most of the framework stuff I couldn't be bothered to add much more content. "
                              "The writing, what there is, is ok, it's got some funny bits I guess. It's also very "
                              'well researched, everything in the game is on the ISS in real life - including Zarya. '
                              'Anyway, I had the idea recently (2021) to make a text based adventure game for Discord, '
                              'so I went back to my old project, touched the code up a bit, ported it, and here we are.')

            # ignore bot-level commands
            elif Do in ['logs', 'log', 'log.txt']:
                pass

            elif Do in ['quit', 'q']:
                await discord_stutter('Thanks for playing!', self.send_channel)
                break

            elif Do in ['look around', 'look', 'la', 'l']:
                await stutter('You are ' + Room['Desc'] + ' ')
                Items = Room['Items']
                if len(Items) > 0:
                    ItemVars = list(Items.values())
                    for i, value in enumerate(Items):
                        await stutter(f"There is{ItemVars[i]['Desc']}")
                if 'Ports' in Room:
                    await stutter('There are ' + str(len(Room['Ports'])) + ' ports: ')
                    Ports = Room['Ports']
                    PortTypes = list(Ports.keys())
                    PortStates = list(Ports.values())
                    for i, value in enumerate(Room['Ports']):
                        await stutter(f'One to {PortTypes[i]} that is {PortStates[i]}.')

            elif Do in ['show inventory', 'inventory', 'si', 'i']:
                if not inventory:
                    await stutter('Your inventory is empty.')
                else:
                    await stutter('In your inventory is: ')
                    for inventory_item in inventory.keys():
                        await stutter(inventory_item)

            elif 'search' in Do:
                Object = Do[7:]
                if Object in Room['Objects']:
                    PrevRoom = Room
                    await stutter(f'You search the {Object}.')
                    ObjectIndx = Room['Objects']
                    Room = ObjectIndx[Object]
                    Items = list(Room['Items'])
                    if len(Items) > 0:
                        await stutter(f'The {Object} contain(s):')
                        for item in Items:
                            await stutter(item)
                    else:
                        await stutter("There isn't anything here.")
                else:
                    await stutter("That isn't in here.")

            elif 'leave' in Do:
                if Room['Leavable'] == 1:
                    await stutter('You leave the ' + str.lower(Room['Name']) + '.')
                    Room = PrevRoom
                else:
                    await stutter(f"I'm sorry {Player['Name']}, I'm afraid you can't do that.")

            elif 'go through' in Do or 'gt' in Do or 'go' in Do:
                if 'go through' in Do and 'port' in Do:
                    SubStringEnd = Do.index('port')
                    SubStringEnd = SubStringEnd - 1
                    Direction = Do[11:SubStringEnd]
                elif 'go through' in Do:
                    Direction = Do[11:]
                elif 'gt' in Do and 'p' in Do:
                    SubStringEnd = Do.index('p')
                    SubStringEnd = SubStringEnd - 1
                    Direction = Do[3:SubStringEnd]
                elif 'gt' in Do or 'go' in Do:
                    Direction = Do[3:]
                if Direction in Room['Ports']:
                    Ports = Room['Ports']
                    if Ports[Direction] == 'open':
                        Near = Room['Near']
                        NextRoom = Near[Direction]
                        await stutter('You go through the port into ' + NextRoom + '.')
                        Room = eval(Near[Direction])
                    else:
                        await stutter('That port is closed.')
                else:
                    await stutter("The module you're in doesn't have a port there.")

            elif Do in ['take all', 'ta']:
                ItemsList = list(Room['Items'])
                if len(ItemsList) > 0:
                    await stutter('You: ')
                    await stutter('TAKE ')
                    await stutter('ALL THE THINGS.')
                    Items = Room['Items']
                    for i, value in enumerate(Items):
                        Item = ItemsList[i]
                        TrueItem = str.upper(Item[0]) + Item[1:]
                        if 'Takeable' in eval(TrueItem):
                            Details = Items[Item]
                            inventory[Item] = Details
                            del Items[Item]
                        else:
                            await stutter(f"You can't take the {Item}.")
                else:
                    await stutter("There's nothing here.")

            elif 'take' in Do:
                Item = Do[5:]
                Items = Room['Items']
                Details = Items[Item]
                if Item in Items:
                    TrueItem = Item.title()
                    if 'Takeable' in eval(TrueItem):
                        await stutter('You take the ' + Item + '.')
                        inventory[Item] = Details
                        del Items[Item]
                    else:
                        await stutter("You can't take that.")
                else:
                    await stutter("That item isn't here.")

            elif 'use' in Do:
                Item = Do[4:]
                if Item in inventory or Item in Room['Items']:
                    TrueItem = Item.title()
                    if 'Usable' in eval(TrueItem):
                        await eval(TrueItem)['usefunc']()
                    else:
                        await stutter("That item isn't usable.")
                else:
                    await stutter("You don't have that item.")

            elif 'drop' in Do:
                Item = Do[5:]
                if Item in inventory:
                    await stutter('You drop the ' + Item + '.')
                    Items = Room['Items']
                    Details = inventory[Item]
                    Items[Item] = Details
                    del inventory[Item]
                else:
                    await stutter("That item isn't in your inventory.")

            elif Do in ['skip', 's']:
                skip = True
                await stutter('Text will now output instantly.')

            elif Do in ['noskip', 'ns', 'n']:
                skip = False
                await stutter('Text will now output gradually.')

            elif Do.startswith('setname'):
                new_name = Do.removeprefix('setname').strip()
                Player['Name'] = new_name
                await stutter(f"Your name is {Player['Name']}.")

            else:
                await stutter("That's not a valid command.")

    # logging
    @staticmethod
    def log(text):
        with open('log.txt', 'a+') as log_file:
            log_file.write('\n' + str(text))

    def log_start(self):
        self.log('\n')
        self.log('hello world!')
        self.log(str(datetime.now()))
