#!/usr/local/bin/python3
"""
A python version of accupedo.r. This obviates accupedo.r and a related bash
script that I never checked into github (the function of the bash script was
to move the sqlite database from the google drive directory - this python
script does that)
"""

from datetime import datetime
from datetime import timedelta
import os
import sqlite3 as sqlite
import pandas as pd

HOME_ = os.environ["HOME"]
DB_FILE_NAME_ = "Accupedo.db"
WORK_DB_ = "work/{0}".format(DB_FILE_NAME_)

def get_transfer_file():
    """Get the database file most recently transferred from the phone"""
    transfer_file = "{0}/Google Drive/Data/{1}".format(HOME_, DB_FILE_NAME_)
    if os.path.exists(transfer_file):
        print("Fetching new database from {0}".format(transfer_file))
        if os.path.exists(WORK_DB_):
            os.remove(WORK_DB_)
        os.rename(transfer_file, WORK_DB_)

def get_aggregate_stats(conn):
    """Read raw accupedo diaries, slice and dice to get what we want"""
    diaries = pd.read_sql_query("select * from diaries", conn)
    diaries.drop(columns=["lap", "lapsteps", "lapdistance", "lapcalories",
                          "lapsteptime", "distance", "calories", "speed",
                          "pace", "achievement"], inplace=True)

    diaries["ymdhm"] = (100*(100*(100*(100*diaries["year"]+diaries["month"])
                                  +diaries["day"]) + diaries["hour"])
                        +diaries["minute"])
    diaries["ymd"] = 100*(100*diaries["year"]+diaries["month"])+diaries["day"]

    diaries.set_index("ymdhm")
    diaries.drop(columns=["_id"], inplace=True)

    diaries["del_steps"] = diaries["steps"] - diaries.shift(1)["steps"]
    diaries["del_time_min"] = (diaries["steptime"]
                               - diaries.shift(1)["steptime"])/60000
    diaries["miia_steps"] = diaries["del_steps"].copy()
    diaries["miia_time_min"] = diaries["del_time_min"].copy()

    # steps reset at midnight so we need to drop the first interval of the day
    diaries.drop(diaries[diaries["del_steps"] <= 0].index, inplace=True)

    diaries.drop(columns=["year", "month", "day", "hour", "minute", "steps",
                          "steptime"], inplace=True)

    match_not_fast = (diaries[diaries["del_steps"]/diaries["del_time_min"]
                              < 125].index)
    diaries.loc[match_not_fast, "miia_steps"] = 0
    diaries.loc[match_not_fast, "miia_time_min"] = 0

    match_too_small = diaries[diaries["del_time_min"] < 1].index
    diaries.loc[match_too_small, "miia_steps"] = 0
    diaries.loc[match_too_small, "miia_time_min"] = 0

    diaries.drop(columns=["ymdhm"], inplace=True)
    diaries.dropna(inplace=True)

    redis = diaries.groupby("ymd").sum()
    # recompute pace as aggregate pace for group
    redis["pace"] = redis["del_steps"]/redis["del_time_min"]
    redis["miia_pace"] = redis["miia_steps"]/redis["miia_time_min"]
    redis.fillna(0, inplace=True)

    return redis

DATETIME_TO_COMPACT_ = lambda date: (100*(100*date.year + date.month) + date.day)

def show_one_timeslice(all_data, days_to_show):
    """Print stats for a given timeframe"""
    last_ymd = all_data.iloc[-1].name
    year_month, date = divmod(last_ymd, 100)
    year, month = divmod(year_month, 100)
    last_date = datetime(year, month, date)
    first_ymd = DATETIME_TO_COMPACT_(last_date - timedelta(days=days_to_show-1))

    subset = all_data.loc[first_ymd:]

    print("{0} day stats ({1} to {2}):"
          .format(days_to_show, first_ymd, last_ymd))
    print("    avg (sd) steps: {0:.0f} ({1:.0f})"
          .format(subset["del_steps"].mean(),
                  subset["del_steps"].std()))
    print("    avg (sd) time: {0:.0f} ({1:.1f}) min"
          .format(subset["del_time_min"].mean(),
                  subset["del_time_min"].std()))
    print("    avg (sd) MIIA steps: {0:.0f} ({1:.0f})"
          .format(subset["miia_steps"].mean(),
                  subset["miia_steps"].std()))
    print("    avg (sd) MIIA time: {0:.0f} ({1:.1f}) min"
          .format(subset["miia_time_min"].mean(),
                  subset["miia_time_min"].std()))


def main():
    """The main function"""
    get_transfer_file()
    with sqlite.connect(WORK_DB_) as conn:
        agg = get_aggregate_stats(conn)
        # Cool, now the only thing we're missing is some accounting for
        # non-MIIA days. A simple count of days since no MIIA activity was
        # detected would suffice
        pd.set_option("precision", 2)
        print("====================")
        pd.set_option("display.width", 0)
        print(agg.tail(30))
        print("====================")
        show_one_timeslice(agg, 365)
        show_one_timeslice(agg, 30)

        last_zero_date = agg[agg["miia_steps"] == 0].index[-1]
        days_since_zero = agg[agg.index > last_zero_date]
        num_days_since_zero = len(days_since_zero.index)
        print("Days continuous MIIA: {0}".format(num_days_since_zero))



if __name__ == "__main__":
    main()
