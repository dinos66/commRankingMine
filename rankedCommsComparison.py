#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:
# Purpose:       This .py file computes the divide and conquer list similarity distance
#                for any two community lists.
#
# Required libs:
# Author:        konkonst
#
# Created:       20/08/2013
# Copyright:     (c) ITI (CERTH) 2013
# Licence:       <apache licence 2.0>
#-------------------------------------------------------------------------------

def computeDiv_Conq(listBase,listQuery):
    lBlength=len(listBase)
    baseDict,count={},0
    for comms in listBase:
        baseDict[comms]=count
    queryRank=[]
    for comms in listQuery:
        queryRank.append(baseDict[comms])
    return myDivConq(queryRank)

def myDivConq(myrank):
    inversions=[0]
    divConq(myrank,inversions)
    return inversions[0]

def divConq(myrank, inversions):
    if len(myrank)<2:
        return myrank
    mid = int(len(myrank)/2)
    return merge(divConq(myrank[:mid],inversions), divConq(myrank[mid:],inversions),inversions)

def merge(fir, sec, inversions):
    ranked=[]
    while fir and sec:
        if fir[0]<sec[0]:
            tmp=fir
        else:
            tmp=sec
        ranked.append(tmp.pop(0))
        if (tmp == sec):
            inversions[0] += len(fir)
    if fir:
        tmp2=fir
    else:
        tmp2=sec
    ranked.extend(tmp2)
    return ranked
