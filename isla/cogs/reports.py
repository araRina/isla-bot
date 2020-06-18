import importlib
import sys

from discord.ext import commands

from common import UserCancellation
from common import NoReportFound
from isla.context import Context
from isla.isla import is_staff

'''= SEMI AUTO REPORTING SUBCOMMANDS =
[{prefix}report create (rollback id)]
Used in conjunction with a rollback id of a grief you fixed on the server. This shows the info for the rollback, and then has you fill in the non automatic details such as proof (image links) and the punishment (if you haven't punished yet, say "skip" to do it later).
[{prefix}report add (report id) (rollback id)]
If you had to use /rollback multiple times on a single grief, you can use this to add more to the existing report
[{prefix}report list rollbacks]
Used to get a list of the rollbacks you haven't reported for yet. If you aren't logged into Discord with the Terraria server bots, use {prefix}report list rollbacks public to see a list of reports made that weren't linked to Discord accounts.'''

reports_help = '''```asciidoc
= MANUAL REPORTING SUBCOMMANDS =
[{prefix}report new]
Used to create a report if the server doesn't send data to the bot to help with the semi automatic reporting process. Functions exactly like the old {prefix}report.
= LISTING SUBCOMMANDS =
[{prefix}report list (page number)]
Brings up a list of reports sorted by ID. 25 reports per page. Not giving a page number shows the latest page.
[{prefix}report id (report id)]
Shows information on a given report by ID
```
'''


class reports(commands.Cog, name='reports'):
    def __init__(self, bot):
        self.bot = bot

    @commands.group()
    async def report(self, ctx):
        if ctx.invoked_subcommand:
            return
        await ctx.send(reports_help.format(prefix=ctx.prefix))

    @report.command()
    async def new(self, ctx: Context):
        username = await ctx.get_username()
        type = await ctx.get_type()

        embed = await ctx.get_info_embed(username)

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

        summary = await ctx.get_summary()

        reporter = str(ctx.author.id)

        id = await self.bot.pool.fetchval(
            '''
            INSERT INTO staff_reports
            (username, type, staff, summary, blocks, image_links, happened_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id;
        ''',
            username,
            type,
            reporter,
            summary,
            blocks,
            image_links,
            happened_at,
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
        importlib.reload(sys.modules['isla.context'])
        from isla.context import Context

        new_ctx = await self.bot.get_context(ctx.message, cls=Context)

        embed = await new_ctx.get_info_embed(username)

        if embed:
            await new_ctx.send(embed=embed)
        else:
            await new_ctx.send('Username not in database.')

    @report.command()
    async def id(self, ctx, id: int):
        report = await self.pool.fetchrow(
        """
        SELECT *
            FROM staff_reports
            WHERE id = $1;
        """, id)

        if not report:
            raise NoReportFound('No report by that ID was found.')






def setup(bot):
    bot.add_cog(reports(bot))
