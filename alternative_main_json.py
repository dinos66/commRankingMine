#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:
# Purpose:       This .py file is the main Framewok file
#
# Required libs: python-dateutil, numpy,matplotlib,pyparsing
# Author:        konkonst
#
# Created:       20/08/2013
# Copyright:     (c) ITI (CERTH) 2013
# Licence:       <apache licence 2.0>
#-------------------------------------------------------------------------------
import tkinter, time, os, pickle,pylab
from alternative_ranking import alternativeranking
import rankedCommsComparison
import matplotlib.pyplot as plt

'''PARAMETERS'''
##root = tkinter.Tk()
##root.withdraw()
##dataset_path = tkinter.filedialog.askdirectory(parent=root,initialdir="f:/Dropbox/ITI/python/community_analysis_framework/",title='Please select a directory')
# User sets json dataset and target folder
#C:/Users/konkonst/Desktop/myDropBox
dataset_path = "d:/Dropbox/ITI/python/community_analysis_framework/royal_baby"
#User sets desired time intervals
timeSeg = 3600
#User sets desired number of displayed top communities
numTopComms = 1000
#User sets how many timeslots back the framework should search
prevTimeslots = 7
#Construct the data class from scratch: 1-yes / 0-no
dataextract = 1

'''Functions'''
t = time.time()
if dataextract==1:
    if not os.path.exists(dataset_path + "/data/tmp/"):
        os.makedirs(dataset_path + "/data/tmp/")
    '''If the data is in typical tweeter form use the .from_json function'''
    data = alternativeranking.from_json(dataset_path, timeSeg)
    dataPck = open(dataset_path + "/data/tmp/alternativedata.pck", "wb")
    pickle.dump(data, dataPck)
    dataPck.close()
    data= data.evol_detect(prevTimeslots)
    dataPckFull = open(dataset_path + "/data/tmp/alternativedataFull.pck", "wb")
    pickle.dump(data, dataPckFull)
    dataPckFull.close()
elif dataextract==2:
    data = pickle.load(open(dataset_path + "/data/tmp/alternativedata.pck", 'rb'))
    data = data.evol_detect(prevTimeslots)
    dataPckFull = open(dataset_path + "/data/tmp/alternativedataFull.pck", "wb")
    pickle.dump(data, dataPckFull)
    dataPckFull.close()
else:
    data = pickle.load(open(dataset_path + "/data/tmp/alternativedataFull.pck", 'rb'))
    
# uniCommIds, uniCommIdsEvol, timeslots = data.evol_detect(prevTimeslots)

pylab.figure()

rankedRetweetsComms, labelsRetweets, verif = alternativeranking.commRankingRetweets(data.uniCommIds, data.uniCommIdsEvol, data.timeslots,data.timeLimit, dataset_path, numTopComms,data.retweetBag, data.verified)
# rTweets = rankedCommsComparison.rbo(labelsRetweets, labelsRetweets)
# print("Retweets to Retweets: " + str(rTweets))
plt.plot(verif,hold=True,label='retweets')
# print(verif)

# rankedRetwBySizeComms, labelsRetwBySize, verif = alternativeranking.commRankingRetwBySize(data.uniCommIds, data.uniCommIdsEvol,data.timeslots, data.timeLimit,dataset_path, numTopComms,data.retweetBag, data.verified)
# rTwBySize = rankedCommsComparison.rbo(labelsRetweets, labelsRetwBySize)
# print("Retweets to RetwBySize: " + str(rTwBySize))
# plt.plot(verif,hold=True,label='retweets')
# print(verif)

rankedAltComboComms, labelsAltCombo, verif = alternativeranking.commRankingAltCombo(data.uniCommIds, data.uniCommIdsEvol, data.timeslots,data.timeLimit, dataset_path, numTopComms, data.verified)
# rAltCombo = rankedCommsComparison.rbo(labelsRetweets, labelsAltCombo)
# print("Retweets to altCombo: " + str(rAltCombo))
plt.plot(verif,hold=True,label='altCombo')
# print(verif)

rankedDegreeComms, labelsDegree, verif = alternativeranking.commRankingDegrees(data.uniCommIds, data.uniCommIdsEvol, data.timeslots,data.timeLimit, dataset_path, numTopComms, data.verified)
# rDegree = rankedCommsComparison.rbo(labelsRetweets, labelsDegree)
# print("Retweets to Degree: " + str(rDegree))
plt.plot(verif,hold=True,label='Degree')
# print(verif)

rankedMentionsComms, labelsMentions, verif = alternativeranking.commRankingMentions(data.uniCommIds, data.uniCommIdsEvol, data.timeslots,data.timeLimit, dataset_path, numTopComms, data.verified)
# rMentions = rankedCommsComparison.rbo(labelsRetweets, labelsMentions)
# print("Retweets to Mentions: " + str(rMentions))
plt.plot(verif,hold=True,label='Mentions')
# print(verif)

rankedSizeComms, labelsSize, verif = alternativeranking.commRankingSize(data.uniCommIds, data.uniCommIdsEvol, data.timeslots, data.timeLimit,dataset_path, numTopComms, data.verified)
# rSize = rankedCommsComparison.rbo(labelsRetweets, labelsSize)
# print("Retweets to Size: " + str(rSize))
plt.plot(verif,hold=True,label='Size')
# print(verif)

# rankedStabilityComms, labelsStability, verif = alternativeranking.commStabilityRanking(data.uniCommIds, data.uniCommIdsEvol, data.timeslots,data.timeLimit, dataset_path,numTopComms, data.userPgRnkBag, data.verified)
# # rStab = rankedCommsComparison.rbo(labelsRetweets, labelsStability)
# # print("Retweets to Stability: " + str(rStab))
# plt.plot(verif,hold=True,label='Stability')
# # print(verif)

# rankedPersistComms, labelsPersist, verif = alternativeranking.commPersistenceRanking(data.uniCommIds, data.uniCommIdsEvol, data.timeslots,data.timeLimit, dataset_path, numTopComms,data.userPgRnkBag, data.verified)
# # rPers = rankedCommsComparison.rbo(labelsRetweets, labelsPersist)
# # print("Retweets to Persistance: " + str(rPers))
# plt.plot(verif,hold=True,label='Persistance')
# # print(verif)

# rankedCentrComms, labelsCentr, verif = alternativeranking.commCentralityRanking(data.uniCommIds, data.uniCommIdsEvol, data.timeslots,data.timeLimit, dataset_path, numTopComms,data.userPgRnkBag, data.verified)
# # rCentr = rankedCommsComparison.rbo(labelsRetweets, labelsCentr)
# # print("Retweets to Centrality: " + str(rCentr))
# plt.plot(verif,hold=True,label='Centrality')
# # print(verif)

rankedPSCRComms, labelsPSCR, verif = alternativeranking.commPSCRRanking(data.uniCommIds, data.uniCommIdsEvol, data.timeslots, data.timeLimit,dataset_path, numTopComms, data.userPgRnkBag, data.verified)
# rPSCR = rankedCommsComparison.rbo(labelsRetweets, labelsPSCR)
# print("Retweets to PSCR: " + str(rPSCR))
plt.plot(verif,hold=True,label='PSCR')
# print(verif)
plt.legend(bbox_to_anchor=(0, 0, 1, 1), bbox_transform=plt.gcf().transFigure)
pylab.savefig(dataset_path+"/data/results/alternative/verifComparison.pdf",bbox_inches='tight')

elapsed = time.time() - t
print('Elapsed: %.2f seconds' % elapsed)


