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
import json, codecs, os, glob, time, dateutil.parser, community, collections, itertools, datetime, pickle
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import interactive
from operator import itemgetter
import networkx as nx


class communityranking:
    @classmethod
    def from_json(cls, dataset_path, timeSeg, simplify_json, rankIrregularTime):
        '''Make temp folder if non existant'''
        if not os.path.exists(dataset_path + "/data/results/forGephi"):
            os.makedirs(dataset_path + "/data/results/forGephi")
        if not os.path.exists(dataset_path + "/data/results/simplified_json"):
            os.makedirs(dataset_path + "/data/results/simplified_json")

        #Get filenames from json dataset path
        files = glob.glob(dataset_path + "/data/json/*.json")
        files.sort(key=os.path.getmtime)

        '''Parse the json files into authors/mentions/alltime/tags/tweetIds/text lists'''
        authors, mentions, alltime, tags, tweetIds, twText, tweetUrls = [], [], [], [], [], [], []
        counter, totTweets, totMentTws, totNonMentTws, totMents, hashes, urlCount = 0, 0, 0, 0, 0, 0, 0
        for filename in files:
            if simplify_json == 1:
                my_txt = open(
                    dataset_path + "/data/results/simplified_json/auth_ment_time_text_" + str(counter) + ".txt",
                    "w")#file containing author mentioned time text
                counter += 1
                # print(filename)
            my_file = open(filename, "r")
            read_line = my_file.readline()
            totTweets += 1
            while read_line:
                json_line = json.loads(read_line)
                if "delete" in json_line or "scrub_geo" in json_line or "limit" in json_line:
                    read_line = my_file.readline()
                    totTweets += 1
                    continue
                else:
                    if json_line["entities"]["user_mentions"] and json_line["user"]["screen_name"]:
                        totMentTws += 1
                        len_ment = len(json_line["entities"]["user_mentions"])
                        dt = dateutil.parser.parse(json_line["created_at"])
                        mytime = int(time.mktime(dt.timetuple()))
                        tmpMents = []
                        for i in range(len_ment):
                            totMents += 1
                            authors.append(json_line["user"]["screen_name"])
                            mentions.append(json_line["entities"]["user_mentions"][i]["screen_name"])
                            alltime.append(mytime)
                            tmpMents.append(json_line["entities"]["user_mentions"][i]["screen_name"])
                            tweetIds.append(json_line["id_str"])
                            twText.append(json_line['text'])
                            if json_line["entities"]["hashtags"]:
                                tmp = []
                                for textIdx in json_line["entities"]["hashtags"]:
                                    hashes += 1
                                    tmp.append(textIdx["text"])
                                tags.append(tmp)
                            else:
                                tags.append([])
                            if json_line["entities"]["urls"]:
                                tmp = []
                                for textIdx in json_line["entities"]["urls"]:
                                    urlCount += 1
                                    tmp.append(textIdx["expanded_url"])
                                tweetUrls.append(tmp)
                            else:
                                tweetUrls.append([])
                        if simplify_json == 1:
                            my_text = json_line["text"].replace("\n", "").replace('\u200F',"").replace('\u2764','').replace('\u2033',"").replace(
                                '\u20aa', "").replace('\x92', "").replace('\u200b', "").replace('\u200e', "").replace(
                                '\u203c', "").replace('\u2002', "").replace('\u2009', "").replace('\u2049',"").replace('\u200a',"").encode()
                            my_txt.write(json_line["user"]["screen_name"] + "\t" + ",".join(tmpMents) + "\t" + "\"" + json_line["created_at"] + "\"" + "\t" + str(my_text) + "\n")
                    else:
                        totNonMentTws += 1
                read_line = my_file.readline()
                totTweets += 1
            else:
                my_file.close()
                if simplify_json == 1:
                    my_txt.close()
        print('Total # of Tweets= ' + str(totTweets) +
              '\nTotal # of Tweets with mentions: ' + str(totMentTws) +
              '\nTotal # of Tweets without mentions: ' + str(totNonMentTws) +
              '\nTotal # of edges: ' + str(totMents) +
              '\nTotal # of hashtags: ' + str(hashes) +
              '\nTotal # of urls: ' + str(urlCount))

        if rankIrregularTime==1:
            zippedall=zip(alltime,authors,mentions,twText, tags, tweetIds, twText, tweetUrls)
            zippedall=sorted(zippedall)
            alltime, authors, mentions, twText, tags, tweetIds, twText, tweetUrls=zip(*zippedall)

        return cls(authors, mentions, alltime, tags, tweetIds, twText, tweetUrls, dataset_path, timeSeg)

    @classmethod
    def from_txt(cls, dataset_path, timeSeg):
        '''Make temp folder if non existant'''
        if not os.path.exists(dataset_path + "/data/results/forGephi"):
            os.makedirs(dataset_path + "/data/results/forGephi")

        #Get filenames from txt dataset path
        files = glob.glob(dataset_path + "/data/txt/*.txt")
        files.sort(key=os.path.getmtime)

        '''Parse the txt files into authors/mentions/alltime lists'''
        authors, mentions, alltime, tags = [], [], [], []
        for filename in files:
            print(filename)
            my_file = open(filename, "r", encoding="utf-8")
            read_line = my_file.readline()
            while read_line:
                read_line = str(read_line)#, encoding='utf8' )
                splitLine = read_line.split("\t")
                dt = dateutil.parser.parse(splitLine[2], fuzzy="True")
                mytime = int(time.mktime(dt.timetuple()))
                tmp = list(set(part[1:] for part in splitLine[3].split() if part.startswith('#')))
                for tmpmentions in splitLine[1].split(","):
                    authors.append(splitLine[0])
                    mentions.append(tmpmentions)
                    alltime.append(mytime)
                    tags.append(tmp)
                read_line = my_file.readline()
            else:
                my_file.close()
        return cls(authors, mentions, alltime, tags, dataset_path, timeSeg)

    def __init__(self, authors, mentions, alltime, tags, tweetIds, twText, tweetUrls, dataset_path, timeSeg):
        self.authors = authors
        self.mentions = mentions
        self.alltime = alltime
        self.tags = tags
        self.tweetIds = tweetIds
        self.twText = twText
        self.tweetUrls = tweetUrls
        self.dataset_path = dataset_path
        self.timeSeg = timeSeg
        self.uniqueUsers = {}
        self.userPgRnkBag = {}
        self.commPgRnkBag = {}
        self.commStrBag = {}
        self.commNumBag = {}
        self.tagBag = {}
        self.tweetIdBag = {}
        self.tweetTextBag = {}
        self.urlBag = {}
        self.degreeBag = {}
        self.commDegreenessBag = {}
        self.commBetweenessBag = {}

    def extraction(self):
        '''Extract adjacency lists,mats,user and community centrality and communities bags'''

        #Compute the first derivative and the point of timeslot separation
        firstderiv, mentionLimit = self.timeslotselection(self.authors, self.mentions, self.alltime)

        #Split time according to the first derivative of the users' activity#
        sesStart, timeslot, timeLimit,commCount = 0, 0, [self.alltime[0]],0
        print("Forming timeslots")
        for k in range(len(mentionLimit)):
            if firstderiv[k] < 0 and firstderiv[k + 1] >= 0:
                #make timeslot timelimit array
                timeLimit.append(self.alltime[int(mentionLimit[k])])
                fileNum = '{0}'.format(str(timeslot).zfill(2))
                # print("Forming Timeslot Data "+str(timeslot)+" at point "+str(k))
                sesEnd = int(mentionLimit[k] + 1)

                #Make pairs of users with weights
                usersPair = list(zip(self.authors[sesStart:sesEnd], self.mentions[sesStart:sesEnd]))

                #Create weighted adjacency list
                weighted = collections.Counter(usersPair)
                weighted = list(weighted.items())
                adjusrs, weights = zip(*weighted)
                adjauthors, adjments = zip(*adjusrs)
                adjList = list(zip(adjauthors, adjments, weights))

                #Write pairs of users to txt file for Gephi
                # my_txt = open(self.dataset_path + "/data/results/forGephi/usersPairs_" + fileNum + ".txt", "w")
                # my_txt.write("Source,Target,Weight" + "\n")
                # for line in adjList:
                #     my_txt.write(",".join(str(x) for x in line) + "\n")
                # my_txt.close()

                #Create dictionary of tags per user
                tmptags = self.tags[sesStart:sesEnd]
                self.tagBag[timeslot] = {}
                for authIdx, auth in enumerate(self.authors[sesStart:sesEnd]):
                    if auth not in self.tagBag[timeslot]:
                        self.tagBag[timeslot][auth] = []
                    elif tmptags[authIdx]:
                        self.tagBag[timeslot][auth].append(tmptags[authIdx])

                #create dictionary of urls per user
                tmpUrls = self.tweetUrls[sesStart:sesEnd]
                self.urlBag[timeslot] = {}
                for authIdx, auth in enumerate(self.authors[sesStart:sesEnd]):
                    if auth not in self.urlBag[timeslot]:
                        self.urlBag[timeslot][auth] = []
                    elif tmpUrls[authIdx]:
                        self.urlBag[timeslot][auth].append(tmpUrls[authIdx])

                #create dictionary of tweet Ids per user
                tmptweetids = self.tweetIds[sesStart:sesEnd]
                self.tweetIdBag[timeslot] = {}
                for authIdx, auth in enumerate(self.authors[sesStart:sesEnd]):
                    if auth not in self.tweetIdBag[timeslot]:
                        self.tweetIdBag[timeslot][auth] = []
                    elif tmptweetids[authIdx]:
                        self.tweetIdBag[timeslot][auth].append(tmptweetids[authIdx])
                for mentIdx, ment in enumerate(self.mentions[sesStart:sesEnd]):
                    if ment not in self.tweetIdBag[timeslot]:
                        self.tweetIdBag[timeslot][ment] = []
                    elif tmptweetids[mentIdx]:
                        self.tweetIdBag[timeslot][ment].append(tmptweetids[mentIdx])

                #create dictionary of text per user
                tmptweetText = self.twText[sesStart:sesEnd]
                self.tweetTextBag[timeslot] = {}
                for authIdx, auth in enumerate(self.authors[sesStart:sesEnd]):
                    if auth not in self.tweetTextBag[timeslot]:
                        self.tweetTextBag[timeslot][auth] = []
                    elif tmptweetText[authIdx]:
                        self.tweetTextBag[timeslot][auth].append(tmptweetText[authIdx])
                for mentIdx, ment in enumerate(self.mentions[sesStart:sesEnd]):
                    if ment not in self.tweetTextBag[timeslot]:
                        self.tweetTextBag[timeslot][ment] = []
                    elif tmptweetText[mentIdx]:
                        self.tweetTextBag[timeslot][ment].append(tmptweetText[mentIdx])

                #Construct networkX graph
                tempDiGraph = nx.DiGraph()
                tempDiGraph.add_weighted_edges_from(adjList)
                tempDiGraph.remove_edges_from(tempDiGraph.selfloop_edges())
                tempGraph = nx.Graph()
                tempGraph.add_weighted_edges_from(adjList)
                tempGraph.remove_edges_from(tempGraph.selfloop_edges())

                #Extract the centrality of each user using the PageRank algorithm
                tempUserPgRnk = nx.pagerank(tempDiGraph, alpha=0.85, max_iter=100, tol=0.001)
                maxPGR=max((pgr for k,(pgr) in tempUserPgRnk.items()))
                for k in tempUserPgRnk.items():
                    tempUserPgRnk[k[0]]/=maxPGR
                self.userPgRnkBag[timeslot] = tempUserPgRnk

                #Detect Communities using the louvain algorithm#
                partition = community.best_partition(tempGraph)
                inv_partition = {}
                for k, v in partition.items():
                    inv_partition[v] = inv_partition.get(v, [])
                    inv_partition[v].append(k)
                    inv_partition[v].sort()
                strComms = [inv_partition[x] for x in inv_partition]
                strComms.sort(key=len, reverse=True)
                commCount+=len(strComms)

                #Construct Communities of uniqueUsers indices and new community dict with size sorted communities
                numComms, new_partition = [], {}
                for c1, comms in enumerate(strComms):
                    numpart = []
                    for ids in comms:
                        numpart.extend(self.uniqueUsers[ids])
                        new_partition[ids] = c1
                    numComms.append(numpart)
                newinv_partition = {}
                for k, v in new_partition.items():
                    newinv_partition[v] = newinv_partition.get(v, [])
                    newinv_partition[v].append(k)
                    newinv_partition[v].sort()

                #Construct a graph using the communities as users
                tempCommGraph = community.induced_graph(new_partition, tempDiGraph)

                #Detect the centrality of each community using the PageRank algorithm
                commPgRnk = nx.pagerank(tempCommGraph, alpha=0.85, max_iter=100, tol=0.001)
                maxCPGR = max((cpgr for k, (cpgr) in commPgRnk.items()))
                commPgRnkList = []
                for key, value in commPgRnk.items():
                    commPgRnkList.append(value/maxCPGR)
                self.commPgRnkBag[timeslot] = commPgRnkList

                #Detect the centrality of each community using the degree centrality algorithm
                commDegreeness = nx.degree_centrality(tempCommGraph)
                maxCDeg = max((cpgr for k, (cpgr) in commDegreeness.items()))
                commDegreenessList = []
                for key, value in commDegreeness.items():
                    commDegreenessList.append(value)#/maxCDeg)
                self.commDegreenessBag[timeslot] = commDegreenessList

                #Detect the centrality of each community using the betweeness centrality algorithm
                commBetweeness = nx.betweenness_centrality(tempCommGraph)
                maxCBet = max((cpgr for k, (cpgr) in commBetweeness.items()))
                commBetweennessList = []
                for key, value in commBetweeness.items():
                    commBetweennessList.append(value)#/maxCDeg)
                self.commBetweenessBag[timeslot] = commBetweennessList

                #Extract community degree
                degreelist=[]
                for k in range(len(tempCommGraph.edge)):
                    tmpdeg=tempCommGraph.degree(k)
                    degreelist.append(tmpdeg)
                degreelist=[x/max(degreelist) for x in degreelist]
                self.degreeBag[timeslot]=degreelist

                '''Construct Community Dictionary'''
                self.commStrBag[timeslot] = strComms
                self.commNumBag[timeslot] = numComms
                sesStart = sesEnd
                timeslot += 1
        day_month = [datetime.datetime.fromtimestamp(int(x)).strftime('%d/%m') for x in timeLimit]
        self.day_month = day_month
        self.timeLimit = [time.ctime(int(x)) for x in timeLimit]
        print('Total # of communities is '+str(commCount))

    def timeslotselection(self, authors, mentions, alltime):
        ###Parsing commences###

        #Extract unique users globally and construct dictionary
        usrs = list(set(np.append(authors, mentions)))
        usrs.sort()
        uniqueUsers, counter1 = {}, 0
        for tmpusrs in usrs:
            uniqueUsers[tmpusrs] = [counter1]
            counter1 += 1
        self.uniqueUsers = uniqueUsers
        print("Total # of users: "+str(len(usrs)))

        #Find time distance between posts#
        time2 = np.append(alltime[0], alltime)
        time2 = time2[0:len(time2) - 1]
        timeDif = alltime - time2
        lT = len(alltime)

        '''Extract the first derivative'''
        # font = {'size': 9}
        # plt.rc('font', **font)
        fig = plt.figure()#figsize=(10,8)
        plotcount, globfirstderiv, globmentionLimit = 0, {}, {}
        for seg in self.timeSeg:
            curTime, bin, freqStat, mentionLimit, timeLabels = 0, 0, [0], [], []
            for i in range(lT):
                curTime += timeDif[i]
                if curTime <= seg:
                    freqStat[bin] += 1
                else:
                    curTime = 0
                    mentionLimit = np.append(mentionLimit, i)
                    timeLabels = np.append(timeLabels, datetime.datetime.fromtimestamp(alltime[i]).strftime('%d/%m'))
                    bin += 1
                    freqStat = np.append(freqStat, 0)
            mentionLimit = np.append(mentionLimit, i)
            timeLabels = np.append(timeLabels, datetime.datetime.fromtimestamp(alltime[-1]).strftime('%d/%m'))
            freqStatIni = np.zeros(len(freqStat) + 1)
            freqStatMoved = np.zeros(len(freqStat) + 1)
            freqStatIni[0:len(freqStat)] = freqStat
            freqStatMoved[1:len(freqStat) + 1] = freqStat
            firstderiv = freqStatIni - freqStatMoved
            firstderiv[len(firstderiv) - 1] = 0

            globfirstderiv[seg] = firstderiv
            globmentionLimit[seg] = mentionLimit

            plotcount += 1
            if seg / 3600 < 1:
                timeNum = seg / 60
                timeTitle = " mins"
            elif seg / 86400 >= 1:
                timeNum = seg / 86400
                timeTitle = " days"
            elif seg / 86400 == 1:
                timeTitle = " day"
            elif seg / 604800 >= 1:
                timeNum = seg / 604800
                timeTitle = " weeks"
            else:
                timeNum = seg / 3600
                timeTitle = " hours"

            if len(self.timeSeg) < 3:
                ax = fig.add_subplot(2, int(np.ceil(len(self.timeSeg) / 2)), plotcount, autoscale_on=True)
            else:
                ax = fig.add_subplot(int(np.ceil(len(self.timeSeg) / 2)), 2, plotcount, autoscale_on=True)
            plt.grid(axis='x')
            plt.plot(freqStat, 'b-', hold=True)
            plt.ylabel("User activity (mentions)")
            plt.xlabel("Initiation time: " + time.ctime(int(self.alltime[0])) + " (sampling period:" + str(timeNum) + timeTitle + ")")
            poi = []
            for k in range(len(mentionLimit)):
                if firstderiv[k] < 0 <= firstderiv[k + 1]:
                    poi = np.append(poi, k)
            poi = np.int32(poi)
            plt.plot(poi, freqStat[poi], 'ro', hold=True)
            pertick=np.ceil(len(freqStat)/self.xLablNum)
            ax.set_xticks(np.arange(0, len(freqStat), pertick))#, minor=False)
            ax.set_xticklabels(timeLabels[0:-1:pertick], minor=False)
            plt.xlim(xmax=(len(freqStat)))
        mng = plt.get_current_fig_manager()
        mng.resize(*mng.window.maxsize())
        interactive(True)
        plt.show()
        plt.savefig(self.dataset_path + "/data/results/user_activity_mentions.pdf", bbox_inches='tight', format='pdf')
        timeSegInput = int(input("Insert Selected Sampling Time Please: \n" + str(self.timeSeg)))
        plt.close()
        del(fig)
        if timeSegInput / 3600 < 1:
            timeNum = timeSegInput / 60
            timeTitle = "per_" + str(int(timeNum)) + "_mins"
        elif timeSegInput / 86400 > 1:
            timeNum = timeSegInput / 86400
            timeTitle = "per_" + str(int(timeNum)) + "_days"
        else:
            timeNum = timeSegInput / 3600
            timeTitle = "per_" + str(int(timeNum)) + "_hours"
        self.fileTitle = timeTitle
        firstderiv = globfirstderiv[timeSegInput]
        mentionLimit = globmentionLimit[timeSegInput]
        return firstderiv, mentionLimit

    def evol_detect(self, prevTimeslots, xLablNum):
        self.xLablNum=xLablNum
        self.extraction()

        """Construct Community Dictionary"""
        commNumBag2 = {}
        commSizeBag = {}
        timeslots = len(self.commNumBag)
        self.timeslots=timeslots
        lC = [] #Number of communities>2people for each timeslot
        for cBlen in range(timeslots):
            commNumBag2[cBlen] = [x for x in self.commNumBag[cBlen] if len(x) > 2]
            commSizeBag[cBlen] = [len(x) for x in self.commNumBag[cBlen] if len(x) > 2]
            lC.append(len(commNumBag2[cBlen]))

        commIds = []
        # name the first line of communities
        commIds.append([])
        for j in range(lC[0]):
            # commIds[str(0)+","+str(j)]=str(0)+','+str(j)
            commIds[0].append(str(0) + ',' + str(j))
        #Detect any evolution and name the evolving communities
        #uniCommIdsEvol is structured as such {'Id':[rowAppearence],[commCentrality],[commSize],[users]}
        tempUniCommIds, evolcounter, uniCommIdsEvol= [], 0, {}
        print('Community similarity search for each timeslot: ')
        for rows in range(1, timeslots):
        # print('Community similarity search for timeslot: '+str(rows))
            commIds.append([])
            for clmns in range(lC[rows]):
                idx = str(rows) + "," + str(clmns)
                bag1 = commNumBag2[rows][clmns]
                tempcommSize = len(bag1)
                if tempcommSize <= 7 and tempcommSize > 2:
                    thres = .41
                elif tempcommSize <= 11 and tempcommSize > 7:
                    thres = .27
                elif tempcommSize <= 20 and tempcommSize > 11:
                    thres = .2
                elif tempcommSize <= 49 and tempcommSize > 20:
                    thres = .15
                elif tempcommSize <= 99 and tempcommSize > 49:
                    thres = .125
                elif tempcommSize <= 499 and tempcommSize > 99:
                    thres = .1
                else:
                    thres = .05
                for invrow in range(1, prevTimeslots + 1):
                    prevrow = rows - invrow
                    tmpsim = []
                    if prevrow >= 0:
                        for prevComms in commNumBag2[prevrow]:
                            if thres > (len(prevComms) / tempcommSize):
                                break
                            elif thres > (tempcommSize / len(prevComms)):
                                tmpsim.append(0)
                                continue
                            else:
                                tmpsim.append(len(list(set(bag1) & set(prevComms))) / len(set(np.append(bag1, prevComms))))
                        if tmpsim:
                            maxval = max(tmpsim)
                        else:
                            maxval = 0
                        if maxval >= thres:
                            evolcounter += 1
                            maxIdx = tmpsim.index(maxval)
                            tempUniCommIds.append(commIds[prevrow][maxIdx])
                            if commIds[prevrow][maxIdx] not in uniCommIdsEvol:
                                uniCommIdsEvol[commIds[prevrow][maxIdx]] = [[], [], [], [], [], [], [], []]
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][0].append(prevrow)#timeslot num for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][1].append(self.commPgRnkBag[prevrow][maxIdx])#community pagerank for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][2].append(commSizeBag[prevrow][maxIdx])#community size per timeslot for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][3].append(self.commStrBag[prevrow][maxIdx])#users in each community for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][4].append(self.degreeBag[prevrow][maxIdx])#community degree for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][5].append(self.commDegreenessBag[prevrow][maxIdx])#community degree centrality for first evolution
                                uniCommIdsEvol[commIds[prevrow][maxIdx]][6].append(self.commBetweenessBag[prevrow][maxIdx])#community betweeness centrality for first evolution
								#uniCommIdsEvol[commIds[prevrow][maxIdx]][7].append(0)
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][0].append(rows)#timeslot num
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][1].append(self.commPgRnkBag[rows][clmns])#community pagerank per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][2].append(commSizeBag[rows][clmns])#community size per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][3].append(self.commStrBag[rows][clmns])#users in each community
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][4].append(self.degreeBag[rows][clmns])#community degree per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][5].append(self.commDegreenessBag[rows][clmns])#community degree centrality per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][6].append(self.commBetweenessBag[rows][clmns])#community betweeness centrality per timeslot
                            uniCommIdsEvol[commIds[prevrow][maxIdx]][7].append(maxval)#similarity between the two communities in evolving timesteps
                            commIds[rows].append(commIds[prevrow][maxIdx])
                            break
                if maxval < thres:
                    commIds[rows].append(str(rows) + ',' + str(clmns))
        uniCommIds = list(set(tempUniCommIds))
        uniCommIds.sort()

        self.uniCommIds,self.uniCommIdsEvol=uniCommIds,uniCommIdsEvol

        del(self.alltime,self.authors,self.mentions,self.commPgRnkBag,self.commStrBag,self.commNumBag)
        uniCommIdsEvolPck = open(self.dataset_path + "/data/tmp/uniCommIdsEvol.pck", "wb")
        pickle.dump(uniCommIdsEvol, uniCommIdsEvolPck)
        uniCommIdsEvolPck.close()
        uniCommIdsPck = open(self.dataset_path + "/data/tmp/uniCommIds.pck", "wb")
        pickle.dump(uniCommIds, uniCommIdsPck)
        uniCommIdsPck.close()
        dataPck = open(self.dataset_path + "/data/tmp/dataFull.pck", "wb")
        pickle.dump(self, dataPck)
        dataPck.close()

        print(str(evolcounter) + " evolutions and " + str(len(uniCommIds)) + " dynamic communities")
        return self

    def commRanking(self,numTopComms, prevTimeslots,xLablNum):
        '''Detect the evolving communities'''
        uniCommIdsEvol=self.uniCommIdsEvol
        timeslots=self.timeslots

        tempcommRanking = {}
        #structure: tempcommRanking={Id:[persistence,stability,commCentrality,degreeness]}
        commRanking,fluctuation,lifetime2 = {},{},0
        for Id in self.uniCommIds:
            uniqueTimeSlLen = len(set(uniCommIdsEvol[Id][0]))
            timeSlLen=len(uniCommIdsEvol[Id][0])
            tempcommRanking[Id] = []
            tempcommRanking[Id].append((uniqueTimeSlLen / timeslots)*.25)#persistence
            tempcommRanking[Id].append(((sum(np.diff(list(set(uniCommIdsEvol[Id][0]))) == 1) + 1) / (timeslots + 1))*.25)#stability
            tempcommRanking[Id].append((sum(uniCommIdsEvol[Id][1]) / timeSlLen)*.25)#commCentrality
            # tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][4]) / timeslots)#Degreeness
            # tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][5])/timeSlLen)#degree centrality
            # tempcommRanking[Id].append(sum(uniCommIdsEvol[Id][6])/timeSlLen)#betweeness centrality
            '''Checking Theseus Ship'''
            theseus=len(list(set(uniCommIdsEvol[Id][3][0]) & set(uniCommIdsEvol[Id][3][-1]))) / len(set(np.append(uniCommIdsEvol[Id][3][0], uniCommIdsEvol[Id][3][-1])))
            tempcommRanking[Id].append(thesius*.25)
            commRanking[Id] = np.sum(tempcommRanking[Id])

            #Construct average jaccardian between timeslots for each dyn comm
            # lifetime=uniCommIdsEvol[Id][0][-1]-uniCommIdsEvol[Id][0][0]+1
            if timeSlLen not in fluctuation:
                fluctuation[timeSlLen]=[(sum(uniCommIdsEvol[Id][7])/(timeSlLen-1))] #[1-sum(np.diff(list(set(uniCommIdsEvol[Id][0]))) == 1)/(lifetime-1)]
            else:
                fluctuation[timeSlLen].append((sum(uniCommIdsEvol[Id][7])/(timeSlLen-1)))#1-sum(np.diff(list(set(uniCommIdsEvol[Id][0]))) == 1)/(lifetime-1))
            lifetime2=max(lifetime2,timeSlLen)

        flux=[]
        for lifeT in range(lifetime2+1):
            if lifeT in fluctuation:
                flux.append(sum(fluctuation[lifeT])/len(fluctuation[lifeT]))
            else:
                flux.append(0)

        fig1 = plt.figure()
        plt.stem(flux, linefmt='b-', markerfmt='bo')
        xmin, xmax = plt.xlim()
        plt.xlim( 1, xmax+1 )
        plt.ylabel("Average Fluctuation")
        plt.xlabel('Persistance')
        plt.tight_layout()
        fig1 = plt.gcf()
        plt.draw()
        fig1.savefig(self.dataset_path + "/data/results/Fluctuation_" + self.fileTitle + ".pdf",bbox_inches='tight', format='pdf')
        plt.close()

        rankedCommunities = sorted(commRanking, key=commRanking.get, reverse=True)
        if numTopComms>len(rankedCommunities):
            numTopComms=len(rankedCommunities)
        row_labels = self.day_month#(range(timeslots))
        column_labels = list(range(numTopComms))
        column_labels2 = rankedCommunities[:numTopComms]
        commSizeHeatData = np.zeros([numTopComms, timeslots])
        for rCIdx, comms in enumerate(rankedCommunities[0:numTopComms]):
            for sizeIdx, timesteps in enumerate(uniCommIdsEvol[comms][0]):
                if commSizeHeatData[rCIdx, timesteps] != 0:
                    commSizeHeatData[rCIdx, timesteps] = max(np.log(uniCommIdsEvol[comms][2][sizeIdx]),commSizeHeatData[rCIdx, timesteps])
                else:
                    commSizeHeatData[rCIdx, timesteps] = np.log(uniCommIdsEvol[comms][2][sizeIdx])

        fig2, ax = plt.subplots()
        pertick=int(np.ceil(timeslots/20))
        heatmap = ax.pcolormesh(commSizeHeatData, cmap=plt.cm.gist_gray_r)
        ax.set_xticks(np.arange(0,commSizeHeatData.shape[1],pertick), minor=False)
        plt.xlim(xmax=timeslots)
        ax.xaxis.tick_top()
        ax.set_xticklabels(row_labels[0:-1:pertick], minor=False)
        ax.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        plt.ylim(ymax=numTopComms)
        ax.invert_yaxis()
        ax.set_yticklabels(column_labels, minor=False, fontsize=7)
        plt.ylabel("Ranked Communities (Best " + str(numTopComms) + ")")
        ax2 = ax.twinx()
        ax2.set_yticks(np.arange(commSizeHeatData.shape[0]), minor=False)
        plt.ylim(ymax=numTopComms)
        ax2.invert_yaxis()
        ax2.set_yticklabels(column_labels2, minor=False, fontsize=7)
        plt.xlabel('Timeslot', {'verticalalignment': 'top'})

        if numTopComms < 101:
            plt.grid(axis='y')
        plt.tight_layout()
        interactive(False)
        mng = plt.get_current_fig_manager()
        mng.resize(*mng.window.maxsize())
        fig2 = plt.gcf()
        plt.show()
        fig2.savefig(self.dataset_path + "/data/results/communitySizeHeatmap_" + self.fileTitle + ".pdf",bbox_inches='tight', format='pdf')
        plt.close()

        '''Writing ranked communities to json files'''
        rankedCommunitiesFinal = {}
        twitterDataFile = open(self.dataset_path + '/data/results/rankedCommunities.json', "w")
        jsondata = dict()
        jsondata["ranked_communities"] = []
        for rank, rcomms in enumerate(rankedCommunities[:numTopComms]):
            tmslUsrs, tmpTags, tmptweetids, commTwText, tmpUrls = [], [], [], [], []
            strRank = '{0}'.format(str(rank).zfill(2))
            rankedCommunitiesFinal[strRank] = [rcomms]
            rankedCommunitiesFinal[strRank].append(commRanking[rcomms])
            rankedCommunitiesFinal[strRank].append(uniCommIdsEvol[rcomms][3])
            timeSlotApp = [self.timeLimit[x] for x in uniCommIdsEvol[rcomms][0]]
            for tmsl, users in enumerate(uniCommIdsEvol[rcomms][3]):
                uscentr, tmptweetText = [], []
                for us in users:
                    uscentr.append([us, self.userPgRnkBag[uniCommIdsEvol[rcomms][0][tmsl]][us]])
                    # uscentr = sorted(uscentr, key=itemgetter(1), reverse=True)
                    if us in self.tagBag[uniCommIdsEvol[rcomms][0][tmsl]]:
                        tmpTags.extend(self.tagBag[uniCommIdsEvol[rcomms][0][tmsl]][us])
                    if us in self.urlBag[uniCommIdsEvol[rcomms][0][tmsl]]:
                        tmpUrls.extend(self.urlBag[uniCommIdsEvol[rcomms][0][tmsl]][us])
                    if us in self.tweetIdBag[uniCommIdsEvol[rcomms][0][tmsl]]:
                        tmptweetids.extend(self.tweetIdBag[uniCommIdsEvol[rcomms][0][tmsl]][us])
                    if us in self.tweetTextBag[uniCommIdsEvol[rcomms][0][tmsl]]:
                        tmptweetText.extend(self.tweetTextBag[uniCommIdsEvol[rcomms][0][tmsl]][us])
                uscentr = sorted(uscentr, key=itemgetter(1), reverse=True)
                tmslUsrs.append({uniCommIdsEvol[rcomms][0][tmsl]: uscentr})
                tmptweetText = [i.replace("\n", "") for i in tmptweetText]
                seen = set()
                seen_add = seen.add
                tmptweetText2 = [x for x in tmptweetText if x not in seen and not seen_add(x)]
                commTwText.append({timeSlotApp[tmsl]: tmptweetText2})
            popTags = [x.lower() for x in list(itertools.chain.from_iterable(tmpTags))]
            popTags = collections.Counter(popTags)
            popTags = popTags.most_common(10)
            popUrls = [x.lower() for x in list(itertools.chain.from_iterable(tmpUrls))]
            popUrls = collections.Counter(popUrls)
            popUrls = popUrls.most_common(10)
            commTweetIds = list(set(tmptweetids))
            jsondata["ranked_communities"].append(
                {'community label': rcomms, 'rank': rank + 1, 'timeslot appearance': timeSlotApp, 'text': commTwText,
                 'persistence:': tempcommRanking[rcomms][0],'total score':commRanking[rcomms],
                 'stability': tempcommRanking[rcomms][1],'community centrality': tempcommRanking[rcomms][2],
                 'community size per slot': uniCommIdsEvol[rcomms][2], 'users:centrality per timeslot': tmslUsrs,
                 'popTags': popTags, 'popUrls': popUrls})
        twitterDataFile.write(json.dumps(jsondata, sort_keys=True))#,ensure_ascii=False).replace("\u200f",""))
        twitterDataFile.close()
        return rankedCommunitiesFinal
