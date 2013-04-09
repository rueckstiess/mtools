# mplotqueries tutorial

### Introduction

mplotqueries is a tool to visualize operations in MongoDB logfiles. It is part of the [mtools](README.mk) collection.
Before you 

### Basic Usage

mplotqueries is a command line tool that takes a logfile or several logfiles and visualizes the log lines in a 2D plot, where the x-axis is the date and time of an event, and the y-axis is the duration of an event. By default, mplotqueries only visualizes timed loglines, i.e. those that have a duration at the end, specified in milliseconds. A typical log line that is a timed event could look like this:

    Thu Feb 21 03:25:44 [conn5] command admin.$cmd command: { writebacklisten: ObjectId('5124bdb43bd5f630b542ff68') } ntoreturn:1 keyUpdates:0  reslen:44 300000ms
    
These "writebacklisten" commands are an essential part of a sharded setup, and their duration is often "300000ms", or 5 minutes. (If you don't see where the number 300000ms comes from, scroll to the far right of the line.) Their purpose is described on MongoDB's manual page on [sharding](http://docs.mongodb.org/manual/faq/sharding/#what-does-writebacklisten-in-the-log-mean).

To plot a mongod or mongos logfile with mplotqueries, you can simply run:

    mplotqueries mongod.log

