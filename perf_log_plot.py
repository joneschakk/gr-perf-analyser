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
                else:
                    # print(v)
                    edge_list = str(v).split("=")[1][1:-2].split("\n")
                    # print(a_list)
                
            with open(self.logfile,'w', encoding='utf-8') as f:
                json.dump(edge_list,f)
                # f.write('\n')
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

class graph:
    def __init__(self, blklist):
        self.nodes = []
        self.neigbhours = []
        self.normalise_nodes(blklist)
        pass
    
    def normalise_nodes(self, blklist):
        neigbhours = []
        for edge in blklist:
            a_node = edge.split('->')[0].split(":")[0]
            b_node = edge.split('->')[1].split(":")[0]
            self.neigbhours.append([a_node,b_node])
            self.nodes.append(a_node)
            self.nodes.append(b_node)
        print(self.neigbhours)
        

    def get_neigbhours(self,node):
        neigbhour_list=[]
        for edge in self.neigbhours:
            if node == edge[0]:
                neigbhour_list.append(edge[1])
        print("nei",neigbhour_list)
        return neigbhour_list
    
    def traverse(self, start_blk):
        start_node = start_blk
        
        if start_node is not None:
            if start_node not in self.nodes:
                print("Error!! No start node")
                sys.exit(0)
                # return []

        stack = set()
        stack.add(start_node)
        nodes_visited = []

        while stack:
            curr_blk = stack.pop()
            nodes_visited.append(curr_blk)
            for downstream_blk in self.get_neigbhours(curr_blk):
                if downstream_blk not in nodes_visited:
                    stack.add(downstream_blk)
        
        print("yoyo",nodes_visited)

def plot_2d(config):
    
    ylabels = ["Percentage","Num of items","Num of items","Percentage","nS","nS"]
    ylabel_avg = ["Percentage","Num of items","Num of items","Percentage","items/s","nS"]
    ylabels_avg  = {k:y for (k,y) in zip(perf_labels_avg,ylabel_avg)}
    ylabels_inst = {k:y for (k,y) in zip(perf_labels_inst,ylabels)}
    ylabels_var = {k:y for (k,y) in zip(perf_labels_var,ylabels)}
    ylabel_dict = {"avg":ylabels_avg,"inst":ylabels_inst,"var":ylabels_var}
    val_type_lut = {"avg":perf_labels_avg,
                    "inst":perf_labels_inst,
                    "var":perf_labels_var}
    blocks =[]
    val_flat = []    
    blocklist = []
    timestamp_list = []
    start_node=["randomSrcTdd0","usrp_source"] #edit the name of start nodes
    # TODO move it to config file
    #read config param
    logfile = config['logfile_path'] 
    val_type = config['plotter']['val_type']
    search_blk = config['plotter']['search_blk']
    multiplot = int(config['plotter']['multi_plot'])
    all_blks = False
    tx_or_rx = 0 #default tx
    if config['plotter']['tx_or_rx']:
        tx_or_rx = 1
    if config['plotter']['all_blocks']:
        all_blks =True
        # print("yo")
    else:
        val_flat = {k:[] for k in val_type_lut[val_type]}
    try:
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
                    # print("Yo")
                    # gr_flowgraph = graph(log_dict)
                    # blocklist_ordered = gr_flowgraph.traverse(start_node[tx_or_rx])
                    blocklist_ordered = ['usrp_source0','complex_to_mag_squared1', 'fir_filter_blk<IN_T,OUT_T,TAP_T>1',
                                         'multiply_ff0', 'delay0', 'conjugate_cc0', 'multiply_cc0', 'fir_filter_blk<IN_T,OUT_T,TAP_T>0', 
                                         'complex_to_arg0', 'complex_to_mag_squared0', 'divide0', 'plateau_detector_fb0', 
                                         'sample_and_hold0', 'frequency_modulator_fc0', 'delay1',  
                                         'multiply_cc1', 'header_payload_demux0',
                                         'fft_v_fftw1', 'ofdm_chanest_vcvc0', 'ofdm_frame_equalizer_vcvc1', 'ofdm_serializer_vcc1', 
                                         'constellation_decoder_cb1', 'packet_headerparser_b0', # 'const_sink_c2', 
                                         'fft_v_fftw0', 'ofdm_frame_equalizer_vcvc0', 'ofdm_serializer_vcc0', 'constellation_decoder_cb0', 
                                         'repack_bits_bb0', 'probe_rate0', # 'eye_sink_c0', 
                                         #'time_sink_c1', 
                                         'const_sink_c0', 'time_sink_c0'] #, 'const_sink_c1']


                elif all_blks: #snapshot from the last timestamp
                    curr_line+=1
                    if curr_line >= tot_lines -3: #the last avg value
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
                                # print("Yo")
                                # for perf_val, blk in zip(val_list,blocklist):
                                ###hack code ~~~
                                for ordered_blk in blocklist_ordered:
                                    blk = ordered_blk
                                    search_bidx = blocklist.index(ordered_blk)
                                    perf_val = val_list[search_bidx]
                                    # print(perf_val)
                                ###hack code ^^^
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
                                    # print("Yo",bidx)
                            else:
                                ###hack code ~~~
                                tmp_val_list = []
                                for ordered_blk in blocklist_ordered:
                                    search_bidx = blocklist.index(ordered_blk)
                                    tmp_val_list.append(val_list[search_bidx])
                                val_flat = tmp_val_list
                                blocks = [blk+' ('+str(bidx)+')' for bidx, blk in enumerate(blocklist_ordered)]
                                ###hack code ^^^  
                                # uncomment below                              
                                # val_flat = val_list
                                # blocks = [blk+' ('+str(bidx)+')' for bidx, blk in enumerate(blocklist)]
                            # print("Yo")
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
            blkname = search_blk
            if type(search_blk) is int:
                blkname = blocklist[search_blk]
            timeaxis = []
            day = timestamp_list[0].split(" ")[0]
            # formatting the timestamp stored in logfile to datetime format to plot
            for x in timestamp_list:
                timeaxis.append((datetime.datetime.strptime(x,"%Y-%m-%d %H:%M:%S.%f")))
            dt_xticks = [ dt.date2num(timeaxis[0]+((timeaxis[-1]-timeaxis[0])/10)*x) for x in range(10)]

            if not multiplot:
                for perf_cntr, vals in val_flat.items():      
                    fig, ax = plt.subplots()                      
                    
                    if '% full' in perf_cntr:
                        for x in range(len(vals)):
                            plt.plot(timeaxis, vals[x], label="buffer"+str(x))
                            ax.set_yticks(np.arange(0,1.1,.1))
                    else:
                        plt.plot(timeaxis, vals)
                        if max(vals): #sometimes all the values are zero, then this is pointless
                            ax.set_yticks(np.arange(0,max(vals)*(1.1),max(vals)/10))
                    ax.set_xticks(dt_xticks)  
                    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))
                    
                    ax.set_ylabel(ylabel_dict[val_type][perf_cntr])
                    ax.set_title(str(blkname)+" "+perf_cntr+" on "+day)            
                    plt.xticks(rotation=90)            
                    plt.subplots_adjust(bottom=0.3)  # Adjust the bottom margin

                    plt.show()
            else:
                for perf_cntr, vals in val_flat.items():      
                    if '% full' not in perf_cntr:
                        fig, ax = plt.subplots()                            
                        in_buff_key = perf_labels[val_type_to_enum[val_type]][0]
                        out_buff_key = perf_labels[val_type_to_enum[val_type]][3]
                        ax2 = ax.twinx()

                        ax.plot(timeaxis, vals, color= 'blue')
                        # print(vals)
                        if max(vals): #sometimes all the values are zero, then this is pointless
                            ax.set_yticks(np.arange(0,max(vals)*(1.1),max(vals)/10))
                        for x in range(len(val_flat[in_buff_key])):
                            if len(val_flat[in_buff_key][x]) != 1:
                                ax2.plot(timeaxis, val_flat[in_buff_key][x],color='red')
                        
                        for x in range(len(val_flat[out_buff_key])):
                            # print(val_flat[out_buff_key][x])
                            if len(val_flat[out_buff_key][x]) != 1:
                                ax2.plot(timeaxis, val_flat[out_buff_key][x],color='green')
                        
                        # !!comment this line for a better correlation!!
                        ax2.set_yticks(np.arange(0,1.1,.1))
                        # ^^comment this line for a better correlation^^
                        ax2.legend(['i/p','o/p'])
                        ax.set_xticks(dt_xticks)  
                        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))

                        ax.set_ylabel(ylabel_dict[val_type][perf_cntr])
                        ax.set_title(str(blkname)+" "+perf_cntr+" on "+day)            
                        plt.xticks(rotation=90)            
                        plt.subplots_adjust(bottom=0.3)  # Adjust the bottom margin

                        plt.show()    
    except KeyboardInterrupt:
        pass
              
    return 0

def plot_3d(config):
     #read config param
    logfile = config['logfile_path']    
    lat = config["plotter"]["3dplot_type"]          
    # if config["plotter"]["3dplot_type"] == 1:
    lat_totwrk = "inst.work time"
    # elif
    if config["plotter"]["3dplot_type"] == 2:
        lat_totwrk = "inst.total work time"
    time_axes = []#{"time":[], "block_val":{}}
    block_axes=[]
    blocklist_n_buff = OrderedDict()
    blocklist_n_buff = {"latency" : {}, "out_buff" : {}, "in_buff" : {}}#, "out_blk" : [], "in_blk" : []}
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
                            # if lat:
                            blocklist_n_buff["latency"][blk].append(perf_dict[lat_totwrk][idx]/1000) #from high_res_timer.h tps conversion (uS)
                            
                            for x, buff_val in enumerate(perf_dict["inst.output % full"][idx]):
                                blocklist_n_buff["out_buff"][blk+":"+str(x)].append(buff_val)
                            for x, buff_val in enumerate(perf_dict["inst.input % full"][idx]):
                                    blocklist_n_buff["in_buff"][blk+":"+str(x)].append(buff_val)
                        else:
                            #if its the first iteration
                            # if lat:
                            blocklist_n_buff["latency"][blk] = [perf_dict[lat_totwrk][idx]/1000]
                            
                            for x, buff_val in enumerate(perf_dict["inst.output % full"][idx]):                                        
                                blocklist_n_buff["out_buff"][blk+":"+str(x)] = [buff_val]
                            for x, buff_val in enumerate(perf_dict["inst.input % full"][idx]):
                                blocklist_n_buff["in_buff"][blk+":"+str(x)] = [buff_val]
                                
        timestamp_list = [ (x-time_axes[0]).total_seconds() for x in time_axes]

        # facecolors = plt.colormaps['viridis_r'](np.linspace(.1, 1, len(blocklist)))
        facecolors = ['r','b','y']
        cntr = 0
        if lat: #latency plot
            fig, ax = plt.subplots(1,1,subplot_kw={'projection':'3d'})
            for blk, p_val in blocklist_n_buff["latency"].items():                
                ax.plot(cntr, timestamp_list, p_val, color=facecolors[cntr%3])#facecolors[cntr])
                ax.fill_between(cntr, timestamp_list, p_val,  
                                cntr, timestamp_list, 0, 
                                facecolors=facecolors[cntr%3], linewidth=0, alpha=.5)
                block_axes.append(blk)
                cntr+=1
        else:
            fig, ax = plt.subplots(1,2,subplot_kw={'projection':'3d'})
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
    with open(logfile.split('.')[0]+'blocklist.log','w') as log:
        log.write("Latency\n----------\n")
        for j, blk in enumerate(blocklist_n_buff["latency"].keys()):
            log.write(str(j)+':'+blk+'\n')
        log.write("----------\nO/P Buff\n----------\n")
        for j, blk in enumerate(blocklist_n_buff["out_buff"].keys()):
            log.write(str(j)+':'+blk+'\n')
        log.write("----------\nI/P Buff\n----------\n")
        for j, blk in enumerate(blocklist_n_buff["in_buff"].keys()):
            log.write(str(j)+':'+blk+'\n')
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
    return 0

def plotter(config):
    #do multi lines in the file for dict with timestamp key
    # which contains avg, inst, var
    # for loop the lines in the file to read each dict
    plot3d = config["plotter"]["type"]
    
    try:
        if plot3d == "2d":
            plot_2d(config)             
        # time - [timestamps]
        # block_val -
        #           blk1 -
        #               perf1 - [list]
        #               perf2 - [list]
        else: #3d plots
            plot_3d(config)             
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
        plotter(config)
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
