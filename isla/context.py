import asyncio
import datetime

import discord
import numpy
import tabulate
from discord.ext import commands

from common import UserCancellation, time_date, time_dh, url_grabber


types = {'grief': 'griefer', 'chat': 'chat abuser', 'hack': 'hacker', 'other': 'abuser', 'tunnel': 'tunneler'}

punishments = ['tban', 'pban', 'mute', 'pmute', 'kick', 'warn']


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

    async def get_info_embed(self, username):
        reports = await self.bot.pool.fetch(
            '''
            SELECT * FROM staff_reports
            WHERE username = $1
            ORDER BY id ASC;
            ''',
            username
        )

        if not reports:
            return None

        def check(x, y):
            if x[y]:
                if y == 'happened_at':
                    return (
                            datetime.datetime.combine(x[y], datetime.time(hour=0, minute=0, second=0))
                            - datetime.datetime(year=1, month=1, day=1, hour=0, minute=0, second=0)
                    ).total_seconds()
                if y == 'created_at':
                    return (
                            x[y] - datetime.datetime(year=1, month=1, day=1, hour=0, minute=0, second=0)
                    ).total_seconds()
            else:
                return 0

        try:
            latest_created = sorted(reports, key=lambda r: check(r, 'created_at'), reverse=True)[0][
                'created_at'
            ].strftime('%d %b %Y at %I:%M %p.')
            latest_created = f'Latest report: {latest_created}\n'
        except:
            latest_created = ''

        try:
            latest_happened = sorted(reports, key=lambda r: check(r, 'happened_at'), reverse=True)[0][
                'happened_at'
            ].strftime('%d %b %Y')
            latest_happened = f'Latest offense: {latest_happened}\n'
        except:
            latest_happened = ''

        offenses = await self.bot.pool.fetch(
            '''
            SELECT DISTINCT type
            FROM staff_reports
            WHERE username = $1
            ''',
            username
        )

        offenses = ', '.join([types[i['type']] for i in offenses])

        embed = discord.Embed(title=f'User Info: {username}', description=offenses)

        blocks_griefs = sum([report['blocks'] for report in reports if report['type'] == 'grief'])
        blocks_tunnels = sum([report['blocks'] for report in reports if report['type'] == 'tunnel'])
        griefs = sum([1 for report in reports if report['type'] == 'grief'])
        tunnels = sum([1 for report in reports if report['type'] == 'grief'])

        griefed = f'Blocks griefed: {blocks_griefs} broken, {round(blocks_griefs / griefs)} average\n' if griefs else ''
        tunneled = f'Blocks tunneled: {blocks_tunnels} broken, {round(blocks_tunnels / tunnels)}average' if griefs else ''

        embed.add_field(
            name='General Data',
            value=f'{latest_created}{latest_happened}{griefed}{tunneled}',
            inline=False
        )

        embed.add_field(
            name='List of reports',
            value='```\n'
                  + tabulate.tabulate(
                [
                    [
                        report['id'],
                        report['type'],
                        str(report['blocks']),
                        report['happened_at'].strftime('%d %b %Y') if report['happened_at'] else '',
                        report['created_at'].strftime('%d %b %Y') if report['created_at'] else '',
                    ]
                    for report in reports
                ],
                headers=['id', 'type', 'blocks', 'happened_at', 'reported on'],
            )
                  + '```',
            inline=False,
        )
        return embed

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

    async def get_image_links(self):
        self.image_links = []

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

    async def get_field(self):
        def check(message):
            return message.content.lower() in [
                'username',
                'type',
                'image links',
                'blocks broken',
                'summary',
                'happened at',
            ]

        def return_operation(message):
            return message.content.lower()

        return await self._get_field_info(
            msg_1=f'Which field do you want to edit? Fields: `username`, `type`, `image links`, `blocks broken`, `summary`, `happened at`.',
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
