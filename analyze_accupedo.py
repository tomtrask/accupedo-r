#!/usr/local/bin/python3

import os
import sqlite3 as sqlite
import numpy as np
import pandas as pd

HOME_ = os.environ["HOME"]
DB_FILE_NAME_ = "Accupedo.db"
WORK_DB_ = "work/{0}".format(DB_FILE_NAME_)

def get_transfer_file():
    """Get the database file most recently transferred from the phone"""
    transfer_file = "{0}/Google Drive/Data/{1}".format(HOME_, DB_FILE_NAME_)
    if os.path.exists(transfer_file):
        if os.path.exists(WORK_DB_):
            os.remove(WORK_DB_)
        os.rename(transfer_file, WORK_DB_)

def get_aggregate_stats(conn):
    df = pd.read_sql_query("select * from diaries", conn)
    df.drop(columns=["lap", "lapsteps", "lapdistance", "lapcalories",
                     "lapsteptime", "distance", "calories", "speed", "pace",
                     "achievement"], inplace=True)

    df["ymdhm"] = 100*(100*(100*(100*df["year"]+df["month"])+df["day"])
                       + df["hour"])+df["minute"]
    df["ymd"] = 100*(100*df["year"]+df["month"])+df["day"]

    df.set_index("ymdhm")
    df.drop(columns=["_id"], inplace=True)

    df["del_steps"] = df["steps"] - df.shift(1)["steps"]
    df["del_time_min"] = (df["steptime"] - df.shift(1)["steptime"])/60000
    df["miia_steps"] = df["del_steps"].copy()
    df["miia_time_min"] = df["del_time_min"].copy()

    # steps reset at midnight so we need to drop the first interval of the day
    df.drop(df[df.del_steps<=0].index, inplace=True)

    df.drop(columns=["year", "month", "day", "hour", "minute", "steps",
                     "steptime"], inplace=True)

    match_not_fast = df[df["del_steps"]/df["del_time_min"] < 125].index
    df.loc[match_not_fast, "miia_steps"] = 0
    df.loc[match_not_fast, "miia_time_min"] = 0

    match_too_small = df[df["del_time_min"] < 1].index
    df.loc[match_too_small, "miia_steps"] = 0
    df.loc[match_too_small, "miia_time_min"] = 0
   
    df.drop(columns=["ymdhm"], inplace=True)
    df.dropna(inplace=True)

    redis = df.groupby("ymd").sum()
    # recompute pace as aggregate pace for group
    redis["pace"] = redis["del_steps"]/redis["del_time_min"]
    redis["miia_pace"] = redis["miia_steps"]/redis["miia_time_min"]

    return redis

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
        print("Lifetime average time: {0:.0f} min (sd={1:.0f})"
              .format(agg["del_time_min"].mean(), agg["del_time_min"].std()))
        print("Lifetime average MIIA time: {0:.0f} min (sd={1:.0f})"
              .format(agg["miia_time_min"].mean(), agg["miia_time_min"].std()))
        last_zero_date = agg[agg["miia_steps"] == 0].index[-1]
        days_since_zero = agg[agg.index > last_zero_date]
        num_days_since_zero = len(days_since_zero.index)
        print("Days continuous MIIA: {0}".format(num_days_since_zero))
              


if __name__ == "__main__":
    main()
