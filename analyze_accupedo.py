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
    df["del_time"] = df["steptime"] - df.shift(1)["steptime"]

    # steps reset at midnight so we need to drop the first interval of the day
    df.drop(df[df.del_steps<0].index, inplace=True)

    df.drop(columns=["year", "month", "day", "hour", "minute", "steps",
                     "steptime"], inplace=True)

    df["pace"] = 60000*df["del_steps"]/df["del_time"]
    df.drop(df[df.del_time < 60000].index, inplace=True)
    df.drop(df[df.pace < 125].index, inplace=True)
    df.drop(columns=["ymdhm"], inplace=True)
    df.dropna(inplace=True)

    redis = df.groupby("ymd").sum()
    redis["pace"] = 60000*redis["del_steps"]/redis["del_time"]

    return redis

def main():
    """The main function"""
    get_transfer_file()
    with sqlite.connect(WORK_DB_) as conn:
        agg = get_aggregate_stats(conn)
        # Cool, now the only thing we're missing is some accounting for
        # non-MIIA days. A simple count of days since no MIIA activity was
        # detected would suffice
        print("====================")
        print(agg.tail(30))


if __name__ == "__main__":
    main()
