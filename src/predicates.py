from discord.ext import commands

# assertion that the command caller is the creator of this bot;
# used to prevent rubes from invoking powerful commands
async def is_wade(ctx):
    is_wade = ctx.message.author.id == 235584665564610561
    return is_wade

# assertion which allows only Collin Smith, Collin Deans, or Wade
# to run this command
async def is_one_of_the_collins_or_wade(ctx):
    is_a_collin_or_wade = await is_wade(ctx) or \
        ctx.message.author.id == 188843663680339968 or \
        ctx.message.author.id == 221481539735781376
    return is_a_collin_or_wade

# decorator for restricting a command to wade
def wade_only():
    async def predicate(ctx):
        # log.info(ctx.message.author.id)
        ret = await is_wade(ctx)
        return ret
    ret = commands.check(predicate)
    return ret

# decorator for restricting a command to only a collin, or wade
def wade_or_collinses_only():
    async def predicate(ctx):
        # log.info(ctx.message.author.id)
        ret = await is_one_of_the_collins_or_wade(ctx)
        return ret
    ret = commands.check(predicate)
    return ret
