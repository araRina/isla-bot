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

from .errors import NoImageLinks, NoReportFound, UserCancellation
from .formatting import remove_accents
from .utils import converter_name, get_context


log = logging.getLogger(__name__)


ERROR_HANDLERS = {}

INTERNAL_ERROR = "Something unexpected went wrong during command execution. Please try again later."


def add_handler(exc_type):
    def decorator(func):
        ERROR_HANDLERS[exc_type] = func
        return func

    return decorator


def get_handler(error):
    """Get the error handler for a given error."""

    chain = type(error).__mro__

    return next(filter(None, map(ERROR_HANDLERS.get, chain)))


def get_message(ctx, error):
    """Get the response for a given error."""

    handler = get_handler(error)

    if handler is not None:
        return handler(ctx, error)


@add_handler(UserCancellation)
def handle_user_cancellation(ctx, error):
    return 'Successfully cancelled.'


@add_handler(NoReportFound)
def handle_no_report_found(ctx, error):
    return 'No report by that ID was found!'


@add_handler(NoImageLinks)
def handle_no_image_links(ctx, error):
    return "There's no image links to remove for this report!"


# Silence the default CommandError handler for these
@add_handler(commands.CheckFailure)
@add_handler(commands.CommandNotFound)
@add_handler(commands.DisabledCommand)
def null_handler(ctx, error):
    pass


@add_handler(commands.CommandError)
def handle_command_error(ctx, error):
    log.exception(f"Unhandled command error!", exc_info=error)
    return INTERNAL_ERROR


@add_handler(commands.ConversionError)
def handle_conversion_error(ctx, error):
    converter = converter_name(error.converter)
    log.exception(f"Unhandled exception in {converter} converter.", exc_info=error)

    return INTERNAL_ERROR


@add_handler(commands.CommandInvokeError)
def handle_command_invoke_error(ctx, error):
    original = error.original

    if isinstance(original, discord.HTTPException) and 500 <= original.status <= 599:
        response = original.response

        # Sometimes this is the generic CF error page,
        # Which is a *bit* too big and unreadable to display
        value = response.headers.get("Content-Type", "")
        text = "" if "text/html" in value else original.text

        return f"Unable to reach Discord: {response.status} {response.reason} {text}"

    command = ctx.command.qualified_name
    log.exception(f'Unhandled exception during "{command}" command execution.', exc_info=error)

    return INTERNAL_ERROR


@add_handler(commands.BotMissingPermissions)
def handle_bot_missing_permissions(ctx, error):
    perms = error.missing_perms

    if len(perms) <= 2:
        formatted = "` and `".join(perms)
    else:
        formatted = "`, `".join(perms[:-1]) + "`, and `" + perms[-1]

    s = "s" if len(perms) > 1 else ""
    missing = formatted.replace("_", " ").replace("guild", "server")

    return f"I'm missing the `{missing}` permission{s} required to run this command."


@add_handler(commands.MissingRequiredArgument)
def handle_missing_required_argument(ctx, error):
    param, signature = get_context(ctx)
    return f"The `{param.name}` argument is required but missing.{signature}"


@add_handler(commands.BadArgument)
def handle_bad_argument(ctx, error):
    error = str(error)
    param, signature = get_context(ctx)

    return remove_accents(error).replace('"', "`") + signature


@add_handler(commands.UnexpectedQuoteError)
@add_handler(commands.ExpectedClosingQuoteError)
@add_handler(commands.InvalidEndOfQuotedStringError)
def handle_unexpected_quote_error(ctx, error):
    error = str(error)
    stop = "" if error.endswith(".") else "."

    return f"{error}{stop}".replace("'", "`")
