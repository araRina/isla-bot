import asyncpg
import discord
import ruamel.yaml
from discord.ext import commands
from discord.ext.commands import Bot

from common import UserCancellation

from .context import Context


async def is_staff():
    def predicate(ctx):
        if ctx.guild:
            if ctx.guild.id == ctx.bot.config['discord']['guild_id']:
                role_ids = [role.id for role in ctx.author.roles]
                return ctx.bot.config['discord']['staff_role'] in role_ids or ctx.author.id == ctx.bot.owner_id
        return ctx.author.id == ctx.bot.owner_id

    return commands.check(predicate)


class Isla(Bot):
    def __init__(self, config, **kwargs):
        super().__init__(
            command_prefix=config['bot']['prefix'], case_insensitive=True, owner_id=config['bot']['owner_id'], **kwargs
        )

        self.config = config
        self.using = []
        self.pool = None

        extensions = ['jishaku', 'isla.cogs.reports']

        for cog in extensions:
            self.load_extension(cog)

    def run(self):
        return super().run(self.config['bot']['token'])

    @classmethod
    def with_config(cls):
        with open('config.yaml', encoding='utf-8') as f:
            data = ruamel.yaml.safe_load(f)
        return cls(data)

    async def start(self, *args, **kwargs):
        self.pool = await asyncpg.create_pool(**self.config['postgres'])
        return await super().start(*args, **kwargs)

    async def on_message(self, message):
        ctx = await self.get_context(message, cls=Context)

        if ctx.author.bot:
            return

        if not ctx.valid:
            return

        if ctx.author.id == self.owner_id or ctx.author.id == message.guild.owner_id:
            return await self.invoke(ctx)

        if message.author.id in self.using:
            return

        try:
            self.using.append(message.author.id)
            await self.invoke(ctx)
        finally:
            self.using.remove(message.author.id)

    async def on_command_error(self, ctx, error):
        if isinstance(error, UserCancellation):
            await ctx.send('Command cancelled.')
        elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
            await ctx.send('Missing argument!')
        else:
            raise error
