#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Nekozilla is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Nekozilla is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Nekozilla.  If not, see <https://www.gnu.org/licenses/>.

"""
Basic utilities and stuff that implement commands for:
- help
- ping
- uptime
- load [extension]
- unload [extension]
- reload [all extensions]
- update [via git]
- redeploy [via git]
- version info
- bot stats
- event loop health
- system health
- lines of code count
- github link
- trello link
- bot source code license
- canirun [determines if the user can run a command here]
- invite [generates an invite URL]
- timeit [times the execution of another command]
- logout [used to restart if running as a system service]
"""
import collections
import logging
import typing

from discord.ext import commands as dpycommands

from neko3 import fuzzy_search
from neko3 import logging_utils
from neko3 import neko_commands
from neko3 import pagination
from neko3 import string
from neko3 import theme


class HelpCog(neko_commands.Cog, logging_utils.Loggable):
    def __init__(self, bot):
        bot.remove_command("help")
        self.bot = bot

    @neko_commands.command(name="help", brief="Gets usage information for commands.")
    async def help_command(self, ctx, *, query: str = None):
        """
        If a command name is given, perform a search for that command and
        display info on how to use it. Otherwise, if nothing is provided, then
        a list of available commands is output instead.

        Run with the -m or --more flag for more details on each command.
        """
        if not query:
            await self._summary_screen(ctx)
        elif query.lower() in ("-m", "--more"):
            await self._new_dialog(ctx)
        else:
            result = await self.get_best_match(query, ctx)
            if result:
                # Unpack
                real_match, command = result
                await self._command_page(ctx, query, command, real_match)
            else:
                await ctx.send(f"No command found that matches `{query}`", delete_after=15)

    async def _new_dialog(self, ctx):
        embeds = []
        # Includes those that cannot be run.
        all_cmds = list(sorted(ctx.bot.commands, key=str))

        commands = []

        for potential_command in all_cmds:
            # noinspection PyUnresolvedReferences
            try:
                if await potential_command.can_run(ctx):
                    commands.append(potential_command)
            except Exception as ex:
                if self.logger.getEffectiveLevel() >= logging.DEBUG:
                    self.logger.exception(ex)
                continue

        items_per_page = 6

        # We only show 10 commands per page.
        for i in range(0, len(commands), items_per_page):
            embed_page = theme.generic_embed(ctx, title="All commands", avatar_injected=True)

            next_commands = commands[i : i + items_per_page]

            for command in next_commands:
                command: neko_commands.Command = command
                # Special space char
                name = command.name

                embed_page.add_field(
                    name=name,
                    # If we put a zero space char first, and follow with an
                    # EM QUAD, it won't strip the space.
                    value="\u200e\u2001" + (command.brief or "—"),
                    inline=False,
                )

            embeds.append(embed_page)

        pagination.EmbedNavigator(pages=embeds, ctx=ctx).start()

    async def _command_page(self, ctx, query, command, real_match):
        """
        Replies with info for the given command object.
        :param ctx: the context to reply to.
        :param query: the original query.
        :param command: the command to document.
        :param real_match: true if we had a perfect match, false if we fell
            back to fuzzy.
        """
        if isinstance(command, dpycommands.GroupMixin):
            _children = sorted(command.commands, key=lambda c: c.name)
            children = []

            for child in _children:
                try:
                    if await child.can_run(ctx):
                        children.append(child)
                except Exception as ex:
                    if self.logger.getEffectiveLevel() >= logging.DEBUG:
                        self.logger.exception(ex)
        else:
            children = []

        @pagination.embed_generator(max_chars=1024)
        def embed_generator(_, page, __):
            next_page = theme.generic_embed(
                ctx, title=f"Help for {ctx.bot.command_prefix}" f"{command.qualified_name}", avatar_injected=True
            )

            brief = command.brief
            examples = getattr(command, "examples", [])
            usage = f"{ctx.prefix}{command.qualified_name} {command.signature}"
            description = []
            cog = command.cog_name or ""
            module = ctx.bot.get_cog(cog)
            module = module.__module__ if module else "No cog!"

            parent = command.full_parent_name
            cooldown = getattr(command, "_buckets")

            if cooldown:
                cooldown = getattr(cooldown, "_cooldown")

            if not real_match:
                description.insert(0, f"Closest match for `{query}`")

            description.append(f"```asciidoc\n{usage}\n```\n")

            if brief:
                description.append(brief)
            next_page.description = "\n".join(description)

            next_page.add_field(name="Details", value=page, inline=False)

            if examples:
                examples = "\n".join(
                    f"- `{ctx.bot.command_prefix}{command.qualified_name} " f"{ex}`" for ex in examples
                )
                next_page.add_field(name="Examples", value=examples, inline=True)

            if cog and module and ctx.author.id == ctx.bot.owner_id:
                next_page.add_field(
                    name="Defined in", value=" ".join((module, cog)).strip().replace(" ", "."), inline=True
                )

            if children:
                children_str = ", ".join(f"`{child.name}`" for child in children)
                next_page.add_field(name="Child commands", value=children_str, inline=True)

            if parent:
                next_page.add_field(name="Parent", value=f"`{parent}`", inline=True)

            if cooldown:
                timeout = cooldown.per
                if timeout.is_integer():
                    timeout = int(timeout)

                next_page.add_field(
                    name="Cooldown policy",
                    value=(
                        f"{cooldown.type.name.title()}-scoped "
                        f"per {cooldown.rate} "
                        f'request{"s" if cooldown.rate - 1 else ""} '
                        f"with a timeout of {timeout} "
                        f'second{"s" if timeout - 1 else ""}'
                    ),
                    inline=True,
                )

            # pages[-1].set_thumbnail(url=ctx.bot.user.avatar_url)

            if hasattr(command.callback, "_probably_broken"):
                next_page.add_field(name="In active development", value="Expect voodoo-type behaviour!")

            return next_page

        full_doc = command.help if command.help else "No detailed description exists."
        full_doc = string.remove_single_lines(full_doc)

        nav = pagination.EmbedNavigatorFactory(embed_generator)
        nav.add_lines(*full_doc.split("\n"))

        nav.start(ctx)

    async def _summary_screen(self, ctx, show_aliases=False):
        """
        Replies with a list of all commands available.
        :param ctx: the context to reply to.
        """
        pages = []

        # Get commands this user can run, only.
        async def get_runnable_commands(mixin):
            cmds = []

            for command in mixin.all_commands.values():
                # If an error is raised by checking permissions for a command,
                # then just ignore that command.
                try:
                    if await command.can_run(ctx):
                        cmds.append(command)
                except Exception as ex:
                    if self.logger.getEffectiveLevel() <= logging.DEBUG:
                        self.logger.exception(ex)
            return cmds

        current_page = ""

        runnable_commands = await get_runnable_commands(ctx.bot)

        unordered_strings = {}
        for c in runnable_commands:
            if show_aliases:
                for alias in c.aliases:
                    unordered_strings[alias] = c
            unordered_strings[c.name] = c

        # Order here now we have the aliases, otherwise the aliases are
        # ignored from the order and it looks kinda dumb.
        keys = list(unordered_strings.keys())
        keys.sort()
        strings = collections.OrderedDict()
        for k in keys:
            strings[k] = unordered_strings[k]

        for i, (name, command) in enumerate(strings.items()):
            if i % 50 == 0 and i < len(strings) and current_page:
                current_page += " _continued..._"
                pages.append(current_page)
                current_page = ""

            if isinstance(command, dpycommands.GroupMixin):
                # This is a command group. Only show if we have at least one
                # available sub-command, though.
                if len(await get_runnable_commands(command)) > 0:
                    name = f"{name}..."

            if current_page:
                current_page += ", "
            current_page += f"`{name}`"

        if current_page:
            pages.append(current_page)

        def mk_page(body):
            """
            Makes a new page with the current body. This is a template
            for embeds to ensure a consistent layout if we can't fit the
            commands list on one page.
            """
            page = theme.generic_embed(ctx, title="All commands", description=body, avatar_injected=True)

            page.set_footer(
                text="Commands proceeded by ellipses signify " "command groups with sub-commands available."
            )
            page.add_field(
                name="Want more information?",
                value=f"Run `{ctx.bot.command_prefix}help <command>` " f"for more details on a specific command!",
                inline=False,
            )

            page.add_field(
                name="Want a more spammy embed?", value="Try running with the `-m` flag for added brief descriptions!"
            )
            page.set_thumbnail(url=ctx.bot.user.avatar_url)

            return page

        if len(pages) == 0:
            await ctx.send("You cannot run any commands here.")
        elif len(pages) == 1:
            await ctx.send(embed=mk_page(pages.pop()))
        else:
            page_embeds = []
            for page in pages:
                page_embeds.append(mk_page(page))

            fsm = pagination.EmbedNavigator(pages=page_embeds, ctx=ctx)
            await fsm.start()

    @property
    def all_commands(self) -> typing.FrozenSet[neko_commands.Command]:
        """
        Generates a set of all unique commands recursively.
        """
        return frozenset([command for command in self.bot.walk_commands()])

    def gen_qual_names(self, command: neko_commands.Command):
        aliases = [command.name, *command.aliases]

        if command.parent:
            parent_names = [*self.gen_qual_names(command.parent)]

            for parent_name in parent_names:
                for alias in aliases:
                    yield f"{parent_name} {alias}"
        else:
            yield from aliases

    @property
    def alias2command(self) -> typing.Dict:
        """
        Generates a mapping of all fully qualified command names and aliases
        to their respective command object.
        """
        mapping = {}

        for command in self.bot.walk_commands():
            for alias in self.gen_qual_names(command):
                mapping[alias] = command
        return mapping

    async def get_best_match(self, string: str, context) -> typing.Optional[typing.Tuple[bool, neko_commands.Command]]:
        """
        Attempts to get the best match for the given string. This will
        first attempt to resolve the string directly. If that fails, we will
        instead use fuzzy string matching. If no match above a threshold can
        be made, we give up.

        We take the context in order to only match commands we can actually
        run (permissions).

        The result is a 2-tuple of a boolean and a command. If the output
        is instead None, then nothing was found. The boolean of the tuple is
        true if we have an exact match, or false if it was a fuzzy match.
        """
        alias2command = self.alias2command

        if string in alias2command:
            command = alias2command[string]
            try:
                if context.author.id == context.bot.owner_id or await command.can_run(context):
                    return True, command
            except Exception:
                pass

        try:
            # Require a minimum of 60% match to qualify. The bot owner
            # gets to see all commands regardless of whether they are
            # accessible or not.
            if context.author.id == context.bot.owner_id:
                result = fuzzy_search.extract_best(
                    string, alias2command.keys(), scoring_algorithm=fuzzy_search.deep_ratio, min_score=60
                )

                if not result:
                    return None
                else:
                    guessed_name, score = result

                return score == 100, alias2command[guessed_name]
            else:
                score_it = fuzzy_search.extract(
                    string,
                    alias2command.keys(),
                    scoring_algorithm=fuzzy_search.deep_ratio,
                    min_score=60,
                    max_results=None,
                )

                for guessed_name, score in score_it:
                    can_run = False
                    next_command = alias2command[guessed_name]

                    try:
                        can_run = await next_command.can_run(context)
                        can_run = can_run and next_command.enabled
                    except Exception:
                        # Also means we cannot run
                        pass

                    if can_run:
                        return score == 100, next_command
        except KeyError:
            pass

        return None


def setup(bot):
    bot.add_cog(HelpCog(bot))
