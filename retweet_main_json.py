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
from retweet_comparison import retweetcomparison

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
#User decides whether to simplify the jsons into readable txts:  1-on / 0-off (time consuming)
simplify_json=0

'''Functions'''
t = time.time()
data=retweetcomparison.from_json(dataset_path,timeSeg)
# data=communityranking.from_txt(dataset_path,timeSeg)
rankedCommunities=data.evol_detect(numTopComms,prevTimeslots)
elapsed = time.time() - t
print ('Elapsed: %.2f seconds'% elapsed)


