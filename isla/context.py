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
import asyncio
import datetime

from discord.ext import commands

from common import time_date, time_dh, url_grabber
from isla.errors import NoImageLinks, UserCancellation


types = {'grief': 'griefer', 'chat': 'chat abuser', 'hack': 'hacker', 'other': 'abuser', 'tunnel': 'tunneler'}

punishments = ['tban', 'pban', 'mute', 'pmute', 'kick', 'warn', 'null']


def default_check(message):
    return True


def default_return_operation(message):
    return message.content


def check_reaction(ctx, my_message, skippable):
    def check_reaction(reaction, user):
        if user.id == ctx.author.id and reaction.message.id == my_message.id:
            if str(reaction) == '❌':
                raise UserCancellation('User cancelled command.')
            return skippable and str(reaction) == '✅'
        return False

    return check_reaction


def message_check(ctx):
    def message_check(message):
        return message.author.id == ctx.author.id and message.channel == ctx.message.channel

    return message_check


async def wait_for_message_or_reaction(ctx, my_message, skippable):
    done, pending = await asyncio.wait(
        [
            ctx.bot.wait_for('message', check=message_check(ctx)),
            ctx.bot.wait_for('reaction_add', check=check_reaction(ctx, my_message, skippable)),
        ],
        return_when=asyncio.FIRST_COMPLETED,
    )

    if done:
        stuff = done.pop().result()

        for future in pending:
            future.cancel()

            if stuff.__class__.__name__ == 'Message':
                if stuff.content.lower() == 'stop':
                    raise UserCancellation('User cancelled command.')
            else:
                stuff = stuff[0]

    return stuff


class Context(commands.Context):
    async def send_all(self, text):
        currently_in_codeblock = 0

        text = text.split('\n')

        current_post = ''
        for line in text:
            if len(f'{current_post}\n{line}') > 1990:
                if currently_in_codeblock:
                    current_post += '```'
                await self.send(current_post)
                current_post = line
                if currently_in_codeblock:
                    current_post = '```' + current_post
            else:
                if line.count('```') % 2 == 1:
                    currently_in_codeblock = 1 - currently_in_codeblock
                current_post += '\n' + line
        await self.send(current_post)

    async def _get_field_info(
        self, msg_1=None, msg_2=None, check=default_check, return_operation=default_return_operation, skippable=False
    ):
        my_message = await self.send(msg_1)
        if skippable:
            await my_message.add_reaction('✅')
        await my_message.add_reaction('❌')

        response = await wait_for_message_or_reaction(self, my_message, skippable)

        while not check(response):
            my_message = await self.send(msg_2)
            if skippable:
                await my_message.add_reaction('✅')
            await my_message.add_reaction('❌')

            response = await wait_for_message_or_reaction(self, my_message, skippable)

        return return_operation(response)

    # Staff Reports

    async def get_username(self):
        return await self._get_field_info(msg_1='Please send the username of the rulebreaker')

    async def get_type(self):
        def check(message):
            return message.content.lower() in types.keys()

        def return_operation(message):
            return message.content.lower()

        return await self._get_field_info(
            msg_1=f'What type of offense happened? Types: grief, chat, hack, other, or tunnel.',
            msg_2='Incorrect input! Try again.',
            check=check,
            return_operation=return_operation,
        )

    async def get_summary(self):
        def return_operation(message):
            if str(message) == '✅':
                return None
            return message.content

        return await self._get_field_info(
            msg_1=f'Type a summary. If you have no summary to add, press the ✅ to skip it.',
            return_operation=return_operation,
            skippable=True,
        )

    async def get_punishment(self):
        def check(message):
            return message.content.lower() in punishments

        def return_operation(message):
            return message.content.lower()

        return await self._get_field_info(
            msg_1=f'What kind of punishment did the user get? Possible punishments are: tban, pban, mute, pmute, kick, or warn.',
            check=check,
            return_operation=return_operation,
            skippable=True,
        )

    async def get_blocks_affected(self):
        def check(message):
            try:
                int(message.content)
                return True
            except:
                return False

        def return_operation(message):
            return int(message.content)

        return await self._get_field_info(
            msg_1=f'Send how many blocks were affected.',
            msg_2=f'Incorrect input! Try sending a number this time.',
            return_operation=return_operation,
            check=check,
        )

    async def get_image_links(self, image_links=[]):
        self.image_links = image_links

        def check(message):
            if message.__class__.__name__ == 'Message':
                new_links = url_grabber.findall(message.content) + [
                    attachment.url for attachment in message.attachments
                ]
            else:
                new_links = []

            self.image_links += new_links

            return not new_links

        def return_operation(message):
            return self.image_links

        return await self._get_field_info(
            msg_1=f'Send proof images/links to images. (Can be in multiple messages).',
            msg_2=f'Press the ✅ to end, or continue sending proof.',
            return_operation=return_operation,
            check=check,
            skippable=True,
        )

    async def remove_image_links(self, image_links=[]):
        if not image_links:
            raise NoImageLinks()

        def check(message):
            try:
                return image_links.pop(int(message.content))
            except:
                return False

        def return_operation(message):
            return image_links

        images_by_number = '\n'.join(f'`{i}`: {j}' for i, j in enumerate(image_links))

        return await self._get_field_info(
            msg_1=f'Send the number corresponding with the image you want removed\n{images_by_number}',
            msg_2='Incorrect input! Try again.',
            check=check,
            return_operation=return_operation,
            skippable=True,
        )

    async def edit_image_links(self, image_links=[]):
        def check(message):
            return message.content.lower() in ['remove', 'add']

        def return_operation(message):
            return {'remove': self.remove_image_links, 'add': self.get_image_links}[message.content.lower()](
                image_links=image_links
            )

        return await (
            await self._get_field_info(
                msg_1='Would you like to add or remove images? Proper responses include: `add`, `remove`',
                msg_2='Incorrect input! Try again.',
                return_operation=return_operation,
                check=check,
            )
        )

    async def get_field(self):
        def check(message):
            return message.content.lower() in [
                'username',
                'type',
                'image links',
                'blocks',
                'summary',
                'happened at',
                'punishment',
            ]

        def return_operation(message):
            return message.content.lower().replace(' ', '_')

        return await self._get_field_info(
            msg_1=f'Which field do you want to edit? Fields: `username`, `type`, `image links`, `blocks`, `summary`, `happened at`, `punishment`.',
            msg_2=f'Incorrect input! Try again.',
            return_operation=return_operation,
            check=check,
            skippable=True,
        )

    async def get_time_dh(self):
        def check(message):
            return time_dh.findall(message.content)

        def return_operation(message):
            time_list = [int(item) for item in time_dh.findall(message.content)[0]]
            return (datetime.datetime.now() - datetime.timedelta(days=time_list[0], hours=time_list[1])).date()

        return await self._get_field_info(
            msg_1=f'How long ago did this occur? Format: XXdXXh',
            msg_2=f'Incorrect input! Try again.',
            return_operation=return_operation,
            check=check,
            skippable=True,
        )

    async def get_time_date(self):
        def message_to_date(message):
            search = time_date.findall(message.content)
            if search:
                time_list = [int(i) for i in search[0]]
                try:
                    return datetime.date(day=time_list[0], month=time_list[1], year=datetime.datetime.now().year)
                except:
                    return False

        return await self._get_field_info(
            msg_1=f'When did this occur? Format: DD/MM',
            msg_2=f'Incorrect input! Try again.',
            return_operation=message_to_date,
            check=message_to_date,
            skippable=True,
        )

    async def get_time(self, type):
        if type in ['grief', 'tunnel']:
            return await self.get_time_dh()
        else:
            return await self.get_time_date()
