# gr-perf-analyser
A python script to poll values from the ControlPort in GNU Radio and saves it as a python-dict log. This can be re-used to plot the performance counters in various ways. The behaviour of the script can be tweaked from the perf_config.yaml file.

Currently the script supports -
- plotting 2D graphs 
	- in a snapshot view i.e., values of all the blocks for a particular timestamp (performance counter value vs block no.)
	- block view i.e., all performance counters of a specified block for the duration of the saved log (performance counter value vs time)
- plotting 3D graphs
	- latency/total time of all the blocks across the duration of the saved log (block no. vs latency vs time)
	- input & output buffer occupancy of all blocks across the duration of the saved log (block no. vs buffer occupancy vs time)
### Performance Counters
Every GNU Radio block that is written with **gr::block** inherits the performance counters and can be read with the help of an interface like Apache Thrift. Currently GNU Radio supports average, instantaneous and variance values for different performance counters for every block -
- average - avg input % full, avg noutput_items, avg nproduced, avg output % full, avg throughput, avg work time
- instantaneous - input % full, noutput_items, nproduced, output % full, work time, total work time
- variance - var input % full, var noutput_items, var nproduced, var output % full, var work time
More information on the GNU Radio [wiki](https://wiki.gnuradio.org/index.php/Performance_Counters)
### Requirements
#### 1. Apache Thrift
For the script to read values from Control Port, Apache Thrift should be installed before building GNU Radio. Apache Thrift version 0.13.0 is the one that is currently tested. Checkout the v0.13.0 tag from the [git repo](https://github.com/apache/thrift/tree/v0.13.0) and follow the instructions in the installation [page](https://thrift.apache.org/docs/BuildingFromSource). Also make sure to install the [required packages](https://thrift.apache.org/docs/install/) beforehand.
#### 2. Additional packages
Make sure to update matplotlib to atleast v3.10. A simple `pip install matplotlib` should be enough.
#### 3. GNU Radio
Now build GNU Radio from source with `-DENABLE_CTRLPORT_THRIFT=ON` and `-DENABLE_PERFORMANCE_COUNTERS=ON` flags when running the cmake command. For more information refer installation [page](https://wiki.gnuradio.org/index.php?title=LinuxInstall#From_Source).
```bash
cmake -DCMAKE_BUILD_TYPE=Release -DPYTHON_EXECUTABLE=/usr/bin/python3 -DENABLE_CTRLPORT_THRIFT=ON -DENABLE_PERFORMANCE_COUNTERS=ON ../
```

After the install, edit the config file to enable Control Port and Performance Counters at /usr/local/etc/gnuradio/conf.d/gnuradio-runtime.conf
This is how the changed values should look like -
```
[PerfCounters]
on = 1
export = 1
clock = thread
#clock = monotonic

[ControlPort]
on = 1
edges_list = 1
```

### Configuration
- The tool can be configured to run as a logger or as a plotter by changing `type_of_operation: plot`
- The logfile to either save or read data can be given as `logfile_path: /path/to/logfile`
#### Plotter
Plotter needs the hostname, port number to connect to the Thrift server and should be changed once GNU Radio starts the server and the values are available.
#### Logger
- Logger can be configure to display 
	- 2D plots for either avg, inst or var value types. If 
		- `all_blocks: 1` then it will give a snapshot of all the blocks for every performance counter. 
		- the parameter is set as '0', you need set `search_blk: 43` to a block ID and it will display the performance counters for the entire duration of saved log.
	- 3D plots to see instantaneous latency, total work time or buffer values for all the blocks for the entire duration of saved log.

