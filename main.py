import logging
import os
import random
import sys

import time
import json
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

# Enabling logging
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger()

# Getting mode, so we could define run function for local and Heroku setup
mode = "dev"#os.getenv("MODE")
TOKEN = '836835953:AAHLVOiFuu32V5tbuBbcuk2JfpOlyNEaF6c'
FACILITATORS = ['@Fellasfaw']

CHALLENGES = [
    ['Minefield', 'Careful where you step. Lead your blind partner through a maze of booby traps.', 'The Room Next To 7D'],
    ['Charades','You\'ll get a word and have to act it out to pass.', 'The Ping Pong Tables'],
    ['Balloon Toss', 'Hydrogen is the lightest gas, so it\'s gonna be okay.','The Basement Across The Basketball Court'],
    ['Password', 'Find the letters, find the prize.', 'Everywhere'],
    ['Tangled', 'You want to do some stretching before this one, Rapunzel.', 'The Social Science Lab'],
    ['Shape Formation','Teamwork and geometry, simple enough.','The Social Science Lab']
]
ROUND2_CHALLENGES = [
    ['Lip Sync Battle', 'Pick a song and make it yours. Fake it \'til you make it.'],
    ['Dodgeball', 'Dodging balls. Something you\'re probably good at.'],
    ['Dance Battle', 'You will have to bust some moves to pass this challenge. Only the best can win!',]
]
DESCRIPTION = [
    "black",
    "white",
    "grey",
    "red",
    "yellow",
    "blue",
    "green",
    "purple",
    "orange",
    "brown",
    "tall",
    "short",
    "hat",
    "shirt",
    "pants",
    "shoes",
    "jacket",
    "dress",
    "skirt"
]

PASSWORD = [
    ['m','green'],
    ['e','black'],
    ['r','red'],
    ['o','orange'],
    ['e','purple'],
    ['a','blue']
]

CHARADES = {
    '🎬 Movie 🎬':list(set(open('movies.txt').readlines())),
    '🐶 Animal 🐶':list(set(open('animals.txt').readlines())),
    '🏛 Place 🏛':list(set(open('places.txt').readlines())),
    '🤷‍♀️ Person 🤷‍♀️':list(set(open('people.txt').readlines()))
}


if mode == "dev":
    def run(updater):
        updater.start_polling()
elif mode == "prod":
    def run(updater):
        PORT = int(os.environ.get("PORT", "8443"))
        HEROKU_APP_NAME = os.environ.get("HEROKU_APP_NAME")
        # Code from https://github.com/python-telegram-bot/python-telegram-bot/wiki/Webhooks#heroku
        updater.start_webhook(listen="0.0.0.0",
                              port=PORT,
                              url_path=TOKEN)
        updater.bot.set_webhook("https://{}.herokuapp.com/{}".format(HEROKU_APP_NAME, TOKEN))
else:
    logger.error("No MODE specified!")
    sys.exit(1)




try:
    game_data = json.loads(open('game_data.txt').read())
except:
    game_data = {
        'players': [],
        'state':'registration',
        'paired_up':False,
        'game_over':False,
        'finalists':[]
    }
players = game_data['players']



def getPlayer(username):
    for p in players:
        if p['username']==username: return p 
    return None
def appearanceMenu():
    reply_markup = []
    for i in range(0,len(DESCRIPTION),3):
        reply_markup.append([InlineKeyboardButton(j.title(), callback_data="appearance_callback_"+j) for j in DESCRIPTION[i:i+3]])

    return InlineKeyboardMarkup(reply_markup, one_time_keyboard=False)

def challengesMenu(p, admin=False):

    reply_markup = []
    for i in CHALLENGES:
        reply_markup.append([
            InlineKeyboardButton({-1:"❌",0:"⭕️", 1:"✅"}[p['challenges'][CHALLENGES.index(i)]]+i[0]+"\n@ '"+ i[2]+"'",callback_data="challenge_"+i[0]),
            #InlineKeyboardButton(, callback_data='none')
        ])
        if admin:
            index = CHALLENGES.index(i)
            if p['challenges'][index] == 0:
                reply_markup[-1].append(
                    InlineKeyboardButton("Pass",callback_data="pass_"+p['username']+str(index))
                )
                reply_markup[-1].append(
                    InlineKeyboardButton("Fail",callback_data="fail_"+p['username']+str(index))
                )
            elif p['challenges'][CHALLENGES.index(i)] == -1:
                reply_markup[-1].append(
                    InlineKeyboardButton("Revive",callback_data="revive_"+p['username']+str(index))
                )

    return InlineKeyboardMarkup(reply_markup)


def player_pass(bot,p,c):

    p['challenges'][c]=1
    bot.sendMessage(p['chat_id'], "You have completed the challenge '{}'. Congratulations!!!".format(CHALLENGES[c][0]))
    
    print(p,c)

    if list(set(p['challenges'])) == [1]:
        if p['lm'] == 'second_round':
            return
        p['lm'] = 'second_round'
        getPlayer(p['partner'])['lm'] = 'second_round'
        bot.sendMessage(p['chat_id'],"Congratulations on being a finalist for the second round.\nNow go back with your partner to the Aemero Club ticket booth.")
        bot.sendMessage(getPlayer(p['partner'])['chat_id'],"Congratulations on being a finalist for the second round.\nNow go back with your partner to the Aemero Club ticket booth.")

        game_data['finalists'].append([p['username'],p['partner']])

        for i in players:
            bot.sendMessage(i['chat_id'],"Attention!!! {} and {} have completed all the challenges of the first round.".format(p['username'],p['partner']))
            if len(game_data['finalists']) != 8:
                bot.sendMessage(i['chat_id'],"They are pair No. {}\nOnly {} to go.".format(len(game_data['finalists']),8-len(game_data['finalists'])))
            else:
                bot.sendMessage(i['chat_id'],"They are the final pair!!! The first round is over!!!")

                p['lm']='second_round'

        if len(game_data['finalists']) == 8:
            game_data['state']='second_round'

    else:
        p['lm']='first_round'

def player_fail(bot,p,c):
    p['challenges'][c] = -1
    p['lm']='first_round'
    bot.sendMessage(p['chat_id'], "You have failed the challenge '{}'.  If you want to try again, you need to pay 5 Birr and revive.".format(CHALLENGES[c][0]))

def start_handler(bot, update):
    if not update.message.chat.type == "private": return

    global game_data

    p = {
        "username":"@"+update.message.chat['username'],
        "chat_id":update.message.chat_id,
        "misc":{}
    }

    if p['username'] in FACILITATORS: 
        return

    if game_data['paired_up']:
        update.message.reply_text("The game has already started.")

    if (getPlayer(p['username'])):
        update.message.reply_text('You have already started this bot.')
        return

    players.append(p)
    
   
    update.message.reply_text("Hello. Welcome to Aemro Club's Treasure Hunt!\n"+
        "I'm here to help you navigate all the challenges and riddles we have for you.\n"+
        "But first you need to answer some questions to make my job easier.")

    p['lm'] = "gender"
    update.message.reply_text("1) Are you male or female?")


def challenges_handler(bot, update):
    if not update.message.chat.type == "private": return

    global game_data

    p = getPlayer("@"+update.message.chat['username'])

    if p['username'] in FACILITATORS: 
        return

    if not game_data['paired_up']:
        update.message.reply_text("The game has not started yet.")
        return
    if game_data['game_over']:
        update.message.reply_text("The game is over.")
        return

    if p.get('challenges',False):
        update.message.reply_text("Your Challenges",reply_markup=challengesMenu(p))




def message_handler(bot, update):
    if not update.message.chat.type == "private": return

    txt = update.message.text

    # Facilitator messages
    if "@"+update.message.chat['username'] in FACILITATORS+['@the_animaniac']:

        if game_data.get('state','') == 'first_round':
            p = getPlayer(txt)
            if p:
                if p.get('challenges',False):
                    update.message.reply_text("{}'s challenges.".format(txt),reply_markup=challengesMenu(p,True))
                    return
                else:
                    update.message.reply_text("{} has no partner yet.".format(txt))


    p = getPlayer("@"+update.message.chat['username'])
    if not p and not "@"+update.message.chat['username'] in FACILITATORS+['@the_animaniac']:
        update.message.reply_text("/start the bot first.")
        return
    
    if p['lm'] == 'gender':
        if txt.lower() in ['male','female']: 
            p['gender'] = txt.lower()

            update.message.reply_text('2) Use the buttons below to tell us your age.', reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("14-15",callback_data="age_14"),
                    InlineKeyboardButton("16-17",callback_data="age_16"),
                    InlineKeyboardButton("18-19",callback_data="age_18"),
                    InlineKeyboardButton("+20",callback_data="age_20"),
                ]]))
            p['lm'] = 'age'
        else: 
            update.message.reply_text("This is Ethiopia. We don't do that LGBTQB+ stuff. Male or Female.")
    elif p['lm'] == 'age':
        update.message.reply_text("Use the menu.")
    elif p['lm'] == 'appearance':
        #update.message.reply_text("Use the menu.")
        if len(txt) < 10:
            update.message.reply_text('Too short.')
        elif len(txt) > 40:
            update.message.reply_text('Too long.')
        else:
            p['lm'] = 'nickname'
            p['appearance'] = txt
            update.message.reply_text("4) Choose a nickname for yourself so your partner can find you.")
    elif p['lm'] == 'nickname':
        if len(txt) < 5:
            update.message.reply_text('Too short.')
        elif len(txt) > 30:
            update.message.reply_text('Too long.')
        else:
            p['nickname'] = txt
            p['lm'] = 'personality'
            update.message.reply_text('5) Are you an introvert or extrovert?')

    elif p['lm'] == 'personality':
        if not txt.lower() in ['introvert','extrovert']:
            update.message.reply_text('I don\'t know what that is. Choose introvert or extrovert.')
        else:
            p['personality'] = txt.lower()

            p['lm'] = 'approve'
            update.message.reply_text('Great. Now go to the ticket booth so that we can approve your account.')
    elif p['lm'] == 'approve':
        update.message.reply_text('You can\'t do anything until your account gets approved.')
    elif p['lm'] == 'wait':
        update.message.reply_text('You have to wait until everyone else is approved. Then we can go on to the fun part.')
    elif p['lm'] == "find_partner":
        if txt == p['partner'] or txt == p['partner'][1:]:
            partner = getPlayer(p['partner'])
            msg = 'Woohoo! You found your partners, {} and {}.\n Now you two will have to complete the /challenges below to win the prize.'.format(p['username'], p['partner'])
            
            update.message.reply_text(msg)
            bot.sendMessage(partner['chat_id'], msg)

            p['lm'] = partner['lm'] = "first_round"
            p['challenges'] = partner['challenges'] = [0]*len(CHALLENGES)
        else:
            update.message.reply_text("That is not your partner's telegram username.")
    elif p['lm'] == "first_round":
        update.message.reply_text("Use the /challenges command to see which ones are left. You can only pass to the next round if you complete them all.")
    elif p['lm'] in ['minefield','charades','balloon_toss','tangled','shape_formation']:
        c = [c for c in CHALLENGES if c[0] == p['lm'].replace('_',' ').title()][0]
        update.message.reply_text("You don\'t need me for this challenge. Talk to the facilitator at '{}'".format(c[2]))
    elif p['lm'].startswith('password'):
        if p['lm']=='password':
            index = 0
        else:
            index = int(p['lm'][-1])

        if txt.lower() != PASSWORD[index][0]:
            for i in [p, getPlayer(p['partner'])]:
                i['misc']['pass_fails'] = i['misc'].get('pass_fails',0)+1
                bot.sendMessage(i['chat_id'], "Incorrect letter. You have failed {}/5 times.".format(i['misc']['pass_fails']))
                if i['misc']['pass_fails'] == 5:
                    i['misc']['pass_fails'] = 0
                    player_fail(bot,i,3)

        else:
            index = index + 1
            if index == len(PASSWORD):
                for i in [p, getPlayer(p['partner'])]:
                    player_pass(bot,i,3)
                    bot.sendMessage(i['chat_id'],"By the way, the word you spelled is an anagram of 'Aemero'.")
            else:
                for i in [p, getPlayer(p['partner'])]:
                    i['lm']='password'+str(index)
                    bot.sendMessage(i['chat_id'], "Correct.")
                    bot.sendMessage(i['chat_id'], "What is the {} letter?".format(PASSWORD[index][1]))

    elif p['lm']=='second_round':

        if len([1 for x in game_data['finalists'] if p['username'] in x]):
            pass


def callback_handler(bot, update):
    query = update.callback_query
    txt = query.message.text

    global players
    global game_data
    
    p = getPlayer("@"+query.message.chat['username'])
    
    if not p and not "@"+query.message.chat['username'] in FACILITATORS+['@the_animaniac']:
        query.message.reply_text("/start the bot first.")
        return


    #query.edit_message_text(text="Selected option: {}".format(query.data))

    if query.data.startswith("appearance_callback_"):
        if p['lm'] == 'appearance':
            p['appearance'] = p.get('appearance',[]) + [query.data.split("_")[-1].title()]
            if len(p['appearance']) <= 7:
                query.edit_message_text(text=txt.split("=")[0]+"=> "+ " ".join(p['appearance']), reply_markup=appearanceMenu())
                if len(p['appearance']) != 7:
                    query.answer(str(7-len(p['appearance'])) +" to go!")
                else:
                    query.answer('Finished!')

                    p['lm'] = 'nickname'
                    query.message.reply_text("4) Choose a nickname for yourself so your partner can find you.")
        else: 
            query.answer('You\'ve already filled this out!')
    elif query.data.startswith('age'):
        if p['lm']=='age':
            p['age'] = int(query.data.split("_")[1])

            p['lm'] = 'appearance'
            #query.message.reply_text('3) Use the buttons below to write a 7 word description of your appearance.\n    =>',reply_markup=appearanceMenu())
            query.message.reply_text('3) Describe what you are wearing right now in 40 letters or less.')
        else:
            query.answer('You have already filled it in.')

    elif query.data.startswith("approve_"):
        p = getPlayer(query.data.split('_',1)[1])

        query.answer("Approved!")
        query.edit_message_text(text=p['username']+"'s account has been approved.")

        p['lm'] = 'wait'
        bot.sendMessage(p['chat_id'], 'Your account has been approved. I will contact you again when the game is about to start.')

    elif query.data.startswith('deny_'):
        p = getPlayer(query.data.split('_',1)[1])

        query.answer("Denied!")
        query.edit_message_text(text=p['username']+"'s account has been denied.")

        players.remove(p)
        bot.sendMessage(p['chat_id'], 'Your account has been denied. I\'m afraid you\'ll have to register again using /start.')
    elif query.data.startswith('pass_'):

        p=getPlayer(query.data[5:-1])
        c=int(query.data[-1])
        if p['challenges'][c] == 0:
            for x in [p,getPlayer(p['partner'])]:
                player_pass(bot,x,c)
            query.answer("Challenge Passed.")      
        else:
            query.answer("Invalid.")

        query.edit_message_text(text="Done.")

    elif query.data.startswith('fail_'):

        p=getPlayer(query.data[5:-1])
        c=int(query.data[-1])
        if p['challenges'][c] == 0:
            for x in [p,getPlayer(p['partner'])]:
                x['challenges'][c] = -1
                x['lm']='first_round'
                bot.sendMessage(x['chat_id'], "You have failed the challenge '{}'.  If you want to try again, you need to pay 5 Birr and revive.".format(CHALLENGES[c][0]))
            query.answer("Challenge Failed.")      
        else:
            query.answer("Invalid.")

        query.edit_message_text(text="Done.")

    elif query.data.startswith('revive_'):
        
        p=getPlayer(query.data[7:-1])
        c=int(query.data[-1])
        if p['challenges'][c] == -1:
            for x in [p,getPlayer(p['partner'])]:
                x['challenges'][c] = 0
                bot.sendMessage(x['chat_id'], "You have been revived for the challenge '{}'.  Now you can try again.".format(CHALLENGES[c][0]))
            query.answer("Challenge Revived.")      
        else:
            query.answer("Invalid.")

        query.edit_message_text(text="Done.")

    elif query.data == 'startgame':

        if not game_data['paired_up']:

            clone = [[[],[]],[[],[]],[[],[]],[[],[]]]
            for i in players:
                if not i['lm']=='wait':
                    continue
                a = clone[
                    {14:0,16:1,18:2,20:3}[i['age']]
                ]
                a[{'male':0,'female':1}[i['gender']]].append(i)

            print(clone)

            for age in clone:
                males = age[0]
                females = age[1]

                random.shuffle(males)
                random.shuffle(females)

                while len(females) and len(males):
                    f = females.pop(0)
                    m = males.pop(0)

                    m['partner'] = f['username']
                    f['partner'] = m['username']

                remainder = ((len(males) and males) or []) + ((len(females) and females) or [])
                while len(remainder) > 1:
                    f = remainder.pop(0)
                    m = remainder.pop(0)

                    m['partner'] = f['username']
                    f['partner'] = m['username']

                if len(remainder):
                    if clone.index(age)+1 != len(clone):
                        clone[clone.index(age)+1][{'male':0,'female':1}[remainder[0]['gender']]].append(remainder[0])

            for i in players:
                if not i.get('partner',None): 
                    bot.sendMessage(i['chat_id'], "Sadly, we couldn't find a partner for you. It seems you are out of the game.")

            game_data['players'] = players = [i for i in players if i.get('partner',False)]


            for i in players:
                i['lm'] = "find_partner"

            for i in players:
                bot.sendMessage(i['chat_id'], "The game has started! First challenge, find your partner!")
                bot.sendMessage(i['chat_id'], "Your partner's nickname is '{}'.".format(getPlayer(i['partner'])['nickname']))
                bot.sendMessage(i['chat_id'], "And their description is '{}'.".format(" ".join(getPlayer(i['partner'])['appearance'])))
                bot.sendMessage(i['chat_id'], "If you enter your telegram username into their phone or if they put theirs into yours, you will pass. Happy hunting!")

            game_data['state'] = 'first_round'
            game_data['paired_up'] = True
            query.edit_message_text(text='Game started!')
        else:
            query.answer("The game has already started.")
    elif query.data == 'nogame':
        query.edit_message_text(text='Game aborted.')
    elif query.data.startswith("challenge_"):

        if p['lm'] != 'first_round':
            query.answer('You can\'t do that now.')
            return

        c = [c for c in CHALLENGES if c[0] == query.data.split("_",1)[1]][0]

        if p['challenges'][CHALLENGES.index(c)] == 1:
            query.message.reply_text("You've already completed this challenge.")
            query.answer()
        elif p['challenges'][CHALLENGES.index(c)] == -1:
            query.message.reply_text("You've lost this challenge. You can't play again without revival.")
            query.answer()
        else:
            messages = ["Your team has chosen the challenge '{}'. You can't choose another until you win or lose this one.".format(c[0]),
                        "=> {}".format(c[1]),
                        "The place this challenge takes place is '{}'. Good luck!!".format(c[2])]

            for i in [p,getPlayer(p['partner'])]:
                if c[0]=='Password':
                    messages.append("What is the 'green' letter?")

                [bot.sendMessage(i['chat_id'],m) for m in messages] 
                i['lm'] = c[0].lower().replace(" ", "_")

    else:
        query.answer()


def approve_handler(bot, update):    
    p = "@"+update.message.chat['username']
    if not p in FACILITATORS+['@the_animaniac']:
        return

    for i in [update.message.text[i.offset:i.offset+i.length] for i in update.message.entities if i.type == "mention"]:
        if getPlayer(i):
            x = getPlayer(i)
            update.message.reply_text("Are you sure about approving {}?\n\nSex: {}\nAge: {}\nAppearance: {}".format(i,x['gender'],x['age'],x['appearance']), 
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Yes",callback_data="approve_"+i),
                     InlineKeyboardButton("No",callback_data="deny_"+i)]
                    ]
                )
            )
        else:
            update.message.reply_text("{} isn't registered!".format(i))

def charades_handler(bot, update):    
    p = "@"+update.message.chat['username']
    if not p in FACILITATORS+['@the_animaniac']:
        return

    try :
        p = getPlayer([update.message.text[i.offset:i.offset+i.length] for i in update.message.entities if i.type == "mention"][0])
    except:
        update.message.reply_text("Either you have not told me a player or that player is not registered.")
        return

    if p['lm'] == 'charades':
        category = random.choice(list(CHARADES.keys()))
        phrase = random.choice(CHARADES[category])

        update.message.reply_text('The category is "{}".\nThe phrase is "{}".'.format(category, phrase))
        bot.sendMessage(p['chat_id'], 'The category is "{}".\nThe phrase is "{}".'.format(category, phrase))
        bot.sendMessage(getPlayer(p['partner'])['chat_id'], 'The category is "{}".\nGuess the phrase.'.format(category))
    else:
        update.message.reply_text("That player is not playing charades.")






def stats_handler(bot, update):    
    p = "@"+update.message.chat['username']
    if not p in FACILITATORS+['@the_animaniac']:
        return
    update.message.reply_text("Total: {}\nApproved: {}\nMales: {}\nFemales: {}\nIntroverts: {}\nExtroverts: {}".format(
        len(players), 
        len([i for i in players if i['lm']=='wait']),
        len([i for i in players if i.get('gender',None)=='male']),
        len([i for i in players if i.get('gender',None)=='female']),
        len([i for i in players if i.get('personality',None)=='introvert']),
        len([i for i in players if i.get('personality',None)=='extrovert'])
    ))
    

def game_begin_handler(bot, update):    
    p = "@"+update.message.chat['username']
    if not p in FACILITATORS+['@the_animaniac']:
        return

    update.message.reply_text("Are you sure about starting the game?", 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes",callback_data="startgame"),
             InlineKeyboardButton("No",callback_data="nogame")]
            ]
        )
    )


if __name__ == '__main__':
    logger.info("Starting bot")
    updater = Updater(TOKEN)

    updater.dispatcher.add_handler(CommandHandler("start", start_handler))
    updater.dispatcher.add_handler(CommandHandler("challenges", challenges_handler))
    updater.dispatcher.add_handler(CommandHandler("charades", charades_handler))


    updater.dispatcher.add_handler(CommandHandler("stats", stats_handler))
    updater.dispatcher.add_handler(CommandHandler("approve", approve_handler))
    updater.dispatcher.add_handler(CommandHandler("let_the_games_begin", game_begin_handler))


    updater.dispatcher.add_handler(CallbackQueryHandler(callback_handler))

    updater.dispatcher.add_handler(MessageHandler(Filters.text, message_handler))

    run(updater)


    while True:
        time.sleep(6)
        f=open('game_data.txt','w')
        f.write(json.dumps(game_data, indent=4))
        f.close()
