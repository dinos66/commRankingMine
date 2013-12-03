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
import time,os,pickle
from CommunityRanking import communityranking

'''PARAMETERS'''
##root = tkinter.Tk()
##root.withdraw()
##dataset_path = tkinter.filedialog.askdirectory(parent=root,initialdir="f:/Dropbox/ITI/python/community_analysis_framework/",title='Please select a directory')
# User sets json dataset and target folder
#C:/Users/konkonst/Desktop/myDropBox
dataset_path = "d:/Dropbox/ITI/python/community_analysis_framework/golden_dawn"
print(dataset_path)
#User sets desired time intervals
#timeSeg = [600,900,1200,1800, 2700, 3600]
#timeSeg = [1800, 2700, 3600, 10800, 21600, 43200]
timeSeg=[86400,129600]#,43200,129600,172800,432000,604800]#,2592000,5184000] # For long datasets (time is in seconds)
#User sets desired number of displayed top communities
numTopComms = 100
#User sets how many timeslots back the framework should search
prevTimeslots = 7
#Number of labels on the x-axis of the activity distribution
xLablNum = 20
#Construct the data class from scratch: 1-yes / 2-only the evoluton / 0-perform only the ranking
dataextract = 0
#User decides whether to simplify the jsons into readable txts:  1-on / 0-off (time consuming)
simplify_json = 1
#If json files have irregular timestamps, set rankIrregularTime to 1
rankIrregularTime = 0

'''Functions'''
t = time.time()

if dataextract==1:#If the basic data(authors, mentions, time) has been created
    if not os.path.exists(dataset_path + "/data/tmp/"):
        os.makedirs(dataset_path + "/data/tmp/")
    '''If the data is in typical tweeter form use the .from_json function'''
    data = communityranking.from_json(dataset_path, timeSeg, simplify_json,rankIrregularTime)
    dataPck = open(dataset_path + "/data/tmp/data.pck", "wb")
    pickle.dump(data, dataPck)
    dataPck.close()
    dataEvol=data.evol_detect(prevTimeslots, xLablNum)
    dataEvolPck = open(dataset_path + "/data/tmp/dataEvol.pck", "wb")
    pickle.dump(dataEvol, dataEvolPck)
    dataEvolPck.close()
elif dataextract==2:
    data = pickle.load(open(dataset_path + "/data/tmp/data.pck", 'rb'))
    data.dataset_path=dataset_path
    dataEvol=data.evol_detect(prevTimeslots, xLablNum)
    dataEvolPck = open(dataset_path + "/data/tmp/dataEvol.pck", "wb")
    pickle.dump(dataEvol, dataEvolPck)
    dataEvolPck.close()
else:
    dataEvol = pickle.load(open(dataset_path + "/data/tmp/dataEvol.pck", 'rb'))
    dataEvol.dataset_path=dataset_path

'''If the data is in a {user1 user2,user3 "date" text} form use the .from_txt function'''
# data=communityranking.from_txt(dataset_path,timeSeg)
rankedCommunities = dataEvol.commRanking(numTopComms, prevTimeslots, xLablNum)
elapsed = time.time() - t
print('Elapsed: %.2f seconds' % elapsed)
