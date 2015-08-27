#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:
# Purpose:       This .py file is the main Framework file 
#                It uses an adaptive timeslot partitioning algorithm
#
# Required libs: python-dateutil, numpy,matplotlib,pyparsing
# Author:        konkonst
#
# Created:       20/08/2013
# Copyright:     (c) ITI (CERTH) 2013
# Licence:       <apache licence 2.0>
#-------------------------------------------------------------------------------
import time,os,pickle,dateutil.parser
from CommunityRanking_v3 import communityranking
print(time.asctime( time.localtime(time.time()) ))

'''PARAMETERS'''
# User sets json dataset folder
dataset_path = "./greekDefault"
#Construct the data class from scratch: 1-yes / 2-only the evolution / 3-perform only the ranking
dataextract = 3
#User sets desired number of displayed top communities
numTopComms = 20
#User sets how many timeslots back the framework should search
prevTimeslots = 3
#Number of labels on the x-axis of the activity distribution
xLablNum = 20
#Id adaptive timeslot creation is required, set adaptive to True
adaptive = False

print(dataset_path)
print('adaptive timeslot creation is: '+str(adaptive))
#User sets desired time intervals if applicable. Else the whole dataset is considered
if dataset_path == "./testDataset":
    timeSeg = [86400]
    timeInterval=86400
if dataset_path == "./snowDataset":
    timeSeg = [3600,3600*2,3600*3,3600*6]
    timeInterval=3600
if dataset_path == "./us_elections":
    timeSeg = [2700, 3600, 3600*3, 3600*6]
    timeInterval=3600*3
if dataset_path == "./greek_elections":
    timeSeg = [3600*3,3600*6,3600*12,86400]
    timeMin = '04:00-19/01/15'
    timeMax = '14:45-29/01/15'
    timeInterval=3600*12
if dataset_path == "./greekDefault":
    timeSeg = [86400]
    timeMin = '25/06/2015 00:00'
    timeInterval=86400
if dataset_path == "./sherlock":
    timeSeg = [3600*6,3600*12,86400,86400*5]
    timeMin = '31/12/2013 00:00'
    timeMax = '14/12/2014 00:00'
    timeInterval=3600*12
if dataset_path == "./varoufakis":
    timeSeg = [3600*6,3600*12,86400,86400*7]
    timeInterval=86400*30

if timeInterval < 3600:
    timeNum = timeInterval / 60
    timeTitle = 'per' + str(int(timeNum)) + 'mins'
elif timeInterval >= 3600 and timeInterval < 86400:
    timeNum = timeInterval / 3600
    timeTitle = 'per' + str(int(timeNum)) + 'hours'
elif timeInterval >= 86400 and timeInterval < 604800:
    timeNum = timeInterval / 86400
    timeTitle = 'per' + str(int(timeNum)) + 'days'
elif timeInterval>= 604800 and timeInterval < 2592000:
    timeNum = timeInterval / 604800
    timeTitle = 'per' + str(int(timeNum)) + 'weeks'
else:
    timeNum = timeInterval / 2592000
    timeTitle = 'per' + str(int(timeNum)) + 'months'

#fix earliest and latest time limits if available
try:
    timeMin = dateutil.parser.parse(timeMin,dayfirst=True)
    timeMin = int(time.mktime(timeMin.timetuple()))
except:
    timeMin = 0
    pass
try:
    timeMax = dateutil.parser.parse(timeMax,dayfirst=True)
    timeMax = int(time.mktime(timeMax.timetuple()))
except:
    timeMax = time.time()
    pass

if adaptive:
    adaptStr = 'adaptive'
else:
    adaptStr = ''

t = time.time()
'''Functions'''

if dataextract==1:#If the basic data(authors, mentions, time) has NOT been created
    if not os.path.exists(dataset_path + "/data/tmp/"+adaptStr):
        os.makedirs(dataset_path + "/data/tmp/"+adaptStr)    
    if not os.path.exists(dataset_path + "/data/results/"):
        os.makedirs(dataset_path + "/data/results/")
    data,tweetDict = communityranking.from_json(dataset_path, timeSeg,timeMin=timeMin,timeMax=timeMax)
    dataPck = open(dataset_path + "/data/tmp/data.pck", "wb")
    pickle.dump(data, dataPck, protocol = 2)
    dataPck.close()
    elapsed = time.time() - t
    print('Stage 1: %.2f seconds' % elapsed)
    
print(timeTitle)

if dataextract==1 or dataextract==2:#If the basic data (authors, mentions, time) has been created      
    if not os.path.exists(dataset_path + '/data/tmp/'+adaptStr+'/dataComm_'+timeTitle+'.pck'):
        data = pickle.load(open(dataset_path + "/data/tmp/data.pck", 'rb'))
    else:
        data = pickle.load(open(dataset_path + "/data/tmp/"+adaptStr+"/dataComm_"+timeTitle+'.pck', "rb"))
    try:
        data.tweetDict = tweetDict
    except:
        data.tweetDict = pickle.load(open(dataset_path + './data/tmp/tweetDict.pck','rb'))
        pass
    data.timeSeg=timeSeg
    dataEvol=data.evol_detect(prevTimeslots, xLablNum, adaptive)
    del(data)
    dataEvolPck = open(dataset_path + "/data/tmp/"+adaptStr+"/dataEvol_prev"+str(prevTimeslots)+dataEvol.fileTitle+".pck", "wb")
    pickle.dump(dataEvol, dataEvolPck, protocol = 2)
    dataEvolPck.close()
    elapsed = time.time() - t
    print('Stage 3: %.2f seconds' % elapsed)

if dataextract==1 or dataextract==2 or dataextract==3:
    try:
        dataEvol
    except:
        dataEvol = pickle.load(open(dataset_path + "/data/tmp/"+adaptStr+"/dataEvol_prev"+str(prevTimeslots)+timeTitle+".pck", 'rb'))
        pass
    dataEvol.dataset_path=dataset_path

print("Ranking Commences")
dataEvol.dirName = dataset_path.lstrip('./')
rankedCommunities = dataEvol.commRanking(numTopComms, prevTimeslots, xLablNum)
elapsed = time.time() - t
print('Elapsed: %.2f seconds' % elapsed)
