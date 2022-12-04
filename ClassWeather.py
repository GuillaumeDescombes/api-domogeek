#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Gruik coded by GuiguiAbloc
# http://blog.guiguiabloc.fr
# http://api.domogeek.fr
#

import urllib.request, urllib.error, urllib.parse
import json

class weather:

  def todayopenweathermap(self, lat, lng, request, apikey):
        url = "http://api.openweathermap.org/data/2.5/forecast/daily?lat=%s&lon=%s&units=metric&cnt=2&APPID=%s" % (urllib.parse.quote(str(lat)), urllib.parse.quote(str(lng)), urllib.parse.quote(apikey))
        #try:
        data = urllib.request.urlopen(url).read()
        dataopenweathermap = json.loads(data)
        temp = dataopenweathermap['list'][0]['temp']
        pressure =  dataopenweathermap['list'][0]['pressure']
        humidity = dataopenweathermap['list'][0]['humidity']
        weather = dataopenweathermap['list'][0]['weather']
        windspeed = dataopenweathermap['list'][0]['speed']
        if request == "temperature":
          return temp
        if request == "pressure" :
          return pressure
        if request == "humidity" :
          return humidity
        if request == "weather" :
          return weather
        if request == "windspeed":
          return windspeed
        if request == "all":
          return dataopenweathermap['list'][0] 
        else:
          return None
        #except:
        #  return "no data"
  def tomorrowopenweathermap(self, lat, lng, request, apikey):
        url = "http://api.openweathermap.org/data/2.5/forecast/daily?lat=%s&lon=%s&units=metric&cnt=2&APPID=%s" % (urllib.parse.quote(str(lat)), urllib.parse.quote(str(lng)), urllib.parse.quote(apikey))
        try:
          data = urllib.request.urlopen(url).read()
          dataopenweathermap = json.loads(data)
          temp =  dataopenweathermap['list'][1]['temp']
          pressure =  dataopenweathermap['list'][1]['pressure']
          humidity =  dataopenweathermap['list'][1]['humidity']
          weather =  dataopenweathermap['list'][1]['weather']
          windspeed = dataopenweathermap['list'][1]['speed']
          if request == "temperature":
            return temp
          if request == "pressure" :
            return pressure
          if request == "humidity" :
            return humidity
          if request == "weather" :
            return weather
          if request == "windspeed":
            return windspeed
          if request == "all":
            return dataopenweathermap['list'][1]
          else:
            return None
        except:
          return "no data"
  def getrain(self, lat, lng, api_key, date):
        url = "http://api.worldweatheronline.com/free/v1//weather.ashx?q=%s,%s&key=%s&format=json&date=%s&includeLocation=no" % (urllib.parse.quote(str(lat)), urllib.parse.quote(str(lng)), urllib.parse.quote(api_key), urllib.parse.quote(date))
        try:  
          data = urllib.request.urlopen(url).read()
          dataopenweathermap = json.loads(data)
          rain = dataopenweathermap['data']['weather'][0]['precipMM']
          return rain 
        except:
          return "no data"

