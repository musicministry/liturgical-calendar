# liturgical-calendar

### Overview

This script creates a United States Catholic liturgical calendar based around the date of Easter passed on execution, formatted `YYYY-DD-MM`. The calendar year is automatically taken to be `YYYY` from Easter; Advent and Christmas are automatically taken from the previous calendar year. The most common prioritization rules are implemented; however, some nuanced exceptions may not be accounted for. Adjustments to the script will be made as such nuances are discovered. The liturgical calendar is written to the current working directory as a CSV file named `YYYY-yearX-liturgical-calendar.csv`, where "YYYY" is the calendar year of Easter and "X" is the liturgical cycle ("A", "B", or "C") for the given year, unless a custom file name with directory path is pass using a `-o, --outfile` flag.

The CSV file contains the following columns:

* `date`: calendar date
* `weekday`: human-readable day of week name (*e.g.*, "Mon")
* `feast`: name of the liturgical feast (*e.g.*, "christmas-day")
* `priority`: prioritization flag to facilitate filtering:
  - 2 for Sundays and holy days of obligation
  - 1 for important days that are not holy days (e.g., Ash Wednesday)
  - 0 otherwise
* `year`: year from `date`
* `month`: month from `date`
* `day`: day from `date`
* `dayofweek`: numbered day of the week, where Monday is 0 and Sunday is 6
* `filename`: name of Quarto markdown file in music planning book for cross-reference

This script was verified against the [official liturgical calendar](https://bible.usccb.org/readings/calendar) for 2025 (Year A) from the United States Council of Catholic Bishops.

### Usage

To execute in terminal:
`python litcalendar.py --easter 2026-04-05`
