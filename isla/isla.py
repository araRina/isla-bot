"""
Isla Bot: Reporting functionality for a Terraria Server
Copyright (C) 2020 Rina

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import logging

import asyncpg
import discord
import ruamel.yaml
from discord.ext import commands
from discord.ext.commands import Bot

from .context import Context


def is_staff():
    def predicate(ctx):
        if ctx.guild:
            if ctx.guild.id == ctx.bot.config['server']['guild_id']:
                role_ids = [role.id for role in ctx.author.roles]
                return ctx.bot.config['server']['staff_role_id'] in role_ids or ctx.author.id == ctx.bot.owner_id
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

        extensions = ['jishaku', 'isla.cogs.reports', 'isla.cogs.errors', 'isla.cogs.roles']

        for cog in extensions:
            self.load_extension(cog)

    def run(self):
        logger = logging.getLogger("discord")
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] (%(levelname)s) %(name)s: %(message)s", datefmt="%y %b %d %H:%M:%S",)
        )
        logger.addHandler(handler)
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
