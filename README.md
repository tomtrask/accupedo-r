# accupedo-r
This is the tool I use to analyze my accupedo pedometer sqlite diaries table
data to answer the question: do I get enough exercise?

### What Accupedo does
Accupedo is a phone pedometer app. It maintains a sqlite
database called Accupedo.db that on my Android phone I can
easily transfer to my computer and analyze.

That database contains approximately one record for each
half hour slice of time for each day the app is installed.
There are times that the slices are shorter and longer,
 I do not understand why. Each slice contains a cumulative
 step count and step time for the day. Note that if you only
 walk 15 minutes in a given half hour slice, the cumulative
 walk time will increase only by 15 minutes, not 30 minutes.

At or about May or June 2018 Accupedo changed the length of the time slices of activity tracking. I changed the script at that time to include shorter time slices in the computation. Previously shorter timeslices were too infrequent and computed to be shorter (conservatively) than the actually were. The effect of those two characteristics was that if we included time slices under a minute was that we'd incorrectly compute too much exercise. The recent changes eliminated a lot of longer intervals - so instead of one 25 minute slice, the new version would give maybe one two-minute slice and 24 sub-minute slices that still looked like exercise. The total in the new version might be 25 minutes but it would probably be less.

At that same time they introduced a new mechanism to use Google Fit (API) to measure activity. If you turn that on, the Accupedo database is effectively useless for tracking exercise.

### What this script does

This tool converts the cumulative time slices into another
table called incremental_diary where records in the incremental_diary
reflect only the time and steps during that time slice.
Each time slice is then graded to determine whether MIIA has
occurred in that time period. Days in which some MIIA has
occurred are separated from days in which no MIIA has
occurred. Stats are presented for the universe of days as
well as those two subsets (MIIA and non-MIIA).

What is MIIA? MIIA is defined as a time interval in which
the user has raised their heart rate to 110 beats per minute.
Since Accupedo doesn't track heart rate, we use a step
rate - miia_rate_cutoff - as a proxy. For me, if I walk
at a rate of 122 steps per minute, about 9 minutes a mile,
or faster, my heart rate gets into that 110 zone.

This script computes statistics for two time frames. The
first time frame is all-time (i.e. since the app was
installed on the phone). The second time frame is user
controlled through the --recent_interval_days command
line flag and the default is 30 days.

I have read in a couple of places that I can tell my doctor
that I exercise regularly if I get 150 minutes per week
of MIIA (Look up a Dr Carrell that does Healthcare Triage
on youtube). That averages out to ~22 minutes a day (it
doesn't pay to round down on your exercise). This target
can be changed with the --target_weekly_miia (-t) command
line parameter.

### How to use the script

On a periodic basis, I will:
1. hook up my phone to the computer (MBP),
2. drag the Accupedo.db sqlite database over to a local folder
3. run accupedo.r either from r or Rscript

### Wait, what about that analyze_accupedo.py script?

That script will fetch the latest Accupedo.db (fixed name() from
${HOME}/Google\ Drive\Data\Accupedo.db and copy it to the work folder and
compute the aggregate statistics for the last 30 days and print them out. In
the time I've been using the accupedo.r script, I've come to rely primarily on
that recent historical view of exercise as my primary indicator that I need to
do more or less exercise.  This script also skips over a lot of the growing
pains I encountered in the R script. The primary motivation for this script is
that I got a new computer and forgot to install R but it seemed that the pandas
version of the script was much simpler than my R script - this turns out to have
been true.

### What's missing

I'd also like to add some weekly aggregates.

Graphs aren't out of the question, but they don't add
a lot of value. The goal is just to see if I'm getting
enough exercise, not to monday-morning quarterback
that month I took off when I was on vacation last
year.

That said, a graph of exercise by day of week could be
useful.
