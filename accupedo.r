library(sqldf)
library(Hmisc)

setwd('~/pg/nw/pedoLog/accupedo/test')

TEST_DB_NAME_ = 'Accupedo.db'

db <- dbConnect(SQLite(), dbname=TEST_DB_NAME_)

# Tables in the database
tableNames <- sqldf('SELECT * FROM sqlite_master', dbname = TEST_DB_NAME_)$tbl_name  
print(tableNames)

# Columns in the School table
x <- sqldf('pragma table_info(diaries)', dbname = TEST_DB_NAME_)$name   
print(x)

# Data in the School table   
dingus <- sqldf('SELECT * FROM diaries', dbname = TEST_DB_NAME_)      
print(paste("diaries has", nrow(dingus), "rows", sep=' '))

#pretty that dataframe all up in here
dingus$ymd <- (dingus$year * 100 + dingus$month) * 100 + dingus$day
dingus$hms = (dingus$hour * 100 + dingus$minute) * 100

sql <- '
SELECT *
  FROM sqlite_master
'
tn <- sqldf(sql, dbname = TEST_DB_NAME_)$tbl_name
print(paste('SQL:', sql, sep=' '))
print(tn)

# sqldf('drop table if exists rediaries', dbname = TEST_DB_NAME_)
# dbBegin(db)
dbSendStatement(db, 'drop table if exists rediaries')
# dbCommit(db)
print("You got here")
create_rediaries_stmt <- '
create TEMPORARY table rediaries as
  SELECT CAST(ymdhm AS INT) ymdhm,
         CAST(MAX(steps) as INT) steps,
         CAST(MAX(steptime_min) AS FLOAT) steptime_min
    FROM (
    SELECT (((year*100+month)*100+day)*100+hour)*100+minute ymdhm,
           steps,
           CAST(steptime AS FLOAT)/60000 steptime_min
      FROM diaries
         ) t0
GROUP BY ymdhm
ORDER BY ymdhm
'
index_stmt <- 'CREATE UNIQUE INDEX idx_rediaries_ymdhm ON rediaries (ymdhm)'

res <- dbSendStatement(db, create_rediaries_stmt)
dbSendStatement(db, index_stmt)

drop_inc_diary_stmt <- 'DROP TABLE IF EXISTS incremental_diary'
create_inc_diary_stmt <- '
CREATE TABLE incremental_diary AS
  SELECT ymdhm,
         CAST(ymdhm/10000 AS INT) ymd,
         CAST(ymdhm % 10000 AS INT) hm,
         CAST(delta_steps AS INT) delta_steps,
         CAST(delta_steptime_min AS FLOAT) delta_steptime
    FROM (
    SELECT A.ymdhm,
           A.steps,
           A.steptime_min,
           IFNULL(A.steps-B.steps,0) delta_steps,
           IFNULL(A.steptime_min-B.steptime_min,0) delta_steptime_min
      FROM rediaries AS A
           LEFT JOIN rediaries AS B
             ON B.ymdhm=(SELECT MAX(ymdhm) FROM rediaries where ymdhm<A.ymdhm)
         ) t0
   WHERE delta_steps > 0
ORDER BY ymdhm
'
dbSendStatement(db, drop_inc_diary_stmt)
dbSendStatement(db, create_inc_diary_stmt)

# it is in our best interest to ignore very short walking intervals (the step
# rates are too high when we include short intervals)
all_walks_stmt <- "
SELECT *
  FROM incremental_diary
 WHERE delta_steptime > 1
"
all_walks <- sqldf(all_walks_stmt, dbname=TEST_DB_NAME_)
II_RATE_CUTOFF_ <- 125
exercise <- all_walks[all_walks$delta_steps/all_walks$delta_steptime >= II_RATE_CUTOFF_,]
exercise_agg <- aggregate(delta_steptime ~ ymd, exercise,
                          function(time) sum(time))

ymd_to_iso <- function(ymd) {
  # Convert a single decimal date to a POSIXct date
  return(as.POSIXct(toString(ymd), format="%Y%m%d"))
}

ymd_add_days <- function(ymd, add_days) {
  # Add some number of days to a decimal date
  ymd_as_iso <- as.POSIXct(toString(ymd), format="%Y%m%d")
  return(strtoi(format(ymd_as_iso + as.difftime(add_days, units="days"),
                       format="%Y%m%d")))
}

decimal_date_diff <- function(decimal_date_1, decimal_date_2) {
  # return decimal_date_1 - decimal_date_2 in days
  return(as.integer(ymd_to_iso(decimal_date_1) - ymd_to_iso(decimal_date_2),
                    units="days")+1)
}

least_recent_day <- min(all_walks$ymd)
most_recent_day <- max(all_walks$ymd)

RECENT_INTERVAL_DAYS_ <- 30
INT_MONTH_BEGIN_ <- ymd_add_days(most_recent_day, 1-RECENT_INTERVAL_DAYS_)

reporter <- function(t1, t2, all_walks, miia_cutoff) {
  # compute and report relevant stats for single time period
  diff_days = decimal_date_diff(t2, t1)

  recent_walks <- all_walks[all_walks$ymd >= t1 & all_walks$ymd <= t2,]

  # strict_miia_walks is only MIIA - it does not include any non-MIIA
  strict_miia_walks <- recent_walks[recent_walks$delta_steps/
                                   recent_walks$delta_steptime >= miia_cutoff,]

  all_walk_dates <- unique(recent_walks$ymd)
  trt_walk_dates <- unique(strict_miia_walks$ymd)
  notrt_walk_dates = setdiff(all_walk_dates, trt_walk_dates)

  # notrt_walks is all walking activity on days in which there is no MIIA
  notrt_walks <- recent_walks[recent_walks$ymd %in% notrt_walk_dates,]
  # and trt_walks is all activity on days in which there was any MIIA
  # notrt_walks + trt_walks = recent_walks
  trt_walks <- recent_walks[recent_walks$ymd %in% trt_walk_dates,]

  num_unv_days <- length(unique(recent_walks$ymd))
  num_notrt_days <- length(notrt_walk_dates)
  num_trt_days <- length(trt_walk_dates)

  num_unv_steps <- sum(recent_walks$delta_steps)
  num_miia_steps <- sum(strict_miia_walks$delta_steps)
  num_notrt_steps <- sum(notrt_walks$delta_steps)
  num_trt_steps <- sum(trt_walks$delta_steps)

  unv_step_time <- sum(recent_walks$delta_steptime)
  miia_step_time <- sum(strict_miia_walks$delta_steptime)
  notrt_step_time <- sum(notrt_walks$delta_steptime)
  trt_step_time <- sum(trt_walks$delta_steptime)

  # ii_time <- sum(miia_walks$delta_steptime)/num_trt_days
  # avg_miia_time <- sum(miia_walks$delta_steptime)/num_unv_days
  all_time <- sum(recent_walks$delta_steptime)/num_unv_days
  no_ii_time <- sum(notrt_walks$delta_steptime)/num_notrt_days

  all_step_rate <- num_unv_steps/all_time

  out <- c()
  out <- c(out, sprintf("History: %d to %d (%d days)\n", t1, t2, diff_days))
  out <- c(out, sprintf("- MIIA Step cutoff: %.1f\n", miia_cutoff))
  out <- c(out, "- Aggregate\n")
  out <- c(out, sprintf("    # days: %d\n", num_unv_days))
  out <- c(out, sprintf("    # MIIA days: %d (%.1f %%)\n", num_trt_days,
                        100*num_trt_days/num_unv_days))
  out <- c(out, sprintf("    Daily steps: %.0f\n",
                        num_unv_steps/num_unv_days))
  out <- c(out, sprintf("    Daily MIIA steps: %.0f (%.1f %%)\n",
                        num_miia_steps/num_unv_days, 100*num_miia_steps/num_unv_steps))
  out <- c(out, sprintf("    Daily time, min: %.1f\n",
                        unv_step_time/num_unv_days))
  out <- c(out, sprintf("    Daily MIIA time, min: %.1f (%.1f %%)\n",
                        miia_step_time/num_unv_days, 100*miia_step_time/unv_step_time))
  out <- c(out, sprintf("    Average pace, steps/min: %.0f\n",
                        num_unv_steps/unv_step_time))
  out <- c(out, "- Non-MIIA days only\n")
  out <- c(out, sprintf("    # days: %d\n", num_notrt_days))
  out <- c(out, sprintf("    Daily steps: %.0f\n",
                        num_notrt_steps/num_notrt_days))
  out <- c(out, sprintf("    Daily time, min: %.1f\n",
                        notrt_step_time/num_notrt_days))
  out <- c(out, sprintf("    Average pace, steps/min: %.0f\n",
                        num_notrt_steps/notrt_step_time))
  out <- c(out, "- MIIA days only\n")
  out <- c(out, sprintf("    # days: %d\n", num_trt_days))
  out <- c(out, sprintf("    Daily steps: %.0f\n",
                        num_trt_steps/num_trt_days))
  out <- c(out, sprintf("    Daily MIIA steps: %.0f (%.1f %%)\n",
                        num_miia_steps/num_trt_days, 100*num_miia_steps/num_trt_steps))
  out <- c(out, sprintf("    Daily time, min: %.1f\n",
                        trt_step_time/num_trt_days))
  out <- c(out, sprintf("    Daily MIIA time, min: %.1f (%.1f %%)\n",
                        miia_step_time/num_trt_days, 100*miia_step_time/trt_step_time))
  out <- c(out, sprintf("    Average pace, steps/min: %.0f\n",
                        num_trt_steps/trt_step_time))
  out <- c(out, "\n")

  cat(out)
  
  return(all_step_rate)
}

reporter(least_recent_day, most_recent_day, all_walks, II_RATE_CUTOFF_)
reporter(INT_MONTH_BEGIN_, most_recent_day, all_walks, II_RATE_CUTOFF_)

dbDisconnect(db)
