#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Gruik coded by GuiguiAbloc
# http://blog.guiguiabloc.fr
# Rewritten by Guillaume Descombes
# 2022.12.04
#

import urllib.request, urllib.error
import syslog
from xml.dom import minidom

#https://donneespubliques.meteofrance.fr/client/document/doc_vigilance_258_269.pdf

class vigilance:

  def __getColor(self, number):
    if number == "0":
      return "vert"
    if number == "1":
      return "vert"
    if number == "2":
      return "jaune"
    if number == "3":
      return "orange"
    if number == "4":
      return "rouge"
    return "non défini"
    
  def __getRisk(self, number):
    if number == "1":
      return "vent"
    if number == "2":
      return "pluie inondation"
    if number == "3":
      return "orages"
    if number == "4":
      return "inondations"
    if number == "5":
      return "neige verglas"
    if number == "6":
      return "canicule"
    if number == "7":
      return "grand froid"
    return "non défini" 

  def getvigilance(self, deprequest):
    if len(deprequest) != 2:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: Error in department number")
    #does not work anymore
    return "non defini", "non defini", "non defini"
    url = 'http://vigilance2019.meteofrance.com/data/NXFR34_LFPW_.xml'
    try:
      data = urllib.request.urlopen(url)
    except:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: cannot get data")
      return "non defini", "non defini", "non defini"
    
    try:
      dom = minidom.parse(data)
    except:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: XML format is incorrect")
      return "non defini", "non defini", "non defini"
    
    try:
      for all in dom.getElementsByTagName('datavigilance'):
        depart = all.attributes['dep'].value
        if depart != deprequest:
          continue
        colorresult = all.attributes['couleur'].value
        riskresult = None
        floodresult = None
        for risk in all.getElementsByTagName('risque'):
          riskresult = risk.attributes['valeur'].value
        for flood in all.getElementsByTagName('crue'):
          floodresult = flood.attributes['valeur'].value
        if riskresult:
          risk = self.__getRisk(riskresult).title()
        else:
          risk = "RAS"
        if floodresult:  
          flood = self.__getColor(floodresult).title()
        else:
          flood = "non défini"
        color = self.__getColor(colorresult).title()
        return color, risk, flood
    except:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: data format is incorrect")
      traceback.print_exc()
      pass
    return "non defini", "non defini", "non defini"
