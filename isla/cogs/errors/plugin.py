# -*- coding: utf-8 -*-

"""
Isla Bot: Reporting functionality for a Terraria Server
Copyright (c) 2016 - 2020 Lilly Rose Berner
Copyright (C) 2020 Rina

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import logging

import discord
from discord.ext import commands

from .handler import get_message


log = logging.getLogger(__name__)


class Errors(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.on_error = self.on_error

    def cog_unload(self):
        self.bot.on_error = commands.Bot.on_error

    async def on_error(self, event, *args, **kwargs):
        log.exception(f"Unhandled exception in {event} handler.")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        message = get_message(ctx, error)

        if message is not None:
            try:
                await ctx.send(message)
            except discord.Forbidden:
                pass
