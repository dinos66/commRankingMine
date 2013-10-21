#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:
# Purpose:       This .py file extracts adjacency lists and detects communities
#                from the corresponding timeslots.
#
# Required libs: python-dateutil,pyparsing,numpy,matplotlib,networkx
# Author:        konkonst
#
# Created:       20/08/2013
# Copyright:     (c) ITI (CERTH) 2013
# Licence:       <apache licence 2.0>
#-------------------------------------------------------------------------------
import json,codecs,os,glob,time,dateutil.parser,community,collections,itertools
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import interactive
from operator import itemgetter
import networkx as nx

class retweetcomparison:
    @classmethod
    def from_json(cls,dataset_path,timeSeg):
        '''Make temp folder if non existant'''

        #Get filenames from json dataset path
        files = glob.glob(dataset_path+"/data/GDD/json/*.json")
        files.sort(key=os.path.getmtime)

        '''Parse the json files into authors/mentions/alltime/tags/tweetIds/text lists'''
        authors,mentions,alltime,retweets=[],[],[],[]
        counter=0
        for filename in files:
            my_file=open(filename,"r")
            read_line=my_file.readline()
            while read_line:
                json_line=json.loads(read_line)
                if json_line["entities"]["user_mentions"] and json_line["user"]["screen_name"]:
                    len_ment=len(json_line["entities"]["user_mentions"])
                    dt=dateutil.parser.parse(json_line["created_at"])
                    mytime=int(time.mktime(dt.timetuple()))
                    for i in range(len_ment):
                        authors.append(json_line["user"]["screen_name"])
                        mentions.append(json_line["entities"]["user_mentions"][i]["screen_name"])
                        alltime.append(mytime)
                        if "retweeted_status" in json_line:
                            retweets.append(json_line["retweeted_status"]["user"]["screen_name"])
                        else:
                            retweets.append([])
                read_line=my_file.readline()
            else:
                my_file.close()
        return cls(authors,mentions,alltime,retweets,dataset_path,timeSeg)

    def __init__(self,authors,mentions,alltime,retweets,dataset_path,timeSeg):
        self.authors=authors
        self.mentions=mentions
        self.alltime=alltime
        self.retweets=retweets
        self.dataset_path=dataset_path
        self.timeSeg=timeSeg
        self.uniqueUsers={}
        self.commStrBag={}
        self.commNumBag={}
        self.retweetBag={}
        self.rankedCommunities={}

    def extraction(self):
        '''Extract adjacency lists,mats,user and community centrality and communities bags'''

        #Compute the first derivative and the point of timeslot separation
        firstderiv,mentionLimit=self.timeslotselection(self.authors,self.mentions,self.alltime)

        #Split time according to the first derivative of the users' activity#
        sesStart,timeslot,timeLimit=0,0,[]
        print("Forming timeslots")
        for k in range(len(mentionLimit)):
            if firstderiv[k]<0 and firstderiv[k+1]>=0:
                #make timeslot timelimit array
                timeLimit.append(self.alltime[int(mentionLimit[k])])
                fileNum='{0}'.format(str(timeslot).zfill(2))
                # print("Forming Timeslot Data "+str(timeslot)+" at point "+str(k))
                sesEnd=int(mentionLimit[k]+1)

                #Make pairs of users with weights
                usersPair=list(zip(self.authors[sesStart:sesEnd],self.mentions[sesStart:sesEnd]))

                #Create weighted adjacency list
                weighted=collections.Counter(usersPair)
                weighted=list(weighted.items())
                adjusrs,weights=zip(*weighted)
                adjauthors,adjments=zip(*adjusrs)
                adjList=list(zip(adjauthors,adjments,weights))

                #Create dictionary of retweets per timeslot per user
                tmpretweets=self.retweets[sesStart:sesEnd]
                tmpretweetBag={}
                for rtwat in tmpretweets:
                    if rtwat:
                        if rtwat not in tmpretweetBag:
                            tmpretweetBag[rtwat]=1
                        else:
                            tmpretweetBag[rtwat]+=1
                self.retweetBag[timeslot]=tmpretweetBag

                #Construct networkX graph
                tempDiGraph=nx.DiGraph()
                tempDiGraph.add_weighted_edges_from(adjList)
                tempDiGraph.remove_edges_from(tempDiGraph.selfloop_edges())
                tempGraph=nx.Graph()
                tempGraph.add_weighted_edges_from(adjList)
                tempGraph.remove_edges_from(tempGraph.selfloop_edges())

                #Detect Communities using the louvain algorithm#
                partition = community.best_partition(tempGraph)
                inv_partition = {}
                for k, v in partition.items():
                    inv_partition[v] = inv_partition.get(v, [])
                    inv_partition[v].append(k)
                    inv_partition[v].sort()
                strComms=[inv_partition[x] for x in inv_partition]
                strComms.sort(key=len,reverse=True)

                #Construct Communities of uniqueUsers indices and new community dict with size sorted communities
                numComms,new_partition=[],{}
                for c1,comms in enumerate(strComms):
                    numpart=[]
                    for ids in comms:
                        numpart.extend(self.uniqueUsers[ids])
                        new_partition[ids]=c1
                    numComms.append(numpart)
                newinv_partition = {}
                for k, v in new_partition.items():
                    newinv_partition[v] = newinv_partition.get(v, [])
                    newinv_partition[v].append(k)
                    newinv_partition[v].sort()

                '''Construct Community Dictionary'''
                self.commStrBag[timeslot]=strComms
                self.commNumBag[timeslot]=numComms
                sesStart=sesEnd
                timeslot+=1

        self.timeLimit=[time.ctime(int(x)) for x in timeLimit]

    def timeslotselection(self,authors,mentions,alltime):
        ###Parsing commences###

        #Extract unique users globally and construct dictionary
        usrs=list(set(np.append(authors,mentions)))
        usrs.sort()
        uniqueUsers,counter1={},0
        for tmpusrs in usrs:
            uniqueUsers[tmpusrs]=[counter1]
            counter1+=1
        self.uniqueUsers=uniqueUsers

        #Find time distance between posts#
        time2=np.append(alltime[0],alltime)
        time2=time2[0:len(time2)-1]
        timeDif=alltime-time2
        lT=len(alltime)

        ###Extract the first derivative###
        seg= self.timeSeg
        curTime,bin,freqStat,mentionLimit=0,0,[0],[]
        for i in range(lT):
            curTime+=timeDif[i]
            if curTime<=seg:
                freqStat[bin]+=1
            else:
                curTime=0
                mentionLimit=np.append(mentionLimit,i)
                bin+=1
                freqStat=np.append(freqStat,0)
        mentionLimit=np.append(mentionLimit,i)

        freqStatIni=np.zeros(len(freqStat)+1)
        freqStatMoved=np.zeros(len(freqStat)+1)
        freqStatIni[0:len(freqStat)]=freqStat
        freqStatMoved[1:len(freqStat)+1]=freqStat
        firstderiv=freqStatIni-freqStatMoved
        firstderiv[len(firstderiv)-1]=0
        return firstderiv,mentionLimit

    def evol_detect(self,numTopComms,prevTimeslots):
        self.extraction()
        """Construct Community Dictionary"""
        commNumBag2={}
        commSizeBag={}
        timeslots=len(self.commNumBag)
        lC=[] #Number of communities>2people for each timeslot
        for cBlen in range(timeslots):
            commNumBag2[cBlen]=[x for x in self.commNumBag[cBlen] if len(x)>2]
            commSizeBag[cBlen]=[len(x) for x in self.commNumBag[cBlen] if len(x)>2]
            lC.append(len(commNumBag2[cBlen]))

        commIds=[]
        # name the first line of communities
        commIds.append([])
        birthcounter=0
        for j in range(lC[0]):
            # commIds[str(0)+","+str(j)]=str(0)+','+str(j)
            commIds[0].append(str(0)+','+str(j))
            birthcounter+=1
        #Detect any evolution and name the evolving communities
        #uniCommIdsEvol is structured as such {'Id':[rowAppearence],[commCentrality],[commSize],[users]}
        tempUniCommIds,evolcounter,uniCommIdsEvol=[],0,{}
        print('Community similarity search for each timeslot: ')
        for rows in range(1,timeslots):
            # print('Community similarity search for timeslot: '+str(rows))
##            commIds[rows]=[]
            commIds.append([])
            for clmns in range(lC[rows]):
                idx=str(rows)+","+str(clmns)
                bag1=commNumBag2[rows][clmns]
                tempcommSize=len(bag1)
                if tempcommSize<=7 and tempcommSize>2:
                    thres=.41
                elif tempcommSize<=11 and tempcommSize>7:
                    thres=.27
                elif tempcommSize<=20 and tempcommSize>11:
                    thres=.2
                elif tempcommSize<=49 and tempcommSize>20:
                    thres=.15
                elif tempcommSize<=99 and tempcommSize>49:
                    thres=.125
                elif tempcommSize<=499 and tempcommSize>99:
                    thres=.1
                else:
                    thres=.05
                for invrow in range(1,prevTimeslots+1):
                    prevrow=rows-invrow
                    tmpsim=[]
                    if prevrow>=0:
                        for prevComms in commNumBag2[prevrow]:
                            if thres>(len(prevComms)/tempcommSize):
                                break
                            elif thres>(tempcommSize/len(prevComms)):
                                tmpsim.append(0)
                                continue
                            else:
                                tmpsim.append(len(list(set(bag1) & set(prevComms)))/len(set(np.append(bag1,prevComms))))
                        if tmpsim:
                            maxval=max(tmpsim)
                        else:
                            maxval=0
                        if maxval>=thres:
                            evolcounter+=1
                            maxIdx=tmpsim.index(maxval)
                            tempUniCommIds.append(commIds[prevrow][maxIdx])
                            if commIds[prevrow][maxIdx] not in uniCommIdsEvol:
                                uniCommIdsEvol[commIds[prevrow][maxIdx]]=[[],[],[],[]]
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][0].append(prevrow)#timeslot num for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][2].append(commSizeBag[prevrow][maxIdx])#community size per timeslot for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][3].append(self.commStrBag[prevrow][maxIdx])#users in each community for first evolution
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][0].append(rows)#timeslot num
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][2].append(commSizeBag[rows][clmns])#community size per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][3].append(self.commStrBag[rows][clmns])#users in each community
                            commIds[rows].append(commIds[prevrow][maxIdx])
                            break
                if maxval<thres:
                    birthcounter+=1
                    commIds[rows].append(str(rows)+','+str(clmns))
        uniCommIds=list(set(tempUniCommIds))
        uniCommIds.sort()
        # return (jaccdict,maxCommSimPercentage,lC)
        print(str(birthcounter)+" births, "+str(evolcounter)+" evolutions and "+str(len(uniCommIds))+" dynamic communities")

        retweetness={}
        #structure: retweetness={Id:[retweetness]}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            retweetness[Id]=[]
            for count,usergroup in enumerate(uniCommIdsEvol[Id][3]):
                tmsl= uniCommIdsEvol[Id][0][count]
                retweetness[Id].append(0)
                for user in usergroup:
                    if user in self.retweetBag[tmsl]:
                        retweetness[Id][count]+=self.retweetBag[tmsl][user]
            commRanking[Id]=np.sum(retweetness[Id])/timeslots#timestimeSlLen

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        row_labels = list(range(timeslots))
        column_labels= rankedCommunities[0:100]
        commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        for rCIdx,comms in enumerate(rankedCommunities[0:100]):
            for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
                if commSizeHeatData[rCIdx,timesteps]!=0:
                    commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
                else:
                    commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        fig, ax = plt.subplots()
        heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        plt.xlim(xmax=(timeslots))
        plt.ylim(ymax=(len(rankedCommunities[0:100])))
        plt.ylabel("Ranked Communities (Best 100)")
        plt.xlabel('Timeslot',{'verticalalignment':'top'})
        ax.invert_yaxis()
        ax.xaxis.tick_top()
        ax.set_xticklabels(row_labels, minor=False)
        ax.set_yticklabels(column_labels, minor=False,fontsize=7)
        ax2 = ax.twinx()
        ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        ax2.invert_yaxis()
        plt.grid(axis='y')
        plt.tight_layout()
        interactive(False)
        plt.show()
        fig.savefig(self.dataset_path+"/data/GDD/results/communityRetweetHeatmap.pdf",bbox_inches='tight',format='pdf')
        plt.close()

        '''Writing ranked communities to json files'''
        rankedCommunitiesFinal={}
        twitterDataFile = open(self.dataset_path+'/data/GDD/results/rankedCommunities_retweet.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmpretweets,tmslUsrs=[],[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedCommunitiesFinal[strRank]=[rcomms]
            rankedCommunitiesFinal[strRank].append(commRanking[rcomms])
            rankedCommunitiesFinal[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[self.timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl,users in enumerate(uniCommIdsEvol[rcomms][3]):
                usretweet=[]
                for us in users:
                    if us in self.retweetBag[uniCommIdsEvol[rcomms][0][tmsl]]:
                        usretweet.append([us,self.retweetBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                    else:
                        usretweet.append([us,0])
                usretweet = sorted(usretweet, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]:usretweet})
            jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community size per slot':uniCommIdsEvol[rcomms][2],'users:retweetness per timeslot':tmslUsrs})
        twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        twitterDataFile.close()
        return rankedCommunitiesFinal
