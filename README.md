# accupedo-r
This is the tool I use to analyze my accupedo pedometer sqlite diaries table
data to answer the question: do I get enough exercise.

On a periodic basis, I will:
1 hook up my phone to the computer (MBP),
2 drag the Accupedo.db sqlite database over to a local folder
3 run accupedo.r (it currently expects the data in that Accupedo.db file)

The tool gives a breakdown of the number of time slices in that database that
can be construed as measurable increased intensity activity (MIIA). MIIA are
those activities that exceed some threshold value. The threshold value I use
is 125 steps per minute but ymmv. The threshold can be determined as that pace
that gets your heart rate up to 110 beats per minute.

The tool divides your pedometer history into days that you have any MIIA and
days in which no MIIA took place. Accupedo keeps a record of all activity since
the time it was installed in 30 minute chunks (with some exceptions I've yet to
figure out). In each 30 minute slice of time, they will record a number of
steps and an amount of time you were in motion. The accupedo app maintains a
running total during the day, this tool reverts that to an incremental quantity
for each time slice.

The end product of this tool is a description of how much MIIA you get per day
for the life of the database and for an interesting recent time-slice. I've set
that interval to be 30 days because I'd really like to not hit my exercise goal
for that period of time. Unfortunately, I'm only showing a daily average MIIA
achievement while the numbers I've read seen to indicate that I should shoot
for a weekly target of 150 minutes. Daily that comes out to something over 21
minutes a day.

As you can maybe see, there are some problems with using Accupedo's data this
way. If I try to get one half hour of fast walking in a day, there's a non-zero
probability that the activity will straddle two of Accupedo's natural measure-
ment intervals and it's possible that other activity in those intervals will
drag the average down enough that the two halves will be lost - neither of
the two Accupedo intervals will look like exercise. There's a couple of work-
arounds.

