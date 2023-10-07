import datetime

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
from discord import File
from loguru import logger
from icecream import ic


import json
import io

from db import BotDb, DbStruct

"""------------------------------------------------------------------------------------------Start up - basic functions----------------------------------------------------------------------------------------------------"""

session = BotDb().session  # Bot Ssession

TOKEN = ""  # Bot Token


logger.add("Logs.log")

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

def get_config() -> dict:
    with open("config.json", "r") as f:
            jdata = json.load(f)
    return  jdata

async def delete_channel(channel:discord.TextChannel):
    ticket = session.query(DbStruct.Live_Tickets).filter(DbStruct.Live_Tickets.channel_id == channel.id)
    ticket:DbStruct.Live_Tickets = ticket.first()
    if ticket:
        ic(type(ticket.creation_date))
        ic(ticket.creation_date)
        archived_ticket = DbStruct.Tickets_Archive(ticket_creator=ticket.ticket_creator,creation_date=ticket.creation_date,claimed_by=ticket.claimed_by)
        session.add(archived_ticket)
        session.delete(ticket)
        session.commit()
    else:
        ic("No Ticket")
    try:
        await channel.delete()
    except Exception as e:
        logger.error(e)
        embed = create_embed("Error Occured","",color=discord.Color.red())
        return embed
class PersistentViewBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents().all()
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"), intents=intents
        )

    async def setup_hook(self) -> None:
        self.add_view(TicketControl())
        self.add_view(NewTicket())


bot = PersistentViewBot()


def is_over_ticket_limit(user_id: int, limit: int = 5) -> bool:
    """_summary_

    Args:
        user_id (int): ticket creator Discord.Member.id
        limit (int, optional): maximum number of tickets allowed for a single user Defaults to 5.

    Returns:
        bool: True means he did hit his limit False means he is still capable of doing new tickets
    """

    tickets = session.query(DbStruct.Live_Tickets).filter(DbStruct.Live_Tickets.ticket_creator == user_id).all()
    ic((len(tickets)+1))
    ic(limit)
    if (len(tickets)) >= limit:
        return True
    else:
        return False

@bot.event
@logger.catch
async def on_ready():
    print("Bot is up and ready!")

    try:
        synced = await bot.tree.sync()
        print(f"synced {len(synced)} command[s]")
    except Exception as e:
        logger.error(str(e))


def create_embed(
    title: str, content: str, color: discord.Color
):  # easily create an embed
    embed = discord.Embed(title=title, color=color)
    embed.add_field(name=content, value="")
    return embed


"""------------------------------------------------------------------------------------------Start up - basic functions End----------------------------------------------------------------------------------------------------"""


"""------------------------------------------------------------------------------------------Configuration----------------------------------------------------------------------------------------------------"""


@bot.tree.command(name="configurate")
@app_commands.describe(
    ticket_channel="A channel where the bot sends a message with a button that allows the user to open a new ticket",
    tickets_category="category for tickets",
    welcome_message="welcome message in the ticket itself",
    transcripts_channel="Channel to save transcripts",
    support_role="role of the support",
    ticket_limit= "maximum number of tickets allowed for a single user Defaults to 5"
)
@commands.has_permissions(administrator=True)
async def configurate(
    interaction: discord.Interaction,
    ticket_channel: discord.TextChannel,
    tickets_category: discord.CategoryChannel,
    transcripts_channel: discord.TextChannel,
    support_role: discord.Role,
    message: str = "Open Ticket Here",
    welcome_message: str = f"Thank you for contacting support. Please describe your issue and await a response ",
    ticket_limit:int = 5
):
    welcome_message = welcome_message + support_role.mention
    await interaction.response.defer()
    Config = {
        "ticket_channel": ticket_channel.id,
        "tickets_category": tickets_category.id,
        "transcripts_channel": transcripts_channel.id,
        "support_role":support_role.id,
        "message": message,
        "welcome_message": welcome_message,
        "ticket_limit":ticket_limit
    }
    with open("config.json", "w") as f:
        json.dump(Config, f)

    embed = create_embed("Success", "Configured Succesfully", discord.Color.green())
    await interaction.followup.send(embed=embed)


"""------------------------------------------------------------------------------------------Configuration End----------------------------------------------------------------------------------------------------"""


"""------------------------------------------------------------------------------------------Send Command----------------------------------------------------------------------------------------------------"""




class TicketControl(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @discord.ui.button(
        label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="1"
    )
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        channel = interaction.channel
        await delete_channel(channel)
        # generate transcripts
        messages = []
        channel_history = channel.history(limit=None)
        async for message in channel_history:
            messages.append(f"{message.author.name}: {message.content}\n")

        formatted_messages = "\n".join(messages[::-1])
        in_memory_file = io.BytesIO()
        in_memory_file.write(formatted_messages.encode('utf-8'))
        in_memory_file.name = f"{channel.name}_{str(datetime.datetime.utcnow())}.txt"
        in_memory_file.seek(0)
        transcript_channel = bot.get_channel(get_config()["transcripts_channel"])
        await transcript_channel.send(file=File(in_memory_file))
        await channel.delete()
        in_memory_file.close()



    @discord.ui.button(
        label="Claim Ticket", style=discord.ButtonStyle.green, custom_id="69"
    )
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        if int(get_config()["support_role"]) in [x.id for x in interaction.user.roles]:
            channel = interaction.channel
            ticket = session.query(DbStruct.Live_Tickets).filter(DbStruct.Live_Tickets.channel_id == channel.id)
            ticket: DbStruct.Live_Tickets = ticket.first()
            if ticket:
                ticket.claimed_by = interaction.user.id
                embed=create_embed(f"Success",f"Ticket Claimed by {interaction.user.mention}",color=discord.Color.green())
                await interaction.followup.send(embed=embed,ephemeral=True)
                session.commit()
            else:
                embed = create_embed("Error Occured","",color=discord.Color.red())
                await interaction.followup.send(embed=embed,ephemeral=True)
                return 1


class NewTicket(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    @discord.ui.button(
        label="Open Ticket", style=discord.ButtonStyle.green, custom_id="2"
    )
    async def menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        jdata = get_config()

        try:
            ic(is_over_ticket_limit(interaction.user.id,limit=int(jdata["ticket_limit"])))
            if is_over_ticket_limit(interaction.user.id,limit=int(jdata["ticket_limit"])):
                embed = create_embed("Error",f"you have passed your ticket limit {str(jdata['ticket_limit'])} per user. please delete one of your tickets before creating a new one",color=discord.Color.red())
                await interaction.followup.send(embed=embed,ephemeral=True)
                return 0 
            else:
                pass
        
        except Exception as e:
            logger.error(e)
            embed = create_embed("Error Occured","",color=discord.Color.red())
            await interaction.followup.send(embed=embed,ephemeral=True)
            return 1
        


        embed = create_embed(
            "Close Ticket",
            "By clicking the button, this ticket will be closed",
            color=discord.Color.red(),
        )

        view = TicketControl()

        jdata = get_config()

        tickets_category_id = int(jdata["tickets_category"])

        tickets_category_object: discord.CategoryChannel = discord.utils.get(
            bot.get_all_channels(), id=int(tickets_category_id)
        )
        channel = await tickets_category_object.create_text_channel(
            name=f"{interaction.user.name}_{len(tickets_category_object.channels)+ 1}"
        )

        try:
            # This try block for database managment

            Ticket = DbStruct.Live_Tickets(interaction.user.id,channel_id=channel.id,claimed_by=None)
            session.add(Ticket)
            session.commit()
            await channel.send(embed=embed, view=view)
            await channel.send(str(jdata["welcome_message"]))
            await channel.set_permissions(
                interaction.user, read_messages=True, send_messages=True
            )
            await channel.send(f"{interaction.user.mention}")

            embed = create_embed("Success", "", color=discord.Color.green())
            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(e)
            embed = create_embed("Error Occured","",color=discord.Color.red())
            await interaction.followup.send(embed=embed,ephemeral=True)
            return 1



@bot.tree.command(name="send_embed")
@app_commands.describe(
    message="Message on the embed",
    channel="A channel where the bot sends a message with a button that allows the user to open a new ticket if none it will send it to the channel previously configured",
)
@commands.has_permissions(administrator=True)
async def send_embed(
    interaction: discord.Interaction, message: str, channel: discord.TextChannel = None
):
    await interaction.response.defer()

    jdata = get_config()


    view = NewTicket()

    embed = create_embed(
        message,
        "By clicking the button, a ticket will be opened for you.",
        discord.Color.green(),
    )

    if channel:
        await channel.send(embed=embed, view=view)
    else:
        channel_id = int(jdata["ticket_channel"])
        ic(channel_id)
        channel = discord.utils.get(bot.get_all_channels(), id=channel_id)
        await channel.send(embed=embed, view=view)

    await interaction.followup.send(
        embed=create_embed("Success", "", color=discord.Color.green())
    )


"""------------------------------------------------------------------------------------------Send Command End----------------------------------------------------------------------------------------------------"""

"""------------------------------------------------------------------------------------------miscellaneous functions----------------------------------------------------------------------------------------------------"""

@bot.tree.command(name="clear_all_tickets")
@commands.has_permissions(administrator=True)
async def clear_all_tickets(interaction:discord.Interaction):
    await interaction.response.defer()
    try:
        tickets_category_id = int(get_config()["tickets_category"])

        tickets_category_object: discord.CategoryChannel = discord.utils.get(
            bot.get_all_channels(), id=int(tickets_category_id)
        )
        channels_len_before = len(tickets_category_object.channels)
        for channel in tickets_category_object.channels:
            try:

                resp = await delete_channel(channel)
                if resp:
                    await interaction.followup.send(embed=resp,ephemeral=True)
            except Exception as e:
                logger.error(e)
                embed = create_embed("Failed to delete channel",f"Failed to delete channel\n{channel.name}:{channel.id}",discord.Color.red())
                await interaction.followup.send(embed=embed)
        channels_len_after = len(tickets_category_object.channels)
        if channels_len_after < channels_len_before:
            embed = create_embed(f"Success, deleted {channels_len_before - channels_len_after} channels","",discord.Color.green())
            await interaction.followup.send(embed=embed)
        else:
            embed = create_embed(f"Failed, deleted {channels_len_before - channels_len_after} channels","",discord.Color.red())
            await interaction.followup.send(embed=embed)
    except Exception as e:
        logger.error(e)
        embed = create_embed(f"Failed","",discord.Color.red())
        await interaction.followup.send(embed=embed)



"""------------------------------------------------------------------------------------------miscellaneous functions End----------------------------------------------------------------------------------------------------"""


""" ____RUN BOT____ """

bot.run(token=TOKEN)

""" ____RUN BOT____ """
