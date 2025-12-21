# =============================================================================
# author: mgrossi
# date:   1 December 2025
#
# This script creates a United States Catholic liturgical calendar based around
# the date of Easter passed on execution, formatted `YYYY-DD-MM`. The calendar
# year is automatically taken to be `YYYY` from Easter; Advent and Christmas
# are automatically taken from the previous calendar year. The most common
# prioritization rules are implemented; however, some nuanced exceptions may
# not yet be accounted for. Adjustments to the script will be made as such
# nuances are discovered. The liturgical calendar is written to the current
# working directory as a CSV file named `YYYY-yearX-liturgical-calendar.csv`
# by default, where "YYYY" is the calendar year of Easter and "X" is the
# liturgical cycle ("A", "B", or "C") for the given year, unless a custom file
# name with directory path is passed to using a `-o, --outfile` flag.
#
# This script was verified against the official liturgical calendar for 2025
# (Year A) from the United States Council of Catholic Bishops and found online
# at https://bible.usccb.org/readings/calendar as of December 2025.
#
# =============================================================================

# To execute in terminal:
# python litcalendar.py --easter 2026-04-05

# =============================================================================
# Package dependencies

from datetime import datetime, timedelta
from titlecase import titlecase
from num2words import num2words
import pandas as pd
import numpy as np
import calendar
import argparse
import os

# =============================================================================
# Functions

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Function control parameters.',
        prog='liturgical-calendar',
        usage='%(prog)s [arguments]')
    parser.add_argument('--easter', metavar='easter', type=str,
                        help='Date of Easter formatted `YYYY-MM-DD`')
    parser.add_argument('-a', '--ascension_thursday', action='store_true',
                        help='Declare that Ascension is celebrated on Ascension Thursday rather than being transferred to the Seventh Sunday of Easter.')
    parser.add_argument('-o', '--outfile', nargs='?', type=str,
                        const='arg_was_not_given',
                        help='Name and directory of csv file to write')
    return parser.parse_args()

def lityear(year):
    """Return the liturgical cycle for year `year`"""
    # Pick a starting year for cycle
    A, B, C = 2020, 2021, 2022
    # Array to index
    years = np.array(['A', 'B', 'C'])
    # Subtract the starting years from `year` and divide by 3
    ind = (year-np.array([A, B, C]))%3==0
    # Return the cycle year that is evenly divisible by 3
    return years[ind][0][0]

def previous_sundays(from_date, n=1, end=None, season=None):
    """Return the `n` Sundays prior to `from_date`, not counting `from_date` if
    `from_date` itself is a Sunday, and optionally include a week number in
    `season`.
    
    Arguments
    ---------
    `from_date` : str or datetime object
        Date from which to find Sundays. If str, must be of the format 
        `YYYY-mm-dd`.
    `n` : int
        Number of previous Sundays to return
    `end` : int
        Used when `season` is passed, specifies the number of the final week in
        the given season.
    `season` : str
        Optional season for which to provide numbered weeks. See `Returns` for
        an example.
    
    Returns
    -------
        List of `n` strings or datetime objects, depending on type(from_date).
        If `season` is passed, each element in the list will itself be a list
        including the date and a numbered weekend in `season`. For example:
        [['2025-11-30', 'advent01']]
    """
    # Convert to datetime if `from_date` is a string
    if isinstance(from_date, str):
        start = datetime.strptime(from_date, "%Y-%m-%d")
    else:
        start = from_date
    # Calculate the previous `n` Sundays
    sundays = [start]
    for i in range(n, 0, -1):
        previous_sunday = sundays[-1] - timedelta(days=sundays[-1].weekday()+1)
        sundays.append(previous_sunday)
    # If a string is passed, return string(s)
    if isinstance(from_date, str):
        sundays = [datetime.strftime(i, "%Y-%m-%d") for i in sundays]
    # If a season is passed, return a list that includes the numbered week of
    # the season.
    if end is None:
        end = n
    if season is not None:
        sundays = [[d, f'{season}{str(i).zfill(2)}'] \
                   for d, i in zip(sundays, range(end+1, 0, -1))]
    # Reverse the list for chronological order
    sundays.reverse()
    return sundays[:-1]

def next_sundays(from_date, n=1, start=1, season=None):
    """Return the `n` Sundays after `from_date`, not counting `from_date` if
    `from_date` itself is a Sunday, and optionally include a week number in
    `season`.
    
    Arguments
    ---------
    `from_date` : str or datetime object
        Date from which to find Sundays. If str, must be of the format 
        `YYYY-mm-dd`.
    `n` : int
        Number of next Sundays to return
    `start` : int
        Used when `season` is passed, specifies the number of the first week in
        the given season.
    `season` : str
        Optional season for which to provide numbered weeks. See `Returns` for
        an example.
    
    Returns
    -------
        List of `n` strings or datetime objects, depending on type(from_date).
        If `season` is passed, each element in the list will itself be a list
        including the date and a numbered weekend in `season`. For example:
        [['2025-11-30', 'advent01']]
    """
    # Convert to datetime if `from_date` is a string
    if isinstance(from_date, str):
        start_date = datetime.strptime(from_date, "%Y-%m-%d").date()
    else:
        start_date = from_date
    sundays = []
    # Find the first Sunday after the start date
    days_ahead = 6 - start_date.weekday()  # 6 is Sunday
    if days_ahead == 0:  # If today is Sunday, get the next one
        days_ahead += 7
    first_sunday = start_date + timedelta(days=days_ahead)
    # Collect the next n Sundays
    for i in range(n):
        sundays.append(first_sunday + timedelta(weeks=i))
    # If a string is passed, return string(s)
    if isinstance(from_date, str):
        sundays = [datetime.strftime(i, "%Y-%m-%d") for i in sundays]
    # If a season is passed, return a list that includes the numbered week of
    # the season.
    if season is not None:
        sundays = [[d, f'{season}{str(i).zfill(2)}'] \
                   for d, i in zip(sundays, range(start, n+start))]
    return sundays

def process_output(weeks, dir='infer'):
    """Process the output of `previous_sundays` or `next_sundays` into a
    dataframe that matches the master dataframe being assembled. If `autodir`
    is set to 'infer' (default), the file directory will be automatically
    inferred from and prefixed to the filename. This works, for example, for
    'advent01.qmd`, but not for `epiphany.qmd`. Manually specify the directory
    by passing it to `dir` instead of "infer".
    """
    # Create a dataframe
    newdf = pd.DataFrame(weeks, columns = ['date', 'feast'])
    
    # Split the date into year, month, and day columns
    newdf['year'] = newdf.date.dt.year
    newdf['month'] = newdf.date.dt.month
    newdf['day'] = newdf.date.dt.day
    newdf['dayofweek'] = newdf.date.dt.dayofweek

    # Add filename
    if dir.lower()=='infer':
        # dir = newdf['feast'][0][:-2]
        dir = ''.join(filter(str.isalpha, newdf['feast'][0]))
    newdf['filename'] = [os.path.join(dir, f'{i}.qmd') \
        for i in newdf['feast']]

    # Sort columns
    newdf = newdf[['date', 'year', 'month', 'day', 'dayofweek', 'feast', 'filename']]
    return newdf

def feast_name(feast):
    """Derive the name of the occasion from `feast`"""
    # Check for a numbered week and derive the name if the last two elements of
    # `feast` are a number
    try:
        sea = titlecase(feast[:-2].replace('-', ' '))
        if sea.lower() == 'ot':
            sea = 'Ordinary Time'
        num = feast[-2:]
        ord = titlecase(num2words(int(num), ordinal=True))
        return f'{ord} Sunday in {titlecase(sea)}'
    # If `feast` is not a numbered week, convert it as-is to a name
    except ValueError:
        return titlecase(feast.replace('-', ' '))

# Variable(s) to be keyword agruments
# easter = '2026-04-05'
# ascension_thursday = True
# year = int(easter.split('-')[0])

# =============================================================================
# Main Program

def main():

    # Parse args
    args = parse_args()
    easter = args.easter
    year = int(easter.split('-')[0])

    # -------------------------------------------------------------------------
    # Advent
    # -------------------------------------------------------------------------
    # There are always four (4) Sundays in Advent, concluding the Sunday before
    # Christmas, regardless of what day of the week Christmas falls. Thus, we
    # count back 4 weeks from Christmas to find the first Sunday of Advent.
    christmas = datetime.strptime(f"{year-1}-12-25", "%Y-%m-%d")
    advent_weeks = previous_sundays(from_date=christmas, n=4, season='advent')
    advent_df = process_output(advent_weeks)

    # Make a master dataframe
    df = advent_df.copy()

    # -------------------------------------------------------------------------
    # Christmas
    # -------------------------------------------------------------------------
    # The Christmas season starts Christmas Even and includes the Solemnities
    # of the Holy Family, Epiphany, and Baptism of the Lord taking place on the
    # Sundays following Christmas, in that order. When Christmas falls on a
    # Sunday, the Solemnity of the Holy Family is celebrated on December 30 so
    # that the Epiphany can be celebrated between January 2 and 8, inclusive.
    if christmas.weekday() == 6:
        christmas_weeks = next_sundays(from_date=christmas, n=2)
        christmas_weeks = [[d, f] for d, f in zip(christmas_weeks, ['epiphany', 'baptism'])]
    else:
        christmas_weeks = next_sundays(from_date=christmas, n=3)
        christmas_weeks = [[d, f] for d, f in zip(christmas_weeks, ['holy-family', 'epiphany', 'baptism'])]
    christmas_weeks.append([christmas, 'christmas-dawn'])
    christmas_weeks.append([christmas, 'christmas-day'])
    christmas_weeks.append([christmas-timedelta(days=1), 'christmas-eve'])
    christmas_weeks.append([christmas-timedelta(days=1), 'christmas-midnight'])
    christmas_df = process_output(christmas_weeks, dir='christmas')
    df = pd.concat((df, christmas_df), axis=0)

    # -------------------------------------------------------------------------
    # Lent
    # -------------------------------------------------------------------------
    # Lent precedes Easter. There are five (5) Sundays of Lent followed by Palm
    # Sunday, which begins Holy Week. Holy Week includes Holy Thursday, Good
    # Friday, and the Easter Vigil on the Saturday evening before Easter Sunday
    # (collectively, the Triduum). Ash Wednesday, which starts Lent, is the
    # Wednesday before the first Sunday of Lent.
    easter = datetime.strptime(easter, "%Y-%m-%d")
    lent_weeks = previous_sundays(from_date=easter, n=6, season="lent")
    lent_df = process_output(lent_weeks)
    lent_df.replace({'lent06': 'palm-sunday',
                    'lent/lent06.qmd': 'holy-week/palm-sunday.qmd'},
                    inplace=True)
    lent_df.set_index('feast', inplace=True)
    easter_vigil = easter - timedelta(days=1)
    good_fri = easter_vigil - timedelta(days=1)
    holy_thurs = good_fri - timedelta(days=1)
    ash_wed = lent_df['date']['lent01'] - timedelta(days=4)
    triduum_df = pd.DataFrame([
        [ash_wed, 'ash-wednesday', 'lent/ash-wednesday.qmd'],
        [holy_thurs, 'holy-thursday', 'holy-week/holy-thursday.qmd'],
        [good_fri, 'good-friday', 'holy-week/good-friday.qmd'],
        [easter_vigil, 'easter-vigil', 'holy-week/easter-vigil.qmd']
        ], columns=['date', 'feast', 'filename'])
    triduum_df['year'] = triduum_df.date.dt.year
    triduum_df['month'] = triduum_df.date.dt.month
    triduum_df['day'] = triduum_df.date.dt.day
    triduum_df['dayofweek'] = triduum_df.date.dt.dayofweek
    lent_df.reset_index(inplace=True)
    df = pd.concat((df, lent_df, triduum_df), axis=0)

    # =========================================================================
    # Easter (through Corpus Christi)
    # =========================================================================
    # There are generally seven (7) Sundays of Easter followed by Pentecost
    # Sunday. In most of the United States, however, the seventh Sunday of
    # Easter is replaced by the Solemnity of the Ascension, which would
    # otherwise be celebrated 40 days after Easter (Ascension Thursday.) The
    # two Sundays after Pentecost are the Solemnities of the Holy Trinity and
    # Corpus Christi, in that order. Although these two solemnities are
    # technically in Ordinary Time, they are defined here for logistical
    # simplicity.
    easter_weeks = next_sundays(from_date=easter, n=9, start=2, 
                                season='easter')
    easter_weeks.append([easter, 'easter'])
    easter_df = process_output(easter_weeks)
    easter_df.replace({
        'easter08': 'pentecost',
        'easter/easter08.qmd': 'easter/pentecost.qmd',
        'easter09': 'holy-trinity',
        'easter/easter09.qmd': 'feasts/holy-trinity.qmd',
        'easter10': 'corpus-christi',
        'easter/easter10.qmd': 'feasts/corpus-christi.qmd'
        }, inplace=True)
    pentecost = pd.Timestamp(easter_df.loc[easter_df.feast=='pentecost'].date.values[0])
    pentecost_vigil = pentecost - timedelta(days=1)
    easter_df = pd.concat((easter_df, pd.DataFrame.from_dict({
        'feast': ['pentecost-vigil']*2,
        'date': [pentecost_vigil]*2,
        'year': [pentecost_vigil.year]*2,
        'month': [pentecost_vigil.month]*2,
        'day': [pentecost_vigil.day]*2,
        'dayofweek': [pentecost_vigil.dayofweek]*2,
        'filename': ['easter/pentecost-vigil.qmd',
                    'easter/pentecost-vigil-extended.qmd']
    })), axis=0)
    if args.ascension_thursday:
        # Ascension is celebrated 40 days after Easter (inclusive)
        ascension = easter + timedelta(days=39)
        ascension_df = {
            'date': ascension,
            'year': year,
            'month': ascension.month,
            'day': ascension.day,
            'dayofweek': ascension.dayofweek,
            'feast': 'ascension',
            'filename': 'easter/ascension.qmd'
            }
        easter_df.loc[len(easter_df)] = ascension_df
    else:
        # Replace Seventh Sunday of Easter with Ascension
        easter_df.replace({
            'easter07': 'ascension',
            'easter/easter07.qmd': 'easter/ascension.qmd'
            }, inplace=True)
    df = pd.concat((df, easter_df), axis=0)

    # -------------------------------------------------------------------------
    # Ordinary Time
    # -------------------------------------------------------------------------
    # The periods between the liturgical seasons of Christmas and Lent and
    # Easter and Advent are Ordinary Time (OT). The Sundays of OT advance
    # sequentially starting with the Second Sunday of Ordinary Time immediately
    # after the Baptism of the Lord. (There is no first Sunday in OT because
    # the Solemnity of the Baptism of the Lord, celebrated on a Sunday, closes
    # the Christmas season. The Monday that follows begins the first week in
    # OT.) The last Sunday in OT, immediately before Advent, is always the
    # Solemnity of Christ the King.
    # 
    # To determine the weeks of OT in winter (between the Baptism of the Lord
    # and Ash Wednesday), count up from the Sunday after the Baptism of Lord,
    # starting with OT 2, until the Sunday before Ash Wednesday. 
    # 
    # To determine the weeks of OT in summer (between Pentecost and Christ the
    # King), start with the Sunday before Christ the King. This Sunday is
    # always the Thirty-third Sunday in Ordinary Time and is always five weeks
    # before Christmas. Then count backwards until Corpus Christi. Note that
    # the first Sunday in OT following Pentecost is not the next number
    # sequentially following the last Sunday in OT before Ash Wednesday.
    df.set_index('feast', inplace=True)
    num_winter_weeks = (df['date']['ash-wednesday'] - df['date']['baptism']).days // 7
    ot_winter_weeks = next_sundays(from_date=df['date']['baptism'],
                                n=num_winter_weeks, start=2, season="ot")
    ot_winter_df = process_output(ot_winter_weeks, dir='ordinary-time')

    next_christmas = datetime.strptime(f"{year}-12-25", "%Y-%m-%d")
    christ_the_king = previous_sundays(from_date=next_christmas, n=5)[0]
    num_summer_weeks = (christ_the_king - df['date']['corpus-christi']).days // 7
    ot_summer_weeks = previous_sundays(from_date=christ_the_king,
                                    n=num_summer_weeks-1, end=33, season='ot')
    ot_summer_df = process_output(ot_summer_weeks)
    df.reset_index(inplace=True)
    df = pd.concat((df, ot_winter_df, ot_summer_df), axis=0)

    # =========================================================================
    # Feasts and Solemnities
    # =========================================================================
    # Several feasts and solemnities are celebrated on weekdays throughout the
    # year; for example, holy days of obligation. Some of the more significant
    # feasts and solemnities are included here. If a feast or solemnity falls
    # on a Sunday, the Sunday liturgy is superceded by that feast or solemnity,
    # regardless of season.

    # Floating dates: Sacred Heart, Christ the King, and Thanksgiving
    sacred_heart = pentecost + timedelta(days=19)
    thanksgiving_date = np.array(calendar.monthcalendar(year, 11))[:,3].max()
    thanksgiving = datetime(year, 11, thanksgiving_date)
    if christ_the_king < thanksgiving:
        others_df = pd.DataFrame([
            [sacred_heart, 'sacred-heart', 'feasts/sacred-heart.qmd'],
            [christ_the_king, 'christ-the-king', 'ordinary-time/christ-the-king-before-thanksgiving.qmd'],
            [thanksgiving, 'thanksgiving', 'ordinary-time/thanksgiving.qmd']
        ], columns=['date', 'feast', 'filename'])
    else:
        others_df = pd.DataFrame([
            [sacred_heart, 'sacred-heart', 'feasts/sacred-heart.qmd'],
            [christ_the_king, 'christ-the-king', 'ordinary-time/christ-the-king-after-thanksgiving.qmd'],
            [thanksgiving, 'thanksgiving', 'ordinary-time/thanksgiving.qmd']
        ], columns=['date', 'feast', 'filename'])    
    others_df['year'] = others_df.date.dt.year
    others_df['month'] = others_df.date.dt.month
    others_df['day'] = others_df.date.dt.day
    others_df['dayofweek'] = others_df.date.dt.dayofweek
    df = pd.concat((df, others_df), axis=0)

    # Fixed dates: feasts and solemnities
    feasts = [
        # Feasts
        [year, 2, 2, 'presentation', 'feasts/feb02-presentation.qmd'],
        [year, 8, 6, 'transfiguration', 'feasts/aug06-transfiguration.qmd'],
        [year, 9, 14, 'holy-cross', 'feasts/sep14-holy-cross.qmd'],
        [year, 11, 2, 'all-souls', 'feasts/nov02-all-souls.qmd'],
        [year, 11, 9, 'john-lateran', 'feasts/nov09-john-lateran.qmd'],

        # Solemnities
        [year-1, 12, 8, 'immaculate-conception', 'feasts/dec08-immaculate-conception.qmd'],
        [year, 1, 1, 'mary-mother-of-god', 'christmas/mary-mother-of-god.qmd'],
        [year, 3, 19, 'stjoseph', 'feasts/st.joseph.qmd'],
        [year, 3, 25, 'annunciation', 'feasts/mar25-annunciation.qmd'],
        [year, 6, 23, 'nativity-john-baptist-vigil', 'feasts/jun23-nativity-john-baptist-vigil.qmd'],
        [year, 6, 24, 'nativity-john-baptist', 'feasts/jun24-nativity-john-baptist.qmd'],
        [year, 6, 28, 'peter-paul-vigil', 'feasts/jun28-peter-paul-vigil.qmd'],
        [year, 6, 29, 'peter-paul', 'feasts/jun29-peter-paul.qmd'],
        [year, 8, 14, 'assumption-vigil', 'feasts/aug14-assumption-vigil.qmd'],
        [year, 8, 15, 'assumption', 'feasts/aug15-assumption.qmd'],
        [year, 11, 1, 'all-saints', 'feasts/nov01-all-saints.qmd'],
    ]
    feasts_df = pd.DataFrame(
        feasts,
        columns=['year', 'month', 'day', 'feast', 'filename'])
    feasts_df['date'] = pd.to_datetime(feasts_df[['year', 'month', 'day']])
    feasts_df['dayofweek'] = feasts_df.date.dt.dayofweek
    # Remove any vigils that occur on Sunday prior to merge, since these won't
    # be celebrated on Sunday
    feasts_df.drop(feasts_df[(feasts_df.feast.str.contains('vigil')) & \
                             (feasts_df.dayofweek==6)].index, inplace=True)
    feasts_df.set_index('date', inplace=True)
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    # Add new feast and solemnity entries, replacing any ordinary Sunday with
    # the feast or solemnity that falls on the same day, if applicable
    df = feasts_df.combine_first(df)

    # Add liturgical season
    df.reset_index(inplace=True)
    df.set_index('feast', inplace=True)
    df['season'] = 'ordinary-time'
    df.loc['advent01':'advent04', 'season'] = 'advent'
    df.loc['christmas-eve':'baptism', 'season'] = 'christmas'
    df.loc['ash-wednesday':'good-friday', 'season'] = 'lent'
    df.loc['easter-vigil':'pentecost', 'season'] = 'easter'
    df.reset_index(inplace=True)
    df.set_index('date', inplace=True)

    # Add human-readable feast name (with some manual overrides)
    df['name'] = df['feast'].apply(feast_name)
    df['name'] = df['name'].replace('Epiphany', 'Epiphany of the Lord')
    df['name'] = df['name'].replace('Mary Mother of God', 'Mary, Mother of God')
    df['name'] = df['name'].replace('Baptism', 'Baptism of the Lord')
    df['name'] = df['name'].replace('Presentation', 'Presentation of the Lord')
    df['name'] = df['name'].replace('Stjoseph', 'Saint Joseph')
    df['name'] = df['name'].replace('Nativity John Baptist', 'Nativity of John Baptist')
    df['name'] = df['name'].replace('Peter Paul', 'Saints Peter and Paul')
    df['name'] = df['name'].replace('Annunciation', 'Annunciation of the Lord')
    df['name'] = df['name'].replace('Ascension', 'Ascension of the Lord')
    df['name'] = df['name'].replace('Transfiguration', 'Transfiguration of the Lord')
    df['name'] = df['name'].replace('Holy Cross', 'Exaltation of the Holy Cross')
    df['name'] = df['name'].replace('John Lateran', 'Dedication of the Lateran Basilica')
    df['name'] = df['name'].replace('Sacred Heart', 'Sacred Heart of Jesus')

    # Add day names for human readability
    df['weekday'] = df.dayofweek.map({
        0: 'Mon',
        1: 'Tues',
        2: 'Wed',
        3: 'Thurs',
        4: 'Fri',
        5: 'Sat',
        6: 'Sun'
    })
    # Add prioritization for facilitate filtering:
    #  -> 2 for Sundays and holy days of obligation
    #  -> 1 for important days that are not holy days (e.g., Ash Wednesday)
    #  -> 0 otherwise
    holy_days = [
        'immaculate-conception',
        'christmas-eve', 'christmas-midnight', 'christmas-dawn', 'christmas-day',
        'mary-mother-of-god',
        'ascension',
        'assumption', 'assumption-vigil',
        'all-saints'
    ]
    important_days = [
        'ash-wednesday',
        'holy-thursday',
        'good-friday',
        'easter-vigil',
        'thanksgiving',
        'all-souls'
    ]
    df['priority'] = df.apply(lambda x: 2 if (x['feast'] in holy_days or x['weekday']=='Sun') else 1 if x['feast'] in important_days else 0, axis=1)

    # Reorder columns for convenience
    df = df[['weekday', 'feast', 'season', 'name', 'priority', 'year', 'month', 'day', 'dayofweek', 'filename']]

    # Write to file
    if args.outfile is None:
        df.to_csv(f'{year}-year{lityear(year)}-liturgical-calendar.csv')
    else:
        df.to_csv(args.outfile)

if __name__ == "__main__":
    main()
