#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# coded by GuiguiAbloc
# http://blog.guiguiabloc.fr
# Rewritten by Guillaume Descombes
# V1 2022.12.04
# V2 2024.09.22

import syslog
import json
import traceback
import time
import requests

#https://donneespubliques.meteofrance.fr/?fond=produit&id_produit=305&id_rubrique=50

class MeteoFranceVigilance:

  def __init__ (self, apiKey):
    self.MeteoFranceOptions = {
            'verify': False,
            'timeout': 5,
            'headers': {
              "User-Agent": "curl/7.88.1",
              "accept": "*/*",
              "apikey": apiKey
            }
    }
    requests.packages.urllib3.disable_warnings()

  def __getColor(self, number):
    if type(number) == int:
      number=str(number)
    if number == "0":
      return "non défini"
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
    if type(number) == int:
      number=str(number)
    if number == "1":
      return "vent"
    if number == "2":
      return "pluie"
    if number == "3":
      return "orages"
    if number == "4":
      return "crues"
    if number == "5":
      return "neige"
    if number == "6":
      return "canicule"
    if number == "7":
      return "grand froid"
    if number == "8":
      return "avalanches"
    if number == "9":
      return "vagues"
    return "non défini" 

  def getVigilance(self, deprequest):
    if type(deprequest) == int:
      if deprequest<10:
        deprequest="0"+str(deprequest)
      else:
        deprequest=str(deprequest)
    if len(deprequest) != 2:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: Error in department number '{deprequest}'")
      traceback.print_exc()
      return "ERROR", "", "", "", ""

    try:
      url = "https://public-api.meteofrance.fr/public/DPVigilance/v1/cartevigilance/encours"
      #disable proxy and meteofrance does not like it ....
      proxies = {
        "http": "",
        "https": "",
      }
      response = requests.get(url, **self.MeteoFranceOptions, proxies=proxies)
    except Exception as err:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: cannot get data ({err})")
      traceback.print_exc()
      return "ERROR", "", "", "", ""

    try:
      data = response.json()
    except:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: JSON format is incorrect")
      traceback.print_exc()
      return "ERROR","", "", "", ""

    try:
      periods = data['product']['periods']
      for period in periods:
        domains = period['timelaps']['domain_ids']
        for domain in domains:
          depart = domain['domain_id']
          if depart != deprequest:
            continue
          #print(f"domain: {domain}")
          globalColorResult = self.__getColor(domain['max_color_id']).title()
          riskNameResult = ""
          floodColorResult = self.__getColor(0).title()
          stormColorResult = self.__getColor(0).title()
          phenomenons = domain['phenomenon_items']
          for phenomenon in phenomenons:
            if phenomenon['phenomenon_id'] == "4": #Crue / Flood
              floodColorResult = self.__getColor(phenomenon['phenomenon_max_color_id']).title()
            if phenomenon['phenomenon_id'] == "3": #Orage / Storm
              stormColorResult = self.__getColor(phenomenon['phenomenon_max_color_id']).title()
            if int(phenomenon['phenomenon_max_color_id']) >= 3: #orange or red
              riskNameResult = riskNameResult + self.__getRisk(phenomenon['phenomenon_id']).title() +", "
          if riskNameResult != "":
            #remove the last coma
            riskNameResult=riskNameResult[0:-2]
          else:
            riskNameResult = "Aucun"
          return "OK", riskNameResult, globalColorResult, floodColorResult, stormColorResult
    except:
      syslog.syslog(syslog.LOG_ERR, "Vigilance: data format is incorrect")
      traceback.print_exc()
    return "UNDEFINED", "", "", "", ""

if __name__ == "__main__":
  #Test for 92 & 34
  VigilanceRequest = MeteoFranceVigilance("")
  VigilanceResponse=VigilanceRequest.getVigilance(92)
  print(f"response (92): {VigilanceResponse}")
  VigilanceResponse=VigilanceRequest.getVigilance(34)
  print(f"response (34): {VigilanceResponse}")
