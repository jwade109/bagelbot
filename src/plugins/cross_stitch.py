import discord
from discord import app_commands
from discord.ext import commands
import logging
from bagelshop.logging import log
from resource_paths import DMC_COLORS_CSV_PATH, WORKSPACE_DIRECTORY
from pandas import read_csv
from dataclasses import dataclass
from state_machine import get_param, set_param


FLOSS_INVENTORY_YAML_PATH = WORKSPACE_DIRECTORY + "/private/cross_stitch.yaml"


@dataclass()
class DMCColor:
    id: str = ""
    name: str = ""
    r: int = 0
    g: int = 0
    b: int = 0
    hex: int = 0


def parse_csv():
    df = read_csv(DMC_COLORS_CSV_PATH)
    colors = {}
    for _, row in df.iterrows():
        c = DMCColor()
        c.id = row["id"]
        c.name = row["name"]
        c.r = row["r"]
        c.g = row["g"]
        c.b = row["b"]
        c.hex = int(row["hex"], 16)
        colors[c.id.lower()] = c
    return colors


DMC_COLORS = parse_csv()


def get_color(floss_id):
    return DMC_COLORS.get(floss_id.lower())


def read_inventory():
    return get_param("inventory", {}, FLOSS_INVENTORY_YAML_PATH)


def write_inventory(inv):
    set_param("inventory", inv, FLOSS_INVENTORY_YAML_PATH)


def dmc_to_embed(dmc: DMCColor, **kwargs):
    quantity = kwargs.get("quantity", None)
    detailed = kwargs.get("detailed", False)
    if quantity is None or detailed:
        embed = discord.Embed(title=f"{dmc.id} - {dmc.name}", color=dmc.hex)
    else:
        embed = discord.Embed(title=f"(x{quantity}) {dmc.id} - {dmc.name}", color=dmc.hex)
    if detailed:
        embed.add_field(name="RGB", value=f"{dmc.r}, {dmc.g}, {dmc.b}")
        embed.add_field(name="Hex", value=f"{dmc.hex:X}")
        if not quantity is None:
            embed.add_field(name="Quantity", value=f"{quantity}")
    return embed


# class Floss(app_commands.Group):

    # @app_commands.command(name="add")
    # async def add(self, inter, floss_code: int):
    #     e = dmc_to_embed(DMC_COLORS[12])
    #     print(e)
    #     await inter.response.send_message(f"add {floss_code}", embed=e)

    # @app_commands.command(name="remove")
    # async def remove(self, inter, floss_code: int):
    #     await inter.response.send_message(f"remove {floss_code}")

    # @app_commands.command(name="move")
    # async def move(self, inter):
    #     await inter.response.send_message("move")

    # @app_commands.command(name="check")
    # async def check(self, inter):
    #     await inter.response.send_message("check")


class CrossStitch(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.inventory = read_inventory()
        # self.bot.tree.add_command(Floss(name="floss",
        #     description="Stuff for cross stitching"))

    def add_floss(self, user_id, floss_code: str, quantity : int = 1):
        if not user_id in self.inventory:
            self.inventory[user_id] = {}
        if not floss_code in self.inventory[user_id]:
            self.inventory[user_id][floss_code] = 0
        new_quantity = self.inventory[user_id][floss_code] + quantity
        self.inventory[user_id][floss_code] = new_quantity
        write_inventory(self.inventory)
        return new_quantity

    def remove_floss(self, user_id, floss_code: str, quantity : int = 1):
        if not user_id in self.inventory:
            return 0, 0
        if not floss_code in self.inventory[user_id]:
            return 0, 0
        if self.inventory[user_id][floss_code] < quantity:
            num_removed = self.inventory[user_id][floss_code]
            del self.inventory[user_id][floss_code]
            write_inventory(self.inventory)
            return 0, num_removed
        self.inventory[user_id][floss_code] -= quantity
        write_inventory(self.inventory)
        return self.inventory[user_id][floss_code], quantity

    @commands.command(name="floss-add")
    async def add(self, ctx, floss_code: str, quantity: int = 1):
        c = get_color(floss_code)
        if not c:
            return await ctx.send(f"No floss found with code {floss_code}")
        new_quantity = self.add_floss(ctx.author.id, c.id, quantity)
        e = dmc_to_embed(c, detailed=True, quantity=new_quantity)
        return await ctx.send(f"Added {quantity} new skein(s) of {c.id}. " \
            f"You currently have {new_quantity}.", embed=e)

    @commands.command(name="floss-remove")
    async def remove(self, ctx, floss_code: str, quantity: int = 1):
        c = get_color(floss_code)
        if not c:
            return await ctx.send(f"No floss found with code {floss_code}")
        new_quantity, num_removed = self.remove_floss(ctx.author.id, c.id, quantity)
        e = dmc_to_embed(c, detailed=True, quantity=new_quantity)
        return await ctx.send(f"Removed {num_removed} new skein(s) of {c.id}. " \
            f"You currently have {new_quantity}.", embed=e)

    @commands.command(name="floss-view")
    async def view(self, ctx, floss_id: str = None):

        if not ctx.author.id in self.inventory:
            await ctx.send("You have no flosses. Register them with floss-add.")
            return

        inv = self.inventory[ctx.author.id]

        if floss_id:
            c = get_color(floss_id)
            if not c:
                return await ctx.send(f"Invalid floss ID: {floss_id}")
            quantity = inv.get(c.id, 0)
            e = dmc_to_embed(c, quantity=quantity, detailed=True)
            return await ctx.send(embed=e)

        embeds = []
        for floss_code, quantity in inv.items():
            c = get_color(floss_code)
            if not c:
                await ctx.send(f"Bad color code: {floss_code}. Skipping.")
                continue
            e = dmc_to_embed(c, quantity=quantity)
            embeds.append(e)
            # await ctx.send(embed=e)
        await ctx.send(embeds=embeds)
