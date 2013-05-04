# Tutorial for mplotqueries

### Introduction

mplotqueries is a tool to visualize operations in MongoDB logfiles. It is part of the [mtools](README.mk) collection.
Before you can use mplotqueries, make sure you have [installed mtools](../INSTALL.md) as well as numpy and matplotlib. 
These dependencies are necessary in order for mplotqueries to work. You can find detailed instructions on the [install](../INSTALL.md) page.

## Basic Usage

mplotqueries is a command line tool that takes a logfile or several logfiles and visualizes the log lines in a 2D plot, where the x-axis is the date and time of an event, and the y-axis is the duration of an event. By default, mplotqueries only visualizes timed loglines, i.e. those that have a duration at the end, specified in milliseconds. A typical log line that is a timed event could look like this:

    Thu Feb 21 03:25:44 [conn5] command admin.$cmd command: { writebacklisten: ObjectId('5124bdb43bd5f630b542ff68') } ntoreturn:1 keyUpdates:0  reslen:44 300000ms
    
These "writebacklisten" commands are an essential part of a sharded setup, and their duration is often "300000ms", or 5 minutes. (If you don't see where the number 300000ms comes from, scroll to the far right of the line.) Their purpose is described on MongoDB's manual page on [sharding](http://docs.mongodb.org/manual/faq/sharding/#what-does-writebacklisten-in-the-log-mean).


### Plotting Duration of Operations in the Logfile

To plot a mongod or mongos logfile with mplotqueries, you can simply run:

    mplotqueries mongod.log

After parsing the logfile, you should see a window pop up that displays the queries, similar to this:

<img src="https://www.dropbox.com/s/g2yo84gevif9z12/mplotqueries-tutorial-1.png?dl=1">

On the x-axis we see the date and time of the events. This particular logfile seems to go from February 20-21. The y-axis represents the duration of events in milliseconds.

Here we already run into our first problem. Most of the operations in MongoDB have sub-second duration, and we can see points on the bottom of the plot, but they are all squashed together. Unfortunately, the logfile also contains these writebacklisten messages, that are known to run for (comparatively) long times, 5 minutes. We can savely ignore those and focus on the "real" events.


### Navigating the Main Window

To navigate within a mplotqueries plot (which, by the way, uses [matplotlib](http://matplotlib.org/) to create the plots), you can use the tool palette at the bottom of the plot:

<img src="https://www.dropbox.com/s/6y8bxqq157chpz9/mplotqueries-tutorial-2.png?dl=1">

The first symbol, the house, takes you back to the initial view, the one you see when the plot first opens. The two arrows on its side are like back and forward buttons in a browser. They let you navigate step by step backward or forward in the history of views. The crossed arrows next to it let you pan around in the plot, by click-dragging the mouse anywhere in the plot area. This lets you move the plot to a different position. The magnifying glass lets you draw a rectangle, that you want to zoom into. This is probably the most useful feature, as you can zoom into very small regions to see what happens close up. The button next to it is for subplot and margin configuration and not very useful in mplotqueries. Finally, the rightmost button, the floppy disk, lets you export your plot into a number of formats. A file dialog will pop up, and depending how you choose your file ending (e.g. `.pdf`, `.png`, `.jpg`), the exporter will write the correct format. Feel free to play around with each of these actions now to get a feel for navigating within a plot.

Another thing you will have noticed by now is the legend in the top left corner. This shows the different "groups", that your plot contains. By default, the plot is grouped into namespaces, showing each namespace (database and collection, spearated by a period) in a different color. If you run out of colors, mplotqueries will also use different symbols (squares, diamonds, etc.) to help you distinguish your groups. We will talk about groups again further down in this tutorial, but for now let's just mention that you can change the grouping by using the parameter `--group <option>`, where `<option>` can for example be `namespace`, `operation`, `thread`, and some others.

Back to the problem from above. Since we are only interested in the short events, let's use the zoom function to get a closer look. I'd like to include all points that are not at the 5 minute mark, and choose to zoom in on the y-axis to have 130 seconds at the top. This cuts of the blue writebacklisteners but still includes my two outliers (in red). The view is a little better, but without cutting off the outliers there's still not much to see at the bottom of the plot.

### More Tricks: `--log`, pipes and combinations with mlogfilter

This is where the `--log` option to plot the y-axis on a logarithmic scale really helps. mplotquery's default is a linear axis, but `--log` forces it to use a log scale, which is very useful to find outliers. Let's close this plot window and start a new one with this option. And while we're at it, we may as well get rid of these writebacklisten points for good. We could use 

    grep -v "writebacklisten" mongod.log | mplotqueries

to filter out all lines that contain the word "writebacklisten" and send the remaining ones to mplotqueries. As you see, mplotqueries doesn't just accept logfiles, you can also pipe a stream of loglines to it. There is a also another alternative. We know that those writebacklisten commands are all admin commands, and their namespace in the logfile is therefore `admin.$cmd`. `mlogfilter` has an option to exclude certain namespaces, so we could run 

    mlogfilter mongod.log --namespace "admin.\$cmd" --exclude | mplotqueries
    
The result looks like this:

<img src="https://www.dropbox.com/s/rrhgxcw5ghnd50d/mplotqueries-tutorial-3.png?dl=1">

Two things of notice: we have to escape the `$` sign, because the shell would otherwise interpret $cmd as a shell variable. And the colors have changed now, because mplotqueries plots the groups in the same order of colors. Since we just removed the first group "admin.$cmd", all groups move one step up in the order of colors.


### Interactive Mode

Now we see the outliers, but also get more detail on the bottom, thanks to the logarithmic scale. But we still don't know what these outliers are. In order to find that out we can use the interactive mode of mplotqueries. First, make sure that you're not in "zoom" or "pan" mode anymore. Check that the buttons at the bottom are not pushed in. If one of them is, click it again to toggle.

Now we can actually click on individual points. Go ahead and click on one of the outlier points. The result will be displayed at the command line from where you started mplotqueries. You will likely see something similar to:

<img src="https://www.dropbox.com/s/i2l9vbx0dldhcxb/mplotqueries-tutorial-4.png?dl=1">

The first two blocks were already there before we even clicked in the plot. The first block shows you an overview of the groups and the number of points that each contains. The second block is just a remainder that you can use the numeric keys to toggle individual plots on and off. Go and try it out: The keys [1-9] toggle the first 9 groups of a plot from visible to invisible and vice versa. The 0 key toggles all plots. Make sure that the focus is on the plot window, and not on the shell, or this won't work.

The line that appeared after we clicked on one of the outliers is the one below that. mplotqueries outputs the exact log line that matches the point in the graph. Here we can see that this particular event was a "getmore" that returned close to 140,000 documents and took about 70 seconds. 

## Advanced features

The earlier versions of `mplotqueries` only had one type of plot: the one we used above, called a "duration" plot, because it plots the durations of log lines. Since then, mplotqueries has grown and now supports a number of different plot types as well as some other features, like grouping and multi-file plotting. When making the tool more general and adding more features, it was always a focus to keep the basic usage as easy as it was at the beginning. The idea was to develop a more abstract, general model, but keep the existing behavior as a "special case", which would plot a simple "duration" plot by default if no other options were specified. Since you are now quite familiar with the basic usage of `mplotqueries`, it's time to move to the more advanced features.


### Group By Different Attributes

Most of the time, we find a root cause for an unknown problem by comparing certain things to each other, with the goal of finding outliers. Very generally speaking, we do that by grouping items together, based on similarities in one attribute, and we contrast them with items that are different in the selected attribute. In `mplotqueries`, we call these attributes `groups`, and we can group by different attributes with the `--group` parameter. By default, the group attribute is on `namespace`. If you go back to the first screenshots at the beginning of this tutorial, you will see in the legend that the different colors (groups) are on `namespace`. In this specific case, we're dealing with a GridFS instance, therefore we have namespaces "a.fs.chunks" and "a.fs.files", as well as "local.oplog.rs" and a pseudo-namespace called "admin.$cmd". Each group contains all log lines that have the same namespace, and each group is displayed in a different color. If we want to use a different group, we can do something like this:

    mplotqueries mongod.log --group operation
    
<img src="https://www.dropbox.com/s/j266bo6v9lgi9ai/mplotqueries-tutorial-6.png?dl=1">

Now we can see different aspects of the same logfile, for example that most of the operations on Feb 20 were queries, while they were getmores, inserts, removes and very few updates on Feb 21. It's easy to spot what different groups there are in a plot by looking at the legend, which lists them all and assigns a color to them.

Another attribute that can be used for grouping is `thread`. This creates an individual group for each thread, for example `[LockPinger]`,`[rsSync]`, etc. and one combined group for all regular connections `[conn####]`, where #### is a number. Future plot types may have additional attributes that they can group by. 


### Multiple files

Sometimes the information we'd like to visualize is spread over several log files. `mplotqueries` lets you specify any number of files at the command line, not just a single one. If you specify more than one log file, then the plot is automatically grouped by a special group attribute, the _filename_. This makes it easy to compare different log files without plotting them all individually.

<img src="https://www.dropbox.com/s/0k7dz29zvcx4gic/mplotqueries-tutorial-7.png?dl=1">


### Plot Types

`mplotqueries` can plot a number of different plot types, which can be selected by the `--type` command line parameter. If no type is specified, a `duration` plot is selected by default. This is why we didn't have to worry about it in the examples above. Currently, there are 3 basic plot types: `duration`, `event`, and `range`. Those three types represent different styles of plotting information. The `duration` plot prints dots on a 2D graph, where the x-axis is the date and time and the y-axis is the duration of the plotted line. This implies that a `duration` plot can only plot timed operations that have a duration (i.e. something like `1563ms` at the end of the line). 

The `event` plot doesn't have that requirement. It can plot any event in the log file, with or without duration, and it does so with a vertical line at the respective time the event happened. Plotting a whole log file as an `event` plot doesn't make much sense, you probably wouldn't be able to see individual lines anymore because there are so many. The idea behind the `event` plot is to filter out certain events, with `grep` or `mlogfilter`, and to only plot these few events. Let's look at an example:

Assume we know that there were some slow `serverStatus` messages in the logfile, and we want to know when those happened. Slow `serverStatus` warnings look like this:

    Thu Feb 21 08:44:18 [conn2283] serverStatus was very slow: { after basic: 0, middle of mem: 650, after mem: 650, after connections: 650, after extra info: 650, after counters: 650, after repl: 650, after asserts: 650, after dur: 1080, at end: 1080 }

They all say "serverStatus was very slow" and then list a number of values for how long different sections of the server status command took. Let's grep all those and make an `event` plot out of them.

    grep "serverStatus was very slow" mongod.log | mplotqueries --type event
    
This results in some sort of barcode style plot that shows when exactly those slow serverStatus events occured. We can quickly see that there were more than usual just at the end of Feb 20. 

<img src="https://www.dropbox.com/s/wjo0tc67rbtljd4/mplotqueries-tutorial-5.png?dl=1">

Of course this works with all kinds of different events. One could grep for assertions, replica set state changes, server restarts, etc and pipe the remaining log lines into `mplotqueries --type event`. And just as with the markers of duration plots, the lines of event plots are clickable and output the log line to each event to stdout.

The third basic plot type is the `range` plot. A range plot displays time periods, or ranges, as horizontal bars. This is useful to see how long certain events took, or when their first and last appearance in the log occurred. Let's see what happens if we use the same log file and plot it as a range plot instead:

    mplotqueries mongod.log --type range
    
    

## To Be Continued...

This concludes part I of the mplotqueries tutorial. Next time, we will talk about groups in more detail, about overlay plots, and how you can plot events that don't have a duration. Watch this page for part II.

