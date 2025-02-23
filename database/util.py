"""
Contains helper functions which will be used in more than one service
"""
import operator as op
import re
from typing import List
import ossapi
import sqlalchemy.sql.operators

modes = ['osu', 'taiko', 'fruits', 'mania']

# Given a mode, return the corresponding table
def get_mode_table(mode: str or int):
    from models import OsuScore, TaikoScore, CatchScore, ManiaScore
    match mode:
        case 'osu' | 0:
            return OsuScore
        case 'taiko' | 1:
            return TaikoScore
        case 'fruits' | 2:
            return CatchScore
        case 'mania' | 3:
            return ManiaScore

# Parses the mod list from the Ossapi score object
def parse_modlist(modlist: List[ossapi.models.NonLegacyMod]):
    if not modlist:
        return '', None
    string = ''
    for mod in modlist:
        string += '%s ' % mod.acronym
    string = string.strip()

    newmodlist = []
    for mod in modlist:
        if mod.settings is None:
            continue
        newmodlist.append((mod.acronym, mod.settings))
    if len(newmodlist) == 0:
        return string, None
    return string, newmodlist

# Given a mode, return the correct list order
def mod_order(mode: str or int):
    match mode:
        case 'osu' | 0:
            return ['EZ', 'NF', 'HT', 'DC', 'HR', 'SD', 'PF', 'DT', 'NC', 'HD', 'FL', 'BL', 'ST', 'AC', 'TP', 'DA', 'CL', 'RD', 'MR', 'AL', 'SG', 'AT', 'CN', 'RX', 'AP', 'SO', 'TR', 'WG', 'SI', 'GR', 'DF', 'WU', 'WD', 'TC', 'BR', 'AD', 'MU', 'NS', 'MG', 'RP', 'AS', 'FR', 'BU', 'SY', 'DP', 'BM', 'TD', 'SV2']
        case 'taiko' | 1:
            return ['EZ', 'NF', 'HT', 'DC', 'HR', 'SD', 'PF', 'DT', 'NC', 'HD', 'FL', 'AC', 'RD', 'DA', 'CL', 'SW', 'SG', 'CS', 'AT', 'CN', 'RX', 'WU', 'WD', 'MU', 'AS', 'SV2']
        case 'fruits' | 2:
            return ['EZ', 'NF', 'HT', 'DC', 'HR', 'SD', 'PF', 'DT', 'NC', 'HD', 'FL', 'AC', 'DA', 'CL', 'MR', 'AT', 'CN', 'RX', 'WU', 'WD', 'FF', 'MU', 'NS', 'SV2']
        case 'mania' | 3:
            return ['EZ', 'NF', 'HT', 'DC', 'NR', 'HR', 'SD', 'PF', 'DT', 'NC', 'FI', 'HD', 'CO', 'FL', 'AC', 'RD', 'DS', 'MR', 'DA', 'CL', 'IN', 'CS', 'HO', '1K', '2K', '3K', '4K', '5K', '6K', '7K', '8K', '9K', '10K', 'AT', 'CN', 'WU', 'WD', 'MU', 'AS', 'SV2']
    '''
    with open('mods.json') as f:
        import json
        data = json.load(f)

        if isinstance(mode, str):
            mod_data = list(filter(lambda x: x['Name'] == mode, data))[0]['Mods']
        else:
            mod_data = list(filter(lambda x: x['RulesetID'] == mode, data))[0]['Mods']

        mod_order = [x['Acronym'] for x in mod_data]

        return mod_order
    '''

# Given a mode and a list of mods, return the sorted list
def sort_mods(mode: str or int, mod_list: List[str]):
    order = mod_order(mode)

    d = {v: i for i, v in enumerate(order)}
    r = sorted(mod_list, key=lambda v: d[v])

    return r

def parse_user_filters(mode: str or int, user_ids: List[int] or int):

    if not user_ids:
        return ()

    if isinstance(user_ids, int):
        user_ids = [user_ids]

    table = get_mode_table(mode)
    return (table.user_id.in_(user_ids), )

def parse_score_filters(mode: str or int, filters: str):
    """
    Builds a query object based on a bunch of filters as a string
    The list of filters available:
    stable_score, lazer_score, classic_score, maxcombo, rank, count50, count100, count300, countmiss, perfect,
    enabled_mods, enabled_mods_settings, date, pp, replay

    An example would be 'date<2010-12-12 pp>100 replay=1'
    This should return a 3-tuple (OsuScore.date<'2010-12-12', OsuScore.pp>100, OsuScore.replay==1)

    :param mode     the game mode
    :param filters  the filters as a string
    :return:
    """

    if filters is None:
        return ()

    import re

    table = get_mode_table(mode)
    filters = filters.lower()
    all_filters = re.split(r'\s', filters)
    all_filters = [x.strip() for x in all_filters]
    all_filters = [re.split('([<>=!/]+)+', x) for x in all_filters]

    op_map = {
    "=": op.eq,
    "!=": op.ne,
    ">": op.gt,
    "<": op.lt,
    "<=": op.le,
    ">=": op.ge,
    "/": op.contains
    }

    # stable_score, lazer_score, classic_score, maxcombo, rank, count50, count100, count300, countmiss, perfect,
    #     enabled_mods, enabled_mods_settings, date, pp, replay
    field_map = {
        "user_id": table.user_id,
        "date": table.date,
        "accuracy": table.accuracy,
        "pp": table.pp,
        "rank": table.rank,
        "perfect": table.perfect,
        "max_combo": table.maxcombo,
        "replay": table.replay,
        "stable_score": table.stable_score,
        "lazer_score": table.lazer_score,
        "classic_score": table.classic_score,
        "count_50": table.count50,
        "count_100": table.count100,
        "count_300": table.count300,
        "count_miss": table.countmiss,
    }

    r = []
    for f in all_filters:
        if f[1] == "/":
            # Match the regex
            f[2] = f[2].upper()
            pattern = r'(XH|SH|X|S|A|B|C|D)'
            a = re.findall(pattern, f[2])
            r.append(field_map[f[0]].in_(a))
            continue

        r.append(op_map[f[1]](field_map[f[0]], f[2]))
    return tuple(r)

def parse_mod_filters(mode: str or int, modstring: str):
    """

    :param mode:        the mode
    :param modstring:   A string representing mods. +mods, -mods, or !mods
    :return:

    NOTES:
    NM scores in lazer have no mods.    Looks like ''
    NM scores in classic have CL        Looks like 'CL'
    """
    from sqlalchemy import not_

    if modstring is None:
        return ()

    modstring = modstring.upper()
    modstring = "".join(modstring.split())
    table = get_mode_table(mode)

    # Exact
    if modstring[0] == '!':
        # Arrange mods in the right order.
        # ex: ['HD', 'DT'] -> ['HD', 'DT'] and ['DT', 'HD'] -> ['HD', 'DT']
        #return (op.eq(table.enabled_mods, mods),)
        mods = modstring[1:]
        mods = [mods[i:i + 2] for i in range(0, len(mods), 2)]
        mods = sort_mods(mode, mods)
        return (op.eq(table.enabled_mods, ' '.join(mods)),)

    # Find + and -
    matches = re.findall(r'([\-\+]\w+)', modstring)
    filters = []
    for match in matches:
        # Including
        if match[0] == '+':
            mods = match[1:]
            mods = [mods[i:i + 2] for i in range(0, len(mods), 2)]
            for mod in mods:
                filters.append(table.enabled_mods.icontains(mod))
        # Excluding
        else:
            mods = match[1:]
            mods = [mods[i:i + 2] for i in range(0, len(mods), 2)]
            for mod in mods:
                filters.append(not_(table.enabled_mods.icontains(mod)))

    return filters

def parse_beatmapset_filters(filters: str):

    if filters is None:
        return ()

    from database.models import BeatmapSet

    op_map = {
        "=": op.eq,
        "!=": op.ne,
        ">": op.gt,
        "<": op.lt,
        "<=": op.le,
        ">=": op.ge,
        "/": sqlalchemy.sql.operators.contains_op # check this.
    }

    field_map = {
        "beatmapset_id": BeatmapSet.beatmapset_id,
        "owner_id": BeatmapSet.owner_id,
        "artist": BeatmapSet.artist,
        "artist_unicode": BeatmapSet.artist_unicode,
        "title": BeatmapSet.title,
        "title_unicode": BeatmapSet.title_unicode,
        "tags": BeatmapSet.tags,
        "bpm": BeatmapSet.bpm,
        "versions_available": BeatmapSet.versions_available,
        "approved_date": BeatmapSet.approved_date,
        "submit_date": BeatmapSet.submit_date,
        "last_update": BeatmapSet.last_update,
        "genre_id": BeatmapSet.genre_id,
        "language_id": BeatmapSet.language_id,
        "nsfw": BeatmapSet.nsfw,
    }

    filters = filters.lower()
    all_filters = re.split(r'\s', filters)
    all_filters = [x.strip() for x in all_filters]
    all_filters = [re.split('([<>=!#/]+)+', x) for x in all_filters]

    r = []
    for f in all_filters:
        if f[1] == "/":
            # Parse the list here. values are comma separated
            tags = f[2].split(',')
            for tag in tags:
                r.append(op_map[f[1]](field_map[f[0]], tag))
            continue
        r.append(op_map[f[1]](field_map[f[0]], f[2]))
    return tuple(r)

def parse_beatmap_filters(filters: str):

    if filters is None:
        return ()

    from database.models import Beatmap

    op_map = {
        "=": op.eq,
        "!=": op.ne,
        ">": op.gt,
        "<": op.lt,
        "<=": op.le,
        ">=": op.ge,
    }

    field_map = {
        "beatmap_id": Beatmap.beatmap_id,
        "beatmapset_id": Beatmap.beatmapset_id,
        "mapper_id": Beatmap.mapper_id,
        "total_length": Beatmap.total_length,
        "hit_length": Beatmap.hit_length,
        "count_total": Beatmap.count_total,
        "count_normal": Beatmap.count_normal,
        "count_slider": Beatmap.count_slider,
        "count_spinner": Beatmap.count_spinner,
        "hp": Beatmap.hp,
        "cs": Beatmap.cs,
        "od": Beatmap.od,
        "ar": Beatmap.ar,
        "status": Beatmap.approved,
        "stars": Beatmap.stars,
        "bpm": Beatmap.bpm,
        "max_combo": Beatmap.max_combo,
    }

    filters = filters.lower()
    all_filters = re.split(r'\s', filters)
    all_filters = [x.strip() for x in all_filters]
    all_filters = [re.split('([<>=!]+)+', x) for x in all_filters]

    r = []
    for f in all_filters:
        r.append(op_map[f[1]](field_map[f[0]], f[2]))
    return tuple(r)

if __name__ == '__main__':
    from sqlalchemy.dialects import mysql
    a = parse_beatmap_filters("count_total<1900 ar<=8 stars>5")
    a = parse_beatmapset_filters("tags/miku,hatsune,goth language_id=2")

    from sqlalchemy import select
    from database.models import BeatmapSet, OsuScore

    stmt = select(BeatmapSet).filter(*a)
    print(str(stmt))
    print(stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))

    b = parse_score_filters('osu', 'rank/ASXBCD')
    c = parse_score_filters('osu', 'rank/A,s,X,B,c,D')

    stmt = select(OsuScore).filter(*b)
    print(str(stmt))
    print(stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))

    stmt = select(BeatmapSet).filter(*c)
    print(str(stmt))
    print(stmt.compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}))