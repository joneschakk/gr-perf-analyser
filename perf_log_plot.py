import sys, json, time, datetime, yaml
from collections import OrderedDict  
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as dt
import matplotlib.dates
import matplotlib.ticker
from gnuradio.ctrlport.GNURadioControlPortClient import GNURadioControlPortClient

perf_labels_avg = ["avg input % full", "avg noutput_items", "avg nproduced", 
            "avg output % full", "avg throughput", "avg work time"]
perf_labels_inst = ["input % full", "noutput_items", "nproduced", 
            "output % full", "work time", "total work time"]
perf_labels_var = ["var input % full", "var noutput_items", "var nproduced", 
            "var output % full", "var work time"]
AVG = 0
INST = 1
VAR = 3
ALL = 4
val_type_to_enum = {"avg":AVG,"inst":INST,"var":VAR,"all":ALL}

perf_labels = {}
perf_labels[AVG] = perf_labels_avg
perf_labels[INST] = perf_labels_inst
perf_labels[VAR] = perf_labels_var

class Logger:
    #readmode for the type of perfcounters & to be saved in the logfile
    AVG = 0
    INST = 1
    VAR = 3
    ALL = 4

    def __init__(self, host, port, logfile, poll_intrvl = 10, readmode = AVG):
        self.host = host
        self.port = port
        self.logfile = logfile
        self.mode = val_type_to_enum[readmode]      
        self.val_dict_avg = {k: [] for k in perf_labels_avg}
        self.sleep = poll_intrvl
        GNURadioControlPortClient(host, port, 'thrift', self.get_performance_counters)
        pass

    def get_performance_counters(self,client):
            
        # try:
            # Connect to the GNU Radio application
            blocks = []
            keystring = []
            knobs = client.getKnobs([])

            for k,v in knobs.items():
                keystring = k.split("::")                
                #discard edge list entries made for flow graph plot
                if not "edge list" in keystring[1]:
                    if keystring[1] in perf_labels_avg:                        
                        if not len(blocks):
                            blocks.append(keystring[0])                            
                        elif blocks[-1] != keystring[0]:                            
                            blocks.append(keystring[0])

                        self.val_dict_avg[keystring[1]].append(v.value)
                        
            with open(self.logfile,'w', encoding='utf-8') as f:
                json.dump(blocks,f)

            #### after sleep
            try:
                while 1:
                    #reading more values from the GNURadio fg(flowgraph)
                    if self.mode == self.AVG or self.mode == self.ALL:
                        self.update_val_dict(blocks,client,self.AVG)                        
                        
                    if self.mode == self.INST or self.mode == self.ALL:
                        self.update_val_dict(blocks,client,self.INST)
                        
                    if self.mode == self.VAR or self.mode == self.ALL:
                        self.update_val_dict(blocks,client,self.VAR)
                    
                    time.sleep(self.sleep)
                    
            except KeyboardInterrupt:
                print('Program interrupted!')

    def update_val_dict(self, blocks, client, mode):
        if mode == self.INST:
            temp = {"inst."+k: [] for k in perf_labels[mode]}
        else:
            temp = {k: [] for k in perf_labels[mode]}
        val_dict = {}

        for key in perf_labels[mode]:
            kl = list(map(lambda x: "%s::%s"% (x,key), blocks))
            knobs = client.getKnobs(kl)
            if mode == self.INST:
                # helps in reading back values in plotter
                key = "inst."+key
            for k,v in knobs.items():                
                temp[key].append(v.value)

        time = datetime.datetime.now()
        val_dict[str(time)] = temp

        with open(self.logfile,'a', encoding='utf-8') as f:
            f.write('\n')
            json.dump(val_dict,f)
                  
def plt_plotter(config):
    # pyqt = 1
    ylabels = ["Percentage","Num of items","Num of items","Percentage","nS","nS"]
    ylabels_avg  = {k:y for (k,y) in zip(perf_labels_avg,ylabels)}
    ylabels_inst = {k:y for (k,y) in zip(perf_labels_inst,ylabels)}
    ylabels_var = {k:y for (k,y) in zip(perf_labels_var,ylabels)}
    ylabel_dict = {"avg":ylabels_avg,"inst":ylabels_inst,"var":ylabels_var}

    val_type_lut = {"avg":perf_labels_avg,
                    "inst":perf_labels_inst,
                    "var":perf_labels_var}
    #do multi lines in the file for dict with timestamp key
    # which contains avg, inst, var
    # for loop the lines in the file to read each dict
    blocks =[]
    val_flat = []    
    blocklist = []
    timestamp_list = []
    #read config param
    logfile = config['logfile_path'] 
    val_type = config['plotter']['val_type']
    search_blk = config['plotter']['search_blk']
    all_blks = False
    if config['plotter']['all_blocks']:
        all_blks =True
    else:
        val_flat = {k:[] for k in val_type_lut[val_type]}
    plot3d = config["plotter"]["type"]
    
    try:
        if plot3d == "2d":
            if all_blks:
                tot_lines = 0
                curr_line = 0
                #just count num lines so to read from the last line, 
                #avg value will be more meaningfull from the las timestamp
                with open(logfile, 'r', encoding='utf-8') as r:
                    for line in r:
                        tot_lines+=1
            with open(logfile, 'r', encoding='utf-8') as r:
                for line in r:
                    log_dict = json.loads(line)
                    if type(log_dict) is list: # if counter == 0:
                        # read all the blocks from logfile
                        blocklist = log_dict
                    elif all_blks: #snapshot from the last timestamp
                        curr_line+=1
                        if curr_line >= tot_lines -3:
                            (timestamp,perf_dict), = log_dict.items()
                            for perf_cntr, val_list in perf_dict.items():
                                if not val_type in perf_cntr:
                                    # break and go to next line in log as we didnt get the 
                                    # expected value type (perf_cntr)
                                    break
                                blocks = []
                                val_flat = [] 
                                if 'inst' in perf_cntr:
                                    perf_cntr = perf_cntr.split('.')[1]                       
                                if "% full" in perf_cntr:
                                    bidx = 0
                                    for perf_val, blk in zip(val_list,blocklist):
                                        if len(perf_val) == 0:
                                            # sometimes the list will be empty, so the corner case is 
                                            # managed by appending that block & inserting '0' as the value
                                            blocks.append(blk+' ('+str(bidx)+')')
                                            perf_val = [0]
                                        else:
                                            # if there is a list for buffer bcoz there are multiple inputs/outputs
                                            for postfix in range(len(perf_val)):    
                                                blocks.append(blk+':'+str(postfix)+' ('+str(bidx)+')')
                                        val_flat.extend(perf_val)
                                        bidx+=1
                                else:
                                    val_flat = val_list
                                    blocks = [blk+' ('+str(bidx)+')' for bidx, blk in enumerate(blocklist)]
                                
                                fig, ax = plt.subplots()                                    
                                bar_colors = ['tab:red', 'tab:blue', 'tab:red', 'tab:orange']
                                ax.bar(blocks, val_flat,  color=bar_colors)
                                ax.set_ylabel(ylabel_dict[val_type][perf_cntr])
                                ax.set_title(perf_cntr+" (at "+timestamp+")")            
                                plt.xticks(rotation=90)            
                                plt.subplots_adjust(bottom=0.3)  # Adjust the bottom margin
                                plt.show()
                    else: #plotting a specific blk for the whole timestamps
                        # dict is time:perf_label/cntr:[list of perf values]                    
                        (timestamp,perf_dict), = log_dict.items()                        
                        time_read = 0
                        for perf_cntr, val_list in perf_dict.items():
                            if not val_type in perf_cntr:
                                # break and go to next line in log as we didnt get the 
                                # expected value type (perf_cntr)
                                break
                            else:
                                if 'inst' in perf_cntr:
                                    perf_cntr = perf_cntr.split('.')[1]                          
                                if not time_read:
                                    timestamp_list.append(timestamp)#append(timest)
                                    time_read =1
                                if "% full" in perf_cntr:
                                    # if the search was blk id in the config file
                                    if type(search_blk) is int:
                                        perf_val = val_list[search_blk]
                                    else: #if name of blk was given
                                        perf_val = val_list[blocklist.index(search_blk)]

                                    if len(perf_val) == 0:
                                        # sometimes the list will be empty, similar to the else part
                                        # only diff is that the xaxis is time and specific to only 1 blk 
                                        perf_val = [0]
                                        val_flat[perf_cntr].append(perf_val)
                                    else:
                                        if not len(val_flat[perf_cntr]):                                        
                                            val_flat[perf_cntr] = [ [x] for x in perf_val]
                                        else:
                                            for x in range(len(perf_val)):
                                                val_flat[perf_cntr][x].append(perf_val[x])                      
                                else:
                                    if type(search_blk) is int:
                                        val_flat[perf_cntr].append(val_list[search_blk])                                        
                                    else:
                                        val_flat[perf_cntr].append(val_list[blocklist.index(search_blk)])                            
                        
            # matplotlib 2d plots for specific blk
            if not all_blks:
                timeaxis = []
                day = timestamp_list[0].split(" ")[0]
                # formatting the timestamp stored in logfile to datetime format to plot
                for x in timestamp_list:
                    timeaxis.append((datetime.datetime.strptime(x,"%Y-%m-%d %H:%M:%S.%f")))
                dt_xticks = [ dt.date2num(timeaxis[0]+((timeaxis[-1]-timeaxis[0])/10)*x) for x in range(10)]

                for perf_cntr, vals in val_flat.items():      
                    fig, ax = plt.subplots()
                    bar_colors = ['red', 'blue']
                    
                    if '% full' in perf_cntr:
                        for x in range(len(vals)):
                            plt.plot(timeaxis, vals[x], label="buffer"+str(x))
                            ax.set_yticks(np.arange(0,1.1,.1))
                    else:
                        plt.plot(timeaxis, vals)
                        ax.set_yticks(np.arange(0,max(vals)*(1.1),max(vals)/10))
                    ax.set_xticks(dt_xticks)  
                    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))

                    ax.set_ylabel(ylabel_dict[val_type][perf_cntr])
                    ax.set_title(str(search_blk)+" "+perf_cntr+" on "+day)            
                    plt.xticks(rotation=90)            
                    plt.subplots_adjust(bottom=0.3)  # Adjust the bottom margin

                    plt.show()
    
    # time - [timestamps]
    # block_val -
    #           blk1 -
    #               perf1 - [list]
    #               perf2 - [list]
     
        else: #3d plots
            lat = config["plotter"]["3dplot_type"]          
            if config["plotter"]["3dplot_type"] == 1:
                lat_totwrk = "inst.work time"
            elif config["plotter"]["3dplot_type"] == 2:
                lat_totwrk = "inst.total work time"
            time_axes = []#{"time":[], "block_val":{}}
            block_axes=[]
            blocklist_n_buff = OrderedDict()
            blocklist_n_buff = {"latency" : {}, "out_buff" : {}, "in_buff" : {}, "out_blk" : [], "in_blk" : []}
            with open(logfile,'r') as file:
                for line in file:
                    log_dict = json.loads(line)
                    if type(log_dict) is list: # if counter == 0:
                        # read all the blocks from logfile
                        blocklist = log_dict
                        # for x in blocklist:
                        #     time_axes["block_val"][x] = {"latency" : [], "out_buff" : [], "in_buff" : []}
                    else:
                        # dict is time:perf_label/cntr:[list of perf values]                    
                        (timestamp,perf_dict), = log_dict.items()                       
                        if "inst.total work time" in perf_dict.keys():                            
                            time_axes.append((datetime.datetime.strptime(timestamp,"%Y-%m-%d %H:%M:%S.%f")))                            
                            for idx, blk in enumerate(blocklist):                                
                                if blk in blocklist_n_buff["latency"].keys() :
                                    if lat:
                                        blocklist_n_buff["latency"][blk].append(perf_dict[lat_totwrk][idx]/1000) #from high_res_timer.h tps conversion (uS)
                                    
                                    for x, buff_val in enumerate(perf_dict["inst.output % full"][idx]):
                                        blocklist_n_buff["out_buff"][blk+":"+str(x)].append(buff_val)
                                    for x, buff_val in enumerate(perf_dict["inst.input % full"][idx]):
                                         blocklist_n_buff["in_buff"][blk+":"+str(x)].append(buff_val)
                                else:
                                    #if its the first iteration
                                    if lat:
                                        blocklist_n_buff["latency"][blk] = [perf_dict[lat_totwrk][idx]/1000]
                                    
                                    for x, buff_val in enumerate(perf_dict["inst.output % full"][idx]):                                        
                                        blocklist_n_buff["out_buff"][blk+":"+str(x)] = [buff_val]
                                    for x, buff_val in enumerate(perf_dict["inst.input % full"][idx]):
                                        blocklist_n_buff["in_buff"][blk+":"+str(x)] = [buff_val]
                            
                timestamp_list = [ (x-time_axes[0]).total_seconds() for x in time_axes]
                # Create a 3D figure
                if lat:
                    fig, ax = plt.subplots(1,1,subplot_kw={'projection':'3d'})
                else:
                    fig, ax = plt.subplots(1,2,subplot_kw={'projection':'3d'})

                # facecolors = plt.colormaps['viridis_r'](np.linspace(.1, 1, len(blocklist)))
                facecolors = ['r','b','y']
                cntr = 0
                if lat:
                    for blk, p_val in blocklist_n_buff["latency"].items():                
                        ax.plot(cntr, timestamp_list, p_val, color=facecolors[cntr%3])#facecolors[cntr])
                        ax.fill_between(cntr, timestamp_list, p_val,  
                                        cntr, timestamp_list, 0, 
                                        facecolors=facecolors[cntr%3], linewidth=0, alpha=.5)
                        block_axes.append(blk)
                        cntr+=1
                else:
                    buff_list = ["out_buff", "in_buff"]
                    block_axes = [[],[]]
                    for idx, x_buff in enumerate(buff_list):
                        cntr=0
                        bkp_cntr=-1                   
                        block =""
                        
                        for blk, p_val in blocklist_n_buff[x_buff].items():
                            # if idx == 0:
                            #     print(blk)
                            if block != blk.split('-')[0]:
                                bkp_cntr+=1
                                sub_cntr=0
                                block = blk.split('_')[0]
                            ax[idx].plot(cntr, timestamp_list, p_val, color=facecolors[bkp_cntr%3])#facecolors[cntr])
                            ax[idx].fill_between(cntr, timestamp_list, p_val,  
                                            cntr, timestamp_list, 0, 
                                            facecolors=facecolors[bkp_cntr%3], linewidth=0, alpha=.5)
                            block_axes[idx].append(blk)
                            cntr+=1
                            # sub_cntr+=1           
            with open('blocklist.log','w') as log:
                for j, blk in enumerate(blocklist_n_buff["latency"].keys()):
                    log.write(str(j)+':'+blk)
                for j, blk in enumerate(blocklist_n_buff["out_buff"].keys()):
                    log.write(str(j)+':'+blk)
                for j, blk in enumerate(blocklist_n_buff["in_buff"].keys()):
                    log.write(str(j)+':'+blk)
            if lat:
                ax.set_xlabel('Blocks')
                ax.set_ylabel('Time(s)')
                ax.set_zlabel('Latency(us)')
                ax.yaxis.set_inverted(1)
                ax.view_init(elev=22, azim=130)
                ax.title.set_text('Latency')
                ax.set_xticks([x for x in range(len(blocklist_n_buff["latency"].items()))])
                ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=3))
                if config['plotter']['xticks'] == 'name':
                    ax.set_xticklabels(block_axes,rotation=80)
                
            else:
                for i in range(2):
                    # ax[i].set_xlabel('Blocks')
                    ax[i].set_xticks([x for x in range(len(block_axes[i]))])
                    if config['plotter']['xticks'] == 'name':
                        ax[i].set_xticklabels(block_axes[i],rotation=80)
                    ax[i].xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(base=3))
                    # ax[i].xticks(rotation=90)  
                    ax[i].set_ylabel('Time(s)')
                    ax[i].set_zlabel('Percent')
                    ax[i].yaxis.set_inverted(1)
                    ax[i].view_init(elev=22, azim=130)
                ax[0].title.set_text('Output Buffer')
                ax[1].title.set_text('Input Buffer')

            # plt.xticks(rotation=90)
            plt.show()                   
    except KeyboardInterrupt:
        pass


def main():
    print(sys.argv[1])
    config_filepath = sys.argv[1]
    with open(config_filepath,'r') as file:
        config = yaml.safe_load(file)

    if config['type_of_operation'] == 'plot':
        print("Plotting w/ mode:%s from %s"%
              (config['plotter']['val_type'],config['logfile_path']))
        plt_plotter(config)
    else:
        
        host = config['perf_logger']['host']
        port = config['perf_logger']['port']
        mode = config['perf_logger']['val_type']
        logfile = config['logfile_path']
        interval = config['perf_logger']['interval']
        print("Logging from ctrl-port host:%s port:%d w/ mode:%s in %s"%
              (host,port,mode,logfile))
        Logger(host, port, logfile, interval, mode)
        

if __name__ == "__main__":
    main()
