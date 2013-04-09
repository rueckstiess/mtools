# mplotqueries tutorial

### Introduction

mplotqueries is a tool to visualize operations in MongoDB logfiles. It is part of the [mtools](README.mk) collection.
Before you can use mplotqueries, make sure you have [installed mtools](../INSTALL.md) as well as numpy and matplotlib. 
These dependencies are necessary in order for mplotqueries to work. You can find detailed instructions on the [install](../INSTALL.md) page.

### Basic Usage

mplotqueries is a command line tool that takes a logfile or several logfiles and visualizes the log lines in a 2D plot, where the x-axis is the date and time of an event, and the y-axis is the duration of an event. By default, mplotqueries only visualizes timed loglines, i.e. those that have a duration at the end, specified in milliseconds. A typical log line that is a timed event could look like this:

    Thu Feb 21 03:25:44 [conn5] command admin.$cmd command: { writebacklisten: ObjectId('5124bdb43bd5f630b542ff68') } ntoreturn:1 keyUpdates:0  reslen:44 300000ms
    
These "writebacklisten" commands are an essential part of a sharded setup, and their duration is often "300000ms", or 5 minutes. (If you don't see where the number 300000ms comes from, scroll to the far right of the line.) Their purpose is described on MongoDB's manual page on [sharding](http://docs.mongodb.org/manual/faq/sharding/#what-does-writebacklisten-in-the-log-mean).

To plot a mongod or mongos logfile with mplotqueries, you can simply run:

    mplotqueries mongod.log

After parsing the logfile, you should see a window pop up that displays the queries, similar to this:

<img src="https://www.dropbox.com/s/g2yo84gevif9z12/mplotqueries-tutorial-1.png?dl=1">

On the x-axis we see the date and time of the events. This particular logfile seems to go from February 20-21. On the y-axis, we can see the axis represents the duration of events in milliseconds.

And already run into our first problem. Most of the operations in MongoDB have sub-second duration, and we can see points on the bottom of the plot, but they are all squashed together. Unfortunately, the logfile also contains these writebacklisten messages, that are known to run for (comparatively) long times, 5 minutes. We can savely ignore those and focus on the "real" events.

### Navigating the Main Window

