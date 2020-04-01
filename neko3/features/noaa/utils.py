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
Utilities for reading and parsing URLs for images and GIFs from NOAA.
"""
import asyncio
import collections

import bs4

from neko3 import aggregates
from neko3 import fuzzy_search

##################
# Overall views. #
##################
OVERVIEW_BASE = "https://weather.gov"
OVERVIEW_MAP_US = "http://forecast.weather.gov/wwamap/png/US.png"
OVERVIEW_MAP_AK = "http://forecast.weather.gov/wwamap/png/ak.png"
OVERVIEW_MAP_HI = "http://weather.gov/wwamap/png/hi.png"

###################
# Tropical Storms #
###################
ATLANTIC_HURRICANE_FORECAST = "https://www.nhc.noaa.gov/xgtwo/two_atl_2d0.png"
EAST_PACIFIC_HURRICANE_FORECAST = "https://www.nhc.noaa.gov/xgtwo/two_pac_2d0.png"
CENTRAL_PACIFIC_HURRICANE_FORECAST = "http://www.prh.noaa.gov/cphc/xgtwo/two_cpac_2d0.png"

#########################
# Wide-views for RADAR. #
#########################
RADAR_US = "https://radar.weather.gov/Conus/Loop/NatLoop_Small.gif"
RADAR_FULL_US = "https://radar.weather.gov/Conus/Loop/NatLoop.gif"

# https://www.weather.gov/jetstream/gis, see "National and Regional Mosaics"
# Worked out there is some nice animated GIFs here: https://radar.weather.gov/Conus/Loop/

_wide_view_radars = dict(
    ALASKA="https://radar.weather.gov/Conus/Loop/alaskaLoop.gif",
    HAWAII="https://radar.weather.gov/Conus/Loop/hawaiiLoop.gif",
    GREAT_LAKES="https://radar.weather.gov/Conus/Loop/centgrtlakes_loop.gif",
    NORTH_EAST="https://radar.weather.gov/Conus/Loop/northeast_loop.gif",
    NORTH_ROCKIES="https://radar.weather.gov/Conus/Loop/northrockies_loop.gif",
    PACIFIC_NORTHWEST="https://radar.weather.gov/Conus/Loop/pacnorthwest_loop.gif",
    PACIFIC_SOUTHWEST="https://radar.weather.gov/Conus/Loop/pacsouthwest_loop.gif",
    SOUTHEAST="https://radar.weather.gov/Conus/Loop/southeast_loop.gif",
    SOUTH_MISSISSIPPI_VALLEY="https://radar.weather.gov/Conus/Loop/southmissvly_loop.gif",
    SOUTH_PLAINS="https://radar.weather.gov/Conus/Loop/southplains_loop.gif",
    SOUTH_ROCKIES="https://radar.weather.gov/Conus/Loop/southrockies_loop.gif",
    UPPER_MISSISSIPPI_VALLEY="https://radar.weather.gov/Conus/Loop/uppermissvly_loop.gif",
)

_URL_T = str


def get_wide_urls_radar_closest_match(query) -> (str, _URL_T):
    location, _ = fuzzy_search.extract_best(query, _wide_view_radars.keys(), scoring_algorithm=fuzzy_search.deep_ratio)

    friendly_location = location.replace("_", " ").title()
    return friendly_location, _wide_view_radars[location]


###########################
# RIDGE radar site views. #
###########################

_radar_map = aggregates.TwoWayDict(
    ABC="Bethel, AK",
    ABR="Aberdeen, SD",
    ABX="La Mesita Negra/Albuquerque, NM",
    ACG="Sitka, AK",
    AEC="Nome, AK",
    AHG="Anchorage/Kenei, AK",
    AIH="Middleton Islands, AK",
    AKC="King Salmon, AK",
    AKQ="Wakefield/Norfolk-Richmond, VA",
    AMA="Amarillo, TX",
    AMX="Miami, FL",
    APD="Fairbanks, AK",
    APX="Alpena/Gaylord, MI",
    ARX="LaCrosse, WI",
    ATX="Everett/Seattle-Tacoma, WA",
    BBX="Beale AFB, CA",
    BGM="Binghamton, NY",
    BHX="Eureka, CA",
    BIS="Bismarck, ND",
    BLX="Billings, MT",
    BMX="Shelby County AP/Birmingham, AL",
    BOX="Taunton/Boston, MA",
    BRO="Brownsville, TX",
    BUF="Buffalo, NY",
    BYX="Key West, FL",
    CAE="Columbia, SC",
    CBW="Caribou (Loring AFB), ME",
    CBX="Boise, ID",
    CCX="Moshannon St Forest/State College, PA",
    CLE="Cleveland, OH",
    CLX="Charleston, SC",
    CRP="Corpus Christi, TX",
    CXX="Burlington, VT",
    CYS="Cheyenne, WY",
    DAX="McClellan AFB/Sacremento, CA",
    DDC="Dodge City, KS",
    DFX="Bracketville/Laughlin AFB, TX",
    DGX="Jackson/Brandon, MS",
    DIX="Fort Dix, NJ/Philadelphia, PA",
    DLH="Duluth, MN",
    DMX="Acorn Valley/Des Moines, IA",
    DOX="Dover AFB, DE",
    DTX="Pontiac/Detroit, MI",
    DVN="Davenport/Quad Cities, IA",
    DYX="Moran/Dyess AFB, TX",
    EAX="Pleasant Hill/KC, MO",
    EMX="Tucson, AZ",
    ENX="East Berne/Albany, NY",
    EOX="Ft. Rucker, AL",
    EPZ="El Paso, TX",
    ESX="Las Vegas, NV",
    EVX="Red Bay/Eglin AFB, FL",
    EWX="New Braunfels AP/Austin-San Ant, TX",
    EYX="Edwards AFB, CA",
    FCX="Roanoke, VA",
    FDR="Frederick, OK",
    FDX="Field Village/Cannon AFB, NM",
    FFC="Peach Tree City/Atlanta, GA",
    FSD="Sioux Falls, SD",
    FSX="Flagstaff, AZ",
    FTG="Front Range AP/Denver, CO",
    FWS="Spinks AP/Dallas-Ft Worth, TX",
    GGW="Glasgow, MT",
    GJX="Grand Junction, CO",
    GLD="Goodland, KS",
    GRB="Green Bay, WI",
    GRK="Central Texas (Ft Hood), TX",
    GRR="Grand Rapids/Muskegon, MI",
    GSP="Greenville/Spartanburg (Greer), SC",
    GUA="Andersen AFB, Guam",
    GWX="Columbus AFB, MS",
    GYX="Gray/Portland, ME",
    HDX="Holloman AFB, NM",
    HGX="League City/Houston, TX",
    HKI="South Kauai, HI",
    HKM="Kohala, HI",
    HMO="Molokai, HI",
    HNX="Hanford AP/San Joaquin Valley, CA",
    HPX="Ft. Campbell, KY",
    HTX="N.E./Hytop, AL",
    HWA="South Hawaii, HI",
    ICT="Wichita, KS",
    ICX="Cedar City, UT",
    ILN="Wilmington/Cincinnati, OH",
    ILX="Central (Springfield), IL",
    IND="Indianapolis, IN",
    INX="Shreck Farm/Tulsa, OK",
    IWA="Williams AFB/Phoenix, AZ",
    IWX="Webster, IN",
    JAX="Jacksonville, FL",
    JGX="Robins AFB, GA",
    JKL="Jackson, KY",
    JUA="San Juan, PR",
    LBB="Lubbock, TX",
    LCH="Lake Charles, LA",
    LGX="Langley Hill, WA",
    LIX="Slidell AP/New Orleans, LA",
    LNX="North Platte, NE",
    LOT="Chicago, IL",
    LRX="Elko, NV",
    LSX="St Charles City/St Louis, MO",
    LTX="Shallotte/Wilmington, NC",
    LVX="Ft Knox Mil Res/Louisville, KY",
    LWX="Sterling, VA/Washington DC",
    LZK="Little Rock, AR",
    MAF="Midland/Odessa, TX",
    MAX="Medford, OR",
    MBX="Minot AFB, ND",
    MHX="Newport/Morehead City, NC",
    MKX="Sullivan Township/Milwaukee, WI",
    MLB="Melbourne, FL",
    MOB="Mobile, AL",
    MPX="Chanhassen Township/Minn-St.P, MN",
    MQT="Marquette, MI",
    MRX="Knoxville, TN",
    MSX="Pt Six Mtn/Missoula, MT",
    MTX="Promontory Pt/Salt Lake City, UT",
    MUX="Mt Umunhum/San Francisco, CA",
    MVX="Fargo, ND",
    MXX="Carrville/Maxwell AFB, AL",
    NKX="San Diego, CA",
    NQA="Millington NAS/Memphis, TN",
    OAX="Omaha, NE",
    OHX="Old Hickory Mt/Nashville, TN",
    OKX="Brookhaven/New York City, NY",
    OTX="Spokane, WA",
    PAH="Paducah, KY",
    PBZ="Coraopolis/Pittsburgh, PA",
    PDT="Pendleton, OR",
    POE="Ft Polk, LA",
    PUX="Pueblo, CO",
    RAX="Triple West AP/Raleigh-Durham, NC",
    RGX="Virginia Peak/Reno, NV",
    RIW="Riverton, WY",
    RLX="Charleston, WV",
    RTX="Portland, OR",
    SFX="Pocatello/Idaho falls, ID",
    SGF="Springfield, MO",
    SHV="Shreveport, LA",
    SJT="San Angelo, TX",
    SOX="Santa Ana Mountains/March AFB, CA",
    SRX="Western Arkansas/Ft. Smith, AR",
    TBW="Ruskin/Tampa Bay, FL",
    TFX="Great Falls, MT",
    TLH="Tallahassee, FL",
    TLX="Twin Lakes/Oklahoma City, OK",
    TWX="Wabaunsee County/Topeka, KS",
    TYX="Ft Drum AFB/Montague, NY",
    UDX="Rapid City, SD",
    UEX="Hastings, NE",
    VAX="Moody AFB, GA",
    VBX="Vandenberg AFB, CA",
    VNX="Vance AFB, OK",
    VTX="Sulphur Mtn/Los Angeles, CA",
    VWX="Evansville, IN",
    YUX="Yuma, AZ",
)

_RadarCodeT = str
_RadarSiteT = str


def _best_radar_match(query) -> (_RadarCodeT, _RadarSiteT):
    upper = query.upper()
    if upper in _radar_map.keys():
        return upper, _radar_map[upper]
    else:
        radar_code, radar_code_score = fuzzy_search.extract_best(
            query, choices=_radar_map.keys(), scoring_algorithm=fuzzy_search.deep_ratio
        )
        radar_loc, radar_loc_score = fuzzy_search.extract_best(
            query, _radar_map.values(), scoring_algorithm=fuzzy_search.deep_ratio
        )

        if radar_loc_score > radar_code_score:
            return reversed(_radar_map)[radar_loc], radar_loc
        else:
            return radar_code, _radar_map[radar_code]


_RIDGE_WEB_PAGE_BASE = "https://radar.weather.gov/radar.php?rid={}"
# N0R
_RIDGE_BASE_REFLECTIVITY_124NM_BASE = "https://radar.weather.gov/lite/N0R/{}_loop.gif"
# N0S
_RIDGE_STORM_RELATIVE_MOTION_BASE = "https://radar.weather.gov/lite/N0S/{}_loop.gif"
# N1P
_RIDGE_ONE_HOUR_PRECIPITATION_BASE = "https://radar.weather.gov/lite/N1P/{}_loop.gif"
# NCR
_RIDGE_COMPOSITE_REFLECTIVITY_BASE = "https://radar.weather.gov/lite/NCR/{}_loop.gif"
# NTP
_RIDGE_STORM_TOTAL_PRECIPITATION_BASE = "https://radar.weather.gov/lite/NTP/{}_loop.gif"
# N0Z
_RIDGE_BASE_REFLECTIVITY_248NMI_BASE = "https://radar.weather.gov/lite/N0Z/{}_loop.gif"

_TEXT_FORECAST_BASE = (
    "https://forecast.weather.gov/product.php?site=NWS&issuedby={" "}&product=HWO&format=txt&version=1&glossary=0"
)

_RIDGEMap = collections.namedtuple(
    "RIDGEMap",
    [
        "radar_site",
        "radar_location",
        "web_page",
        "text_forecast",
        "base_reflectivity_124nm",
        "storm_relative_motion",
        "one_hour_precipitation",
        "composite_reflectivity",
        "storm_total_precipitation",
        "base_reflectivity_248nmi",
    ],
)


async def generate_ridge_images_closest_match(session, query, *_) -> _RIDGEMap:
    """
    Generate a set of RIDGE URLs for the given query. Uses fuzzy matching.

    Also downloads and extracts the full text forecast.

    https://www.weather.gov/jetstream/ridge_download

    If TINYURL is True, gifs are passed through TinyURL. This is done for Discord
    to prevent the media server from caching these URLs.
    """
    site, location = _best_radar_match(query)

    async def soup_forecast():
        async with session.get(_TEXT_FORECAST_BASE.format(site)) as resp:
            resp.raise_for_status()
            html = await resp.text()
            soup = bs4.BeautifulSoup(html, features="html.parser")
            tag = soup.find(name="pre", attrs={"class": "glossaryProduct"})
            try:
                return tag.text
            except AttributeError:
                return None

    async def maybe_shortlink(url, argument):
        return url.format(argument)

    urls = await asyncio.gather(
        *[
            soup_forecast(),
            maybe_shortlink(_RIDGE_BASE_REFLECTIVITY_124NM_BASE, site),
            maybe_shortlink(_RIDGE_STORM_RELATIVE_MOTION_BASE, site),
            maybe_shortlink(_RIDGE_ONE_HOUR_PRECIPITATION_BASE, site),
            maybe_shortlink(_RIDGE_COMPOSITE_REFLECTIVITY_BASE, site),
            maybe_shortlink(_RIDGE_STORM_TOTAL_PRECIPITATION_BASE, site),
            maybe_shortlink(_RIDGE_BASE_REFLECTIVITY_248NMI_BASE, site),
        ]
    )

    return _RIDGEMap(site, location, _RIDGE_WEB_PAGE_BASE.format(site), *urls)
