from __future__ import print_function
from discord.ext import commands
import discord, time, asyncio, pymongo, string, random, csv, smtplib
from generator import KajGenerator
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
if __name__ == '__main__':
    import config


bot = commands.Bot(command_prefix='$', case_insensitive=True)
version = "Alpha 0.1.5"
bot.remove_command('help')
print("Loading....")
owner_ids=[245653078794174465, 282565295351136256]
gen = KajGenerator()

# lol don't touch this
client = pymongo.MongoClient(config.uri)
print("authenticated with mongo database")
hcs_db = client.HCS
user_col = hcs_db.users
print('collected documents (' + str(user_col.count_documents({})) + ")")


def sendemail(studentemail, emailcode):
    body = "Your HCSDiscord Verification Code is \n\n" + str(emailcode)+"\n\nPlease use $verify "+str(emailcode)+ " in your setup channel\n\n" + "If you don't believe this was you please msg Larvey#0001 on Discord."
    emailsubject = "HCSDiscord Authenitcation"

    emailmsg = MIMEMultipart()
    emailmsg['To'] = studentemail
    emailmsg['From'] = config.mailfromAddress
    emailmsg['Subject'] = emailsubject
    emailmsg.attach(MIMEText(body, 'plain'))
    message = emailmsg.as_string()

    emailserver = smtplib.SMTP(config.mailfromserver)
    emailserver.starttls()
    emailserver.login(config.mailfromAddress, config.mailfrompassword)
    print("Sending Email....")
    emailserver.sendmail(config.mailfromAddress, studentemail, message)
    print("Email Sent to " + studentemail)
    emailserver.quit()


def MakeEmbed(author=None, author_url=None, title=None, description=None, url=None, thumbnail=None, doFooter=False):
    if url is not None:
        embed = discord.Embed(title=title, description=description, url=url, color=discord.Color.dark_blue())
    else:
        embed = discord.Embed(title=title, description=description, color=discord.Color.dark_blue())

    if thumbnail is not None:
        embed.set_thumbnail(url=thumbnail)
    if author is not None and author_url is not None:
        embed.set_author(name=author, url=author_url)
    if doFooter is True:
        embed.set_footer(text="HCS discord bot.", icon_url=bot.user.avatar_url)
    return embed


def make_doc(user_name=None, user_id=None, code=None, grade=None, roles=None, student_id=None, verified=False):
    doc_ = {'user_name': user_name, 'user_id': str(user_id), 'code': code, 'grade': str(grade), 'roles': roles, 'student_id': str(student_id), 'verified': verified}  # 'code' == None if verified and verified will be true
    return doc_


def gen_code(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))


def check_for_doc(check_key, check_val, check_key2=None, check_val2=None):
    if not check_key2 or not check_val2:
        the_doc = user_col.find_one({check_key: check_val})
        if the_doc:
            return True
        else:
            return False
    else:
        the_doc = user_col.find_one({check_key: check_val, check_key2: check_val2})
        if the_doc:
            return True
        else:
            return False


@bot.command()
async def purge_all(ctx):
    msg = await ctx.send('checking user...')
    if ctx.author.id in owner_ids:
        print('owner requested purge of database')
        print('purging...')
        await msg.edit(content='purging...')
        user_col.delete_many({})
        await msg.edit(content='database purged!')
        print('database purged')
        return
    else:
        print('user requested purge of database: '+ctx.author.name+'\nbut was denied.')
        await msg.edit(content='you can\'t do that lmao')
        return


@bot.event
async def on_ready():
    guilds = list(bot.guilds)
    print("bot logged in with version: "+version)
    print("Connected to " + str(len(bot.guilds)) + " server(s):")
    print("Bot Connected to Gmail Servers")
    print('Started Status Loop')
    while True:
        a_name = gen.MakeUsername(1)
        a_name[0] = a_name[0].replace('_', ' ')
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=a_name[0]))
        print('changed name to '+ a_name[0])
        await asyncio.sleep(60)


async def make_new_channel(member):
    overwrites = {
        member.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, add_reactions=False),
        bot.user: discord.PermissionOverwrite(read_messages=True)
    }

    category = discord.utils.get(member.guild.categories, name="Setup")
    if not category:
        await member.guild.create_category_channel(name='Setup')
        category = discord.utils.get(member.guild.categories, name="Setup")

    channel = await member.guild.create_text_channel(str(member.id), overwrites=overwrites, category=category)
    print("Creating new setup for " + str(member) + ".")
    return channel


async def select_middle_school(member, channel):
    print(member.name + " choose middleschool, saving to file...")
    await channel.send('-Saving (Middle School)')

    their_code = gen_code()
    if not check_for_doc("user_id", str(member.id)):
        user_col.insert_one(make_doc(member.name, member.id, their_code, 'middle', None, None, False))
        await get_student_id(member, channel)

        # send code to email?


async def get_student_id(member, channel):
    await channel.send("Please tell me your student ID")
    while True:
        idmsg = await bot.wait_for('message')
        if idmsg.author.id is member.id:
            student_id6 = ''.join(filter(lambda x: x.isdigit(), idmsg.content))
            if student_id6 is '':
                await channel.send('Thats not a Valid ID')
                continue
            if await compare_id(idmsg.channel, idmsg.author, student_id6):
                return
            else:
                continue
        else:
            print('not right')
            continue


@bot.command()
async def verify(ctx, code: str=None):
    if code is not None:
        doc = user_col.find_one({'code': code, 'user_id': str(ctx.author.id)})
        if doc is not None:
            updated_tag = {"$set": {'verified': True, 'code': None}}
            user_col.update_one({'code': code, 'user_id': str(ctx.author.id)}, updated_tag)
            await ctx.author.send("Yeah Boi U got **Verified**!")
            roleid = 573953106417680409
            role = discord.utils.get(ctx.guild.roles, id=roleid)
            await ctx.author.remove_roles(role)

            channel = discord.utils.get(ctx.guild.text_channels, name=str(ctx.author.id))
            if channel:
                print(str(ctx.author.id) + " is verified, deleting their setup")
                await channel.delete()


async def compare_id(channel, member, student_id):
    print('started comparing')
    last_message = await channel.send('Searching for your Student ID...')
    with open('eggs.csv', newline='') as csvfile:
        csvReader = csv.reader(csvfile, delimiter=',')
        for row in csvReader:
            student_id9 = ''.join(filter(lambda x: x.isdigit(), row[30]))
            if str(student_id) in row[30] and len(str(student_id)) == 8:
                print(row[30] + ' - ' + student_id9)
                their_doc = user_col.find_one({'user_id': str(member.id)})
                if their_doc is not None:
                    updated_tag = {"$set": {'student_id': str(student_id)}}
                    user_col.update_one({'user_id': str(member.id)}, updated_tag)
                    print('updated user id to be the user id they have so yeah. Now ima send an email. *dabs*')
                    print('verify using this... $verify '+ their_doc['code'])
                    emailcode = their_doc['code']
                    studentemail = str(student_id)+"@hartlandschools.us"
                    await last_message.delete()
                    confirmmsg = await channel.send("We found that Student ID! ("+student_id+") "+"Would you like us to send you an email to confirm it is you?")
                    await confirmmsg.add_reaction("🇾")
                    await confirmmsg.add_reaction("🇳")
                    while True:
                        reaction3, react_member3 = await bot.wait_for('reaction_add')
                        if react_member3.id is member.id:
                            if reaction3.emoji == "🇾":
                                print(member.name + " has confirmed that "+student_id+" is their student ID. Sending Email.")
                                print("Email Address is: "+studentemail)
                                await channel.send("We have sent you an email with a Verifiation Code to "+studentemail)
                                sendemail(studentemail, emailcode)
                                return True
                            if reaction3.emoji == "🇳":
                                await channel.send("Ok Restarting Student ID question.")
                                await get_student_id(member, channel)


        print('No ID Found(Welp.. Thats a Wrap)')
        await channel.send('Sorry, That ID was not Found. Please Try Again')
        return False


async def select_high_school(member, channel):
    print(member.name + " choose highschool, saving to file...")
    await channel.send('-Saving (High School)')

    msg2 = await channel.send("Whats your grade?\n\nA: Freshmen\nB: Sophmore\nC: Junior\nD: Senior")
    await msg2.add_reaction("🇦")
    await msg2.add_reaction("🇧")
    await msg2.add_reaction("🇨")
    await msg2.add_reaction("🇩")
    while True:
        reaction2, react_member2 = await bot.wait_for('reaction_add')
        if react_member2.id is member.id:
            if reaction2.emoji == "🇦":
                print(member.name + " Choose Freshmen... ew")
                await channel.send('-Saving (9th Grade)')
                gradeselect = "9th"
                break
            elif reaction2.emoji == "🇧":
                print(member.name + " Choose Sophmore")
                await channel.send('-Saving (10th Grade)')
                gradeselect = "10th"
                break
            elif reaction2.emoji == "🇨":
                print(member.name + " Choose Junior")
                await channel.send('-Saving (11th Grade)')
                gradeselect = "11th"
                break
            elif reaction2.emoji == "🇩":
                print(member.name + " Choose Senior")
                await channel.send('-Saving (12th Grade)')
                gradeselect = "12th"
                break
            else:
                print("not right emoji")
                continue
        else:
            print("not right user")
            continue

    print("generating code...")
    their_code = gen_code()
    print("generated code: " + str(their_code))
    if not check_for_doc("user_id", str(member.id)):
        print("saving...")
        user_col.insert_one(make_doc(member.name, member.id, their_code, gradeselect, None, None, False))
        print("saved.")
        await get_student_id(member, channel)

        # send code to email?


async def joinmsg(member):
    welcome = discord.utils.get(member.guild.channels, id=int(573171504234233888))
    embed = discord.Embed(title="Member Joined", description=member.name, color=0x1394ff)
    await welcome.send(embed=embed)


async def playerjoin(member):
    if check_for_doc('user_id', str(member.id), 'verified', True):
        print("user is already registered")
        return
    else:
        await giverole(member)

    print('New player joined... Making Setup Room')
    channel = await make_new_channel(member)

    msg = await channel.send("Welcome " + str(member) + " to the HCS Discord Server!\nLets Start the Setup!\nAre you from the Highschool, or the Middleschool? React Acordingly")
    await msg.add_reaction("🇭")
    await msg.add_reaction("🇲")

    while True:
        reaction, react_member = await bot.wait_for('reaction_add')
        if react_member.id is member.id:
            if reaction.emoji == "🇲":
                await select_middle_school(member, channel)
                break

            elif reaction.emoji == "🇭":
                await select_high_school(member, channel)
                break

            else:
                continue


@bot.event
async def on_member_remove(member):
    if check_for_doc("user_id", str(member.id)):
        user_col.delete_many({'user_id': str(member.id), 'verified': False})

    channel = discord.utils.get(member.guild.text_channels, name=str(member.id))
    if channel:

        print(str(member.id) +" left, deleting their setup")
        await channel.delete()


@bot.command()
async def shutdown(ctx):
    if ctx.author.id in owner_ids:
        print(ctx.author.name + ' (' + str(ctx.author.id) + ')' + ' has requested a shutdown.')
        print('Shutting down')
        await ctx.send(":wave::wave:")
        await bot.change_presence(status='offline')
        await bot.logout()
    else:
        print(ctx.author.name + ' (' + str(ctx.author.id) + ')' + ' has requested a shutdown.')
        print('But they do not have enough permissions')


async def giverole(member):
    roleid = 573953106417680409
    role = discord.utils.get(member.guild.roles, id=roleid)
    await member.add_roles(role)
    print(member.name + "(" + str(member.id) + ") " + "has Joined the discord adding them to the role: " + str(role))



@bot.event
async def on_member_join(member):
    if member.id==bot.user.id:
        return
    await playerjoin(member)
    await joinmsg(member)


bot.run(config.TOKEN)
