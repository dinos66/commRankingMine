#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:
# Purpose:       This .py file computes list similarity distances
#                for any two community lists.
#
# Required libs:
# Author:        konkonst
#
# Created:       20/08/2013
# Copyright:     (c) ITI (CERTH) 2013
# Licence:       <apache licence 2.0>
#-------------------------------------------------------------------------------
from math import log

def computeDiv_Conq(listBase,listQuery):
    lBlength=len(listBase)
    baseDict={}
    for count,comms in enumerate(listBase):
        baseDict[comms]=count
    queryRank=[]
    for comm in listQuery:
        queryRank.append(baseDict[comm])
    return myDivConq(queryRank)

def spearmans(listBase,listQuery):
    lBlength=len(listBase)
    baseDict={}
    for count,comms in enumerate(listBase):
        baseDict[comms]=count
    queryRank=[]
    for comm in listQuery:
        queryRank.append(baseDict[comm])
    baseRank=list(range(lBlength))
    dif=[a - b for a, b in zip(baseRank,queryRank)]
    sumdifSq=sum([a**2 for a in dif])
    rho=1-(6*sumdifSq/(lBlength*(lBlength**2-1)))
##    if rho==1:
##        rho=0.9999999
##    tDistr=rho*((((lBlength-2)/(1-rho**2)))**(1/2))
    return rho

def ndcg(listBase,listQuery):
    lBlength=len(listBase)
    gt=list(range(1,lBlength+1))
    rnk=gt.copy()
    gt.reverse()
    gt=[x/lBlength for x in gt]
    baseDict={}
    for count,comms in enumerate(listBase):
        baseDict[comms]=gt[count]
    '''IDCG'''
    idcg=0
    for count,rel in enumerate(gt[1:]):
        idcg+=gt[count+1]/log((count+2),2)
    idcg+=gt[0]
    '''GDCG'''
    queryRelev=[]
    for comms in listQuery:
        queryRelev.append(baseDict[comms])
    dcg=0
    for count,rel in enumerate(queryRelev[1:]):
        dcg+=queryRelev[count+1]/log((count+2),2)
    dcg+=queryRelev[0]
    gdcg=dcg/idcg
    # print("IDCG: "+str(idcg)+", DCG: "+str(dcg)+", GDCG: "+str(gdcg))
    return gdcg

def rbo(listBase, listQuery, p = 0.98):
    """
        Calculates Ranked Biased Overlap (RBO) score. 
        listBase -- Ranked List 1
        listQuery -- Ranked List 2
    """
    if listBase == None: listBase = []
    if listQuery == None: listQuery = []
    
    sl,ll = sorted([(len(listBase), listBase),(len(listQuery),listQuery)])
    s, S = sl
    l, L = ll
    if s == 0: return 0

    # Calculate the overlaps at ranks 1 through l 
    # (the longer of the two lists)
    ss = set([]) # contains elements from the smaller list till depth i
    ls = set([]) # contains elements from the longer list till depth i
    x_d = {0: 0}
    sum1 = 0.0
    for i in range(l):
        x = L[i]
        y = S[i] if i < s else None
        d = i + 1
        
        # if two elements are same then 
        # we don't need to add to either of the set
        if x == y: 
            x_d[d] = x_d[d-1] + 1.0
        # else add items to respective list
        # and calculate overlap
        else: 
            ls.add(x) 
            if y != None: ss.add(y)
            x_d[d] = x_d[d-1] + (1.0 if x in ss else 0.0) + (1.0 if y in ls else 0.0)     
        #calculate average overlap
        sum1 += x_d[d]/d * pow(p, d)
        
    sum2 = 0.0
    for i in range(l-s):
        d = s+i+1
        sum2 += x_d[d]*(d-s)/(d*s)*pow(p,d)

    sum3 = ((x_d[l]-x_d[s])/l+x_d[s]/s)*pow(p,l)

    # Equation 32
    rbo_ext = (1-p)/p*(sum1+sum2)+sum3
    return rbo_ext

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
