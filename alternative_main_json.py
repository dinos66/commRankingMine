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
import tkinter,time
from alternative_ranking import alternativeranking
import rankedCommsComparison

'''PARAMETERS'''
##root = tkinter.Tk()
##root.withdraw()
##dataset_path = tkinter.filedialog.askdirectory(parent=root,initialdir="f:/Dropbox/ITI/python/community_analysis_framework/",title='Please select a directory')
# User sets json dataset and target folder
#C:/Users/konkonst/Desktop/myDropBox
dataset_path = "d:/Dropbox/ITI/python/community_analysis_framework/golden_dawn"
#User sets desired time intervals
timeSeg=86400
#User sets desired number of displayed top communities
numTopComms=100
#User sets how many timeslots back the framework should search
prevTimeslots=7

'''Functions'''
t = time.time()
data=alternativeranking.from_json(dataset_path,timeSeg)
uniCommIds,uniCommIdsEvol,timeslots=data.evol_detect(prevTimeslots)

rankedAltComboComms,labelsAltCombo=alternativeranking.commRankingAltCombo(uniCommIds,uniCommIdsEvol,timeslots,data.timeLimit,dataset_path,numTopComms)
rankedDegreeComms,labelsDegree=alternativeranking.commRankingDegrees(uniCommIds,uniCommIdsEvol,timeslots,data.timeLimit,dataset_path,numTopComms)
rankedMentionsComms,labelsMentions=alternativeranking.commRankingMentions(uniCommIds,uniCommIdsEvol,timeslots,data.timeLimit,dataset_path,numTopComms)
rankedSizeComms,labelsSize=alternativeranking.commRankingSize(uniCommIds,uniCommIdsEvol,timeslots,data.timeLimit,dataset_path,numTopComms)

rankedRetweetsComms,labelsRetweets=alternativeranking.commRankingRetweets(uniCommIds,uniCommIdsEvol,timeslots,data.timeLimit,dataset_path,numTopComms,data.retweetBag)
rankedPSCRComms,labelsPSCR=alternativeranking.commPSCRRanking(uniCommIds,uniCommIdsEvol,timeslots,data.timeLimit,dataset_path,numTopComms,data.userPgRnkBag)


elapsed = time.time() - t
print ('Elapsed: %.2f seconds'% elapsed)


