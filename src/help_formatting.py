
import discord

class BagelHelper(discord.ext.commands.DefaultHelpCommand):
    pass

    # disabled for now -- issues with pagination, and exceeding
    # the maximum discord message size

    # async def send_pages(self):
    #     destination = self.get_destination()
    #     e = discord.Embed(color=discord.Color.blurple(),
    #         title="Help Text", description='')
    #     for page in self.paginator.pages:
    #         e.description += page
    #     await destination.send(embed=e)
