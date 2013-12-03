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
import json,codecs,os,glob,time,dateutil.parser,community,collections,itertools,pylab
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import interactive
from operator import itemgetter
import networkx as nx

class alternativeranking:
    @classmethod
    def from_json(cls,dataset_path,timeSeg):
        '''Make temp folder if non existant'''

        #Get filenames from json dataset path
        files = glob.glob(dataset_path+"/data/json/*.json")
        files.sort(key=os.path.getmtime)

        '''Parse the json files into authors/mentions/alltime/ lists'''
        authors,mentions,alltime,retweets,retwCount,retwalltime=[],[],[],[],[],[]
        verified,nonVerified=[],[]
        counter=0
        for filename in files:
            my_file=open(filename,"r")
            read_line=my_file.readline()
            while read_line:
                json_line=json.loads(read_line)
                if "delete" in json_line or "scrub_geo" in json_line or "limit" in json_line:
                    read_line=my_file.readline()
                    continue
                else:
                    counter+=1
                    if json_line["user"]["screen_name"]:
                        dt=dateutil.parser.parse(json_line["created_at"])
                        mytime=int(time.mktime(dt.timetuple()))
                        if json_line["user"]["verified"]==True:
                            verified.append(json_line["user"]["screen_name"])
                        else:
                            nonVerified.append(json_line["user"]["screen_name"])
                        if "retweeted_status" in json_line:
                            retweets.append(json_line["retweeted_status"]["user"]["screen_name"])
                            retwCount.append(json_line["retweeted_status"]['retweet_count'])
                            retwalltime.append(mytime)
                        if json_line["entities"]["user_mentions"]:
                            len_ment=len(json_line["entities"]["user_mentions"])
                            for i in range(len_ment):
                                authors.append(json_line["user"]["screen_name"])
                                mentions.append(json_line["entities"]["user_mentions"][i]["screen_name"])
                                alltime.append(mytime)                            
                read_line=my_file.readline()
            else:
                my_file.close()
        verified=list(set(verified))
        nonVerified=list(set(nonVerified))
        print('length of mentions is: '+str(len(authors))+' , length of retweets is: '+str(len(retweets))+' and length of posts is: '+str(counter))
        print('length of verified is: '+str(len(verified))+' and of nonVerified is: '+str(len(nonVerified)))        
        return cls(authors,mentions,alltime,retweets,dataset_path,timeSeg,retwCount,retwalltime,verified)

    def __init__(self,authors,mentions,alltime,retweets,dataset_path,timeSeg,retwCount,retwalltime,verified):
        self.authors=authors
        self.mentions=mentions
        self.alltime=alltime
        self.retweets=retweets
        self.dataset_path=dataset_path
        self.timeSeg=timeSeg
        self.uniqueUsers={}
        self.userPgRnkBag={}
        self.commPgRnkBag={}
        self.commStrBag={}
        self.commNumBag={}
        self.degreeBag={}
        self.mentionBag={}
        self.retweetBag={}
        self.retwCount=retwCount
        self.retwalltime=retwalltime
        self.verified=verified

    def extraction(self):
        '''Extract adjacency lists,mats,user and community centrality and communities bags'''

        #Compute the first derivative and the point of timeslot separation
        firstderiv,mentionLimit=self.timeslotselection(self.authors,self.mentions,self.alltime)

        #Split time according to the first derivative of the users' activity#
        sesStart,timeslot,timeLimit,twsesStart=0,0,[],0
        retwPlot=[]
        mentPlot=[]
        print("Forming timeslots")
        for k in range(len(mentionLimit)):
            if firstderiv[k]<0 and firstderiv[k+1]>=0:
                #make timeslot timelimit array
                timeLimit.append(self.alltime[int(mentionLimit[k])])
                # fileNum='{0}'.format(str(timeslot).zfill(2))
                # print("Forming Timeslot Data "+str(timeslot)+" at point "+str(k))
                sesEnd=int(mentionLimit[k]+1)

                tmpmentPlot=len(self.mentions[sesStart:sesEnd])
                mentPlot.append(tmpmentPlot)

                if k==len(mentionLimit)-1:
                    twsesEnd = len(self.retwalltime)-1
                else:
                    if int(mentionLimit[k]+1) in self.alltime:
                        twsesEnd=self.retwalltime.index(self.alltime[int(mentionLimit[k]+1)])
                    else:
                        smtmp=self.alltime[int(mentionLimit[k]+1)]
                        while smtmp not in self.retwalltime:
                            smtmp+=1
                        twsesEnd=self.retwalltime.index(smtmp)
                #Create dictionary of retweets per timeslot per user
                tmpretweets=self.retweets[twsesStart:twsesEnd]
                tmpretwCount=self.retwCount[twsesStart:twsesEnd]
                tmpFullRetw=zip(tmpretweets,tmpretwCount)
                tmpretweetBag={}
                tmpretwPlot=0
                for rtwat,rtwCnt in tmpFullRetw:
                    # if rtwat:
                    if rtwat not in tmpretweetBag:
                        tmpretweetBag[rtwat]=rtwCnt
                        tmpretwPlot+=1
                    else:
                        tmpretweetBag[rtwat]+=rtwCnt
                        tmpretwPlot+=1
                self.retweetBag[timeslot]=tmpretweetBag
                twsesStart=twsesEnd
                retwPlot.append(tmpretwPlot)

                #Make pairs of users with weights
                usersPair=list(zip(self.authors[sesStart:sesEnd],self.mentions[sesStart:sesEnd]))

                #Create weighted adjacency list
                weighted=collections.Counter(usersPair)
                weighted=list(weighted.items())
                adjusrs,weights=zip(*weighted)
                adjauthors,adjments=zip(*adjusrs)
                adjList=list(zip(adjauthors,adjments,weights))

                #Construct networkX graph
                tempDiGraph=nx.DiGraph()
                tempDiGraph.add_weighted_edges_from(adjList)
                tempDiGraph.remove_edges_from(tempDiGraph.selfloop_edges())
                tempGraph=nx.Graph()
                tempGraph.add_weighted_edges_from(adjList)
                tempGraph.remove_edges_from(tempGraph.selfloop_edges())

                #Extract the centrality of each user using the PageRank algorithm
                tempUserPgRnk=nx.pagerank(tempDiGraph,alpha=0.85,max_iter=100,tol=0.001)
##                maxPGR=max((pgr for k,(pgr) in tempUserPgRnk.items()))
##                for k in tempUserPgRnk.items():
##                    tempUserPgRnk[k[0]]/=maxPGR
                self.userPgRnkBag[timeslot]=tempUserPgRnk

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

                #Construct a graph using the communities as users
                tempCommGraph=community.induced_graph(new_partition,tempDiGraph)

                #Detect the centrality of each community using the PageRank algorithm
                commPgRnk=nx.pagerank(tempCommGraph,alpha=0.85,max_iter=100,tol=0.001)
                maxCPGR=max((cpgr for k,(cpgr) in commPgRnk.items()))
                commPgRnkList=[]
                for key,value in commPgRnk.items():
                    commPgRnkList.append(value)#/maxCPGR)
                self.commPgRnkBag[timeslot]=commPgRnkList

                #Extract community degree and full # of mentions
                degreelist,mentionlist=[],[]
                for k in range(len(tempCommGraph.edge)):
                   tmpdeg=tempCommGraph.degree(k)
                   degreelist.append(tmpdeg)
                   if tmpdeg>0:
                    mentionlist.append(sum(value.get('weight', 0) for value in tempCommGraph.edge[k].values())-tempCommGraph.edge[k][k]['weight'])
                   else:
                    mentionlist.append(0)


                self.degreeBag[timeslot]=degreelist
                self.mentionBag[timeslot]=mentionlist


                '''Construct Community Dictionary'''
                self.commStrBag[timeslot]=strComms
                self.commNumBag[timeslot]=numComms
                sesStart=sesEnd
                timeslot+=1
        pylab.figure()
        plt.plot(retwPlot)
        # plt.show()
        pylab.savefig(self.dataset_path+"/data/results/alternative/retwPlot.pdf",bbox_inches='tight')
        pylab.figure()
        plt.plot(mentPlot)
        # plt.show()
        pylab.savefig(self.dataset_path+"/data/results/alternative/mentPlot.pdf",bbox_inches='tight')
        print('sum of retweets is: '+str(sum(retwPlot)))
        # plt.close()
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


    def evol_detect(self,prevTimeslots):
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
        #uniCommIdsEvol is structured as such {'Id':[rowAppearence],[commDegree],[commSize],[users],[commMentions]}
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
                                uniCommIdsEvol[commIds[prevrow][maxIdx]]=[[],[],[],[],[],[]]
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][0].append(prevrow)#timeslot num for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][2].append(commSizeBag[prevrow][maxIdx])#community size per timeslot for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][3].append(self.commStrBag[prevrow][maxIdx])#users in each community for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][1].append(self.degreeBag[prevrow][maxIdx])#community degree for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][4].append(self.mentionBag[prevrow][maxIdx])#community mentions for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][5].append(self.commPgRnkBag[prevrow][maxIdx])#community pagerank for first evolution
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][0].append(rows)#timeslot num
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][2].append(commSizeBag[rows][clmns])#community size per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][3].append(self.commStrBag[rows][clmns])#users in each community
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][1].append(self.degreeBag[rows][clmns])#community degree per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][4].append(self.mentionBag[rows][clmns])#community mentions per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][5].append(self.commPgRnkBag[rows][clmns])#community pagerank per timeslot
                            commIds[rows].append(commIds[prevrow][maxIdx])
                            break
                if maxval<thres:
                    birthcounter+=1
                    commIds[rows].append(str(rows)+','+str(clmns))
        uniCommIds=list(set(tempUniCommIds))
        uniCommIds.sort()
        self.uniCommIds=uniCommIds
        self.uniCommIdsEvol=uniCommIdsEvol
        self.timeslots=timeslots
        print(str(birthcounter)+" births, "+str(evolcounter)+" evolutions and "+str(len(uniCommIds))+" dynamic communities")
        return self

    def commRankingAltCombo(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,verified):
        tempcommRanking={}
        #structure: tempcommRanking={Id:[degreeness,mentioness,sizeness]}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            tempcommRanking[Id]=[]
            tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][1])/timeslots)
            tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][4])/timeslots)
            tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][2])/timeslots)
            commRanking[Id]=np.prod(tempcommRanking[Id])

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()      
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityAltComboHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityAltComboHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedAltComboComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedCommunities_altCombo.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmpdegree=[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedAltComboComms[strRank]=[rcomms]
            rankedAltComboComms[strRank].append(commRanking[rcomms])
            rankedAltComboComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]

        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community size per slot':uniCommIdsEvol[rcomms][2],
        #     'degree per timeslot':uniCommIdsEvol[rcomms][1],'mentions per timeslot':uniCommIdsEvol[rcomms][4],'avg_size':commRanking[rcomms]})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedAltComboComms,column_labels,validNumList

    def commRankingDegrees(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,verified):
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            commRanking[Id]=sum(uniCommIdsEvol[Id][1])/timeSlLen #timeslots

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels2= list(range(numTopComms))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels2, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False, fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()      
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityDegreeHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityDegreeHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedDegreeComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedCommunities_degrees.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            strRank='{0}'.format(str(rank).zfill(2))
            rankedDegreeComms[strRank]=[rcomms]
            rankedDegreeComms[strRank].append(commRanking[rcomms])
            rankedDegreeComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]

        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community size per slot':uniCommIdsEvol[rcomms][2],
        #     'degree per timeslot':uniCommIdsEvol[rcomms][1],'avg_degrees':commRanking[rcomms]})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedDegreeComms,column_labels,validNumList

    def commRankingMentions(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,verified):
        #structure: commRanking={Id:mentioness}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            commRanking[Id]=sum(uniCommIdsEvol[Id][4])/timeSlLen #timeslots

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels2= list(range(numTopComms))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels2, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityMentionsHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityMentionsHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedMentionsComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedCommunities_mentions.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            strRank='{0}'.format(str(rank).zfill(2))
            rankedMentionsComms[strRank]=[rcomms]
            rankedMentionsComms[strRank].append(commRanking[rcomms])
            rankedMentionsComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]

        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community size per slot':uniCommIdsEvol[rcomms][2],
        #     'mentions per timeslot':uniCommIdsEvol[rcomms][1],'avg_mentions':commRanking[rcomms]})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedMentionsComms,column_labels,validNumList

    def commRankingSize(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,verified):
        #structure: commRanking={Id:sizeness}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            commRanking[Id]=sum(uniCommIdsEvol[Id][2])/timeSlLen #timeslots

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels2= list(range(numTopComms))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels2, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # interactive(False)
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communitySizeHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communitySizeHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedSizeComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedCommunities_size.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            strRank='{0}'.format(str(rank).zfill(2))
            rankedSizeComms[strRank]=[rcomms]
            rankedSizeComms[strRank].append(commRanking[rcomms])
            rankedSizeComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]

        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community size per slot':uniCommIdsEvol[rcomms][2],
        #     'mentions per timeslot':uniCommIdsEvol[rcomms][1],'avg_size':commRanking[rcomms]})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedSizeComms,column_labels,validNumList

    def commRankingRetweets(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,retweetBag,verified):
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
                    if user in retweetBag[tmsl]:
                        retweetness[Id][count]+=retweetBag[tmsl][user]
            commRanking[Id]=np.sum(retweetness[Id])/timeslots

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityRetweetHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityRetweetHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedRetweetsComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedCommunities_retweet.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmpretweets,tmslUsrs=[],[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedRetweetsComms[strRank]=[rcomms]
            rankedRetweetsComms[strRank].append(commRanking[rcomms])
            rankedRetweetsComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl,users in enumerate(uniCommIdsEvol[rcomms][3]):
                usretweet=[]
                for us in users:
                    if us in retweetBag[uniCommIdsEvol[rcomms][0][tmsl]]:
                        usretweet.append([us,retweetBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                    else:
                        usretweet.append([us,0])
                usretweet = sorted(usretweet, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]:usretweet})
        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community size per slot':uniCommIdsEvol[rcomms][2],'users:retweetness per timeslot':tmslUsrs})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedRetweetsComms,column_labels,validNumList

    def commRankingRetwBySize(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,retweetBag,verified):
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
                    if user in retweetBag[tmsl]:
                        retweetness[Id][count]+=retweetBag[tmsl][user]
                retweetness[Id][count]/=len(usergroup)
            commRanking[Id]=np.sum(retweetness[Id])/timeSlLen

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityRetwBySizeHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityRetwBySizeHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedRetwBySizeComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedCommunities_retwBySize.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmpretweets,tmslUsrs=[],[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedRetwBySizeComms[strRank]=[rcomms]
            rankedRetwBySizeComms[strRank].append(commRanking[rcomms])
            rankedRetwBySizeComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl,users in enumerate(uniCommIdsEvol[rcomms][3]):
                usretweet=[]
                for us in users:
                    if us in retweetBag[uniCommIdsEvol[rcomms][0][tmsl]]:
                        usretweet.append([us,retweetBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                    else:
                        usretweet.append([us,0])
                usretweet = sorted(usretweet, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]:usretweet})
        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community size per slot':uniCommIdsEvol[rcomms][2],'users:retweetness per timeslot':tmslUsrs})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedRetwBySizeComms,column_labels,validNumList

    def commPSCRRanking(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,userPgRnkBag,verified):
        tempcommRanking={}
        #structure: tempcommRanking={Id:[persistence,stability,commCentrality]}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            tempcommRanking[Id]=[]
            tempcommRanking[Id].append(timeSlLen/timeslots)#persistence
            tempcommRanking[Id].append((sum(np.diff(list(set(uniCommIdsEvol[Id][0])))==1)+1)/(timeslots+1))#stability
            tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][5])/timeSlLen)#commCentrality
            commRanking[Id]=np.prod(tempcommRanking[Id])

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels2= list(range(numTopComms))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels2, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityPSCRHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityPSCRHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedPSCRComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedPSCRCommunities.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmslUsrs=[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedPSCRComms[strRank]=[rcomms]
            rankedPSCRComms[strRank].append(commRanking[rcomms])
            rankedPSCRComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl,users in enumerate(uniCommIdsEvol[rcomms][3]):
                uscentr=[]
                for us in users:
                    uscentr.append([us,userPgRnkBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                uscentr = sorted(uscentr, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]:uscentr})
        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'persistence:':tempcommRanking[rcomms][0],
        #     'stability':tempcommRanking[rcomms][1],'community centrality':tempcommRanking[rcomms][2],'community size per slot':uniCommIdsEvol[rcomms][2],'users:centrality per timeslot':tmslUsrs})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedPSCRComms,column_labels,validNumList

    def commPersistenceRanking(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,userPgRnkBag,verified):
        tempcommRanking={}
        #structure: tempcommRanking={Id:[persistence,stability,commCentrality]}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            tempcommRanking[Id]=[]
            tempcommRanking[Id].append(timeSlLen/timeslots)#persistence
            commRanking[Id]=tempcommRanking[Id]

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels2= list(range(numTopComms))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels2, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityPersistenceHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityPersistenceHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedPersistenceComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedPersistenceCommunities.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmslUsrs=[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedPersistenceComms[strRank]=[rcomms]
            rankedPersistenceComms[strRank].append(commRanking[rcomms])
            rankedPersistenceComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl,users in enumerate(uniCommIdsEvol[rcomms][3]):
                uscentr=[]
                for us in users:
                    uscentr.append([us,userPgRnkBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                uscentr = sorted(uscentr, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]:uscentr})
        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'persistence:':tempcommRanking[rcomms][0],
        #     'community size per slot':uniCommIdsEvol[rcomms][2],'users:centrality per timeslot':tmslUsrs})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedPersistenceComms,column_labels,validNumList

    def commStabilityRanking(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,userPgRnkBag,verified):
        tempcommRanking={}
        #structure: tempcommRanking={Id:[persistence,stability,commCentrality]}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            tempcommRanking[Id]=[]
            tempcommRanking[Id].append((sum(np.diff(list(set(uniCommIdsEvol[Id][0])))==1)+1)/(timeslots+1))#stability
            commRanking[Id]=tempcommRanking[Id]

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap
        row_labels = list(range(timeslots))
        column_labels2= list(range(numTopComms))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels2, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityStabilityHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityStabilityHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedStabilityComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedStabilityCommunities.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmslUsrs=[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedStabilityComms[strRank]=[rcomms]
            rankedStabilityComms[strRank].append(commRanking[rcomms])
            rankedStabilityComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl,users in enumerate(uniCommIdsEvol[rcomms][3]):
                uscentr=[]
                for us in users:
                    uscentr.append([us,userPgRnkBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                uscentr = sorted(uscentr, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]:uscentr})
        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,
        #     'stability':tempcommRanking[rcomms][0],'community size per slot':uniCommIdsEvol[rcomms][2],'users:centrality per timeslot':tmslUsrs})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedStabilityComms,column_labels,validNumList

    def commCentralityRanking(uniCommIds,uniCommIdsEvol,timeslots,timeLimit,dataset_path,numTopComms,userPgRnkBag,verified):
        tempcommRanking={}
        #structure: tempcommRanking={Id:[persistence,stability,commCentrality]}
        commRanking={}
        for Id in uniCommIds:
            timeSlLen=len(set(uniCommIdsEvol[Id][0]))
            tempcommRanking[Id]=[]
            tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][5])/timeSlLen)#commCentrality
            commRanking[Id]=np.prod(tempcommRanking[Id])

        rankedCommunities= sorted(commRanking, key=commRanking.get,reverse=True)

        #Extract validated number of users
        validNumList=[]
        for Id in rankedCommunities:
            allUsrsDynComm=sum(uniCommIdsEvol[Id][3], [])
            allUsrsDynComm=list(set(allUsrsDynComm))
            verfdCount=0
            for usr in allUsrsDynComm:
                if usr in verified:
                    verfdCount+=1
            validNumList.append(verfdCount)

        #Construct heatmap        
        row_labels = list(range(timeslots))
        column_labels2= list(range(numTopComms))
        column_labels= rankedCommunities[0:numTopComms]
        # commSizeHeatData=np.zeros([len(rankedCommunities),timeslots])
        # for rCIdx,comms in enumerate(rankedCommunities[0:numTopComms]):
        #     for sizeIdx,timesteps in enumerate(uniCommIdsEvol[comms][0]):
        #         if commSizeHeatData[rCIdx,timesteps]!=0:
        #             commSizeHeatData[rCIdx,timesteps]=max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx,timesteps])
        #         else:
        #             commSizeHeatData[rCIdx,timesteps]=np.log(uniCommIdsEvol[comms][2][sizeIdx])
        # fig, ax = plt.subplots()
        # heatmap=ax.pcolormesh(commSizeHeatData,cmap=plt.cm.gist_gray_r)
        # ax.set_xticks(np.arange(commSizeHeatData.shape[1]), minor=False)
        # ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # plt.xlim(xmax=(timeslots))
        # plt.ylim(ymax=(len(rankedCommunities[0:numTopComms])))
        # plt.ylabel("Ranked Communities (Best "+str(numTopComms)+")")
        # plt.xlabel('Timeslot',{'verticalalignment':'top'})
        # ax.invert_yaxis()
        # ax.xaxis.tick_top()
        # ax.set_xticklabels(row_labels, minor=False)
        # ax.set_yticklabels(column_labels2, minor=False,fontsize=7)
        # ax2 = ax.twinx()
        # ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        # ax2.set_yticklabels(column_labels, minor=False,fontsize=7)
        # ax2.invert_yaxis()
        # if numTopComms<101:
        #     plt.grid(axis='y')
        # plt.tight_layout()
        # mng = plt.get_current_fig_manager()
        # mng.resize(*mng.window.maxsize())
        # interactive(False)
        # # plt.show()
        # pylab.savefig(dataset_path+"/data/results/alternative/communityCentralityHeatmap.pdf",bbox_inches='tight')
        # # fig.savefig(dataset_path+"/data/results/alternative/communityCentralityHeatmap.pdf",bbox_inches='tight',format='pdf')
        # plt.close()

        '''Writing ranked communities to json files'''
        rankedCentralityComms={}
        twitterDataFile = open(dataset_path+'/data/results/alternative/rankedCentralityCommunities.json', "w")
        jsondata=dict()
        jsondata["ranked_communities"]=[]
        for rank,rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmslUsrs=[]
            strRank='{0}'.format(str(rank).zfill(2))
            rankedCentralityComms[strRank]=[rcomms]
            rankedCentralityComms[strRank].append(commRanking[rcomms])
            rankedCentralityComms[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp=[timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl,users in enumerate(uniCommIdsEvol[rcomms][3]):
                uscentr=[]
                for us in users:
                    uscentr.append([us,userPgRnkBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                uscentr = sorted(uscentr, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]:uscentr})
        #     jsondata["ranked_communities"].append({'community label':rcomms,'rank':rank+1,'timeslot appearance':timeSlotApp,'community centrality':tempcommRanking[rcomms][0]
        #     ,'community size per slot':uniCommIdsEvol[rcomms][2],'users:centrality per timeslot':tmslUsrs})
        # twitterDataFile.write(json.dumps(jsondata, sort_keys=True))
        # twitterDataFile.close()
        return rankedCentralityComms,column_labels,validNumList