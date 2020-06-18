from discord.ext import commands


class roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener(name="on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload):
        react_roles = await self.bot.pool.fetch(
            '''
            SELECT *
                FROM terraria_one_roles;
            '''
        )

        if payload.guild_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            for record in filter(
                lambda record: record["message_id"] == payload.message_id and payload.emoji.id == record["emoji_id"],
                react_roles,
            ):
                await member.add_roles(guild.get_role(record["role_id"]))
            else:
                return None

    @commands.Cog.listener(name="on_raw_reaction_remove")
    async def on_raw_reaction_remove(self, payload):
        react_roles = await self.bot.pool.fetch(
            '''
            SELECT *
                FROM terraria_one_roles;
            '''
        )

        if payload.guild_id:
            guild = self.bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            for record in filter(
                lambda record: record["message_id"] == payload.message_id and payload.emoji.id == record["emoji_id"],
                react_roles,
            ):
                await member.remove_roles(guild.get_role(record["role_id"]))
            else:
                return None


def setup(bot):
    bot.add_cog(roles(bot))
