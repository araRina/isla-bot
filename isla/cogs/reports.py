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
import datetime
import importlib
import sys

import discord
import tabulate
from discord.ext import commands

from isla.context import Context, punishments, types
from isla.isla import is_staff

from .errors import NoReportFound, UserCancellation


'''= SEMI AUTO REPORTING SUBCOMMANDS =
[{prefix}report create (rollback id)]
Used in conjunction with a rollback id of a grief you fixed on the server. This shows the info for the rollback, and then has you fill in the non automatic details such as proof (image links) and the punishment (if you haven't punished yet, say "skip" to do it later).
[{prefix}report add (report id) (rollback id)]
If you had to use /rollback multiple times on a single grief, you can use this to add more to the existing report
[{prefix}report list rollbacks]
Used to get a list of the rollbacks you haven't reported for yet. If you aren't logged into Discord with the Terraria server bots, use {prefix}report list rollbacks public to see a list of reports made that weren't linked to Discord accounts.
[{prefix}report list (page number)]
Brings up a list of reports sorted by ID. 25 reports per page. Not giving a page number shows the latest page.'''

reports_help = '''```asciidoc
= MANUAL REPORTING SUBCOMMANDS =
[{prefix}report new]
Used to create a report. Functions exactly like the old report command.
[{prefix}report edit (report id)]
Used to edit a report.
= LISTING SUBCOMMANDS =
[{prefix}report id (report id)]
Shows information tied to a report id.
[{prefix}report info (username)]
Shows information on a rule-breaker and any past offenses they may have.
```
'''


class reports(commands.Cog, name='reports'):
    def __init__(self, bot):
        self.bot = bot

    async def get_info_embed(self, username):
        reports = await self.bot.pool.fetch(
            '''
            SELECT * FROM staff_reports
            WHERE username = $1
            ORDER BY id ASC;
            ''',
            username,
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
            username,
        )

        offenses = ', '.join([types[i['type']] for i in offenses])

        embed = discord.Embed(title=f'User Info: {username}', description=offenses)

        blocks_griefs = sum([report['blocks'] for report in reports if report['type'] == 'grief'])
        blocks_tunnels = sum([report['blocks'] for report in reports if report['type'] == 'tunnel'])
        griefs = sum([1 for report in reports if report['type'] == 'grief'])
        tunnels = sum([1 for report in reports if report['type'] == 'grief'])
        punishes = [report['punishment'] for report in reports if report['punishment'] in punishments]

        griefed = f'Blocks griefed: {blocks_griefs} broken, {round(blocks_griefs / griefs)} average\n' if griefs else ''
        tunneled = (
            f'Blocks tunneled: {blocks_tunnels} broken, {round(blocks_tunnels / tunnels)} average\n' if griefs else ''
        )
        punished = f'Previous punishments: {",".join(punishes)}' if punishes else ''

        embed.add_field(
            name='General Data', value=f'{latest_created}{latest_happened}{griefed}{tunneled}{punished}', inline=False
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

    @commands.group()
    async def report(self, ctx):
        if ctx.invoked_subcommand:
            return
        await ctx.send(reports_help.format(prefix=ctx.prefix))

    @report.command()
    async def new(self, ctx: Context):
        username = await ctx.get_username()
        type = await ctx.get_type()

        embed = await self.get_info_embed(username)

        if type in ['grief', 'tunnel']:
            happened_at = await ctx.get_time_dh()
            image_links = await ctx.get_image_links()
            blocks = await ctx.get_blocks_affected()
        elif type == 'hack':
            happened_at = await ctx.get_time_date()
            image_links = await ctx.get_image_links()
            blocks = 0
        else:
            happened_at = await ctx.get_time_date()
            image_links = await ctx.get_image_links()
            blocks = await ctx.get_blocks_affected()

        if embed:
            await ctx.send('User is already in database.', embed=embed)

        punishment = await ctx.get_punishment()

        summary = await ctx.get_summary()

        reporter = str(ctx.author.id)

        id = await self.bot.pool.fetchval(
            '''
            INSERT INTO staff_reports
            (username, type, staff, summary, blocks, image_links, happened_at, punishment)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id;
        ''',
            username,
            type,
            reporter,
            summary,
            blocks,
            image_links,
            happened_at,
            punishment,
        )

        if embed:
            await ctx.send(f'Report saved to ID {id}')
        else:
            embed = await ctx.get_info_embed(username)
            await ctx.send(f'Report saved to ID {id}', embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id == self.bot.config['server']['communication_channel_id']:
            pass  # TODO: Program auto reporting

    @report.command()
    async def info(self, ctx, username):
        embed = await self.get_info_embed(username)

        if embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send('Username not in database.')

    @report.command()
    async def id(self, ctx, id: int):
        report = await self.bot.pool.fetchrow(
            """
        SELECT *
            FROM staff_reports
            WHERE id = $1;
        """,
            id,
        )

        if not report:
            raise NoReportFound('No report by that ID was found.')

        embed = discord.Embed(title=f"Report #{id}", description=f"Reporting {report['username']}'s {report['type']}")

        if report['created_at']:
            embed.add_field(name='Reported at', value=report['created_at'].strftime("%y %b %d %H:%M:%S"))

        if report['happened_at']:
            embed.add_field(name='Happened at', value=report['happened_at'].strftime("%y %b %d"))

        try:
            reporter = int(report['staff'])
            reporter = reporter.mention
        except:
            reporter = report['staff']

        if report['blocks']:
            embed.add_field(name=f'Blocks edited', value=report['blocks'])

        embed.add_field(name='Reporter', value=reporter)

        if report['punishment']:
            embed.add_field(name='Punishment', value=report['punishment'])

        if report['summary']:
            embed.add_field(name='Summary', value=report['summary'])

        post = '\n'.join(report['image_links'])

        embed.set_footer(text=f'Use r!report info {report["username"]} for more info.')

        await ctx.send("", embed=embed)

        if post:
            await ctx.send(post)

    @report.command()
    async def edit(self, ctx, id: int):
        report = await self.bot.pool.fetchrow(
            """
        SELECT *
            FROM staff_reports
            WHERE id = $1
        """,
            id,
        )

        if not report:
            raise (NoReportFound('No Report by that ID was found.'))

        field = await ctx.get_field()

        if field == 'username':
            field_info = await ctx.get_username()
        elif field == 'type':
            field_info = await ctx.get_type()
        elif field == 'image_links':
            field_info = await ctx.edit_image_links(image_links=report['image_links'])
        elif field == 'blocks':
            field_info = await ctx.get_blocks()
        elif field == 'summary':
            field_info = await ctx.get_summary()
        elif field == 'happened_at':
            field_info = await ctx.get_time(report['type'])
        elif field == 'punishment':
            field_info = await ctx.get_punishment()

        await self.bot.pool.execute(
            f"""
            UPDATE staff_reports
                SET {field} = $1
                WHERE id = $2
            """,
            field_info,
            id,
        )

        await ctx.send(f'Report edited! Use r!report id {id} to check out the edited report.')


def setup(bot):
    bot.add_cog(reports(bot))
