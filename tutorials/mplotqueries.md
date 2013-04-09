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

On the x-axis we see the date and time of the events. This particular logfile seems to go from February 20-21. The y-axis represents the duration of events in milliseconds.

And we already run into our first problem. Most of the operations in MongoDB have sub-second duration, and we can see points on the bottom of the plot, but they are all squashed together. Unfortunately, the logfile also contains these writebacklisten messages, that are known to run for (comparatively) long times, 5 minutes. We can savely ignore those and focus on the "real" events.


### Navigating the Main Window

To navigate within a mplotqueries plot (which, by the way, uses [matplotlib](http://matplotlib.org/) to create the plots), you can use the tool palette at the bottom of the plot:

<img src="https://www.dropbox.com/s/6y8bxqq157chpz9/mplotqueries-tutorial-2.png?dl=1">

The first symbol, the house, takes you back to the initial view, the one you see when the plot first opens. The two arrows on its side are like back and forward buttons in a browser. They let you navigate step by step backward or forward in the history of views. The crossed arrows next to it let you pan around in the plot, by click-dragging the mouse anywhere in the plot area. This lets you move the plot to a different position. The magnifying glass lets you draw a rectangle, that you want to zoom into. This is probably the most useful feature, as you can zoom into very small regions to see what happens close up. The button next to it is for subplot and margin configuration and not very useful in mplotqueries. Finally, the rightmost button, the floppy disk, lets you export your plot into a number of formats. A file dialog will pop up, and depending how you choose your file ending (e.g. `.pdf`, `.png`, `.jpg`), the exporter will write the correct format. Feel free to play around with each of these actions now to get a feel for navigating within a plot.

Another thing you will have noticed by now is the legend in the top left corner. This shows the different "groups", that your plot contains. By default, the plot is grouped into namespaces, showing each namespace (database and collection, spearated by a period) in a different color. If you run out of colors, mplotqueries will also use different symbols (squares, diamonds, etc.) to help you distinguish your groups. We will talk about groups again further down in this tutorial, but for now let's just mention that you can change the grouping by using the parameter `--group <option>`, where `<option>` can be one of the following: `namespace`, `operation`, `thread`.

Back to the problem from above. Since we are only interested in the short events, let's use the zoom function to get a closer look. I'd like to include all points that are not at the 5 minute mark, and choose to zoom in on the y-axis to have 130 seconds at the top. This cuts of the blue writebacklisteners but still includes my two outliers (in red). The view is a little better, but without cutting off the outliers there's still not much to see at the bottom of the plot.

### More Command Line Parameters: `--log`, `--exclude-ns` and pipes

This is where the `--log` option to plot the y-axis on a logarithmic scale really helps. mplotquery's default is a linear axis, but `--log` forces it to use a log scale. Perfect for outliers. Let's close this plot window and start a new one with this option. And while we're at it, we may as well get rid of these writebacklisten points for good. We could use 

    grep -v "writebacklisten" mongod.log | mplotqueries

to filter out all lines that contain the word "writebacklisten" and send the remaining ones to mplotqueries. As you see, mplotqueries doesn't just accept logfiles, you can also pipe a stream of loglines to it. However, for our case there is a simpler alternative. We know that those writebacklisten commands are all admin commands, and their namespace in the logfile is therefore `admin.$cmd`. mplotqueries supports to in- or exclude namespaces directly. Inclusion (`--ns`) means that only the specified namespaces are plotted, and exclusion (`--exclude-ns`) means that __all but__ the specified namespaces are plotted. Let's test this:

    mplotqueries mongod.log --exclude-ns "admin.\$cmd" --log
    
The result looks like this:

<img src="https://www.dropbox.com/s/rrhgxcw5ghnd50d/mplotqueries-tutorial-3.png?dl=1">

Two things of notice: we have to escape the `$` sign, because the shell would otherwise interpret $cmd as a shell variable. And the colors have changed now, because mplotqueries plots the groups in the same order of colors. Since we just removed the first group "admin.$cmd", all groups move one step up in the order of colors.


### Interactive Mode

Now we see the outliers, but also get more detail on the bottom, thanks to the logarithmic scale. But we still don't know what these outliers are. In order to find that out we can use the interactive mode of mplotqueries. First, make sure that you're not in "zoom" or "pan" mode anymore. Check that the buttons at the bottom are not pushed in. If one of them is, click it again to toggle.

Now we can actually click on individual points. Go ahead and click on one of the outlier points. The result will be displayed at the command line from where you started mplotqueries. You will likely see something similar to:

<img src="https://www.dropbox.com/s/i2l9vbx0dldhcxb/mplotqueries-tutorial-4.png?dl=1">

