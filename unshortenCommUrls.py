#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:GDD_parser
# Purpose:       This .py file extracts urls from json twitter files.
#
# Required libs: python-dateutil,pyparsing,numpy,matplotlib,networkx
# Author:        konkonst
#
# Created:       20/08/2013
# Copyright:     (c) ITI (CERTH) 2013
# Licence:       <apache licence 2.0>
#-------------------------------------------------------------------------------
import json,codecs,os,glob,time, pickle, collections, requests
import concurrent.futures
import urllib.parse
from urllib.request import urlopen

#Get shrinked urls
shrinkedUrls = [x.strip().decode() for x in urlopen('https://www.dropbox.com/s/y1elvhioeg5tr9f/allShrinks.txt?raw=1').readlines()]
shrinkedUrls.sort() 

session = requests.Session()

def load_url(url, timeout):
    try:
        resp = session.head(url, allow_redirects=True, timeout = timeout)
        trueUrl = resp.url
        if not trueUrl.startswith('http'):
            trueUrl = url
    except:
        trueUrl = url
        pass
    return trueUrl

def unshrinkUrlsInParallel(urlArray,dataset_path):
    
    print('unshortenCommUrlsFromPickles.py:\nThis .py file extracts urls')

    for i in range(2):
        if i:
            print('Repassing to ensure full unshortening')
        shorts = [x for x in list(urlArray.keys()) if (not urlArray[x]['trueUrl'] or len(urlArray[x]['trueUrl'])<=30 or urllib.parse.urlparse(urlArray[x]['trueUrl']).netloc.lower() in shrinkedUrls) and 'ow.ly/i/' not in urlArray[x]['trueUrl']]
        # print('Number of all URLs is: '+str(len(urlArray)))
        # print('Number of Shrinks is: '+str(len(shorts)))

        batchShorts = [shorts[x:x+40] for x in range(0, len(shorts), 40)]

        urlLength = len(batchShorts)
        print('There are '+str(urlLength)+' batches of 40 urls')
        ts = int(urlLength/40)

        
        with concurrent.futures.ThreadPoolExecutor(max_workers=1000) as executor:
            for idx,tmpshorts in enumerate(batchShorts):
                # Start the load operations and mark each future with its URL   
                future_to_url = {executor.submit(load_url, url, 10): url for url in tmpshorts}
                try:
                    for future in concurrent.futures.as_completed(future_to_url, timeout=60):
                        thisUrl = future_to_url[future]
                        trueUrl = future.result()
                        if trueUrl and thisUrl!=trueUrl:                    
                            domain = urllib.parse.urlparse(trueUrl).netloc.lower()
                            urlArray[thisUrl]['trueUrl'] = trueUrl
                            urlArray[thisUrl]['domain'] = domain
                except concurrent.futures._base.TimeoutError:
                    print('error in futures')
                    for thisUrl in tmpshorts:    
                        if urlArray[thisUrl]['trueUrl']:                    
                            trueUrl = load_url(thisUrl, 10)
                            if trueUrl and thisUrl!=trueUrl:                    
                                domain = urllib.parse.urlparse(trueUrl).netloc.lower()
                                urlArray[thisUrl]['trueUrl'] = trueUrl
                                urlArray[thisUrl]['domain'] = domain
                    pass
                if not trueUrl:
                    urlArray[thisUrl]['trueUrl'] = thisUrl
                    urlArray[thisUrl]['domain'] = urllib.parse.urlparse(thisUrl).netloc.lower()
                # time.sleep(10)
                if not idx%20:
                    pickle.dump(urlArray, open(dataset_path + '/data/tmp/commsUrls.pck','wb'))
                    print('@@@@@ Just passed batch '+str(idx)+' at '+time.strftime("%H:%M||%d/%m ")) 

    pickle.dump(urlArray, open(dataset_path + '/data/tmp/commsUrls.pck','wb'))

    return urlArray

