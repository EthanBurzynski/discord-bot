# importing discord and commands
import discord
from discord import app_commands
import json
import os
from dotenv import find_dotenv, load_dotenv
import datetime
from dateutil.relativedelta import relativedelta
import time
import heapq
import asyncio
import random
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import patches
import numpy as np
import io
from lz.reversal import reverse
from pytz import timezone
from twscrape import API, gather
from twscrape.logger import set_log_level
import urllib.request
import re
from collections import defaultdict

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
TWITTER_EMAIL_PASSWORD = os.getenv("TWITTER_EMAIL_PASSWORD")
# current server: egirls
ACTIVE_SERVER = 468638089359785984
MESSAGE_FILE_PATH = 'message_history.json'
TWEET_FILE_PATH = 'tweet_storage.json'
TWEET_ID_FILE_PATH = 'tweet_id_storage.json'
DELETED_BOT_MESSAGES_FILE_PATH = 'deleted_bot_history.json'
COMMAND_HISTORY_FILE_PATH = 'command_history.json'

# slash commands setup
discord.VoiceClient.warn_nacl = False
mintents = discord.Intents.all()
client = discord.Client(intents=mintents)
tree = app_commands.CommandTree(client)

# when bot is ready, prints the contents
@client.event
async def on_ready():
    await tree.sync(guild=discord.Object(id=ACTIVE_SERVER))
    print("bot is ready")
    # channel = client.get_channel(1261771365539909674)
    # await channel.send("bot is ready")

# -- MYCOMMAND --

@tree.command(
    name="mycommand",
    description="My first application command",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def first_command(interaction):
    num = random.randint(1,20)
    if num > 1:
        await interaction.response.send_message("Hello!")
    else:
        await interaction.response.send_message(f'You are a gooner \ud83e\udef5')

# -- REPEAT --

@tree.command(
    name="repeat",
    description="repeats what you say",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(repeat = "What should be repeated?")
async def repeat(interaction, repeat: str):
    if '@everyone' in repeat or '@here' in repeat:
        await interaction.response.send_message(f'not here either man. im better')
        return
    await interaction.response.send_message(repeat)

# -- NUKE --

@tree.command(
    name="nuke",
    description="deletes a number of messages",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(amount = "How many messages to delete? Maximum of 20")
async def nuke(interaction, amount: int):
    if amount < 21:
        await interaction.response.send_message(content=f'{amount} messages deleted', ephemeral=True)
        await interaction.channel.purge(limit=amount)
    else:
        await interaction.response.send_message(content=f'this command is capped at 20 messages at a time.', ephemeral=True)

# -- SEARCH --

@tree.command(
    name="search",
    description="search for a word or phrase",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(phrase = "What phrase to search for?")
@app_commands.describe(nobots = "Defaults to True, set to False to have bot results show up in search")
@app_commands.describe(fullwords = "Defaults to True, set to False to remove the full word filter")
async def search(interaction, phrase: str, nobots: bool = True, fullwords: bool = True):
    sortedSearchHits = []
    msgDict = {}
    server = client.get_guild(ACTIVE_SERVER)
    flags = re.IGNORECASE
    if fullwords:
        if phrase.isalnum():
            pattern = re.compile(fr'\b{phrase}\b', flags)
        else:
            pattern = re.compile(fr'(?<!\w){phrase}(?!\w)', flags)
    else:
        pattern = re.compile(phrase, flags)
    if '@everyone' in phrase or '@here' in phrase:
        await interaction.response.send_message(f'bro you really thought? naur...')
        return
    await interaction.response.send_message(f'Searching for phrase \'{phrase}\'...')
    with open(MESSAGE_FILE_PATH, 'r') as f:
        for line in f:
            x = json.loads(line)
            matches = pattern.findall(x.get("content"))
            if matches:
                if msgDict.get(x.get("authorID")):
                    msgDict[x.get("authorID")] += len(matches)
                else:
                    msgDict[x.get("authorID")] = len(matches)
    totalnum = 0
    for key,val in msgDict.items():
        if nobots:
            if client.get_user(key) != None and not client.get_user(key).bot:
                sortedSearchHits.append((val, client.get_user(key).name, str(server.get_member(key).color)))
                totalnum += val
        else:
            if client.get_user(key) != None and key != 1256666003417469028:
                sortedSearchHits.append((val, client.get_user(key).name, str(server.get_member(key).color)))
                totalnum += val
    sortedSearchHits = sorted(sortedSearchHits, key=lambda tup: tup[0], reverse=True)
    if not sortedSearchHits:
        await interaction.edit_original_response(content=f'nobody has said \'{phrase}\'. very sad')
    else:
        await interaction.edit_original_response(content=f'the phrase \'{phrase}\' came up {totalnum} times. it was sent the most times by {sortedSearchHits[0][1]} with {sortedSearchHits[0][0]} results.')

# -- SEARCH GRAPH --

@tree.command(
    name="searchgraph",
    description="create a bar graph of search results",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(phrase = "What phrase to search for?")
@app_commands.describe(nobots = "Defaults to True, set to False to have bot results show up in search")
@app_commands.describe(fullwords = "Defaults to True, set to False to remove the full word filter")
@app_commands.describe(normalize= "Defaults to False, set to True to normalize talking less")
async def searchgraph(interaction, phrase: str, nobots: bool = True, fullwords: bool = True, normalize: bool = False):
    sortedSearchHits = []
    msgDict = {}
    msgCount = {}
    server = client.get_guild(ACTIVE_SERVER)
    # make a pattern that will either filter for full words or not filter for full words
    flags = re.IGNORECASE
    if fullwords:
        if phrase.isalnum():
            pattern = re.compile(fr'\b{phrase}\b', flags)
        else:
            pattern = re.compile(fr'(?<!\w){phrase}(?!\w)', flags)
    else:
        pattern = re.compile(phrase, flags)
    
    if '@everyone' in phrase or '@here' in phrase:
        await interaction.response.send_message(f'bro you really thought? naur...')
        return
    await interaction.response.send_message(f'Searching for phrase \'{phrase}\'...')

    with open(MESSAGE_FILE_PATH, 'r') as f:
        for line in f:
            x = json.loads(line)
            # use the pattern from before and search for every non overlapping match in the content string and store them as a list
            matches = pattern.findall(x.get("content"))
            # if any matches were found, then...
            if matches:
                if msgDict.get(x.get("authorID")):
                    msgDict[x.get("authorID")] += len(matches)
                else:
                    msgDict[x.get("authorID")] = len(matches)
            if msgCount.get(x.get("authorID")):
                msgCount[x.get("authorID")] += 1
            else:
                msgCount[x.get("authorID")] = 1
    # msgDict should be filled up by now. what to do with it?
    # i want to transfer every element to a tuple so that i can sort by most search hits
    if not normalize:
        for key,val in msgDict.items():
            if nobots:
                if client.get_user(key) != None and not client.get_user(key).bot:
                    sortedSearchHits.append((val, client.get_user(key).name, str(server.get_member(key).color)))
            else:
                if client.get_user(key) != None and key != 1256666003417469028:
                    sortedSearchHits.append((val, client.get_user(key).name, str(server.get_member(key).color)))
    else: 
        for key,val in msgDict.items():
            if nobots:
                if client.get_user(key) != None and not client.get_user(key).bot:
                    sortedSearchHits.append((100 * val / msgCount[key], client.get_user(key).name, str(server.get_member(key).color)))
            else:
                if client.get_user(key) != None and key != 1256666003417469028:
                    sortedSearchHits.append((100 * val / msgCount[key], client.get_user(key).name, str(server.get_member(key).color)))
    # sort the list of tuples by the first element (the search hits), highest element first
    sortedSearchHits = sorted(sortedSearchHits, key=lambda tup: tup[0], reverse=True)
    nummessages, people, colors = map(list, zip(*sortedSearchHits))
    figsizemod = len(people) / 8
    plt.figure(figsize=(6.4 * figsizemod, 4.8 * figsizemod))
    if not normalize:
        plt.title(f'How many times \'{phrase}\' was sent')
    else:
        plt.title(f'What percent of messages contain \'{phrase}\'?')
    ax = plt.gca()
    bars = ax.bar(people, nummessages, width=0.8)
    tick_labels = ax.get_xticklabels()
    ax.set_yticks([])
    # ax.set_yticks(nummessages)
    # ax.yaxis.grid(visible=True, alpha=0.25)
    count = 0
    for label, bar in zip(tick_labels, bars):
        label.set_horizontalalignment('center')
        label.set_verticalalignment('bottom')
        label.set_fontweight('bold')
        label.set_fontfamily('monospace')
        label.set_fontsize('small')
        bar.set_color(colors[count])
        if not normalize:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), nummessages[count], ha='center', va='bottom')
        else: 
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(round(nummessages[count], 2)) + '%', ha='center', va='bottom')
        count += 1
        label.set_position((bar.get_x() + bar.get_width() / 2, (-0.02 / figsizemod) + (-0.05 / figsizemod) * (count % max(int(len(people) / 3), 1))))

    filename = "searchgraph.png"
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    graph = discord.File(filename)
    embed = discord.Embed()
    embed.set_image(url="attachment://searchgraph.png")
    await interaction.edit_original_response(embed=embed, attachments=[graph])

# -- ALPHABET --

@tree.command(
    name="alphabet",
    description="get a distribution of alphabetic characters for a user",
    guild = discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(person = "which person will it be")
@app_commands.describe(heatmap = "defaults to True, set to false to get a bar graph")
async def alphabet(interaction, person: str, heatmap: bool = True):
    # the answer is a dictionary. its always a dictionary
    # each key will be an alphabetical character, the value will be the number of that character
    # for each message hit in the file, iterate through each character and add it to the correct bucket when applicable
    # this will take a while, maybe have a interaction.edit_original_response in there 
    # then plot the data in a heat map
    await interaction.response.send_message(f'Searching...')
    frequency = defaultdict(int)
    serverfreq = defaultdict(int)
    charcount = 0
    servercharcount = 0
    with open(MESSAGE_FILE_PATH, 'r') as f:
        # MY TIME COMPLEXITY NOOOOOO actually its fine its O(n)
        for line in f:
            x = json.loads(line)
            linetoparse = x.get("content").casefold()
            for char in linetoparse:
                if x.get("author") == person:
                    if isenglishalpha(char):
                        frequency[char] += 1
                        serverfreq[char] += 1
                        charcount += 1
                        servercharcount += 1
                else:
                    if isenglishalpha(char):
                        serverfreq[char] += 1
                        servercharcount += 1
    print(frequency)
    if heatmap:
        keyboard_layout = {
            'q': (0, 0), 'w': (0, 1), 'e': (0, 2), 'r': (0, 3), 't': (0, 4), 'y': (0, 5), 'u': (0, 6), 'i': (0, 7), 'o': (0, 8), 'p': (0, 9),
            'a': (1, 0), 's': (1, 1), 'd': (1, 2), 'f': (1, 3), 'g': (1, 4), 'h': (1, 5), 'j': (1, 6), 'k': (1, 7), 'l': (1, 8),
            'z': (2, 0), 'x': (2, 1), 'c': (2, 2), 'v': (2, 3), 'b': (2, 4), 'n': (2, 5), 'm': (2, 6)
        }
        # create a 3 x 10 numpy array of zeroes
        formatteddata = np.zeros((3, 10))
        # for every key value pair in frequency
        for key, val in frequency.items():
            # get the row and column number from keyboard_layout at the key's position
            row, col = keyboard_layout[key]
            # add the data to the array at that position
            formatteddata[row, col] = val
        
        plt.figure(figsize=(10, 3))
        plt.title(f'{person}\'s alphabet heatmap! wow so cool')
        plt.imshow(formatteddata, cmap='cool', interpolation='nearest')

        for char, (row, col) in keyboard_layout.items():
            plt.text(col, row, char.upper(), ha='center', va='center', color='black', fontfamily='monospace', fontweight='bold')

        plt.colorbar()
        plt.xticks([])
        plt.yticks([])
    else:
        wikinumchars = [12.7, 9.1, 8.2, 7.5, 7.0, 6.7, 6.3, 6.1, 6.0, 4.3, 4.0, 2.8, 2.8, 2.4, 2.4, 2.2, 2.0, 2.0, 1.9, 1.5, 1.0, 0.8, 0.2, 0.2, 0.1, 0.1]
        # create a new dictionary of lists instead of using this list for wikinumchars
        # then for each key 'char':, append both the values of frequency and serverfreq at that key to the new dictionary
        # this way the data is all consistent per character centered on the wikinumchars
        listoftup = []
        serverchars = []
        server = client.get_guild(ACTIVE_SERVER)
        for key, val in frequency.items():
            listoftup.append((100 * val / charcount, key))
        listoftup = sorted(listoftup, key=lambda tup: tup[0], reverse=True)
        numchars, letter = map(list, zip(*listoftup))
        for key, val in serverfreq.items():
            serverchars.append(100 * val / servercharcount)
        serverchars = sorted(serverchars, reverse=True)
        index = np.arange(26)
        plt.figure(figsize=(6.4 * 3, 4.8 * 3))
        plt.title(f'average letter frequency for {person}')
        ax = plt.gca()
        # personbars = ax.bar(letter, numchars, width=0.8)
        bar_width = 0.25
        personbars = ax.bar(index, numchars, bar_width, label=f'{person}', color='C0')
        serverbars = ax.bar(index+bar_width, serverchars, bar_width, label='server', color='C1')
        wikibars = ax.bar(index+(bar_width * 2), wikinumchars, bar_width, label='english', color='C2')
        ax.legend()
        ax.set_xticks(index + bar_width)
        ax.set_xticklabels([letter])
        # tick_labels = ax.get_xticklabels()
        # ax.set_yticks([])
        # count = 0
        # for label, bar in zip(tick_labels, personbars):
        #     label.set_horizontalalignment('center')
        #     label.set_verticalalignment('bottom')
        #     label.set_fontweight('bold')
        #     label.set_fontfamily('monospace')
        #     bar.set_color(str(server.get_member_named(person).color))
        #     ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), str(round(numchars[count], 1)) + '%', ha='center', va='bottom')
        #     count += 1
        #     label.set_position((bar.get_x() + bar.get_width() / 2, -0.02))
    filename = "alphabet.png"
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    graph = discord.File(filename)
    embed = discord.Embed()
    embed.set_image(url="attachment://alphabet.png")
    await interaction.edit_original_response(embed=embed, attachments=[graph])


def isenglishalpha(char):
    return char.isascii() and char.isalpha()

# -- SCRAPE --

@tree.command(
    name="scrape",
    description="scrape some data or smth",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(person= "which person to get data for")
async def scrape(interaction, person: str):
    totalchar = 0
    msgcount = 0
    with open(MESSAGE_FILE_PATH, 'r') as f:
        for line in f:
            x = json.loads(line)
            if (x.get("author") == person):
                totalchar += len(x.get("content"))
                msgcount += 1
    await interaction.response.send_message(f'Average message length for {person}: {round((totalchar / msgcount), 3)}')

# -- WHEN THE DELETE IS MANY --

@tree.command(
    name="whenthedeleteismany",
    description="get a top 10 list of who has deleted the sus bot messages the most",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def whenthedeleteismany(interaction):
    strToSend = ""
    n = 10
    count = 0
    thingy = []
    with open(DELETED_BOT_MESSAGES_FILE_PATH, 'r') as f:
        log = json.loads(f.read())
        for key,val in log.items():
            heapq.heappush(thingy, (val, key))
        if len(thingy) < 10:
            n = len(thingy)
        thingy = heapq.nlargest(n, thingy)
        for i in thingy:
            count += 1
            strToSend += f'{count}. {i[1]}: {i[0]}\n'
    await interaction.response.send_message(strToSend)

# -- COMMAND STATS --

@tree.command(
    name="commandstats",
    description="gets a list of how many times each command has been used",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(person = "which person to get stats for, defaults to nobody")
async def commandstats(interaction, person: str = None):
    strToSend = ""
    # n = 10
    count = 0
    globaldict = {}
    thingy = []
    with open(COMMAND_HISTORY_FILE_PATH, 'r') as f:
        for line in f:
            log = json.loads(line)
            for name,ndict in log.items():
                if not person:
                    for comname,comnum in ndict.items():
                        if not globaldict.get(comname):
                            globaldict[comname] = comnum
                        else:
                            globaldict[comname] += comnum
                else:
                    if name == person:
                        for comname,comnum in ndict.items():
                            if not globaldict.get(comname):
                                globaldict[comname] = comnum
                            else:
                                globaldict[comname] += comnum
                        strToSend += f'{person}\'s command stats:\n'
        if not globaldict:
            strToSend += f'no command history found for {person}'
            await interaction.response.send_message(strToSend)
            return
        for key,val in globaldict.items():
            heapq.heappush(thingy, (val, key))
        # if len(thingy) < 10:
        #     n = len(thingy)
        thingy = heapq.nlargest(len(thingy), thingy)
        for i in thingy:
            count += 1
            strToSend += f'{count}. {i[1]}: {i[0]}\n'
    await interaction.response.send_message(strToSend)

# -- COINFLIP --

@tree.command(
    name="coinflip",
    description="flip a coin. any coin",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(hidden = "Defaults to False, change to True to hide the coinflip from the world")
@app_commands.describe(numsides = "Defaults to 2. The number of sides to the coin")
async def coinflip(interaction, hidden: bool = False, numsides: int = 2):
    numsides = abs(numsides)
    try:
        num = random.randint(1,numsides)
        if(numsides == 2):
            if num == 1:
                await interaction.response.send_message("its heads bitch", ephemeral=hidden)
            else:
                await interaction.response.send_message("tails. bet u like tails. fury", ephemeral=hidden)
        else:
            formatted_num = format_numsides(num)
            await interaction.response.send_message(f'secret {formatted_num} side!', ephemeral=hidden)
    except ValueError as e:
        print('ValueError raised: ', e)
        await interaction.response.send_message(f'narr bro. dont zero')

def format_numsides(num):
    if num % 100 != 12 and num % 10 == 2:
        return f'{num}nd'
    elif num % 100 != 13 and num % 10 == 3:
        return f'{num}rd'
    elif num % 100 != 11 and num % 10 == 1:
        return f'{num}st'
    else:
        return f'{num}th'

# -- NO LIFE GRAPH --

@tree.command(
    name="nolifegraph",
    description="generate an up to date no life graph",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(date = "Enter a date in the format MM/DD/YY. No response defaults to current date")
@app_commands.describe(minimum = "The minimum number of total messages someone needs to show up on the graph. Defaults to 1,000")
@app_commands.describe(maximum = "The maximum number of total messages someone can have to show up on the graph. Defaults to 1,000,000")
@app_commands.describe(person = "Filter to specific usernames. If entering multiple, separate with commas. Defaults to nobody")
@app_commands.describe(word = "specific word to format graph around. leave blank for no specific word")
async def nolifegraph(interaction, date: str = str(datetime.datetime.now().strftime("%x")), minimum: int = 1000, maximum: int = 1000000, person: str = None, word: str = None):
    # make sure the input is allowed
    try:
        # main code block
        # re converting date back to a datetime object from a string
        # and then converting the mm/dd/yy format to time since epoch since that format works better for message_history.json
        date = datetime.datetime.strptime(date, '%m/%d/%y')
        # adding 86400 because datetime.datetime.now().strftime("%x") gets the mm/dd/yy but not the exact time of day
        # since the goal for the default state is to get EVERY message, adding 86400 (the number of seconds in a day) 
        # adds a day to date and guarantees that every message was sent before it
        date = time.mktime((date).timetuple()) + 86400

        if person:
            person = person.replace(' ', '')
            person = list(person.split(","))
        flags = re.IGNORECASE
        if word:
            if word.isalnum():
                pattern = re.compile(fr'\b{word}\b', flags)
                if minimum == 1000:
                    minimum = 0
            else:
                pattern = re.compile(fr'(?<!\w){word}(?!\w)', flags)
                if minimum == 1000:
                    minimum = 0
        # start time, hardcoded to the first message every sent (keith's joining message)
        startTime = datetime.datetime.fromtimestamp(1535451470)
        # this will be a dictionary of lists, where each list is [totalmessages, dictionary] - each key will be a username that points to a list
        # the nested dictionary will have one key for each month (denoted by count). for example, the first month
        # could be {'0': 182} and the second month could be {'1': 723}.
        msgHistory = {}
        count = 1
        # the amount of total messages that have needed to be sent before a data point appears on the graph
        oldval = 0
        # messing with matplotlib stuff
        plt.title("No Life Graph")
        plt.xlabel("Date (MM/YY)")
        plt.ylabel("Number of Total Messages")
        ax = plt.gca()
        with open(MESSAGE_FILE_PATH, 'r') as f:
            await interaction.response.send_message(content=f'Processing messages...')
            if not person:
                for line in f:
                    # the everything variable
                    z = json.loads(line)
                    if not word:
                        # check if the author of z has a key in the dictionary. if not, add one
                        if not msgHistory.get(z.get("author")):
                            msgHistory[z.get("author")] = [0, {}, z.get("authorID")]

                        # now check if the author of z has the key 'count' in the dictionary. if not, add one and set the initial value to 1
                        if not msgHistory.get(z.get("author"))[1].get(count):
                            msgHistory.get(z.get("author"))[1][count] = 1
                            msgHistory.get(z.get("author"))[0] += 1
                        # otherwise, increment the value by 1
                        else:
                            msgHistory.get(z.get("author"))[1][count] += 1
                            msgHistory.get(z.get("author"))[0] += 1
                        # input date checking
                        if date < z.get("time"):
                            break
                        # code to check if a month has passed
                        # 365 / 12 * 86400 is the average number of seconds in a month across a 365 day year
                        # that magic number is 2,628,000
                        timeElapsed = z.get("time") - startTime.timestamp()
                        if(timeElapsed >= 2628000):                            
                            # should run at the end of this code block
                            timeElapsed = 0
                            count += 1
                            startTime = datetime.datetime.fromtimestamp(z.get("time"))
                    else:
                        matches = pattern.findall(z.get("content"))
                        # check if the author of z has a key in the dictionary. if not, add one
                        if not msgHistory.get(z.get("author")):
                            msgHistory[z.get("author")] = [0, {}, z.get("authorID")]

                        # now check if the author of z has the key 'count' in the dictionary. if not, add one and set the initial value to 1
                        if not msgHistory.get(z.get("author"))[1].get(count):
                            msgHistory.get(z.get("author"))[1][count] = len(matches)
                            msgHistory.get(z.get("author"))[0] += len(matches)
                        # otherwise, increment the value by 1
                        else:
                            msgHistory.get(z.get("author"))[1][count] += len(matches)
                            msgHistory.get(z.get("author"))[0] += len(matches)
                        # input date checking
                        if date < z.get("time"):
                            break
                        # code to check if a month has passed
                        # 365 / 12 * 86400 is the average number of seconds in a month across a 365 day year
                        # that magic number is 2,628,000
                        timeElapsed = z.get("time") - startTime.timestamp()
                        if(timeElapsed >= 2628000):                            
                            # should run at the end of this code block
                            timeElapsed = 0
                            count += 1
                            startTime = datetime.datetime.fromtimestamp(z.get("time"))
            else:
                # one comparison is faster than 330k comparisons so i just basically copied the code block above and modified it a tiny bit
                # for when the person attribute is a person and not None
                for line in f:
                    # the everything variable
                    z = json.loads(line)
                    if not word:
                        # check if the author of z has a key in the dictionary. if not, add one
                        if not msgHistory.get(z.get("author")) and z.get("author") in person:
                            msgHistory[z.get("author")] = [0, {}, z.get("authorID")]

                        # now check if the author of z has the key 'count' in the dictionary. if not, add one and set the initial value to 1
                        if z.get("author") in person:
                            if not msgHistory.get(z.get("author"))[1].get(count):
                                msgHistory.get(z.get("author"))[1][count] = 1
                                msgHistory.get(z.get("author"))[0] += 1
                            # otherwise, increment the value by 1
                            else:
                                msgHistory.get(z.get("author"))[1][count] += 1
                                msgHistory.get(z.get("author"))[0] += 1
                        # input date checking
                        if date < z.get("time"):
                            break
                        # code to check if a month has passed
                        # 365 / 12 * 86400 is the average number of seconds in a month across a 365 day year
                        # that magic number is 2,628,000
                        timeElapsed = z.get("time") - startTime.timestamp()
                        if(timeElapsed >= 2628000):                            
                            # should run at the end of this code block
                            timeElapsed = 0
                            count += 1
                            startTime = datetime.datetime.fromtimestamp(z.get("time"))
                    else:
                        matches = pattern.findall(z.get("content"))
                        # check if the author of z has a key in the dictionary. if not, add one
                        if not msgHistory.get(z.get("author")) and z.get("author") in person:
                            msgHistory[z.get("author")] = [0, {}, z.get("authorID")]

                        # now check if the author of z has the key 'count' in the dictionary. if not, add one and set the initial value to 1
                        if z.get("author") in person:
                            if not msgHistory.get(z.get("author"))[1].get(count):
                                msgHistory.get(z.get("author"))[1][count] = len(matches)
                                msgHistory.get(z.get("author"))[0] += len(matches)
                            # otherwise, increment the value by 1
                            else:
                                msgHistory.get(z.get("author"))[1][count] += len(matches)
                                msgHistory.get(z.get("author"))[0] += len(matches)
                        # input date checking
                        if date < z.get("time"):
                            break
                        # code to check if a month has passed
                        # 365 / 12 * 86400 is the average number of seconds in a month across a 365 day year
                        # that magic number is 2,628,000
                        timeElapsed = z.get("time") - startTime.timestamp()
                        if(timeElapsed >= 2628000):                            
                            # should run at the end of this code block
                            timeElapsed = 0
                            count += 1
                            startTime = datetime.datetime.fromtimestamp(z.get("time"))
            await interaction.edit_original_response(content=f'Generating the graph...')
            # code block for adding current points to plot
            # will want to run this one more time outside of the loop to get the last fragment of a month
            for ndict in msgHistory.keys():
                w = []
                y = []
                # f = []
                if not "#" in ndict:
                    for key, val in msgHistory[ndict][1].items():                            
                        if maximum > msgHistory[ndict][0] > minimum:
                            w.append(key)
                            y.append(val + oldval)
                            # if key % 4 == 0:
                            #     f.append(key)
                            oldval += val
                tflag = False
                if y:
                    tflag = True
                #x = np.array(x)
                if tflag:
                    server = client.get_guild(ACTIVE_SERVER)
                    if server.get_member(msgHistory[ndict][2]) != None:
                        member = server.get_member(msgHistory[ndict][2])
                        memColor = str(member.color)
                        # real start date is 2018/08/27 but this will make it look nicer
                        start_date = datetime.datetime(2018, 8, 1)
                        date_list = [start_date + relativedelta(months = i) for i in w]
                        # point_date_list = [start_date + relativedelta(months = i) for i in f]
                        # point_messages = [y[min(index - w[0], len(point_date_list)*4 - 1)] for index in f]
                        x = np.array(date_list)
                        y = np.array(y)
                        plt.plot(x, y, color=memColor, linewidth=2)
                        # plt.scatter(point_date_list, point_messages, color=memColor, zorder=5, s=8)
                        plt.text(x[-1], y[-1], f'{ndict}')
                oldval = 0
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=4))
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linewidth=1, alpha=0.8)
        ax.grid(which='major', axis='x', linewidth=0.5, alpha=0.25)
        plt.setp(ax.get_xticklabels(), rotation=60, ha='center')
        filename = "nolifegraph.png"
        plt.savefig(filename, bbox_inches='tight')
        plt.close()
        graph = discord.File(filename)
        embed = discord.Embed()
        embed.set_image(url="attachment://nolifegraph.png")
        if not word:
            word = "no word specified"
        if maximum == 1000000:
            await interaction.edit_original_response(content=f'no life graph generated :3\ndate: {datetime.datetime.fromtimestamp(date)}\nminimum: {minimum}\nspecific word: {word}')
        else:
            await interaction.edit_original_response(content=f'no life graph generated :3\ndate: {datetime.datetime.fromtimestamp(date)}\nminimum: {minimum}\nmaximum: {maximum}\nspecific word: {word}')
        await interaction.edit_original_response(embed=embed, attachments=[graph])
    except ValueError as e:
        print('ValueError Raised:', e)
        await interaction.response.send_message("narr bro")

# -- TEST GRAPH --

@tree.command(
    name="testgraph",
    description="this is a testing function for generating a graph",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def testgraph(interaction):
    plt.title(":8D:")
    plt.axis('off')
    fig = plt.gcf()
    ax = fig.gca()
    fig.set_facecolor('yellow')
    t = np.linspace(0, 2*np.pi, num=1000)
    x1 = (np.cos(t) / (np.sin(t) ** 2 + 1)) + 1
    y1 = np.cos(t) * np.sin(t) / (np.sin(t) ** 2 + 1)
    plt.plot(x1, y1, color='black', linewidth=6, fillstyle='full', gapcolor='white')
    ax.fill_between(x1, y1, color='white')
    x2 = np.array([0, 2])
    y2 = np.array([-0.5, -0.5])
    plt.plot(x2, y2, color='black', linewidth=6)
    x3 = np.linspace(0, 2, num=1000)
    y3 = (-1 * np.sqrt(((-1 * ((x3 - 1) ** 2)) + 1))) - 0.5
    plt.plot(x3, y3, color='black', linewidth=6)
    ax.fill_between(x3, y3, -0.5, color='white')
    testCircle = patches.Circle((0.425, 0), 0.1, color='black', fill=True)
    testCircle2 = patches.Circle((1.575, 0), 0.1, color='black', fill=True)
    ax.add_patch(testCircle)
    ax.add_patch(testCircle2)
    filename = "testgraph.png"
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    graph = discord.File(filename)
    embed = discord.Embed()
    embed.set_image(url="attachment://testgraph.png")
    await interaction.response.send_message(embed=embed, file=graph)

# -- GET PAST DAY MESSAGES --

@tree.command(
    name="getpastdaymessages",
    description="get all the messages sent from midnight pst to now and update the message file with them",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.checks.has_permissions(administrator=True)
async def getpastdaymessages(interaction):
    await interaction.response.send_message(content="Beginning message processing...", ephemeral=True)
    # for each channel, keep parsing messages until the time the message was sent is older than midnight pst
    # we'll have to do some time processing before this loop by getting the current time and figuring out what day it is from that
    # once we have a list of message dictionaries, sort this list by the msg id (maybe store as tuples (id, msgdict) to easily sort?)
    # or: newlist = sorted(list_to_be_sorted, key=lambda d: d['name'])
    # format for dates
    dateFormat = '%Y/%m/%d %H:%M:%S %Z'
    # get current time in pst
    # curTime = datetime.datetime.now(tz=pytz.utc).astimezone(timezone('US/Pacific'))
    curTime = datetime.datetime.now()
    # convert curTime to time since epoch and subtract a day from that 
    endTimeUnix = time.mktime((curTime).timetuple()) - 86400
    # get every channel and make a list of them
    server = client.get_guild(ACTIVE_SERVER)
    channel_list = []
    for cchannel in server.channels:
        if(str(cchannel.type) == 'text'):
            channel_list.append(cchannel)
    await interaction.edit_original_response(content=f'{len(channel_list)} channels loaded...')
    # actual loop to get messages
    msgList = []
    for tchannel in channel_list:
        # can use limit=None here to keep getting messages
        # can then break out of the loop once "time" is less than endTimeUnix
        async for msg in tchannel.history(limit=None):
            msgStored = {
                "author": str(msg.author),
                "authorID": msg.author.id,
                "content": msg.content,
                "channel": str(msg.channel),
                "channelID": msg.channel.id,
                "msgID": msg.id,
                # subtracting 25200 to hardcode the timezone to pst instead of utc
                # could use float(time.mktime(((msg.created_at).astimezone(timezone('US/Pacific'))).timetuple())) 
                # for timezone support but im lazy and idk if it would work
                "time": float(time.mktime((msg.created_at).timetuple()) - 25200)
            }
            if msgStored.get("time") < endTimeUnix:
                break
            # order doesnt matter so im just appending
            # we will sort after
            msgList.append(msgStored)
    await interaction.edit_original_response(content=f'{len(msgList)} messages loaded...')
    # plan from here on out: have two files. one is the dynamically updated one that updates with messages throughout the day
    # the other will be one that only has messages up to the start of the current day
    # we can open that second file in append mode, append the sorted list of messages (still have to sort)
    # then, copy the file we just wrote to and overwrite the dynamically updating one
    # this way i dont have to iterate backwards through the file

    # potential problem: this function only gets messages from midnight until the time its run, so overwriting files like this could lose some messages
    # for example: this function is run at noon, and gets 12 hours of messages. Then, a bunch of messages are sent and stored in the dynamic file
    # the next day, this function is again run at noon. Since the daycapped file only has messages up to yesterdays noon, it misses every message sent between noon and 11:59pm
    # potential solution: automatically run this function every day at 11:59pm
    # other potential solution: traverse backwards instead of this two file overwriting system
    msgList = sorted(msgList, key=lambda d: d["msgID"])
    charCount = 0
    with open(MESSAGE_FILE_PATH, 'r+') as f:
        for line in reverse(f, batch_size=io.DEFAULT_BUFFER_SIZE):
            # char count is to change the position of the file cursor eventually
            charCount += len(line)
            if json.loads(line).get("time") < endTimeUnix:
                charCount -= len(line)
                f.seek(0, 2)
                # the one extra character is the end of file character thingy
                # seek to position right at the start of the final message we logged
                f.seek(f.tell() - charCount - 1, 0)
                f.truncate()
                break
        for ndict in msgList:
            json.dump(ndict, f)
            f.write('\n')

# -- GET ALL MESSAGES --

@tree.command(
    name="getallmessages",
    description="goes through every message and stores them",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.checks.has_permissions(administrator=True)
async def getallmessages(interaction):
    #general
    channelToSend = interaction.channel
    channel = client.get_channel(686423342345093203)
    channel_list = []
    # numOfRemainingChannels = 0
    # hard coded server id (currently testing emoji)
    server = client.get_guild(ACTIVE_SERVER)
    await interaction.response.send_message(content=f'Beginning the process...', ephemeral=True)
    for cchannel in server.channels:
        if(str(cchannel.type) == 'text'):
            channel_list.append(cchannel)
            # numOfRemainingChannels += 1
    # channel = bot.get_all_channels
    await interaction.edit_original_response(content=f'Adding {len(channel_list)} channels...')
    msgCount = 0
    allMessage = []
    lastUnchecked = []
    messageDump = {}
    oldestChnl = channel
    markForDel = []
    seenIDS = set()
    curMessage = datetime.datetime.fromtimestamp(1483272000)

    # get 100 messages from each channel initially to fill messageDump
    for tchannel in channel_list:
        templ = []
        async for msg in tchannel.history(limit=100, after=curMessage, oldest_first=True):
            templ.append(msg)
        # messageDump is a dictionary with channels as the key and 100 (or less) messages as the value
        # check to remove any channels with 0 messages since they cause an index out of bounds error
        if templ:
            messageDump[tchannel] = templ
            msgCount += 1
            await interaction.edit_original_response(content=f'Adding {len(messageDump[tchannel])} messages to the initial list... ({msgCount}/{len(channel_list) - len(markForDel)})')
        else:
            markForDel.append(msgCount)
    for x in markForDel:
        del channel_list[x]
    msgCount = 0
    # initial filling of lastUnchecked so that the loop after this works
    for tchannel in channel_list:
        msg = (messageDump.get(tchannel))[0]
        msgStored = {
            "author": str(msg.author),
            "authorID": msg.author.id,
            "content": msg.content,
            "channel": str(msg.channel),
            "channelID": msg.channel.id,
            "msgID": msg.id,
            # subtracting 25200 because thats the number of seconds in 7 hours (utc to pst)
            "time": float(time.mktime((msg.created_at).timetuple()) - 25200)
        }
        msgCount += 1
        # remove first item in list
        (messageDump.get(tchannel)).pop(0)
        # should only need to run this once, then in the while loop just check the second condition
        # first condition is just a check to see if there are any elements in the list since the next condition breaks without any elements in the list

        heapq.heappush(lastUnchecked, (msgStored["msgID"], msgStored))

    # printing the length of lastUnchecked and the length of the allMessage list.
    # left side should be number of channels and right side should count up to the number of total messages
    print(f'{len(lastUnchecked)}, {len(allMessage) + 1}')
    # using messages for the after= part of .history since it's way more accurate
    # tried using dates but it would skip every remaining message from the day the message was sent
    # probably my fault
    curMessage = discord.Object(id=lastUnchecked[0][1].get("msgID"))
    oldestChnl = client.get_channel(lastUnchecked[0][1].get("channelID"))
    # removes first element from list and appends it to allMessage
    # using a set to check if the element is a duplicate
    mID = lastUnchecked[0][1].get("msgID")
    if mID not in seenIDS:
        seenIDS.add(mID)
        allMessage.append(heapq.heappop(lastUnchecked)[1])
    else:
        heapq.heappop(lastUnchecked)
        msgCount -= 1
        print("duplicate found!")
    # allMessage.append(heapq.heappop(lastUnchecked)[1])

    # while elements are in lastUnchecked, this loop will run. this should end after the last message has been processed
    while lastUnchecked:
        if messageDump:
            msg = (messageDump.get(oldestChnl))[0]
            msgStored = {
                "author": str(msg.author),
                "authorID": msg.author.id,
                "content": msg.content,
                "channel": str(msg.channel),
                "channelID": msg.channel.id,
                "msgID": msg.id,
                # subtracting 25200 because thats the number of seconds in 7 hours (utc to pst)
                "time": float(time.mktime((msg.created_at).timetuple()) - 25200)
            }
            msgCount += 1
            (messageDump.get(oldestChnl)).pop(0)
            heapq.heappush(lastUnchecked, (msgStored["msgID"], msgStored))
            curMessage = discord.Object(id=lastUnchecked[0][1].get("msgID"))
            oldestChnl = client.get_channel(lastUnchecked[0][1].get("channelID"))

        print(f'{len(lastUnchecked)}, {len(allMessage) + 1}')
        # if (len(allMessage) + 1) > 331677:
        #     print("test")

        if not messageDump.get(oldestChnl):
            messageDump[oldestChnl] = await get100Messages(oldestChnl, curMessage)
            # this problem becomes greater the more channels there are
            # there is definitely a solution to be had here with a loop
            # but i dont want to try that right now
            # so instead ill just manually clear up the messages
            # if (int(msgStored.get("channelID")) == int(lastUnchecked[0][1].get("channelID"))) and (msgStored.get("msgID") != lastUnchecked[0][1].get("msgID")):
            #     del messageDump.get(oldestChnl)[0]
            # first check: if there still isnt anything in messagedump at position oldestChnl, do this if statement
            # second check: if messagedump still has something left in it. if this isnt true, theres no need to 
            # go through all of this since every remaining message is in lastUnchecked
            if not messageDump.get(oldestChnl):
                # remove the emptry key/value pair from messagedump since its no longer needed
                del messageDump[oldestChnl]
                if messageDump:
                    temp = []
                    for item in messageDump.values():
                    # i have no idea if this will even work
                    # theoretically we are indexing to the first (and only) dictionary of item
                    # which should be the key value pair of channel : [list of messages]
                    # then find the first index of that list (which should be a message object)
                    # get the channel id and the message id of that message and submit it as a tuple
                        if item:
                            heapq.heappush(temp, (item[0].id, item[0].channel.id))
                    # HERE WAS THE PROBLEM
                    if temp:
                        oldestChnl = client.get_channel(temp[0][1])
                    else:
                        messageDump.clear()
        mID = lastUnchecked[0][1].get("msgID")
        if mID not in seenIDS:
            seenIDS.add(mID)
            allMessage.append(heapq.heappop(lastUnchecked)[1])
        else:
            heapq.heappop(lastUnchecked)
            msgCount -= 1
            print("duplicate found!")
        # allMessage.append(heapq.heappop(lastUnchecked)[1])

    # i really cant be bothered to fix the issue of duplicate values at the end of the list sooo
    # heres a linear time thingy that uses a set to check if there is a duplicate msg ID
    # if the id isnt a duplicate, add it to noDupeMessage
    # if it is a duplicate, subtract 1 from msgCount to correct the errors
    # seenIDS = set()
    # noDupeMessage = []
    # for ndict in allMessage:
    #     mID = ndict.get("msgID")
    #     if mID not in seenIDS:
    #         seenIDS.add(mID)
    #         noDupeMessage.append(ndict)
    #     else:
    #         msgCount -= 1

    with open(MESSAGE_FILE_PATH, 'w') as f:
        for mdict in allMessage:
            json.dump(mdict, f)
            f.write('\n')
    print(msgCount)

    await confirmationMessage(msgCount, channelToSend)
    # await interaction.edit_original_response(content=f'Found and stored {msgCount} messages')

# helper function for getAllMessages
# takes a channel and a message to get the messages after
async def get100Messages(channel, curMessage):
    msgList = []
    async for msg in channel.history(limit=100, after=curMessage, oldest_first=True):
        msgList.append(msg)
    return msgList

async def confirmationMessage(msgCount, channel):
    await channel.send(f'Found and stored {msgCount} messages')

# -- TWITTER THING --

@tree.command(
    name="yey",
    description="lol",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def yey(interaction):
    await interaction.response.send_message("YEY!!!!!!!!!!!!! LETS GO !!!! you are a stupid little bitch")

@tree.command(
    name="twt",
    description="get twitter image. wow",
    guild=discord.Object(id=ACTIVE_SERVER)
)
# @app_commands.checks.has_permissions(administrator=True)
async def twt(interaction):
    # create a list and a set - the set is for checking duplicate ids cause im lazy
    tweetlist = []
    seenIDS = set()
    await interaction.response.send_message(f'searching for image...')
    with open(TWEET_ID_FILE_PATH, 'r') as f:
        for line in f:
            seenIDS.add(json.loads(line).get("msgID"))
    # open the tweet file
    with open(TWEET_FILE_PATH, 'r+') as f:
        # load every dictionary from the file
        for line in f:
            x = json.loads(line)
            tweetlist.append(x)
        testlist = []
        imageurl = "noimage"
        # if the file has less than 10 entries left, get 20 new entries (duplicates filtered out)
        if len(tweetlist) < 3:
            api = API()
            # add twitter accounts and log in
            await api.pool.add_account(TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_EMAIL, TWITTER_EMAIL_PASSWORD)
            await api.pool.login_all()
            testlist = await gather(api.search("filter:follows filter:images include:nativeretweets", limit=20))
            for tweet in testlist:
                if ((tweet.id not in seenIDS) and (tweet.retweetedTweet == None)):
                    seenIDS.add(tweet.id)
                    if tweet.media.photos:
                        imageurl = tweet.media.photos[0].url
                    tweetStored = {
                        "url": tweet.url,
                        "imgurl": imageurl,
                        "username": tweet.user.username,
                        "msgID": tweet.id
                    }
                    tweetlist.append(tweetStored)
                elif ((tweet.retweetedTweet) and (tweet.retweetedTweet.id not in seenIDS)):
                    seenIDS.add(tweet.retweetedTweet.id)
                    tweetStored = {
                        "url": tweet.retweetedTweet.url,
                        "imgurl": tweet.retweetedTweet.media.photos[0].url,
                        "username": tweet.retweetedTweet.user.username,
                        "msgID": tweet.retweetedTweet.id
                    }
                    tweetlist.append(tweetStored)
        if not tweetlist:
            await interaction.edit_original_response(content=f'no new posts yet. stop gooning and wait a while')
            return
        # shuffle everything in tweetlist
        random.shuffle(tweetlist)
        # store the tweet author and the link to the tweet in one embed, store the image itself in another
        embedAuthor = discord.Embed()
        embedAuthor.set_author(name=f'from {tweetlist[0].get("username")}:', url=tweetlist[0].get("url"))
        if not tweetlist[0].get("imgurl") == "noimage":
            filename = "tweetimage.png"
            urllib.request.urlretrieve(tweetlist[0].get("imgurl"), filename)
            tweetfile = discord.File(filename)
            embedFile = discord.Embed()
            embedFile.set_image(url="attachment://tweetimage.png")
        else:
            filename = "lips.png"
            tweetfile = discord.File(filename)
            embedFile = discord.Embed()
            embedFile.set_image(url="attachment://lips.png")
        # send both embeds
        await interaction.edit_original_response(content=None, embeds=[embedAuthor, embedFile], attachments=[tweetfile])
        # remove first element of the list (it's already been sent, no need to send it again)
        tweetlist.pop(0)
        # seek to beginning of file and truncate
        f.seek(0, 0)
        f.truncate()
        # write everything in tweetlist to file
        for ndict in tweetlist:
            json.dump(ndict, f)
            f.write('\n')
    with open(TWEET_ID_FILE_PATH, 'w') as f:
        for id in seenIDS:
            idStored = {"msgID": id}
            json.dump(idStored, f)
            f.write('\n')


@client.event
async def on_audit_log_entry_create(entry):
    channel = client.get_channel(1261771365539909674)
    ACTION_STRING = format_action(entry)
    #print(f'{(entry.after).__dict__.keys()}')
    await channel.send(f'{entry.user} {ACTION_STRING}')

def format_action(entry):
    match (entry.action).name:
        case "guild_update":
            return f'updated the server: {(entry.after).__dict__}'
        case "channel_create":
            return f'created a {(entry.after).type} channel #{entry.target}'
        case "channel_update":
            return f'made changes to #{entry.target}: {(entry.after).__dict__}'
        case "channel_delete":
            return f'deleted the {(entry.before).type} channel #{(entry.before).name}'
        case "overwrite_create":
            return f'created a channel permission overwrite in #{entry.target} for {(entry.extra)}: {(entry.after).__dict__}'
        case "overwrite_delete":
            return f'deleted a channel permission overwrite in #{entry.target} for {(entry.extra)}: {(entry.after).__dict__}'
        case "kick":
            return f'kicked {entry.target.name} from the server'
        case "ban":
            return f'banned {entry.target.name} from the server'
        case "unban":
            return f'unbanned {entry.target.name} from the server'
        case "member_update":
            return f'updated {entry.target}: {(entry.after).__dict__}'
        case "member_role_update":
            return f'updated {entry.target}\'s roles: {(entry.after).__dict__}'
        case "member_move":
            return f'moved a member to {(entry.extra).channel}'
        case "member_disconnect":
            return f'disconnected a member from a voice channel'
        case "role_create":
            return f'created a new role named {(entry.after).name}'
        case "role_update":
            return f'updated the role named {(entry.before).name}: {(entry.after).__dict__}'
        case "role_delete":
            return f'deleted the role named {(entry.before).name}'
        case "invite_create":
            return f'created a new invitation to the server'
        case "invite_update":
            return f'updated an invitation to the server: {(entry.after).__dict__}'
        case "invite_delete":
            return f'deleted an invitation to the server'
        case "emoji_create":
            return f'created an emoji named {(entry.after).name}'
        case "emoji_update":
            return f'updated the emoji named {(entry.before).name}: {(entry.after).__dict__}'
        case "emoji_delete":
            return f'deleted the emoji named {(entry.before).name}'
        case "message_delete":
            return f'deleted {(entry.extra).count} messages sent by {entry.target} in #{(entry.extra).channel}'
        case "message_bulk_delete":
            return f'deleted {(entry.extra).count} messages in #{entry.target}'
        case "message_pin":
            return f'pinned the message (ID: {(entry.extra).message_id}) sent by {entry.target} to #{(entry.extra).channel}'
        case "message_unpin":
            return f'unpinned the message (ID: {(entry.extra).message_id}) sent by {entry.target} to #{(entry.extra).channel}'
        case "sticker_create":
            return f'created a sticker named {(entry.after).name}'
        case "sticker_update":
            return f'updated the sticker named {(entry.before).name}: {(entry.after).__dict__}'
        case "sticker_delete":
            return f'deleted the sticker named {(entry.before).name}'
        case _:
            return 'did an unknown action... ooooooh...h.... how meysterious,'

@client.event
async def on_app_command_completion(interaction, command):
    loglist = []
    success = {}
    with open(COMMAND_HISTORY_FILE_PATH, 'r+') as f:
        for line in f:
            # each line will be a dictionary with a key value pair of user:dict
            # the dict will be the actual command stats
            log = json.loads(line)
            if not log.get(interaction.user.name):
                loglist.append(log)
            else:
                success = log
        if not success:
            success[interaction.user.name] = {}
            success[interaction.user.name][command.name] = 1
            loglist.append(success)
        else:
            if not success[interaction.user.name].get(command.name):
                success[interaction.user.name][command.name] = 1
            else:
                success[interaction.user.name][command.name] += 1
            loglist.append(success)
        f.seek(0)
        for ndict in loglist:
            json.dump(ndict, f)
            f.write('\n')
        f.truncate()

@client.event
async def on_message(msg):
    msgStored = {
        "author": str(msg.author),
        "authorID": msg.author.id,
        "content": msg.content,
        "channel": str(msg.channel),
        "channelID": msg.channel.id,
        "msgID": msg.id,
        # subtracting 25200 because thats the number of seconds in 7 hours (utc to pst)
        "time": float(time.mktime((msg.created_at).timetuple()) - 25200)
    }
    # when the x is x sus bot reaction code
    if((msgStored.get("authorID") == 812172490256285747) and ("when " in msgStored.get("content"))):
        await msg.add_reaction("❌")
        await asyncio.sleep(3)
        if(msg.reactions[0].count > 1):
            with open(DELETED_BOT_MESSAGES_FILE_PATH, 'r+') as f:
                log = json.loads(f.read())
                async for person in msg.reactions[0].users():
                    # check if user is NOT this bot
                    if person.id != 1256666003417469028:
                        if not log.get(person.name):
                            log[person.name] = 1
                        else:
                            log[person.name] += 1
                f.seek(0)
                json.dump(log, f)
                f.truncate()
            await msg.delete()
        else:
            await msg.clear_reactions()
            with open(MESSAGE_FILE_PATH, 'a') as f:
                json.dump(msgStored, f)
                f.write('\n')
    elif(msg.guild == client.get_guild(ACTIVE_SERVER)):
        with open(MESSAGE_FILE_PATH, 'a') as f:
            json.dump(msgStored, f)
            f.write('\n')
    # shut up congor
    if(msgStored.get("authorID") == 247858291760300032):
        if(random.randint(1,1000) == 1):
            await msg.channel.send("shut up congor")
    # keith test command thing
    kstr = "voidwhite"
    count = 0
    for char in msgStored.get("content").casefold():
        if char == kstr[count]:
            count += 1
        if count == len(kstr):
            await msg.channel.send("OMNI HOLY SHIT!!!!!!")
            break

async def clearReaction(msg):
    await msg.clear_reactions()

client.run(BOT_TOKEN)

# -- DISABLED FUNCTIONS --

# -- ON MESSAGE EDIT EVENT --
#     CURRENTLY DISABLED

# @client.event
# async def on_message_edit(msgb, msga):
#     # store the msg to replace with later
#     reverseMsgList = []
#     charCount = 0
#     msgStored = {
#         "author": str(msga.author),
#         "authorID": msga.author.id,
#         "content": msga.content,
#         "channel": str(msga.channel),
#         "channelID": msga.channel.id,
#         "msgID": msga.id,
#         "time": float(time.mktime((msga.created_at).timetuple()) - 25200)
#     }
#     # i have no idea
#     with open(MESSAGE_FILE_PATH, 'r+') as f:
#         for line in reverse(f, batch_size=io.DEFAULT_BUFFER_SIZE):
#             # char count is to change the position of the file cursor eventually
#             charCount += len(line)
#             # store the message we found
#             reverseMsgList.insert(0, json.loads(line))
#             # kill the for loop
#             # death to all for loops
#             if reverseMsgList[0].get("msgID") == msgb.id:
#                 # seek to end of file
#                 f.seek(0, 2)
#                 # the one extra character is the end of file character thingy
#                 # seek to position right at the start of the final message we logged
#                 f.seek(f.tell() - charCount - 1, 0)
#                 reverseMsgList.pop(0)
#                 # store the edited message instead of the unedited one
#                 reverseMsgList.insert(0, msgStored)
#                 # truncate the file at that position
#                 f.truncate()
#                 break
#         # write everything stored to file
#         for line in reverseMsgList:
#             json.dump(line, f)
#             f.write('\n')

# -- ON MESSAGE DELETE EVENT --
#       CURRENTLY DISABLED

# # this function will be have similarly to the one above, getting the message id 
# # and then removing the associated entry in message_history.json
# @client.event
# async def on_message_delete(msg):
#     reverseMsgList = []
#     charCount = 0
#     with open(MESSAGE_FILE_PATH, 'r+') as f:
#         for line in reverse(f, batch_size=io.DEFAULT_BUFFER_SIZE):
#             charCount += len(line)
#             reverseMsgList.insert(0, json.loads(line))
#             if reverseMsgList[0].get("msgID") == msg.id:
#                 f.seek(0, 2)
#                 f.seek(f.tell() - charCount - 1, 0)
#                 reverseMsgList.pop(0)
#                 f.truncate()
#                 break
#         for line in reverseMsgList:
#             json.dump(line, f)
#             f.write('\n')

# -- ON MESSAGE BULK DELETE EVENT --
#        CURRENTLY DISABLED

# # same as function above, except made to handle a list of messages deleted at the same time
# @client.event
# async def on_bulk_message_delete(msgs):
#     reverseMsgList = []
#     reverseMsgList2 = []
#     idList = []
#     charCount = 0
#     for msg in msgs:
#         idList.append(msg.id)
#     with open(MESSAGE_FILE_PATH, 'r+') as f:
#         for line in reverse(f, batch_size=io.DEFAULT_BUFFER_SIZE):
#             charCount += len(line)
#             reverseMsgList.insert(0, json.loads(line))
#             if reverseMsgList[0].get("msgID") == msgs[0].id:
#                 f.seek(0, 2)
#                 f.seek(f.tell() - charCount - 1, 0)
#                 for msg in reverseMsgList:
#                     if msg.get("msgID") not in idList:
#                         reverseMsgList2.insert(0, msg)
#                 f.truncate()
#                 break
#         for line in reverseMsgList2:
#             json.dump(line, f)
#             f.write('\n')
#
# -- OLD SEARCH COMMAND --
# count = 0
#     highestNum = 0
#     highestAuthor = "nobody :("
#     mostMsg = {}
#     correction = 0
#     if '@everyone' in phrase or '@here' in phrase:
#         await interaction.response.send_message(f'bro you really thought? naur...')
#         return
#     await interaction.response.send_message(f'Searching for phrase \'{phrase}\'...')
#     if fullwords:
#         phrase = ' ' + phrase + ' '
#     # to get the person with the most results for a phrase i can make a dictionarie
#     # each key value pair will be author: num of results
#     # at the end i can loop through to find the highest number
#     with open(MESSAGE_FILE_PATH, 'r') as f:
#         for line in f:
#             x = json.loads(line)
#             teststr = (x.get("content").endswith(phrase.casefold()[:-1]))
#             if phrase.casefold() in str(x.get("content")).casefold() or teststr:
#                 count += 1
#                 if not mostMsg.get(x.get("authorID")):
#                     mostMsg[x.get("authorID")] = 1
#                 else:
#                     mostMsg[x.get("authorID")] += 1
#     for key, value in mostMsg.items():
#         if not nobots:
#             if client.get_user(int(key)) != None and value > highestNum and int(key) != 1256666003417469028:
#                 highestNum = value
#                 highestAuthor = client.get_guild(ACTIVE_SERVER).get_member(int(key)).name
#             elif int(key) == 1256666003417469028:
#                 correction = value
#         else:
#             if client.get_user(int(key)) != None and value > highestNum and not client.get_user(int(key)).bot:
#                 highestNum = value
#                 highestAuthor = client.get_guild(ACTIVE_SERVER).get_member(int(key)).name
#             elif client.get_user(int(key)) != None and client.get_user(int(key)).bot:
#                 correction += value
#     if fullwords:
#         phrase = phrase[1:-1]
#     await interaction.edit_original_response(content=f'the phrase \"{phrase}\" came up {count - correction} times. it was sent the most times by {highestAuthor} with {highestNum} results.')
