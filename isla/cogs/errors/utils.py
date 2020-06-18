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

import re

from discord.ext import commands

from .formatting import remove_accents


def clean_prefix(bot, prefix):
    # Replace emoji and mentions with their rendered counterparts
    # Otherwise users are shown the raw form due to the code block

    prefix = re.sub(r"<a?:(\w{2,32}):\d{15,21}>", ":\\1:", prefix)  # Emoji
    prefix = re.sub(fr"<@!?{bot.user.id}>", f"@{bot.user}", prefix)  # Mentions

    return remove_accents(prefix)


def converter_name(converter):
    try:
        return converter.__name__
    except AttributeError:
        return type(converter).__name__


def get_failed_param(ctx):
    """
    Get which parameter a CheckFailure failed on.

    Some errors only have error text, and no useful attributes giving us this information.
    """

    params = tuple(ctx.command.params.values())
    handled = (*ctx.args, *ctx.kwargs.values())

    return params[len(handled)]


def get_context(ctx):
    """Get the failed parameter and a common signature for error messages."""

    param = get_failed_param(ctx)

    name = ctx.command.qualified_name
    prefix = clean_prefix(ctx.bot, ctx.prefix)

    # The zws is needed as mobile apps remove leading/following white space in code otherwise
    usage = re.sub(fr"(\s*[<\[]{param.name}[.=\w]*[>\]]\s*)", "`**`\u200b\\1\u200b`**`", ctx.command.signature,)
    usage = usage.rstrip("`") if usage.endswith("*`") else f"{usage}`"

    signature = (
        f"\n\nUsage: `{prefix}{name} {usage}\n"  # Unbalanced code is closed in usage
        f"See `{prefix}help {name}` for more information."
    )

    return param, signature
