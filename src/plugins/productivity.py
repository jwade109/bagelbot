from discord.ext import commands, tasks
from state_machine import get_param, set_param


class Productivity(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.reminders = get_param("reminders", [])
        self.todos = get_param("todo_lists", {})

    def get_todos(self, id):
        if id not in self.todos:
            self.todos[id] = []
        return self.todos[id]

    def set_todos(self, id, todos):
        self.todos[id] = todos
        set_param("todo_lists", self.todos)

    def add(self, id, todo : str):
        todos = self.get_todos(id)
        todos.append(todo)
        self.set_todos(id, todos)

    def delete(self, id, index):
        print("Delete element {index}.")

    @commands.command(aliases=["cl", "captains-log"], help="Look your to-do list, or add a new to-do item.")
    async def todo(self, ctx, *varargs):
        id = ctx.message.author.id

        if not varargs:
            varargs = ["show"]
        subcommand = varargs[0]

        if subcommand == "show":
            varargs = varargs[1:]
            todos = self.get_todos(id)
            if not todos:
                await ctx.send("You have no items on your to-do list. To add an item, " \
                    "use `bb todo add [thing you need to do]`.")
                return
            username = ctx.message.author.name.upper()
            resp = f"```\n=== {username}'S TODO LIST ==="
            for i, todo in enumerate(todos):
                resp += f"\n{i+1:<5} {todo}"
            resp += "\n```"
            await ctx.send(resp)
            return
        if subcommand == "add":
            varargs = varargs[1:]
            if not varargs:
                await ctx.send("I can't add nothing to your to-do list!")
                return
            task = " ".join(varargs)
            self.add(id, task)
            await ctx.send(f"Ok, I've added \"{task}\" to your to-do list.")
            return
        if subcommand == "del" or subcommand == "done":
            varargs = varargs[1:]
            index = None
            try:
                index = int(varargs[0])
            except Exception:
                await ctx.send("This command requires a to-do item number to delete.")
                return
            todos = self.get_todos(id)
            if index > len(todos) or index < 1:
                await ctx.send(f"Sorry, I can't delete to-do item {index}.")
                return
            del todos[index-1]
            self.set_todos(id, todos)
            await ctx.send(f"Ok, I've removed item number {index} from your to-do list.")
            return
        else:
            if not varargs:
                await ctx.send("I can't add nothing to your to-do list!")
                return
            task = " ".join(varargs)
            self.add(id, task)
            await ctx.send(f"Ok, I've added \"{task}\" to your to-do list.")
            return

        await ctx.send(f"`{subcommand}`` is not a valid todo command. Valid subcommands are: `show`, `add`, `del`.")

