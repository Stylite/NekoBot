from discord.ext import commands
import discord
import datetime, random, config, math, aiohttp, aiomysql
from collections import Counter
from .utils.chat_formatting import pagify
from urllib.parse import quote_plus
import string, json
from .utils.paginator import EmbedPages, Pages
from scipy import stats
import numpy
from .utils.paginator import HelpPaginator
from colorthief import ColorThief
from io import BytesIO
from .utils import checks

LOWERCASE, UPPERCASE = 'x', 'X'
def triplet(rgb, lettercase=LOWERCASE):
    return format(rgb[0]<<16 | rgb[1]<<8 | rgb[2], '06'+lettercase)

class Discriminator(commands.Converter):
    async def convert(self, ctx, argument):
        try:
            if not int(argument) in range(1, 10000):
                raise commands.BadArgument('That isn\'t a valid discriminator.')
        except ValueError:
            raise commands.BadArgument('That isn\'t a valid discriminator.')
        else:
            return int(argument)


class Selector(commands.Converter):
    async def convert(self, ctx, argument):
        if argument not in ['>', '>=', '<', '<=', '=']:
            raise commands.BadArgument('Not a valid selector')
        return argument

def millify(n):
    millnames = ['', 'k', 'M', ' Billion', ' Trillion']
    n = float(n)
    millidx = max(0, min(len(millnames) - 1,
                         int(math.floor(0 if n == 0 else math.log10(abs(n)) / 3))))

    return '{:.0f}{}'.format(n / 10 ** (3 * millidx), millnames[millidx])

# Languages
languages = ["english", "weeb", "tsundere"]
english = json.load(open("lang/english.json"))
weeb = json.load(open("lang/weeb.json"))
tsundere = json.load(open("lang/tsundere.json"))

def getlang(lang:str):
    if lang == "english":
        return english
    elif lang == "weeb":
        return weeb
    elif lang == "tsundere":
        return tsundere
    else:
        return None

class General:
    """General Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.counter = Counter()

    async def execute(self, query: str, isSelect: bool = False, fetchAll: bool = False, commit: bool = False):
        connection = await aiomysql.connect(host='localhost', port=3306,
                                              user='root', password=config.dbpass,
                                              db='nekobot')
        async with connection.cursor() as db:
            await db.execute(query)
            if isSelect:
                if fetchAll:
                    values = await db.fetchall()
                else:
                    values = await db.fetchone()
            if commit:
                await connection.commit()
        if isSelect:
            return values

    async def on_socket_response(self, msg):
        self.bot.socket_stats[msg.get('t')] += 1

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def setlang(self, ctx, lang:str=None):
        """Change the bot language for you."""
        if lang is None:
            em = discord.Embed(color=0xDEADBF, title="Change Language.",
                               description="Usage: `n!setlang <language>`\n"
                                           "Example: `n!setlank english`\n"
                                           "\n"
                                           "List of current languages:\n"
                                           "`english`,\n"
                                           "`weeb`,\n"
                                           "`tsundere` - Translated by computerfreaker#4054")
            return await ctx.send(embed=em)
        if lang.lower() in languages:
            await self.bot.redis.set(f"{ctx.message.author.id}-lang", lang.lower())
            await ctx.send(f"Set language to {lang.title()}!")
        else:
            await ctx.send("Invalid language.")

    @commands.command()
    async def lmgtfy(self, ctx, *, search_terms: str):
        """Creates a lmgtfy link"""
        search_terms = search_terms.replace(" ", "+")
        await ctx.send("https://lmgtfy.com/?q={}".format(search_terms))

    @commands.command(pass_context=True)
    async def cookie(self, ctx, user: discord.Member):
        """Give somebody a cookie :3"""
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
            await ctx.send(getlang(lang)["general"]["cookie"].format(ctx.message.author.name, user.mention))
        else:
            await ctx.send(english["general"]["cookie"].format(ctx.message.author.name, user.mention))

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def keygen(self, ctx, length:int=64):
        await ctx.send(''.join(random.choice(string.digits + string.ascii_letters) for _ in range(length)))

    @commands.command()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def flip(self, ctx):
        """Flip a coin"""
        x = random.randint(0, 1)
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
            if x == 1:
                await ctx.send(getlang(lang)["general"]["flip"]["heads"], file=discord.File("data/heads.png"))
            else:
                await ctx.send(getlang(lang)["general"]["flip"]["tails"], file=discord.File("data/tails.png"))
        else:
            if x == 1:
                await ctx.send("**Heads**", file=discord.File("data/heads.png"))
            else:
                await ctx.send("**Tails**", file=discord.File("data/tails.png"))

    def id_generator(self, size=7, chars=string.ascii_letters + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def get_bot_uptime(self, *, brief=False):
        now = datetime.datetime.utcnow()
        delta = now - self.bot.uptime
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        if not brief:
            if days:
                fmt = '{d} days, {h} hours, {m} minutes, and {s} seconds'
            else:
                fmt = '{h} hours, {m} minutes, and {s} seconds'
        else:
            fmt = '{h}h {m}m {s}s'
            if days:
                fmt = '{d}d ' + fmt

        return fmt.format(d=days, h=hours, m=minutes, s=seconds)

    @commands.command(aliases=['version'])
    async def info(self, ctx):
        servers = len(self.bot.guilds)
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"
        info = discord.Embed(color=0xDEADBF,
                             title=getlang(lang)["general"]["info"]["info"],
                             description=getlang(lang)["general"]["info"]["stats"].format(millify(servers),
                                                                                          servers,
                                                                                          millify(len(set(
                                                                                            self.bot.get_all_members()))),
                                                                                          str(len(self.bot.commands)),
                                                                                          millify(len(set(
                                                                                              self.bot.get_all_channels()))),
                                                                                          self.bot.shard_count,
                                                                                          len(
                                                                                              self.bot.voice_clients),
                                                                                          self.get_bot_uptime(),
                                                                                          millify(self.bot.counter[
                                                                                                      'messages_read'])))
        info.add_field(name=getlang(lang)["general"]["info"]["links"]["name"],
                       value=getlang(lang)["general"]["info"]["links"]["links"])
        info.set_thumbnail(url=self.bot.user.avatar_url_as(format='png'))
        info.set_footer(text=getlang(lang)["general"]["info"]["footer"])
        await ctx.send(embed=info)

    @commands.command(hidden=True)
    async def socketstats(self, ctx):
        delta = datetime.datetime.utcnow() - self.bot.uptime
        minutes = delta.total_seconds() / 60
        total = sum(self.bot.socket_stats.values())
        cpm = total / minutes
        em = discord.Embed(color=0xDEADBF, title="Websocket Stats",
                           description=f'{total} socket events observed ({cpm:.2f}/minute):\n{self.bot.socket_stats}')
        await ctx.send(embed=em)

    @commands.command()
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def whois(self, ctx, userid:int):
        """Lookup a user with a userid"""
        user = self.bot.get_user(userid)
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"
        if user is None:
            return await ctx.send(f"```css\n[ {getlang(lang)['general']['whois_notfound'].format(userid)}```")
        text = f"```css\n" \
               f"{getlang(lang)['general']['whois'].format(userid, user.name, user.id, user.discriminator, user.bot, user.created_at)}" \
               f"```"
        embed = discord.Embed(color=0xDEADBF, description=text)
        embed.set_thumbnail(url=user.avatar_url)
        await ctx.send(embed=embed)

    @commands.command(aliases=['user'])
    @commands.guild_only()
    async def userinfo(self, ctx, user: discord.Member = None):
        """Get a users info."""
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        if user == None:
            user = ctx.message.author
        try:
            playinggame = user.activity.title
        except:
            playinggame = None
        server = ctx.message.guild
        embed = discord.Embed(color=0xDEADBF)
        embed.set_author(name=user.name,
                         icon_url=user.avatar_url)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["id"], value=user.id)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["discrim"], value=user.discriminator)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["bot"], value=str(user.bot))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["created"], value=user.created_at.strftime("%d %b %Y %H:%M"))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["joined"], value=user.joined_at.strftime("%d %b %Y %H:%M"))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["animated_avatar"], value=str(user.is_avatar_animated()))
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["playing"], value=playinggame)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["status"], value=user.status)
        embed.add_field(name=getlang(lang)["general"]["userinfo"]["color"], value=user.color)

        try:
            roles = [x.name for x in user.roles if x.name != "@everyone"]

            if roles:
                roles = sorted(roles, key=[x.name for x in server.role_hierarchy
                                           if x.name != "@everyone"].index)
                roles = ", ".join(roles)
            else:
                roles = "None"
            embed.add_field(name="Roles", value=roles)
        except:
            pass

        await ctx.send(embed=embed)

    @commands.command(aliases=['server'])
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Display Server Info"""
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        server = ctx.message.guild

        verif = server.verification_level

        online = len([m.status for m in server.members
                      if m.status == discord.Status.online or
                      m.status == discord.Status.idle])

        embed = discord.Embed(color=0xDEADBF)
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["name"], value=f"**{server.name}**\n({server.id})")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["owner"], value=server.owner)
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["online"], value=f"**{online}/{len(server.members)}**")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["created_at"], value=server.created_at.strftime("%d %b %Y %H:%M"))
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["channels"], value=f"Text Channels: **{len(server.text_channels)}**\n"
                                               f"Voice Channels: **{len(server.voice_channels)}**\n"
                                               f"Categories: **{len(server.categories)}**\n"
                                               f"AFK Channel: **{server.afk_channel}**")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["roles"], value=len(server.roles))
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["emojis"], value=f"{len(server.emojis)}/100")
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["region"], value=str(server.region).title())
        embed.add_field(name=getlang(lang)["general"]["serverinfo"]["security"], value=f"Verification Level: **{verif}**\n"
                                               f"Content Filter: **{server.explicit_content_filter}**")

        try:
            embed.set_thumbnail(url=server.icon_url)
        except:
            pass

        await ctx.send(embed=embed)

    @commands.command(aliases=['channel'])
    @commands.guild_only()
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        """Get Channel Info"""
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        if channel is None:
            channel = ctx.message.channel

        embed = discord.Embed(color=0xDEADBF,
                              description=channel.mention)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["name"], value=channel.name)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["guild"], value=channel.guild)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["id"], value=channel.id)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["category_id"], value=channel.category_id)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["position"], value=channel.position)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["nsfw"], value=str(channel.is_nsfw()))
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["members"], value=len(channel.members))
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["category"], value=channel.category)
        embed.add_field(name=getlang(lang)["general"]["channelinfo"]["created_at"], value=channel.created_at.strftime("%d %b %Y %H:%M"))

        await ctx.send(embed=embed)

    @commands.command()
    async def urban(self, ctx, *, search_terms: str, definition_number: int = 1):
        """Search Urban Dictionary"""

        def encode(s):
            return quote_plus(s, encoding='utf-8', errors='replace')

        search_terms = search_terms.split(" ")
        try:
            if len(search_terms) > 1:
                pos = int(search_terms[-1]) - 1
                search_terms = search_terms[:-1]
            else:
                pos = 0
            if pos not in range(0, 11):  # API only provides the
                pos = 0                  # top 10 definitions
        except ValueError:
            pos = 0

        search_terms = "+".join([encode(s) for s in search_terms])
        url = "http://api.urbandictionary.com/v0/define?term=" + search_terms
        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(url) as r:
                    result = await r.json()
            if result["list"]:
                definition = result['list'][pos]['definition']
                example = result['list'][pos]['example']
                defs = len(result['list'])
                msg = ("**Definition #{} out of {}:\n**{}\n\n"
                       "**Example:\n**{}".format(pos + 1, defs, definition,
                                                 example))
                msg = pagify(msg, ["\n"])
                for page in msg:
                    await ctx.send(page)
            else:
                await ctx.send("Your search terms gave no results.")
        except IndexError:
            await ctx.send("There is no definition #{}".format(pos + 1))
        except Exception as e:
            await ctx.send(f"Error. {e}")

    @commands.command()
    async def avatar(self, ctx, user: discord.Member = None, type:str = None):
        """Get a user's avatar"""
        await ctx.channel.trigger_typing()
        if user is None:
            user = ctx.message.author
        async with aiohttp.ClientSession() as cs:
            async with cs.get(user.avatar_url_as(format='png')) as r:
                res = await r.read()
        color_thief = ColorThief(BytesIO(res))
        hexx = int(triplet(color_thief.get_color()), 16)
        em = discord.Embed(color=hexx, title=f"{user.name}'s Avatar")
        if type is None or type not in ['jpeg', 'jpg', 'png']:
            await ctx.send(embed=em.set_image(url=user.avatar_url))
        else:
            await ctx.send(embed=em.set_image(url=user.avatar_url_as(format=type)))

    @commands.command()
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def coffee(self, ctx):
        """Coffee owo"""
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"

        url = "https://coffee.alexflipnote.xyz/random.json"
        await ctx.channel.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                res = await r.json()
            em = discord.Embed()
            msg = await ctx.send(getlang(lang)["general"]["coffee"], embed=em.set_image(url=res['file']))
            async with cs.get(res['file']) as r:
                data = await r.read()
            color_thief = ColorThief(BytesIO(data))
            hexx = int(triplet(color_thief.get_color()), 16)
            em = discord.Embed(color=hexx)
            await msg.edit(embed=em.set_image(url=res['file']))

    @commands.command()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def animepic(self, ctx):
        url = "https://api.computerfreaker.cf/v1/anime"
        await ctx.channel.trigger_typing()
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                res = await r.json()
            em = discord.Embed()
            msg = await ctx.send(embed=em.set_image(url=res['url']))
            async with cs.get(res['url']) as r:
                data = await r.read()
            color_thief = ColorThief(BytesIO(data))
            hexx = int(triplet(color_thief.get_color()), 16)
            em = discord.Embed(color=hexx)
            await msg.edit(embed=em.set_image(url=res['url']))

    @commands.command()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def qr(self, ctx, *, message: str):
        """Generate a QR Code"""
        new_message = message.replace(" ", "+")
        url = f"http://api.qrserver.com/v1/create-qr-code/?data={new_message}"

        embed = discord.Embed(color=0xDEADBF)
        embed.set_image(url=url)
        await ctx.send(embed=embed)

    @commands.command()
    async def vote(self, ctx):
        lang = await self.bot.redis.get(f"{ctx.message.author.id}-lang")
        if lang:
            lang = lang.decode('utf8')
        else:
            lang = "english"
        embed = discord.Embed(color=0xDEADBF,
                              title=getlang(lang)["general"]["voting_link"],
                              description="https://discordbots.org/bot/310039170792030211/vote")
        await ctx.send(embed=embed)

    @commands.command(aliases=["perms"])
    async def permissions(self, ctx, user: discord.Member = None, channel: str = None):
        """Get Permissions,

        Example Usage:
            .permissions/.perms @ReKT#0001 testing
        or
            .permissions/.perms ReKT#0001 #testing
        anyway doesn't matter ;p"""
        if user == None:
            user = ctx.message.author

        if channel == None:
            channel = ctx.message.channel
        else:
            channel = discord.utils.get(ctx.message.guild.channels, name=channel)
            print(channel)
        amount = await self.execute(isSelect=True, query=f"SELECT 1 FROM dbl WHERE user = {ctx.message.author.id} AND type = \"upvote\"")
        if amount != 0:
            try:
                perms = user.permissions_in(channel)
                if perms.create_instant_invite:
                    create_instant_invite = "✅"
                else:
                    create_instant_invite = "❌"
                if perms.kick_members:
                    kick_members = "✅"
                else:
                    kick_members = "❌"
                if perms.ban_members:
                    ban_members = "✅"
                else:
                    ban_members = "❌"
                if perms.administrator:
                    administrator = "✅"
                else:
                    administrator = "❌"
                if perms.manage_channels:
                    manage_channels = "✅"
                else:
                    manage_channels = "❌"
                if perms.manage_guild:
                    manage_guild = "✅"
                else:
                    manage_guild = "❌"
                if perms.add_reactions:
                    add_reactions = "✅"
                else:
                    add_reactions = "❌"
                if perms.view_audit_log:
                    view_audit_log = "✅"
                else:
                    view_audit_log = "❌"
                if perms.read_messages:
                    read_messages = "✅"
                else:
                    read_messages = "❌"
                if perms.send_messages:
                    send_messages = "✅"
                else:
                    send_messages = "❌"
                if perms.send_tts_messages:
                    send_tts_messages = "✅"
                else:
                    send_tts_messages = "❌"
                if perms.manage_messages:
                    manage_messages = "✅"
                else:
                    manage_messages = "❌"
                if perms.embed_links:
                    embed_links = "✅"
                else:
                    embed_links = "❌"
                if perms.attach_files:
                    attach_files = "✅"
                else:
                    attach_files = "❌"
                if perms.read_message_history:
                    read_message_history = "✅"
                else:
                    read_message_history = "❌"
                if perms.mention_everyone:
                    mention_everyone = "✅"
                else:
                    mention_everyone = "❌"
                if perms.external_emojis:
                    external_emojis = "✅"
                else:
                    external_emojis = "❌"
                if perms.mute_members:
                    mute_members = "✅"
                else:
                    mute_members = "❌"
                if perms.deafen_members:
                    deafen_members = "✅"
                else:
                    deafen_members = "❌"
                if perms.move_members:
                    move_members = "✅"
                else:
                    move_members = "❌"
                if perms.change_nickname:
                    change_nickname = "✅"
                else:
                    change_nickname = "❌"
                if perms.manage_roles:
                    manage_roles = "✅"
                else:
                    manage_roles = "❌"
                if perms.manage_webhooks:
                    manage_webhooks = "✅"
                else:
                    manage_webhooks = "❌"
                if perms.manage_emojis:
                    manage_emojis = "✅"
                else:
                    manage_emojis = "❌"
                if perms.manage_nicknames:
                    manage_nicknames = "✅"
                else:
                    manage_nicknames = "❌"

                embed = discord.Embed(color=0xDEADBF,
                                      title=f"Permissions for {user.name} in {channel.name}",
                                      description=f"```css\n"
                                                  f"Administrator       {administrator}\n"
                                                  f"View Audit Log      {view_audit_log}\n"
                                                  f"Manage Server       {manage_guild}\n"
                                                  f"Manage Channels     {manage_channels}\n"
                                                  f"Kick Members        {kick_members}\n"
                                                  f"Ban Members         {ban_members}\n"
                                                  f"Create Invite       {create_instant_invite}\n"
                                                  f"Change Nickname     {change_nickname}\n"
                                                  f"Manage Nicknames    {manage_nicknames}\n"
                                                  f"Manage Emojis       {manage_emojis}\n"
                                                  f"Read Messages       {read_messages}\n"
                                                  f"Read History        {read_message_history}\n"
                                                  f"Send Messages       {send_messages}\n"
                                                  f"Send TTS Messages   {send_tts_messages}\n"
                                                  f"Manage Messages     {manage_messages}\n"
                                                  f"Embed Links         {embed_links}\n"
                                                  f"Attach Files        {attach_files}\n"
                                                  f"Mention Everyone    {mention_everyone}\n"
                                                  f"Use External Emotes {external_emojis}\n"
                                                  f"Add Reactions       {add_reactions}\n"
                                                  f"Manage Webhooks     {manage_webhooks}\n"
                                                  f"Manage Roles        {manage_roles}\n"
                                                  f"Mute Members        {mute_members}\n"
                                                  f"Deafen Members      {deafen_members}\n"
                                                  f"Move Members        {move_members}"
                                                  f"```")
                if ctx.message.guild.owner_id == user.id:
                    embed.set_footer(text="Is Owner.")
                await ctx.send(embed=embed)
            except:
                await ctx.send("Problem getting that channel...")
        else:
            embed = discord.Embed(color=0xDEADBF,
                                  title="OwO Whats this",
                                  description="To use this command you need to `n!vote` >.<")
            await ctx.send(embed=embed)

    @commands.command(aliases=["8"], name="8ball")
    async def _8ball(self, ctx, *, question: str):
        """Ask 8Ball a question"""
        answers = ["<:online:313956277808005120> It is certain", "<:online:313956277808005120> As I see it, yes",
                   "<:online:313956277808005120> It is decidedly so", "<:online:313956277808005120> Most likely",
                   "<:online:313956277808005120> Without a doubt", "<:online:313956277808005120> Outlook good",
                   "<:online:313956277808005120> Yes definitely", "<:online:313956277808005120> Yes",
                   "<:online:313956277808005120> You may rely on it", "<:online:313956277808005120> Signs point to yes",
                   "<:away:313956277220802560> Reply hazy try again", "<:away:313956277220802560> Ask again later",
                   "<:away:313956277220802560> Better not tell you now",
                   "<:away:313956277220802560> Cannot predict now",
                   "<:away:313956277220802560> Concentrate and ask again",
                   "<:dnd:313956276893646850> Don't count on it",
                   "<:dnd:313956276893646850> My reply is no", "<:dnd:313956276893646850> My sources say no",
                   "<:dnd:313956276893646850> Outlook not so good", "<:dnd:313956276893646850> Very doubtful"]
        await ctx.send(embed=discord.Embed(title=random.choice(answers), color=0xDEADBF))

    @commands.command()
    async def botinfo(self, ctx, bot_user : int = None):
        """Get Bot Info"""
        if bot_user == None:
            bot_user = self.bot.user.id
        url = f"https://discordbots.org/api/bots/{bot_user}"
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                bot = await r.json()

        em = discord.Embed(color=0xDEADBF, title=bot['username'] + "#" + bot['discriminator'], description=bot['shortdesc'])
        try:
            em.add_field(name="Prefix", value=bot['prefix'])
        except:
            pass
        try:
            em.add_field(name="Lib", value=bot['lib'])
        except:
            pass
        try:
            em.add_field(name="Owners", value=f"<@{bot['owners'][0]}>")
        except:
            pass
        try:
            em.add_field(name="Votes", value=bot['points'])
        except:
            pass
        try:
            em.add_field(name="Server Count", value=bot['server_count'])
        except:
            pass
        try:
            em.add_field(name="ID", value=bot['id'])
        except:
            pass
        try:
            em.add_field(name="Certified", value=bot['certifiedBot'])
        except:
            pass
        try:
            em.add_field(name="Links", value=f"[GitHub]({bot['github']}) - [Invite]({bot['invite']})")
        except:
            pass
        try:
            em.set_thumbnail(url=f"https://images.discordapp.net/avatars/{bot['id']}/{bot['avatar']}")
        except:
            pass

        await ctx.send(embed=em)

    @commands.command()
    async def discriminfo(self, ctx):
        """Get some stats about the servers discrims"""
        discrim_list = [int(u.discriminator) for u in ctx.guild.members]

        # The range is so we can get any discrims that no one has.
        # Just subtract one from the number of uses.
        count = Counter(discrim_list + [int(i) for i in range(1, 10000)])
        count = sorted(count.items(), key=lambda c: c[1], reverse=True)

        embeds = {
            'Summary': {
                'Most Common': ', '.join(str(d[0]) for d in count[:3])
                               + ', and ' + str(count[4][0]),
                'Least Common': ', '.join(str(d[0]) for d in count[-4:-1][::-1])
                                + ', and ' + str(count[-1][0]),
                'Three Unused': '\n'.join([str(d[0]) for d in count
                                           if d[1] == 1][:3]),
                'Average': numpy.mean(discrim_list),
            },
            'Statistics': {
                'Average': numpy.mean(discrim_list),
                'Mode': stats.mode(discrim_list)[0][0],
                'Median': numpy.median(discrim_list),
                'Standard Deviation': numpy.std(discrim_list),
            }
        }

        final_embeds = []

        for embed_title in embeds.keys():
            e = discord.Embed(title=embed_title)
            for field_name in embeds[embed_title].keys():
                e.add_field(name=field_name,
                            value=embeds[embed_title][field_name], inline=False)
            final_embeds.append(e)

        p = EmbedPages(ctx, embeds=final_embeds)
        await p.paginate()

    # It's a converter, not a type annotation in this case
    # noinspection PyTypeChecker
    @commands.command()
    async def discrim(self, ctx, discriminator: Discriminator = None,
                      *, selector: Selector = '='):
        """Search for specific discriminators.

        Optional parameter for ranges to be searched.

        It can be >, >=, <=, or <.

        Ranges between two numbers hasn't been implemented yet."""
        if not discriminator:
            discriminator = int(ctx.author.discriminator)
        if selector == '>':
            p = Pages(ctx, entries=[
                f'{u.display_name}#{u.discriminator}'
                for u in ctx.guild.members
                if int(u.discriminator) > discriminator
            ])
        elif selector == '<':
            p = Pages(ctx, entries=[
                f'{u.display_name}#{u.discriminator}'
                for u in ctx.guild.members
                if int(u.discriminator) < discriminator
            ])
        elif selector == '>=':
            p = Pages(ctx, entries=[
                f'{u.display_name}#{u.discriminator}'
                for u in ctx.guild.members
                if int(u.discriminator) >= discriminator
            ])
        elif selector == '<=':
            p = Pages(ctx, entries=[
                f'{u.display_name}#{u.discriminator}'
                for u in ctx.guild.members
                if int(u.discriminator) <= discriminator
            ])
        elif selector == '=':
            p = Pages(ctx, entries=[
                f'{u.display_name}#{u.discriminator}'
                for u in ctx.guild.members
                if int(u.discriminator) == discriminator
            ])
        else:
            raise commands.BadArgument('Could not parse arguments')

        if not p.entries:
            return await ctx.send('No results found.')

        await p.paginate()

    @commands.group()
    @checks.is_admin()
    async def config(self, ctx):
        """Configuration"""
        if ctx.invoked_subcommand is None:
            em = discord.Embed(color=0xDEADBF, title="Config",
                               description=" - avatar, **Owner Only**\n"
                                           "- username, **Owner Only**")
            await ctx.send(embed=em)

    @config.command(name="avatar")
    @commands.is_owner()
    async def conf_avatar(self, ctx, *, avatar_url: str):
        """Change bots avatar"""
        async with aiohttp.ClientSession() as cs:
            async with cs.get(avatar_url) as r:
                res = await r.read()
        await self.bot.user.edit(avatar=res)
        try:
            emoji = self.bot.get_emoji(408672929379909632)
            await ctx.message.add_reaction(emoji)
        except:
            pass

    @config.command(name="username")
    @commands.is_owner()
    async def conf_name(self, ctx, *, name: str):
        """Change bots username"""
        await self.bot.user.edit(username=name)
        try:
            emoji = self.bot.get_emoji(408672929379909632)
            await ctx.message.add_reaction(emoji)
        except:
            pass

    @commands.command()
    @commands.is_owner()
    async def addvote(self, ctx, user_id:int):
        """Add user id to votes"""
        try:
            await self.execute(f"INSERT INTO dbl VALUES (0, {user_id}, 0, 0)", commit=True)
            try:
                emoji = self.bot.get_emoji(408672929379909632)
                await ctx.message.add_reaction(emoji)
            except:
                pass
        except Exception as e:
            await ctx.send(f"`{e}`")

    @commands.command()
    @commands.is_owner()
    async def testlol(self, ctx):
        allcogs = [cogs for cogs in self.bot.cogs]
        for cog in allcogs:
            print([str(i) for i in self.bot.commands if i.cog_name == cog])

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def help(self, ctx, option: str = None):
        """Help Command OwO"""
        color = 0xDEADBF
        if not option is None:
            entity = self.bot.get_cog(option) or self.bot.get_command(option)

            if entity is None:
                clean = option.replace('@', '@\u200b')
                return await ctx.send(f'Command or category "{clean}" not found.')
            elif isinstance(entity, commands.Command):
                p = await HelpPaginator.from_command(ctx, entity)
            else:
                p = await HelpPaginator.from_cog(ctx, entity)
            return await p.paginate()
        try:
            embed = discord.Embed(color=color)
            embed.set_author(name="NekoBot",
                             icon_url=self.bot.user.avatar_url_as(format='png'))

            embed.add_field(name="General",
                            value="`help`, `discrim`, `discriminfo`, `botinfo`, `8ball`, `permissions`, `vote`, "
                                  "`qr`, `animepic`, `coffee`, `avatar`, `urban`, `channelinfo`, `userinfo`, "
                                  "`serverinfo`, `whois`, `info`, `flip`, `keygen`, `cookie`, `lmgtfy`, `setlang`, `crypto`", inline=False)
            embed.add_field(name="Audio", value="`play`, `skip`, `stop`, `now`, `queue`, `pause`, `volume`, `shuffle`, `repeat`, `find`, `disconnect`", inline=True)
            embed.add_field(name="Donator", value="`donate`, `redeem`, `upload`, `trapcard`")
            embed.add_field(name="Moderation",
                            value="`kick`, `ban`, `massban`, `unban`, `rename`, `snipe`, `poll`, `purge`, `mute`, `unmute`, `dehoist`", inline=False)
            embed.add_field(name="Roleplay", value="`card`")
            embed.add_field(name="IMGWelcomer", value="`imgwelcome`", inline=False)
            embed.add_field(name="Levels & Economy", value="`bank`, `register`, `profile`, `daily`, `rep`, `setdesc`, `transfer`, "
                                                           "`coinflip`, `blackjack`, `top`", inline=False)
            embed.add_field(name="Fun",
                            value="`deepfry`, `blurpify`, `blurplate`, `awooify`, `dragonic`, `dedragonic`,`food`, `bodypillow`, `weebify`, `toxicity`, `tweet`, `nichijou`, `ship`, `achievement`, `shitpost`, `meme`, `changemymind`, `penis`, `vagina`, `jpeg`, `isnowillegal`, `gif`, `cat`, `dog`, "
                                  "`bitconnect`, `feed`, `thiccen`, `widen`, `lovecalculator`, `butts`, `boom`, `rude`, `fight`, `clyde`, `monkaS`, `joke`, "
                                  "`b64`, `md5`, `kannagen`, `iphonex`, `baguette`, `owoify`, `lizard`, `duck`, `captcha`, `whowouldwin`, `threats`", inline=False)

            embed.add_field(name="NSFW",
                            value="`pgif`, `4k`, `phsearch`, `yandere`, `boobs`, `bigboobs`, `ass`, `cumsluts`, `thighs`,"
                                  " `gonewild`, `nsfw`, `doujin`, `girl`, `hentai`, `rule34`, `lewdkitsune`, `anal`", inline=False)

            embed.add_field(name="Reactions",
                            value="`awoo`, `blush`, `confused`, `cry`, `dance`, `insult`, `cry`, `hug`, `kiss`, `pat`, `cuddle`, `tickle`, `bite`, `slap`, `punch`,"
                                  "`poke`, `nom`, `lick`, `lewd`, `trap`, `owo`, `wasted`, `banghead`,"
                                  "`discordmeme`, `stare`, `thinking`, `dab`, `kemonomimi`, `why`, `rem`, `poi`, `greet`, "
                                  "`insultwaifu`, `foxgirl`, `jojo`, `megumin`, `pout`, `shrug`, `sleepy`, `sumfuk`, `initiald`, `deredere`, `triggered`", inline=False)
            embed.add_field(name="Game Stats",
                            value="`osu`, `overwatch`, `fortnite`, `minecraft`", inline=False)
            embed.add_field(name="Marriage", value="`marry`, `divorce`", inline=False)

            await ctx.send(embed=embed)
        except:
            await ctx.send("I can't send embeds.")
        try:
            emoji = self.bot.get_emoji(408672929379909632)
            await ctx.message.add_reaction(emoji)
        except:
            pass

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def crypto(self, ctx, crypto: str):
        """Get cryptocurrency info"""
        coin = "USD,EUR,GBP,JPY,CHF,AUD,CAD,INR,IDR,NZD,ZAR,SEK,SGD,KRW,NOK,MXN,BRL,HKD,RUB,MYR,THB,"
        tsyms = coin + "BTC,BCH,ETH,ETC,LTC,XMR,DASH,ZEC,DOGE,DCR"
        url = f"https://min-api.cryptocompare.com/data/price?fsym={crypto.upper()}&tsyms={tsyms}"
        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                res = await r.json()
        try:
            USD  = res['USD']
            EUR  = res['EUR']
            GBP  = res['GBP']
            JPY  = res['JPY']
            CHF  = res['CHF']
            AUD  = res['AUD']
            CAD  = res['CAD']
            INR  = res['INR']
            IDR  = res['IDR']
            NZD  = res['NZD']
            ZAR  = res['ZAR']
            SEK  = res['SEK']
            SGD  = res['SGD']
            KRW  = res['KRW']
            NOK  = res['NOK']
            MXN  = res['MXN']
            BRL  = res['BRL']
            HKD  = res['HKD']
            RUB  = res['RUB']
            MYR  = res['MYR']
            THB  = res['THB']

            BTC  = res['BTC']
            BCH  = res['BCH']
            ETH  = res['ETH']
            LTC  = res['LTC']
            XMR  = res['XMR']
            DASH = res['DASH']
            ZEC  = res['ZEC']
            DOGE = res['DOGE']
            DCR  = res['DCR']

            e = discord.Embed(color=0xDEADBF, title=f"{crypto.upper()} Conversion",
                              description=f"🇺🇸 US Dollar: **${USD}**\n"
                                          f"🇪🇺 Euro: **€{EUR}**\n"
                                          f"🇬🇧 British Pound: **£{GBP}**\n"
                                          f"🇯🇵 Japanese Yen: **¥{JPY}**\n"
                                          f"🇨🇭 Swiss Franc: **Fr.{CHF}**\n"
                                          f"🇦🇺 Australian Dollar: **${AUD}**\n"
                                          f"🇨🇦 Canadian Dollar: **${CAD}**\n"
                                          f"🇮🇳 Indian Rupee: **₹{INR}**\n"
                                          f"🇮🇩 Indonesian Rupiah: **IDR {IDR}**\n"
                                          f"🇳🇿 New Zealand Dollar: **${NZD}**\n"
                                          f"🇿🇦 South African Rand: **R{ZAR}**\n"
                                          f"🇸🇪 Swedish Krona: **kr {SEK}**\n"
                                          f"🇸🇬 Singapore Dollar: **${SGD}**\n"
                                          f"🇰🇷 South Korean Won: **₩{KRW}**\n"
                                          f"🇳🇴 Norwegian Krone: **kr {NOK}**\n"
                                          f"🇲🇽 Mexican Peso: **Mex${MXN}**\n"
                                          f"🇧🇷 Brazilian Real: **R${BRL}**\n"
                                          f"🇭🇰 Hong Kong Dollar: **HK${HKD}**\n"
                                          f"🇷🇺 Russian Ruble: **₽{RUB}**\n"
                                          f"🇲🇾 Malaysian Ringgit: **RM {MYR}**\n"
                                          f"🇹🇭 Thai Baht: **฿ {THB}**")
            e.add_field(name="Cryptocurrency",
                        value=f"<:bitcoin:423859742281302036> Bitcoin: **₿{BTC}**\n"
                              f"<:bitcoincash:423863215840034817> Bitcoin Cash: {BCH}**\n"
                              f"<:eth:423859767211982858> Ethereum: ♦{ETH}**\n"
                              f"<:ltc:423859753698197507> Litecoin: Ł{LTC}**\n"
                              f"<:monero:423859744936034314> Monero: ɱ{XMR}**\n"
                              f"<:dash:423859742520377346> Dash: {DASH}**\n"
                              f"<:yellowzcashlogo:423859752045379594> Zcash: ⓩ{ZEC}**\n"
                              f"<:dogecoin:423859755384045569> Dogecoin: Đ{DOGE}**\n"
                              f"<:decred:423859744361676801> Decred: {DCR}**", inline=True)
        except:
            e = discord.Embed(color=0xDEADBF, title="⚠ Error", description="Not a valid currency format.")
        await ctx.send(embed=e)



def setup(bot):
    if not hasattr(bot, 'socket_stats'):
        bot.socket_stats = Counter()
    bot.remove_command('help')
    bot.add_cog(General(bot))
