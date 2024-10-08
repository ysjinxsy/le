import nextcord
from nextcord.ext import commands 
from nextcord import Interaction, SelectOption, ui, SlashOption, TextInputStyle, ChannelType, File
from nextcord.ui import Button, View, Modal, TextInput, RoleSelect, ChannelSelect, Select
import aiosqlite 
import re
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import io
from nextcord.utils import utcnow 
from db import get_config, get_teams
import logging
import aiohttp
import datetime
from shared import guild_id
from datetime import datetime
import requests
import functools
import random
import time
import asyncio
logging.basicConfig(
    level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    handlers=[
        logging.StreamHandler()          # Log to console
    ]
)
ADMIN_USER_IDS = [1211365819054030960]  
intents = nextcord.Intents.all()
guild_id = 1266153230300090450
client = commands.Bot(command_prefix="?", intents=intents, help_command=None)
DATABASE_PATH = "soccer_cards.db"

def format_number(number):
    return f"{number:,}"


@client.slash_command(name="addcard", description="Add a new card to the database.", guild_ids=[guild_id])
async def addcard(
    interaction: Interaction,
    name: str = SlashOption(description="Card name"),
    ovrate: int = SlashOption(description="Overall rating of the player"),
    position: str = SlashOption(description="Position of the player"),
    price: int = SlashOption(description="Price of the card"),
    country: str = SlashOption(description="Country of the player"),
    club: str = SlashOption(description="Club of the player"),
    image_attachment: nextcord.Attachment = SlashOption(description="Image attachment of the player's image")
):
    
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    

    await interaction.response.defer()  # Defer the interaction to avoid timeout

    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            image_data = await image_attachment.read()
            image_buffer = io.BytesIO(image_data)

            # Convert the image data to a BLOB for storage in the database
            await db.execute('''
                INSERT INTO cards (name, ovrate, position, price, country, club, image_blob)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, ovrate, position, price, country, club, image_buffer.getvalue()))
            
            await db.commit()
            await interaction.followup.send(f"{name} with overall rating {ovrate} and position {position} has been added to the database!")
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")



CHEMISTRY_IMAGES_URLS = {
    'green': "https://cdn.discordapp.com/attachments/1275351829659516938/1275768324869066752/green.png?ex=66c71757&is=66c5c5d7&hm=725588e1d8423ee61faa0b44954b78591b0e072042f7f80ed6c0640f3aabd384&",
    'orange': "https://cdn.discordapp.com/attachments/1275351829659516938/1275768324625793069/yellow.png?ex=66c71757&is=66c5c5d7&hm=38b64c7e2ac201c62bb1d3e1b013d701aed5be408525617c0d692cbf3cf2a9bf&",
    'red': "https://cdn.discordapp.com/attachments/1275351829659516938/1275768325162536972/red.png?ex=66c71757&is=66c5c5d7&hm=c67707eb98254438b1ab9e38f2e2510832f3c0ea5f0586c0b1984e3716a57496&"
}

@client.slash_command(name="lineup", description="View your card collection in a lineup image.", guild_ids=[guild_id])
async def lineup(interaction: nextcord.Interaction):
    await interaction.response.defer()

    user_id = str(interaction.user.id)
    username = interaction.user.name

    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            # Fetch cards from the user's lineup
            async with db.execute('''
                SELECT cards.name, cards.position, cards.ovrate, cards.price, cards.club, cards.country, cards.image_blob
                FROM cards
                INNER JOIN user_lineups ON cards.id = user_lineups.card_id
                WHERE user_lineups.user_id = ?
            ''', (user_id,)) as cursor:
                cards = await cursor.fetchall()

            if not cards:
                await interaction.followup.send("You don't have any cards in your lineup yet.")
                return

            chemistry, level = calculate_chemistry(cards)

            # Calculate OVR RATING and OVR VALUE
            total_ovr = sum(card[2] for card in cards)
            total_value = sum(card[3] for card in cards)

            background_url = "https://cdn.discordapp.com/attachments/1274834660504899624/1275010384956358687/lineupahh.png?ex=66c45574&is=66c303f4&hm=069c8c165aa50355ca2cf2b3d894367f714b5e951ab98c6ab395739fad2c5c35&"

            try:
                background_image_data = await download_image(background_url)
                background_image = Image.open(io.BytesIO(background_image_data))
            except Exception as e:
                await interaction.followup.send("Failed to load background image.")
                return

            # Download chemistry level images
            try:
                chemistry_images = {}
                for level_name, url in CHEMISTRY_IMAGES_URLS.items():
                    try:
                        image_data = await download_image(url)
                        chemistry_images[level_name] = Image.open(io.BytesIO(image_data)).resize((25, 25))
                    except Exception as e:
                        print(f"Failed to process image for {level_name}: {e}")
                        await interaction.followup.send(f"Failed to process {level_name} image.")
            except Exception as e:
                print(f"Failed to load chemistry images: {e}")
                await interaction.followup.send("Failed to load chemistry images.")
                return

            lineup_width, lineup_height = 892, 725
            card_width, card_height = 123, 174

            lineup_image = background_image.resize((lineup_width, lineup_height))
            draw = ImageDraw.Draw(lineup_image)

            # Load custom font
            font_path = "FFGoodProCond-Black.ttf"  # Update with your font file path
            font = ImageFont.truetype(font_path, 24)

            # Add OVR RATING, OVR VALUE, and Chemistry text
            draw.text((120, 8), f"OVR RATING:", font=font, fill="black")
            draw.text((125, 27), f"{total_ovr}", font=font, fill="black")
            draw.text((264, 8), f"OVR VALUE:", font=font, fill="black")
            draw.text((270, 27), f"{format_number(total_value)}", font=font, fill="black")
            draw.text((656, 13), f"Chemistry:", font=font, fill="black")
            draw.text((459, 13), f"{username}", font=font, fill="black")

            # Overlay the chemistry level image
            chemistry_image = chemistry_images.get(level, chemistry_images['red'])
            lineup_image.paste(chemistry_image, (746, 12), chemistry_image.convert("RGBA"))

            position_coords = {
                'ST': (395, 72),
                'CAM': (395, 220),
                'GK': (395, 516),
                'LW': (170, 111),
                'RW': (620, 111),
                'CB': (395, 368),
                'RB': (569, 368),
                'LB': (221, 368)
            }

            for card in cards:
                try:
                    name, position, ovr, price, club, country, image_blob = card
                    coords = position_coords.get(position, (0, 0))

                    card_image = Image.open(io.BytesIO(image_blob)).resize((card_width, card_height))
                    lineup_image.paste(card_image, coords, card_image.convert("RGBA"))

                except Exception as e:
                    print(f"Error processing card {card}: {e}")
                    continue

            try:
                with io.BytesIO() as buffer:
                    lineup_image.save(buffer, format="PNG")
                    buffer.seek(0)
                    await interaction.followup.send("Here is your lineup image:", file=nextcord.File(fp=buffer, filename="lineup.png"))
            except Exception as e:
                await interaction.followup.send(f"Failed to generate lineup image: {e}")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")


def calculate_chemistry(cards):
    clubs = {}
    countries = {}

    for card in cards:
        _, _, _, _, club, country, _ = card  # Unpack the correct number of values
        clubs[club] = clubs.get(club, 0) + 1
        countries[country] = countries.get(country, 0) + 1

    max_club_chemistry = max(clubs.values(), default=0)
    max_country_chemistry = max(countries.values(), default=0)

    # Calculate overall chemistry level
    chemistry = max_club_chemistry + max_country_chemistry

    # Determine the chemistry performance level
    if max_club_chemistry >= 5 or max_country_chemistry >= 5:
        level = 'green'
    elif max_club_chemistry >= 3 or max_country_chemistry >= 3:
        level = 'orange'
    else:
        level = 'red'

    return chemistry, level



async def download_image(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()



@client.slash_command(name="balance", description="Check your current balance.", guild_ids=[guild_id])
async def balance(interaction: Interaction):
    await interaction.response.defer()

    user_id = str(interaction.user.id)
    user_name = interaction.user.display_name  # Get the user's display name

    async with aiosqlite.connect('soccer_cards.db') as db:
        try:
            # Fetch the user's balance
            async with db.execute('''
                SELECT balance
                FROM user_balances
                WHERE user_id = ?
            ''', (user_id,)) as cursor:
                result = await cursor.fetchone()

            if result:
                balance = result[0]

                # Fetch the card IDs from user_collections
                async with db.execute('''
                    SELECT card_id
                    FROM user_collections
                    WHERE user_id = ?
                ''', (user_id,)) as cursor:
                    card_ids = await cursor.fetchall()

                if not card_ids:
                    player_value = 0
                else:
                    # Extract card IDs
                    card_ids = [card_id[0] for card_id in card_ids]

                    # Fetch the values of the cards from the cards table
                    async with db.execute('''
                        SELECT SUM(price)
                        FROM cards
                        WHERE id IN ({seq})
                    '''.format(seq=','.join(['?'] * len(card_ids))), tuple(card_ids)) as cursor:
                        player_value_result = await cursor.fetchone()

                    player_value = player_value_result[0] if player_value_result[0] else 0
                
                sell_value = int(0.8 * player_value)
                embed = nextcord.Embed(description=f"{user_name} has a budget of  ``{format_number(balance)}``<:aifa:1275168935737557012> .")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("You don't have a balance record. Please check with the administrator.")

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")



@client.slash_command(name="view_cards", description="View all available cards for purchase and their prices.", guild_ids=[guild_id])
async def view_cards(interaction: Interaction):
    await interaction.response.defer()

    async with aiosqlite.connect('soccer_cards.db') as db:
        try:
            async with db.execute('''
                SELECT name, price
                FROM cards
            ''') as cursor:
                cards = await cursor.fetchall()

            if not cards:
                await interaction.followup.send("No cards are available for purchase at the moment.")
                return

            # Format the card list
            card_list = "\n".join([f"**{name}**: {format_number(price)} coins" for name, price in cards])
            
            # Send the response
            embed = nextcord.Embed(
                title='Available Cards',
                description=card_list  # You can choose any color you'd like
            )
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")



@client.slash_command(name="club", description="Shows all players you have in your collection.", guild_ids=[guild_id])
async def club(interaction: Interaction):
    user_id = str(interaction.user.id)

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Fetch the cards in the user's collection along with their details
            async with db.execute('''
                SELECT cards.name, cards.position
                FROM cards 
                INNER JOIN user_collections ON cards.id = user_collections.card_id 
                WHERE user_collections.user_id = ?
            ''', (user_id,)) as cursor:
                cards = await cursor.fetchall()

            if not cards:
                await interaction.response.send_message("You don't have any cards yet.")
                return

            # Format the list of cards
            card_list = "\n".join([f"{name} - Position: {position}" for name, position in cards])
            await interaction.response.send_message(f"Your club:\n{card_list}")
            
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")




@client.slash_command(name="switch", description="Change the position of a player in your collection.", guild_ids=[guild_id])
async def switch(interaction: Interaction, card_name: str, new_position: str):
    user_id = str(interaction.user.id)

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Check if the card is in the user's collection
            async with db.execute('''
                SELECT card_id
                FROM user_collections
                INNER JOIN cards ON user_collections.card_id = cards.id
                WHERE cards.name = ? AND user_collections.user_id = ?
            ''', (card_name, user_id)) as cursor:
                result = await cursor.fetchone()

            if not result:
                await interaction.response.send_message("Card not found in your collection.")
                return

            card_id = result[0]

            # Check if the new position is available
            async with db.execute('''
                SELECT card_id
                FROM user_collections
                INNER JOIN cards ON user_collections.card_id = cards.id
                WHERE cards.position = ? AND user_collections.user_id = ?
            ''', (new_position, user_id)) as cursor:
                conflict_card = await cursor.fetchone()

            if conflict_card:
                await interaction.response.send_message(f"Position '{new_position}' is already occupied by another card.")
                return

            # Update the position of the card
            async with db.execute('''
                UPDATE cards
                SET position = ?
                WHERE id = ?
            ''', (new_position, card_id)):
                await db.commit()

            await interaction.response.send_message(f"Position of card '{card_name}' has been updated to '{new_position}'.")

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")




cooldown_end_times = {}
COOLDOWN_DURATION = 86400  # 24 hours in seconds

@client.slash_command(name="claim", description="Claim a random card and add it to your collection.", guild_ids=[guild_id])
async def claim(interaction: Interaction):
    user_id = str(interaction.user.id)
    current_time = time.time()  # Get current time in seconds

    # Check if the user is on cooldown
    if user_id in cooldown_end_times:
        end_time = cooldown_end_times[user_id]
        if current_time < end_time:
            await interaction.response.send_message(
                f"You need to wait {end_time - current_time:.2f} seconds before using this command again.",
                ephemeral=True
            )
            return

    try:
        # Acknowledge the interaction
        await interaction.response.defer()

        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Get available cards
            async with db.execute('''
                SELECT cards.id AS card_id, cards.name, cards.ovrate, cards.position, cards.price, cards.country, cards.club, cards.image_blob
                FROM cards
                WHERE cards.id NOT IN (SELECT card_id FROM user_collections WHERE user_id = ?)
            ''', (user_id,)) as cursor:
                available_cards = await cursor.fetchall()

        if not available_cards:
            await interaction.followup.send("There are no available cards left to claim!")
            return

        # Create a list of cards with weights based on their OVR
        cards_with_weights = [(card, card[2]) for card in available_cards]  # (card, ovrate)
        total_weight = sum(weight for _, weight in cards_with_weights)

        # Choose a card based on weighted probability
        pick = random.uniform(0, total_weight)
        current = 0
        for card, weight in cards_with_weights:
            current += weight
            if current > pick:
                selected_card = card
                break

        card_id, card_name, ovrate, position, card_price, country, club, image_blob = selected_card

        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Check if user already owns this card
            async with db.execute('''
                SELECT COUNT(*)
                FROM user_collections
                WHERE user_id = ? AND card_id = ?
            ''', (user_id, card_id)) as cursor:
                already_owned = (await cursor.fetchone())[0] > 0

        view = nextcord.ui.View()

        if already_owned:
            # Provide only the sell button
            async def sell_card(interaction: Interaction):
                # Ensure only the original user can interact
                if interaction.user.id != int(user_id):
                    await interaction.response.send_message("This button is not for you!", ephemeral=True)
                    return

                try:
                    async with aiosqlite.connect(DATABASE_PATH) as db:
                        await db.execute('''
                            INSERT INTO user_balances (user_id, balance)
                            VALUES (?, ?)
                            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
                        ''', (user_id, int(card_price * 0.8), int(card_price * 0.8)))
                        await db.commit()
                    await interaction.response.edit_message(content=f"You've sold the card '{card_name}' for :coin: {card_price} coins!", view=None)
                except Exception as e:
                    await interaction.response.edit_message(content=f"An error occurred: {e}", view=None)

            sell_button = nextcord.ui.Button(label="Sell", style=nextcord.ButtonStyle.gray, emoji="<:aifa:1275168935737557012>")
            sell_button.callback = sell_card
            view.add_item(sell_button)

            embed = nextcord.Embed(
                title=f"You already own {card_name}",
                description=f":coin: **Value:** ``{format_number(card_price)}`` coins **Sells for:** ``{format_number(int(card_price * 0.8))}`` coins"
            )
            embed.set_image(url=f"attachment://card_image.png")

        else:
            # Provide both claim and sell buttons
            async def claim_card(interaction: Interaction):
                # Ensure only the original user can interact
                if interaction.user.id != int(user_id):
                    await interaction.response.send_message("This button is not for you!", ephemeral=True)
                    return

                try:
                    async with aiosqlite.connect(DATABASE_PATH) as db:
                        await db.execute('INSERT INTO user_collections (user_id, card_id, position) VALUES (?, ?, ?)', (user_id, card_id, position))
                        await db.commit()
                    await interaction.response.edit_message(content=f"You've claimed the card '{card_name}'!", view=None)
                except Exception as e:
                    await interaction.response.edit_message(content=f"An error occurred: {e}", view=None)

            async def sell_card(interaction: Interaction):
                # Ensure only the original user can interact
                if interaction.user.id != int(user_id):
                    await interaction.response.send_message("This button is not for you!", ephemeral=True)
                    return

                try:
                    async with aiosqlite.connect(DATABASE_PATH) as db:
                        await db.execute('''
                            INSERT INTO user_balances (user_id, balance)
                            VALUES (?, ?)
                            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
                        ''', (user_id, int(card_price * 0.8), int(card_price * 0.8)))
                        await db.commit()
                    await interaction.response.edit_message(content=f"You've sold the card '{card_name}' for :coin: {card_price} coins!", view=None)
                except Exception as e:
                    await interaction.response.edit_message(content=f"An error occurred: {e}", view=None)

            claim_button = nextcord.ui.Button(label="Add to Club", style=nextcord.ButtonStyle.gray, emoji="<:arrow:1275032436958433312>")
            claim_button.callback = claim_card

            sell_button = nextcord.ui.Button(label="Sell", style=nextcord.ButtonStyle.gray, emoji="<:aifa:1275168935737557012>")
            sell_button.callback = sell_card

            view.add_item(claim_button)
            view.add_item(sell_button)

            embed = nextcord.Embed(
                title=f"{card_name} joins your club",
                description=f':coin: **Value:** ``{format_number(card_price)}`` coins **Sells for:** ``{format_number(int(card_price * 0.8))}`` coins \n\n :coin: ``Quick Sell`` \n <:arrow:1275032436958433312> ``Add To Club``'
            )
            embed.set_image(url=f"attachment://card_image.png")

        await interaction.followup.send(embed=embed, view=view, files=[nextcord.File(fp=io.BytesIO(image_blob), filename="card_image.png")])

        # Set cooldown end time for the user
        cooldown_end_times[user_id] = current_time + COOLDOWN_DURATION

        # Optionally, remove expired cooldowns periodically
        async def cleanup_expired_cooldowns():
            while True:
                await asyncio.sleep(COOLDOWN_DURATION)  # Sleep for the duration of the cooldown
                current_time = time.time()
                expired_users = [uid for uid, end_time in cooldown_end_times.items() if current_time >= end_time]
                for uid in expired_users:
                    cooldown_end_times.pop(uid, None)

        # Run the cleanup task in the background
        asyncio.create_task(cleanup_expired_cooldowns())

    except Exception as e:
        if interaction.response.is_done():
            await interaction.followup.send(f"An error occurred: {e}")
        else:
            await interaction.response.send_message(f"An error occurred: {e}")





@client.slash_command(name="delete_user_collection", description="Remove all cards from a user's collection (admin only).",guild_ids=[guild_id])
async def delete_user_collection(interaction: Interaction, user_id: str):
    if interaction.user.id not in ADMIN_USER_IDS:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Check if the user has any cards in their collection
            async with db.execute('''
                SELECT COUNT(*)
                FROM user_collections
                WHERE user_id = ?
            ''', (user_id,)) as cursor:
                count = await cursor.fetchone()

            if count[0] == 0:
                await interaction.response.send_message("The user does not have any cards in their collection.")
                return

            # Delete all cards from the user's collection
            async with db.execute('''
                DELETE FROM user_collections
                WHERE user_id = ?
            ''', (user_id,)):
                await db.commit()

            await interaction.response.send_message(f"All cards from user {user_id}'s collection have been removed.")

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}")





@client.slash_command(name="7remove", description="Remove a card from your club by name, making it unavailable for your lineup.", guild_ids=[guild_id])
async def remove_from_club(interaction: Interaction, card_name: str):
    user_id = str(interaction.user.id)

    try:
        # Acknowledge the interaction
        await interaction.response.defer()

        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Check if the card exists by name
            async with db.execute('SELECT id FROM cards WHERE name = ?', (card_name,)) as cursor:
                card = await cursor.fetchone()

            if not card:
                await interaction.followup.send(f"Card with the name '{card_name}' does not exist.")
                return

            card_id = card[0]

            # Check if the user owns the card
            async with db.execute('SELECT * FROM user_clubs WHERE user_id = ? AND card_id = ?', (user_id, card_id)) as cursor:
                existing_card = await cursor.fetchone()

            if not existing_card:
                await interaction.followup.send(f"You do not have the card '{card_name}' in your club.")
                return

            # Remove the card from the user's club
            await db.execute('DELETE FROM user_clubs WHERE user_id = ? AND card_id = ?', (user_id, card_id))
            await db.commit()

        await interaction.followup.send(f"The card '{card_name}' has been successfully removed from your club and is no longer available for your lineup.")

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")


@client.slash_command(name="7add", description="Add a card from your club to your lineup by name.", guild_ids=[guild_id])
async def add_to_lineup(interaction: Interaction, card_name: str):
    user_id = str(interaction.user.id)

    try:
        # Acknowledge the interaction
        await interaction.response.defer()

        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Check if the card exists by name
            async with db.execute('SELECT id, position FROM cards WHERE name = ?', (card_name,)) as cursor:
                card = await cursor.fetchone()

            if not card:
                await interaction.followup.send(f"Card with the name '{card_name}' does not exist.")
                return

            card_id, card_position = card[0], card[1]

            # Check if the user owns the card in their collection
            async with db.execute('SELECT * FROM user_collections WHERE user_id = ? AND card_id = ?', (user_id, card_id)) as cursor:
                owned_card = await cursor.fetchone()

            if not owned_card:
                await interaction.followup.send(f"You do not own the card '{card_name}' in your club.")
                return

            # Check if the card is already in the user's lineup
            async with db.execute('SELECT * FROM user_lineups WHERE user_id = ? AND card_id = ?', (user_id, card_id)) as cursor:
                existing_lineup_card = await cursor.fetchone()

            if existing_lineup_card:
                await interaction.followup.send(f"The card '{card_name}' is already in your lineup.")
                return

            # Add the card to the user's lineup
            await db.execute('INSERT INTO user_lineups (user_id, card_id, position) VALUES (?, ?, ?)', (user_id, card_id, card_position))
            await db.commit()

        await interaction.followup.send(f"The card '{card_name}' has been successfully added to your lineup!")

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")


import random

@client.slash_command(name="friendly", description="Challenge another user to a friendly match.", guild_ids=[guild_id])
async def friendly(interaction: Interaction, opponent: nextcord.Member):
    await interaction.response.defer()

    user_id = str(interaction.user.id)
    opponent_id = str(opponent.id)

    async with aiosqlite.connect('soccer_cards.db') as db:
        try:
            # Fetch the user's lineup and total player value
            async with db.execute('''
                SELECT cards.ovrate, cards.club
                FROM cards
                INNER JOIN user_lineups ON cards.id = user_lineups.card_id
                WHERE user_lineups.user_id = ?
            ''', (user_id,)) as cursor:
                user_cards = await cursor.fetchall()

            user_player_value = sum(card[0] for card in user_cards)
            user_club = user_cards[0][1] if user_cards else "Unknown Club"

            # Check if the user's player value meets the minimum requirement
            if user_player_value < 30000000:  # 30M as total rating
                await interaction.followup.send("You need a player value of at least 30M to run this command.")
                return

            # Fetch the opponent's lineup and total player value
            async with db.execute('''
                SELECT cards.ovrate, cards.club
                FROM cards
                INNER JOIN user_lineups ON cards.id = user_lineups.card_id
                WHERE user_lineups.user_id = ?
            ''', (opponent_id,)) as cursor:
                opponent_cards = await cursor.fetchall()

            if not opponent_cards:
                await interaction.followup.send(f"{opponent.display_name} does not have a lineup set up.")
                return

            opponent_player_value = sum(card[0] for card in opponent_cards)
            opponent_club = opponent_cards[0][1] if opponent_cards else "Unknown Club"

            # Simulate match result based on player value and a luck factor
            user_luck = random.uniform(0.8, 1.2)
            opponent_luck = random.uniform(0.8, 1.2)

            user_final_value = user_player_value * user_luck
            opponent_final_value = opponent_player_value * opponent_luck

            if user_final_value > opponent_final_value:
                user_goals = random.randint(1, 5)
                opponent_goals = random.randint(0, user_goals - 1)
                winner = interaction.user.display_name
            elif user_final_value < opponent_final_value:
                opponent_goals = random.randint(1, 5)
                user_goals = random.randint(0, opponent_goals - 1)
                winner = opponent.display_name
            else:
                user_goals = opponent_goals = random.randint(0, 3)
                winner = "It's a draw!"

            # Display the result
            await interaction.followup.send(
                f"**Friendly Match Result**\n\n"
                f"**{user_club}** vs **{opponent_club}**\n\n"
                f"**Final Score:** {user_club} {user_goals} - {opponent_goals} {opponent_club}\n"
                f"**Winner:** {winner}"
            )

        except Exception as e:
            await interaction.followup.send(f"An error occurred: {e}")


@client.slash_command(name="flip", description="Flip a coin! Bet on heads or tails and win or lose money.", guild_ids=[guild_id])
async def flip_coin(
    interaction: Interaction,
    choice: str = SlashOption(
        name="choice",
        description="Pick heads or tails.",
        choices={"Heads": "heads", "Tails": "tails"},
        required=True
    ),
    amount: int = SlashOption(
        name="amount",
        description="The amount of money to bet (max 3000).",
        required=True
    )
):
    user_id = str(interaction.user.id)

    if amount <= 0 or amount > 3000:
        await interaction.response.send_message("Invalid amount! Please bet an amount between 1 and 3000.")
        return

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check the user's balance
        async with db.execute('SELECT balance FROM user_balances WHERE user_id = ?', (user_id,)) as cursor:
            result = await cursor.fetchone()

        if not result:
            await interaction.response.send_message("You don't have an account yet. Earn some money first!")
            return

        user_balance = result[0]

        if amount > user_balance:
            await interaction.response.send_message(f"You don't have enough money! Your current balance is {user_balance}.")
            return

        # Perform the coin flip
        flip_result = random.choice(["heads", "tails"])

        if flip_result == choice.lower():
            new_balance = user_balance + amount
            message = f"Congratulations! You won the flip and earned {amount} coins. Your new balance is {new_balance}."
        else:
            new_balance = user_balance - amount
            message = f"Sorry, you lost the flip and lost {amount} coins. Your new balance is {new_balance}."

        # Update the user's balance
        await db.execute('UPDATE user_balances SET balance = ? WHERE user_id = ?', (new_balance, user_id))
        await db.commit()

    await interaction.response.send_message(message)


@client.slash_command(name="buy", description="Buy a card from the shop.", guild_ids=[guild_id])
async def buy(interaction: Interaction):
    await interaction.response.defer()

    user_id = str(interaction.user.id)

    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Fetch all available cards
            async with db.execute('''
                SELECT id, name, price, ovrate, image_blob
                FROM cards
            ''') as cursor:
                cards = await cursor.fetchall()

            if not cards:
                await interaction.followup.send("No cards available in the shop.")
                return

        # Initialize the pagination
        current_index = 0
        total_cards = len(cards)

        async def update_embed(index):
            card_id, card_name, price, ovrate, image_blob = cards[index]

            embed = nextcord.Embed(
                title=f"{card_name} - OVR: {ovrate}",
                description=f"Price: {price} coins"
            )
            embed.set_image(url=f"attachment://card_image.png")

            return embed, nextcord.File(fp=io.BytesIO(image_blob), filename="card_image.png"), card_id, price

        # Create initial embed and buttons
        embed, image_file, current_card_id, current_price = await update_embed(current_index)
        
        view = nextcord.ui.View()

        async def previous_card(interaction: Interaction):
            nonlocal current_index, current_card_id, current_price
            if current_index > 0:
                current_index -= 1
            else:
                current_index = total_cards - 1
            
            embed, _, current_card_id, current_price = await update_embed(current_index)
            try:
                await interaction.response.edit_message(embed=embed, view=view)
            except nextcord.errors.NotFound:
                await interaction.followup.send(embed=embed, view=view)

        async def next_card(interaction: Interaction):
            nonlocal current_index, current_card_id, current_price
            if current_index < total_cards - 1:
                current_index += 1
            else:
                current_index = 0
            
            embed, _, current_card_id, current_price = await update_embed(current_index)
            try:
                await interaction.response.edit_message(embed=embed, view=view)
            except nextcord.errors.NotFound:
                await interaction.followup.send(embed=embed, view=view)

        async def buy_card(interaction: Interaction):
            nonlocal current_card_id, current_price
            async with aiosqlite.connect(DATABASE_PATH) as db:
                # Check if user has enough balance
                async with db.execute('''
                    SELECT balance
                    FROM user_balances
                    WHERE user_id = ?
                ''', (user_id,)) as cursor:
                    balance_result = await cursor.fetchone()

                if not balance_result:
                    await interaction.followup.send("User balance not found.")
                    return

                balance = balance_result[0]
                if balance < current_price:
                    await interaction.response.send_message("Insufficient balance.", ephemeral=True)
                    return

                # Add card to the user's collection
                await db.execute('''
                    INSERT INTO user_collections (user_id, card_id)
                    VALUES (?, ?)
                ''', (user_id, current_card_id))
                await db.commit()

                # Update user's balance
                await db.execute('''
                    UPDATE user_balances
                    SET balance = balance - ?
                    WHERE user_id = ?
                ''', (current_price, user_id))
                await db.commit()

            await interaction.response.send_message(f"You have successfully bought the card '{cards[current_index][1]}' for {current_price} coins.", ephemeral=True)

        previous_button = nextcord.ui.Button(label="<", style=nextcord.ButtonStyle.primary)
        previous_button.callback = previous_card

        next_button = nextcord.ui.Button(label=">", style=nextcord.ButtonStyle.primary)
        next_button.callback = next_card

        buy_button = nextcord.ui.Button(label="Buy", style=nextcord.ButtonStyle.success)
        buy_button.callback = buy_card

        view.add_item(previous_button)
        view.add_item(buy_button)
        view.add_item(next_button)

        # Send the first embed with the file attachment
        await interaction.followup.send(embed=embed, view=view, file=image_file)

    except Exception as e:
        await interaction.followup.send(f"An error occurred: {e}")
