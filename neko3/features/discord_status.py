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
Discord service status.

Ported from Nekozilla V1
"""
import asyncio
import datetime
import re
import typing

import aiohttp

import neko3.cog
from neko3 import embeds
from neko3 import neko_commands
from neko3 import pagination

endpoint_base = "https://status.discordapp.com/api"
api_version = "v2"

# Max fields per page on short pages
max_fields = 4


class ListMix(list):
    """Quicker than replacing a bunch of internal calls. I know this is inefficient anyway."""

    def __iadd__(self, other):
        self.append(other)
        return self


def get_endpoint(page_name):
    """Produces the endpoint URL."""
    return f"{endpoint_base}/{api_version}/{page_name}"


def get_impact_color(impact, is_global=False):
    return {"none": 0x00FF00 if is_global else 0x0, "minor": 0xFF0000, "major": 0xFFA500, "critical": 0xFF0000}.get(
        impact.lower(), 0x0
    )


def find_highest_impact(entries):
    print(entries)

    for state in ("critical", "major", "minor", "none"):
        for entry in entries:
            if entry["impact"].lower() == state:
                return state.title()
    return "none"
    
    
def make_incident_update_body(recent_update):
    updated_at = recent_update.get("updated at")
    created_at = recent_update.get("created at")
    body = recent_update.get("body")
    
    ru_message = "\n_**" + recent_update.get("status").title() + "**_"

    if updated_at:
        ru_message += f" - Last updated at {friendly_date(updated_at)}"
    elif created_at:
        ru_message += f" - Created at {friendly_date(created_at)}"

    ru_message += f"\n{body}\n"
    
    return "\n".join(ru_message.split("\n"))


def make_incident_body(incident):
    created = friendly_date(incident["created at"])
    updated = incident.get("updated at")
    updated = friendly_date(updated) if updated else "N/A"
    monitoring = incident.get("monitoring at")
    monitoring = friendly_date(monitoring) if monitoring else "N/A"
    url = incident.get("shortlink", "https://status.discordapp.com")
    affects = ", ".join(component["name"] for component in incident.get("components")) or "nothing"

    recent_updates = incident.get("updates")

    ru_message = ""
    if recent_updates:
        ru_message = f"Updates:\n"
        for recent_update in recent_updates:
            ru_message += make_incident_update_body(recent_update)
        
    return (
        f"_**[{incident['name']}]({url})**_\n\n"
        f"Affects: `{affects}`\n"
        f"Status: `{incident['status']}`\n"
        f"Created: `{created}`\n"
        f"Updated: `{updated}`\n"
        f"Monitoring: `{monitoring}`\n"
        f"{ru_message if recent_updates else 'No updates yet.'}"
    )


def parse_timestamp(timestamp):
    """
    Discord use a timestamp that is not compatible with Python by
    default, which is kind of annoying.

    Expected format: YYYY-mm-ddTHH:MM:SS.sss(sss)?[+-]hh:mm

    :param timestamp: timestamp to parse.
    :return: datetime object.
    """

    if timestamp is None:
        return None

    # Remove the periods, T and colons.
    timestamp = re.sub(r"[:.T]", "", timestamp, flags=re.I)

    # extract the date part and time part.
    if "+" in timestamp:
        dt, tz = timestamp.rsplit("+", maxsplit=1)
        tz = "+" + tz
    else:
        dt, tz = timestamp.rsplit("-", maxsplit=1)
        tz = "-" + tz

    # Remove hyphens from date (we didn't want to mess up the timezone earlier)
    dt = dt.replace("-", "")

    expected_dt_len = len("YYYYmmddHHMMSSssssss")
    # Append zeros onto the end to make it in microseconds.
    dt = dt + ("0" * (expected_dt_len - len(dt)))

    timestamp = dt + tz
    dt_obj = datetime.datetime.strptime(timestamp, "%Y%m%d%H%M%S%f%z")
    return dt_obj.astimezone(datetime.timezone.utc)


def friendly_date(value: datetime.datetime):
    """Creates a friendly date format for the given datetime."""

    if value is None:
        return "N/A"

    return value.strftime("%d %B %Y at %H:%M %Z")


class DiscordServiceStatusCog(neko3.cog.CogBase):
    """
    Holds the service status command.
    """

    @neko_commands.command(name="discord", aliases=["discordstatus"], brief="Check if Discord is down (again)")
    async def discord_status_command(self, ctx):
        """
        Gets a list of all Discord systems, and their service
        status.
        """

        async with ctx.message.channel.typing():
            stat_res, comp_res, inc_res, sms_res = await asyncio.gather(
                self._get(get_endpoint("summary.json")),
                self._get(get_endpoint("components.json")),
                self._get(get_endpoint("incidents.json")),
                self._get(get_endpoint("scheduled-maintenances.json")),
            )

            status, components, incidents, sms = await asyncio.gather(
                self.get_status(stat_res),
                self.get_components(comp_res),
                self.get_incidents(inc_res),
                self.get_scheduled_maintenances(sms_res),
            )
            
            footer_text = status["indicator"]

            @pagination.embed_generator(max_chars=1100)
            def factory(_, page, __):
                if not incidents["unresolved"]:
                    color = status["color"]
                else:
                    color = get_impact_color(find_highest_impact(incidents["unresolved"]))

                e = embeds.Embed(
                    colour=color, title="API Status for discordapp.com", description=page, url=status["url"]
                )
                if footer_text != "None":
                    e.set_footer(text=footer_text[:2000])
                return e

            nav = pagination.EmbedNavigatorFactory(factory=factory, max_lines=25)

            # Make the front page, if needed.
            headline = status["indicator"]
            if str(headline) != "None":
                nav.add_block(f"**{headline}**\n")
                nav.add_block(f'{status["description"]}\n\n' f'Last updated: {friendly_date(status["updated_at"])}.')
                nav.add_page_break()

            if incidents["unresolved"]:
                first = incidents["unresolved"][0]
                name = first["name"]
                body = make_incident_body(first)

                nav.add_block(f"\n**{name}**\n{body}\n")
                nav.add_page_break()
            
            """
            PAGE 3
            ======
            
            Incidents.
            """

            if incidents["unresolved"]:
                nav.add_block("**__UNRESOLVED INCIDENTS__**\n")
                
                incident = incidents["unresolved"][0]

                name = f'**{incident["name"]}**'
                desc = make_incident_body(incident)

                nav.add_block(name + "\n" + desc.strip())

                for incident in incidents["unresolved"][1:3]:
                    body = make_incident_body(incident)
                    name = incident["name"]
    
                    body = name + "\n" + body
    
                    nav.add_block(body.strip())
    
                nav.add_page_break()

            nav.add_block("**__RESOLVED INCIDENTS__**\n")
            
            # Add six most recent.
            for incident in incidents["resolved"][:6]:
                body = make_incident_body(incident)
                nav.add_block(body)
                nav.add_line()
                
                
            nav.add_page_break()
        
            nav.add_block("**__PRIMARY COMPONENTS__**\n")

            for i, component in enumerate(components["showcase"], start=1):
                if i and not (i % max_fields):
                    nav.add_page_break()
                
                title = component.pop("name")
                desc = []
                for k, v in component.items():
                    line = f"**{k}**: "
                    if isinstance(v, datetime.datetime):
                        line += friendly_date(v)
                    else:
                        line += str(v)
                    desc.append(line)
                desc = "\n".join(desc)
                nav.add_block(f"**{title}**\n{desc}\n")

            nav.add_page_break()

            """
            PAGE 5
            ======

            Non showcase components
            """
            nav.add_block("**__OTHER COMPONENTS__**\n")

            for i, component in enumerate(components["rest"], start=1):
                if i and not (i % max_fields):
                    nav.add_page_break()
                
                title = component.pop("name")
                desc = []
                for k, v in component.items():
                    if k == "components":
                        continue

                    line = f"{k}: "
                    if isinstance(v, datetime.datetime):
                        line += friendly_date(v)
                    else:
                        line += str(v)

                    desc.append(line)

                nav.add_block(f"\n**{title}**\n" + "\n".join(desc))

            nav.start(ctx)

    @classmethod
    async def _get(cls, *args, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.get(*args, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json()

    @staticmethod
    async def get_status(res) -> typing.Dict[str, typing.Any]:
        """
        Gets the short overall status of Discord.

        :param res: the http response.
        :return: a map of:
            description - str, None
            color - int
            indicator - str
            updated_at - datetime
            url - str
        """
        updated_at = res["page"]["updated_at"]
        updated_at = parse_timestamp(updated_at)

        return {
            "description": res["status"]["description"],
            "color": get_impact_color(res["status"]["indicator"], True),
            "indicator": res["status"]["indicator"].title(),
            "updated_at": updated_at,
            "url": res["page"]["url"],
        }

    @staticmethod
    async def get_components(res, hide_un_degraded=True) -> typing.Dict[str, typing.List]:
        """
        Gets the status of individual components of Discord.

        :param res: the http response.
        :param hide_un_degraded: defaults to true. If true, we respect the
               API's intent to hide any component marked true under
               "only_show_if_degraded" unless the component is actually
               degraded.
        :return: a dict containing two lists: 'showcase' and 'rest'.
                Both lists contain components, with fields:

                status - str
                name - str
                created_at - datetime
                updated_at - datetime
                description - str, None
        """
        # Anything that is not set to "showcase" belongs in the
        # rest list instead.
        showcase_result = []
        rest_result = []

        components: list = res["components"]
        for component in components:
            comp_dict = {}

            for k, v in component.items():
                # Skip these keys.
                if k in ("id", "page_id", "position", "group", "only_show_if_degraded", "showcase", "group_id"):
                    continue
                elif v is None:
                    continue

                friendly_key = k.replace("_", " ")

                # If a date/time
                if k in ("created_at", "updated_at"):
                    comp_dict[friendly_key] = parse_timestamp(v)
                elif k == "status":
                    # This is always formatted with underscores (enum really)
                    comp_dict[friendly_key] = v.replace("_", " ")
                else:
                    comp_dict[friendly_key] = v

            # Determine whether to skip the only-show-if-degraded element
            # if it is flagged as such.
            show_always = not component["only_show_if_degraded"]
            if not show_always:
                is_degraded = component["status"] != "operational"
                should_hide = not show_always and is_degraded
                if hide_un_degraded and should_hide:
                    continue

            if component["showcase"]:
                showcase_result.append(comp_dict)
            else:
                rest_result.append(comp_dict)

        return {"showcase": showcase_result, "rest": rest_result}

    @classmethod
    async def get_incidents(cls, res) -> typing.Dict[str, typing.List]:
        """
        Gets a dict containing two keys: 'resolved' and 'unresolved'.

        These contain incidents and incident updates.

        Due to the quantity of information this returns, we only get the
        first 5, resolved. All unresolved are returned.

        :param res: the http response.
        """
        max_resolved = 5

        res = res["incidents"]

        unresolved = []
        resolved = []

        for inc in res:
            if inc["status"] in ("investigating", "identified", "monitoring"):
                target = unresolved
            elif len(resolved) < max_resolved:
                target = resolved
            else:
                continue

            incident = {}

            for k, v in inc.items():
                if k in ("id", "page_id") or v is None:
                    continue

                friendly_key = k.replace("_", " ")

                if k in ("updated_at", "created_at", "monitoring_at"):
                    incident[friendly_key] = parse_timestamp(v)
                elif k == "incident_updates":
                    incident["updates"] = cls.__parse_incident_updates(v)
                elif k in ("impact", "status"):
                    incident[friendly_key] = v.replace("_", " ")

                else:
                    incident[friendly_key] = v

            target.append(incident)
        return {"resolved": resolved, "unresolved": unresolved}

    @staticmethod
    def __parse_incident_updates(v):
        # Parse incident updates.
        updates = []

        if v is None:
            return updates

        for up in v:
            update = {}
            for up_k, up_v in up.items():
                up_f_k = up_k.replace("_", " ")

                # Ignore custom_tweet and affected_components,
                # as we do not have any info on how these are
                # formatted...
                if (
                    up_k
                    in (
                        "id",
                        "incident_id",
                        "display_at",
                        "custom_tweet",
                        "affected_components",
                        "deliver_notifications",
                    )
                    or up_v is None
                ):
                    continue
                elif up_k in ("created_at", "updated_at"):
                    if up_v is None:
                        continue
                    else:
                        update[up_f_k] = parse_timestamp(up_v)
                elif up_k == "status":
                    update[up_f_k] = up_v.replace("_", " ")
                else:
                    update[up_f_k] = up_v

            updates.append(update)
        return updates

    @staticmethod
    async def __get_active_and_scheduled_maintenances(res):
        """
        We do not care about maintenances that are done with, but this contains
        a lot of irrelevant information, so I guess we should skip what we
        don't need now.

        :param res: the response to use.
        """
        res = res["scheduled_maintenances"]

        return [r for r in res if r.get("status", None) != "completed"]
        # test: return res

    @classmethod
    async def get_scheduled_maintenances(cls, res) -> typing.List[typing.Dict]:
        """
        Gets a list of active and scheduled maintenance events.

        :param res: the response to use.
        """
        in_events = await cls.__get_active_and_scheduled_maintenances(res)

        out_events = []

        for event in in_events:
            event_obj = {}

            for k, v in event.items():
                if k in ("id", "page_id", "shortlink") or v is None:
                    continue

                friendly_key = k.replace("_", " ")

                if k in ("created_at", "monitoring_at", "scheduled_for", "scheduled_until", "updated_at"):
                    event_obj[friendly_key] = parse_timestamp(v)
                elif k == "incident_updates":
                    event_obj["updates"] = cls.__parse_incident_updates(v)
                elif k in ("status", "impact"):
                    event_obj[friendly_key] = v.replace("_", " ")
                else:
                    event_obj[friendly_key] = v
            out_events.append(event_obj)

        return out_events


def setup(bot):
    bot.add_cog(DiscordServiceStatusCog(bot))
