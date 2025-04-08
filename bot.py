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
from twscrape import API, gather
from twscrape.logger import set_log_level
import re
from collections import defaultdict
from PIL import Image
import csv
import aiohttp
import math
import pandas as pd
from datetime import timezone, timedelta
from asyncio import run_coroutine_threadsafe

dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
# bot token and twitter account info
BOT_TOKEN = os.getenv("BOT_TOKEN")
TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")
TWITTER_EMAIL_PASSWORD = os.getenv("TWITTER_EMAIL_PASSWORD")
# current server: egirls
ACTIVE_SERVER = os.getenv("ACTIVE_SERVER")
# fun little file paths
MESSAGE_FILE_PATH = 'message_history.json'
TWEET_FILE_PATH = 'tweet_storage.json'
TWEET_ID_FILE_PATH = 'tweet_id_storage.json'
DELETED_BOT_MESSAGES_FILE_PATH = 'deleted_bot_history.json'
COMMAND_HISTORY_FILE_PATH = 'command_history.json'
# music file paths
NIGHTCORE = ["nightcore/clarity.mp3", "nightcore/godisagirl.mp3", "nightcore/shatterme.mp3", "nightcore/takeahint.mp3"]
NIGHTCORE_NAMES = ["Nightcore - Clarity", "Nightcore - God is a Girl", "Nightstep - Shatter Me", "Nightcore - Take a Hint"]
# music globals
SELECTED_SONGS = None
SELECTED_SONG_NAMES = None
CURRENT_SONG = None
CURRENT_SONG_NAME = None

# proxy
proxy = os.getenv("PROXY")

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

# -- ACTIVITY HEAT MAP --

@tree.command(
    name="activityheatmap",
    description="generate a heatmap",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.describe(type = "heatmap or line")
async def activityheatmap(interaction, type: str = 'heatmap'):
    await interaction.response.send_message(f'lets do this shit!')
    # want to get the number of messages sent for every month
    # useful numbers: 86400 seconds is one day, 2628000 seconds is one month
    # start time, hardcoded to first message every sent
    startTime = datetime.datetime.fromtimestamp(1535451470)
    messagesInMonth = 0
    monthList = []
    with open(MESSAGE_FILE_PATH, 'r') as f:
        for line in f:
                # the everything variable
                z = json.loads(line)
                timeElapsed = z.get("time") - startTime.timestamp()
                if(timeElapsed >= 2628000):  
                    monthList.append(messagesInMonth)
                    messagesInMonth = 0
                    startTime = datetime.datetime.fromtimestamp(z.get("time"))
                else:
                    messagesInMonth += 1
    if(type == 'heatmap'):
        cols = 12
        rows = math.ceil(len(monthList) / cols)
        for x in range(len(monthList), rows * cols):
            monthList.append(0)
        hmData = np.array(monthList[:rows * cols]).reshape(rows, cols)
        # print(hmData)
        # plt.figure(figsize=(rows, cols))
        plt.title(f'Activity heatmap of messages sent by month')
        plt.imshow(hmData, cmap='cool', interpolation='nearest', aspect='equal')
        plt.colorbar()
        plt.xlabel("Months passed")
        plt.ylabel("Years passed")
        i = 0
        for hmInt in monthList:
            plt.text(i % cols, i // cols, hmInt, ha='center', va='bottom', color='black', fontfamily='monospace', fontweight='bold', fontsize = 7)
            i += 1
    elif(type == 'line'):
        plt.figure(figsize = (12,6))
        plt.plot(range(len(monthList)), monthList, color='r', marker='o', linewidth=2, label='Messages per Month')
        plt.title(f'Line graph of messages sent by month')
        plt.xlabel(f'Months passed')
        plt.ylabel(f'Number of messages sent')
        plt.grid(True)
    filename = "activity.png"
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    graph = discord.File(filename)
    embed = discord.Embed()
    embed.set_image(url="attachment://activity.png")
    await interaction.edit_original_response(embed=embed, attachments=[graph])
    return

# -- TIME AVERAGE --

@tree.command(
    name="timeaverage",
    description="unique words",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def timeaverage(interaction):
    await interaction.response.send_message(f'lets do this shit!')
    messages = []
    with open(MESSAGE_FILE_PATH, 'r') as f:
        for line in f:
            z = json.loads(line)
            messages.append(z)
    messagesDF = pd.DataFrame(messages)
    messagesDF['hour'] = messagesDF['time'].apply(lambda x: datetime.datetime.fromtimestamp(x, tz=timezone(timedelta(hours=-8)))).dt.hour
    # pst = timezone(timedelta(hours=-8))
    # messagesDF['hour'] = messagesDF['hourUTC'].apply(lambda x: pst.fromutc(x))
    messagesByHour = messagesDF['hour'].value_counts().sort_index()
    plt.figure(figsize=(10, 6))
    plt.title(f'Messages sorted by time sent')
    plt.bar(messagesByHour.index, messagesByHour.values)
    formattedHours = []
    for hour in messagesByHour.index:
        formattedHours.append(f'{hour if hour != 0 else 24}:00')
    plt.xticks(messagesByHour.index, formattedHours, fontsize=6)
    plt.xlabel('Hour of the day')
    plt.ylabel('Total messages sent')
    plt.grid(axis='y', alpha=0.7)

    filename = "timeaverage.png"
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    graph = discord.File(filename)
    embed = discord.Embed()
    embed.set_image(url="attachment://timeaverage.png")
    await interaction.edit_original_response(embed=embed, attachments=[graph])
    return

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

# -- SECRET SANTA --

@tree.command(
    name="santa",
    description="its secret snata bro",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(people = "enter a comma separated list of usernames")
async def santa(interaction, people: str):
    names = os.getenv("ALLOWED_PPL_NAMES")
    participants = []
    for mention in people.split(','):
        for member in interaction.guild.members:
            if member.name == mention.strip():
                participants.append(member)
    giftees = await fuckaroundandfindout(participants)
    finalpairs = dict(zip(participants, giftees))
    for gifter, giftee in finalpairs.items():
        giftee_name = names[giftee.name]
        try:
            await gifter.send(f'secret santa motherfuckers. you alraedy know whats up\n\nyour\'e person is: {giftee_name}')
        except discord.Forbidden:
            print(f'{gifter.name} needs to enable DMs')
    await interaction.response.send_message(f'sent out messages')
    return

async def fuckaroundandfindout(gifters):
    while True:
        giftees = gifters.copy()
        random.shuffle(giftees)
        if not any(gifters[i] == giftees[i] for i in range(len(gifters))):
            return giftees

# -- GET ALL MESSAGES --

CONCURRENT_CHANNEL_LIMIT = 10
semaphore = asyncio.Semaphore(CONCURRENT_CHANNEL_LIMIT)

@tree.command(
    name="getallmessages",
    description="gets every message sent and sorts them, and then stores them",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.checks.has_permissions(administrator=True)
async def getallmessages(interaction):
    # send a starter message
    await interaction.response.send_message(content=f'beginning message search', ephemeral=True)
    messageList = []
    server = client.get_guild(ACTIVE_SERVER)
    # create a task for every text channel in ACTIVE_SERVER
    taskList = [channelMessageCollector(chnl) for chnl in server.channels if str(chnl.type) == 'text']
    timeStart = time.time()
    # start running the tasks in taskList
    messageList = await asyncio.gather(*taskList)
    # flatten the list of lists into one single list
    allMessages = [msg for channelMsgs in messageList for msg in channelMsgs]
    timeEnd = time.time()
    print(f'{len(allMessages)} messages found and stored in allMessages, took {(timeEnd - timeStart):.2f} seconds')
    # begin sort
    timeStart = time.time()
    allMessagesSorted = sorted(allMessages, key = lambda msg: msg.created_at)
    timeEnd = time.time()
    print(f'{len(allMessagesSorted)} messages sorted, took {(timeEnd - timeStart):.2f} seconds')
    messageList.clear()
    # get all the essential information
    for msg in allMessagesSorted:
        msgDict = {
                "author": str(msg.author),
                "authorID": msg.author.id,
                "content": msg.content,
                "channel": str(msg.channel),
                "channelID": msg.channel.id,
                "msgID": msg.id,
                # subtracting 25200 because thats the number of seconds in 7 hours (utc to pst)
                "time": float(time.mktime((msg.created_at).timetuple()) - 25200)
        }
        messageList.append(msgDict)
    with open(MESSAGE_FILE_PATH, 'w') as f:
        for msg in messageList:
            json.dump(msg, f)
            f.write('\n')

async def channelMessageCollector(chnl):
    # make sure that no more processes than allowed are running
    async with semaphore:
        messageList = []
        timeList = []
        # only proceed with message gathering if the channel type is text
        timeStart = time.time()
        # run an initial history call to get the oldest 500 messages to establish the currentMessage variable
        async for msg in chnl.history(limit=500, oldest_first=True):
            messageList.append(msg)
        # set currentMessage to the most recently added message
        # could be a rare edge case where there's a channel with no messages
        currentMessage = messageList[-1] if messageList else None
        # once the last messages have been processed, currentMessage should be set to None
        while currentMessage:
            tempMessageList = []
            async for msg in chnl.history(limit=500, after=currentMessage, oldest_first=True):
                tempMessageList.append(msg)
            # exit loop if no messages were found
            if not tempMessageList:
                currentMessage = None
                timeEnd = time.time()
                timeList.append(timeEnd - timeStart)
            else:
                # add values from tempMessageList to messageList
                messageList.extend(tempMessageList)
                currentMessage = messageList[-1]
            # console info to amke sure everything is running
            if(len(messageList) % 3000 == 0):
                timeEnd = time.time()
                timeList.append(timeEnd - timeStart)
                print(f'channel: {chnl.name}, {len(messageList)}, took {timeList[-1]:.2f} seconds')
                timeStart = time.time()
        print(f'channel: {chnl.name} DONE, {len(messageList)} messages took {sum(timeList):.2f} seconds')
        return messageList

@tree.command(
    name="tempcommand",
    description="this is a command where i do things",
    guild=discord.Object(id=ACTIVE_SERVER)
)
@app_commands.checks.has_permissions(administrator=True)
async def tempcommand(interaction):
    # read the last 1000 messages, parse out the content, then create a dictionary with every
    # unique word in the content being a key and the value being that word's frequency
    content = {}
    num = 1
    count = 0
    with open(MESSAGE_FILE_PATH, 'r+') as f:
        for line in reverse(f, batch_size=io.DEFAULT_BUFFER_SIZE):
            if num > 1000:
                break
            num += 1
            words = re.findall(r'\b\w+\b', json.loads(line).get("content"))
            for word in words:
                if not word.isnumeric() and not ishex(word):
                    if word in content:
                        content[word] += 1
                    else:
                        content[word] = 1
                    count += 1
    with open("wordfreq.csv", 'w', newline = '') as f:
        writer = csv.writer(f)
        writer.writerow(['Word', 'Frequency'])
        for key,val in content.items():
            writer.writerow([key, val])
    await interaction.response.send_message(f'wrote last 1000 messages to csv file')

def ishex(nstring):
    try:
        int(nstring, 16)
        return True
    except ValueError:
        return False

# -- MUSIC --

@tree.command(
    name="nightcore",
    description="ifourloveistragedywhyareyoumyremedy",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def nightcore(interaction):
    global SELECTED_SONGS, SELECTED_SONG_NAMES, NIGHTCORE, NIGHTCORE_NAMES
    # make sure author is in vc
    if not interaction.user.voice:
        await interaction.response.send_message(f'join a voice channel first bozo')
        return
    channel = interaction.user.voice.channel
    vc = interaction.guild.voice_client
    # connect to vc, or move vc
    if vc is None:
        vc = await channel.connect()
    elif vc.channel != channel:
        await vc.move_to(channel)
    await interaction.response.send_message(f'going nightcore mode')
    # load the nightcore playlist into the selected songs list
    SELECTED_SONGS = NIGHTCORE
    SELECTED_SONG_NAMES = NIGHTCORE_NAMES
    # begin the audio loop
    if not vc.is_playing():
        await play_next(vc, None)

async def play_next(vc, e):
    global SELECTED_SONGS, SELECTED_SONG_NAMES, CURRENT_SONG_NAME, CURRENT_SONG
    if e:
        print(f'error on that thang: {e}')
    # remove current song from front of queue and move it to the back of the queue
    CURRENT_SONG = SELECTED_SONGS.pop(0)
    CURRENT_SONG_NAME = SELECTED_SONG_NAMES.pop(0)
    SELECTED_SONGS.append(CURRENT_SONG)
    SELECTED_SONG_NAMES.append(CURRENT_SONG_NAME)
    # creating audio source, dirty little async stuff to get it to actually play, and then play command with recursive call
    audio_source = discord.FFmpegPCMAudio(CURRENT_SONG)
    loop = asyncio.get_event_loop()
    vc.play(audio_source, after=lambda e: run_coroutine_threadsafe(play_next(vc, e), loop))

@tree.command(
    name="vcpause",
    description="figure it out",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def vcpause(interaction):
    vc = interaction.guild.voice_client
    # makes sure music is actually playing
    if not vc or not vc.is_playing():
        await interaction.response.send_message(f'no song playing lil bro')
        return
    vc.pause()
    await interaction.response.send_message(f'paused the audio. just for u. i would do anything for you')

@tree.command(
    name="vcresume",
    description="the sequel to pausing",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def vcresume(interaction):
    vc = interaction.guild.voice_client
    # makes sure music is actually paused
    if not vc or not vc.is_paused():
        await interaction.response.send_message(f'what are you doing')
        return
    vc.resume()
    await interaction.response.send_message(f'YEAHHHHHHHHHH LETS GET THIS PARTY FUCKING GOING!!!!!!!!!!!')

@tree.command(
    name="vcstop",
    description="makes bot leave vc and stop audio",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def vcstop(interaction):
    global CURRENT_SONG_NAME, CURRENT_SONG, SELECTED_SONGS, SELECTED_SONG_NAMES
    vc = interaction.guild.voice_client
    if vc:
        # resets four of the globals just to be safe. the selected songs have to be reset, not sure on the current songs but i'd rather not risk it
        vc.stop()
        CURRENT_SONG = None
        CURRENT_SONG_NAME = None
        SELECTED_SONGS = None
        SELECTED_SONG_NAMES = None
        await vc.disconnect()
        await interaction.response.send_message(f'bye bey !')
    else:
        await interaction.response.send_message(f'so hatefu;l??')

@tree.command(
    name="vcskip",
    description="you dont need this",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def vcskip(interaction):
    global CURRENT_SONG_NAME
    vc = interaction.guild.voice_client
    if not vc:
        await interaction.response.send_message(f'fuck u doin bro')
        return
    # calling vc.stop() before the skip message gets sent causes the current song to change since the next play_next() call goes through immediately.
    # so i have this
    song_name_before_stop = CURRENT_SONG_NAME
    vc.stop()
    await interaction.response.send_message(f"skipped {song_name_before_stop}")

@tree.command(
    name="vcqueue",
    description="lists queue",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def vcqueue(interaction):
    global SELECTED_SONG_NAMES
    if not SELECTED_SONG_NAMES:
        await interaction.response.send_message(f'aint nothing here lil bro')
    else:
        # i dont know
        queue_message = "\n".join([f"{index + 1}. {song}" for index, song in enumerate(NIGHTCORE_NAMES)])
        await interaction.response.send_message(f"Song queue:\n{queue_message}")

@client.event
async def on_voice_state_update(member, before, after):
    global CURRENT_SONG, CURRENT_SONG_NAME, SELECTED_SONGS, SELECTED_SONG_NAMES
    vc = discord.utils.get(client.voice_clients, guild=member.guild)
    if vc and vc.channel:
        non_bots = [m for m in vc.channel.members if not m.bot]
        # if on voice state update there are no real people in vc and the bot is in vc, do all the exit stuff and leave
        if not non_bots:
           if vc.is_playing() or vc.is_paused():
               vc.stop()
               CURRENT_SONG = None
               CURRENT_SONG_NAME = None
               SELECTED_SONGS = None
               SELECTED_SONG_NAMES = None
               await vc.disconnect()

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
    goonnum = random.randint(1,50)
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
        # if the file has less than 10 entries left, get 20 new entries (duplicates filtered out)
        if len(tweetlist) < 3:
            testtuple = await refill_tweet_storage(seenIDS)
            tweetlist += testtuple[0]
            seenIDS = seenIDS.union(testtuple[1])
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
            await urllib_download(tweetlist[0].get("imgurl"), filename)
            tweetfile = discord.File(filename)
            embedFile = discord.Embed()
            embedFile.set_image(url="attachment://tweetimage.png")
        else:
            filename = "lips.png"
            tweetfile = discord.File(filename)
            embedFile = discord.Embed()
            embedFile.set_image(url="attachment://lips.png")
        # send both embeds
        if goonnum != 1:
            await interaction.edit_original_response(content=None, embeds=[embedAuthor, embedFile], attachments=[tweetfile])
        else:
            await interaction.edit_original_response(content=f'{interaction.user.name} is a gooner <:meowblush:846965478773882880>', embeds=[embedAuthor, embedFile], attachments=[tweetfile])
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

@tree.command(
    name="twttournament",
    description="tournament between 16 twitter images",
    guild=discord.Object(id=ACTIVE_SERVER)
)
async def twttournament(interaction):
    initialtweets = []
    round1 = [] # 16
    round2 = [] # 8
    round3 = [] # 4
    round4 = [] # 2
    # create set of seen IDS and populate the set
    seenIDS = set()
    await interaction.response.send_message(f'searching for images...')
    with open(TWEET_ID_FILE_PATH, 'r') as f:
        for line in f:
            seenIDS.add(json.loads(line).get("msgID"))
    # populate tweet storage with as many tweets as possible
    # get all the data from file and combine it with the freshly grabbed data
    with open(TWEET_FILE_PATH, 'r+') as f:
        for line in f:
            x = json.loads(line)
            initialtweets.append(x)
    # grab 16 tweets
    if len(initialtweets) < 16:
        testtuple = await refill_tweet_storage(seenIDS)
        initialtweets += testtuple[0]
        seenIDS = seenIDS.union(testtuple[1])
    # length check - abort command if failed
    if len(initialtweets) < 16:
        await interaction.edit_original_response(content=f'not enough stored tweets for a tournament')
        return
    random.shuffle(initialtweets)
    for i in range(16):
        round1.append(initialtweets[0])
        initialtweets.pop(0)
    # store the remaining elements
    with open(TWEET_FILE_PATH, 'r+') as f:
        f.seek(0, 0)
        f.truncate()
        for ndict in initialtweets:
            json.dump(ndict, f)
            f.write('\n')
    with open(TWEET_ID_FILE_PATH, 'w') as f:
        for id in seenIDS:
            idStored = {"msgID": id}
            json.dump(idStored, f)
            f.write('\n')
    # main code
    # need to get the message from the interaction, and then replace all interaction code after this comment with message code instead
    msg = await interaction.original_response()
    await msg.create_thread(name='tournament discussion')
    round2 = await tournament_helper(msg, round1, 5, 1, 1)
    # refresh message
    msg = await msg.fetch()
    if not round2:
        await msg.edit(content=f'well thats no fun.', embed=None, attachments=[])
        return
    # round 1 over, round 2 begins
    await msg.edit(content=f'ROUND ONE OVER !!! BEGINNING ROUND TWO IN THREE SECONDS...', embed=None, attachments=[])
    await asyncio.sleep(3)
    round3 = await tournament_helper(msg, round2, 6, 1, 2)
    msg = await msg.fetch()
    if not round3:
        await msg.edit(content=f'well thats no fun.', embed=None, attachments=[])
        return
    await msg.edit(content=f'ROUND TWO OVER !!! BEGINNING ROUND THREE IN THREE SECONDS...', embed=None, attachments=[])
    await asyncio.sleep(3)
    round4 = await tournament_helper(msg, round3, 7, 1, 3)
    msg = await msg.fetch()
    if not round4:
        await msg.edit(content=f'well thats no fun.', embed=None, attachments=[])
        return
    await msg.edit(content=f'TIME FOR THE FINAL BATTLE!!!', embed=None, attachments=[])
    await asyncio.sleep(3)
    round4 = await tournament_helper(msg, round4, 7, 0, 4)
    msg = await msg.fetch()
    if not round4:
        await msg.edit(content=f'well thats no fun.', embed=None, attachments=[])
        return
    embedAuthor = discord.Embed()
    embedAuthor.set_author(name=f'from {round4[0].get("username")}:', url=round4[0].get("url"))
    await urllib_download(round4[0].get("imgurl"), "tweetimaget1.png")
    tweetfile = discord.File("tweetimaget1.png")
    embedFile = discord.Embed()
    embedFile.set_image(url="attachment://tweetimaget1.png")
    await msg.edit(content=f'THE TOURNAMENT WINNER!', embeds=[embedAuthor, embedFile], attachments=[tweetfile])

async def urllib_download(imgurl, filename):
    for i in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(imgurl) as response:
                    if response.status == 200:
                        with open(filename, 'wb') as f:
                            f.write(await response.read())
                        return
                    else:
                        print(f'failed with status {response.status}')
            # urllib.request.urlretrieve(imgurl, filename)
            # await asyncio.sleep(0.5)
            # return
        except Exception as e:
            # last try
            if i == 2:
                print(f'download of {imgurl} failed 3 times')
                return
            print(f'error downloading {imgurl}, retrying in 3 seconds...')
            await asyncio.sleep(3)

async def tournament_helper(msg, roundlist, peoplerequiredplustwo, enablescaling, roundnum):
    returnlist = []
    timewaited = 0
    votingnum = 1
    weirdflag = 0
    while roundlist:
        # image 1
        if not roundlist[0].get("imgurl") == "noimage":
            filename = "tweetimaget1.png"
            await urllib_download(roundlist[0].get("imgurl"), filename)
            leftImage = Image.open(filename)
        else:
            filename = "lips.png"
            leftImage = Image.open(filename)
        # image 2
        if not roundlist[1].get("imgurl") == "noimage":
            filename = "tweetimaget2.png"
            await urllib_download(roundlist[1].get("imgurl"), filename)
            rightImage = Image.open(filename)
        else:
            filename = "lips.png"
            rightImage = Image.open(filename)
        # resize the second image to be the same size as the first, and add the 1 OR 2 image between them
        authors = f'left image by: {roundlist[0].get("username")} | right image by: {roundlist[1].get("username")}'
        middleImage = Image.open("1or2.png")
        newRightWidth = int(rightImage.size[0] * (leftImage.size[1] / rightImage.size[1]))
        newMiddleWidth = int(middleImage.size[0] * (leftImage.size[1] / middleImage.size[1]))
        newHeight = leftImage.size[1]
        rightImage = rightImage.resize((newRightWidth, newHeight))
        middleImage = middleImage.resize((newMiddleWidth, newHeight))
        combinedImage = Image.new('RGB', (leftImage.size[0] + rightImage.size[0] + middleImage.size[0], leftImage.size[1]))
        combinedImage.paste(leftImage, (0, 0))
        combinedImage.paste(middleImage, (leftImage.size[0], 0))
        combinedImage.paste(rightImage, (leftImage.size[0] + middleImage.size[0], 0))
        combinedImage.save("combinedtweetimage.png")
        tweetfile = discord.File("combinedtweetimage.png")
        embedFile = discord.Embed()
        embedFile.set_image(url="attachment://combinedtweetimage.png")
        # send both embeds
        await msg.edit(content=authors, embeds=[embedFile], attachments=[tweetfile])
        msg = await msg.fetch()
        await msg.clear_reactions()
        await msg.add_reaction("1️⃣")
        await msg.add_reaction("2️⃣")
        # update msg to have both reactions
        msg = await msg.fetch()
        await asyncio.sleep(5)
        if len(msg.reactions) <= 1:
            await msg.clear_reactions()
            return []
        if not (str(msg.reactions[0]) == "1️⃣" and str(msg.reactions[1]) == "2️⃣"):
            await msg.clear_reactions()
            return []
        # another while loop inside the while loop to check for reactions
        # continuously update the msg to make sure the reaction count is accurate
        msg = await msg.fetch()
        if len(msg.reactions) <= 1:
            await msg.clear_reactions()
            return []
        if not (str(msg.reactions[0]) == "1️⃣" and str(msg.reactions[1]) == "2️⃣"):
            await msg.clear_reactions()
            return []
        while (msg.reactions[0].count + msg.reactions[1].count < peoplerequiredplustwo):
            await asyncio.sleep(15)
            if timewaited == 120 and enablescaling == 1:
                peoplerequiredplustwo -= 2
                weirdflag = 1
            if timewaited % 4 == 0:
                await msg.edit(content=f'{authors}\nBRACKET: {roundnum}   ROUND: {votingnum}   {timewaited / 4} MINUTES ELAPSED\nVOTES: {(msg.reactions[0].count + msg.reactions[1].count - 2)}/{peoplerequiredplustwo - 2}')
            timewaited += 1
            msg = await msg.fetch()
            if len(msg.reactions) <= 1:
                await msg.clear_reactions()
                return []
            if not (str(msg.reactions[0]) == "1️⃣" and str(msg.reactions[1]) == "2️⃣"):
                await msg.clear_reactions()
                return []
        if weirdflag == 1:
            peoplerequiredplustwo += 2
            weirdflag = 0
        timewaited = 0
        # left image wins OR tie (shouldnt be a tie but just in case)
        if msg.reactions[0].count > msg.reactions[1].count:
            returnlist.append(roundlist[0])
        elif msg.reactions[0].count < msg.reactions[1].count:
            returnlist.append(roundlist[1])
        else:
            returnlist.append(roundlist[random.randint(0, 1)])
        roundlist.pop(0)
        roundlist.pop(0)
        votingnum += 1
        await msg.channel.send(content='plap plap plap get notified get notified get notified', delete_after=1.0)
    await msg.clear_reactions()
    return returnlist

async def refill_tweet_storage(seenIDS):
    tweetlist = []
    imageurl = "noimage"
    testlist = []
    api = API(proxy=proxy)
    # add twitter accounts and log in
    await api.pool.add_account(TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_EMAIL, TWITTER_EMAIL_PASSWORD)
    await api.pool.login_all()
    testlist = await gather(api.search("filter:follows filter:images include:nativeretweets min_faves:4000", limit=80))
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
    return (tweetlist, seenIDS)

@client.event
async def on_audit_log_entry_create(entry):
    channel = client.get_channel(1261771365539909674)
    ACTION_STRING = format_action(entry)
    if ACTION_STRING == None:
        return
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
        case "thread_create":
            return f'created a thread named {(entry.before).name}'
        case "thread_update":
            return f'updated a thread named {(entry.before).name}'
        case "thread_delete":
            return f'deleted a thread named {(entry.before).name}'
        case _:
            return None

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
        i = 1
        cancel = 0
        async for message in client.get_channel(msgStored.get("channelID")).history(limit=2):
            # me, avery, and the sus bot
            if (i == 2 and (message.author.id == 731200697076547644 or message.author.id == 164560262031081472 or message.author.id == 812172490256285747)):
                await msg.delete()
                cancel = 1
            i += 1
        if cancel == 0:
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
            await msg.channel.send("shut up corgal")
    # keith test command thing
    kstr = "voidwhiteletsfuckinggo"
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
