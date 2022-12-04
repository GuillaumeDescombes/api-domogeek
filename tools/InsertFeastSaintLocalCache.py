#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Gruik coded by GuiguiAbloc
# http://blog.guiguiabloc.fr
# http://api.domogeek.fr
#
# Insert feasted saint day list in Redis
 
import csv
import sys
import hashlib
import configparser

configFileName = "/etc/apidomogeek.conf"
config = configparser.ConfigParser()

print ("opening config file")
with open(configFileName) as configfile:
  config.read_file(configfile)

try:
  config.add_section('cache')
except:
  pass

class TransformCSV(csv.Dialect):
    delimiter = ";"
    quotechar = None
    escapechar = None
    doublequote = None
    lineterminator = "\r\n"
    quoting = csv.QUOTE_NONE
    skipinitialspace = False

file = open("saintlist.csv", "rt", encoding = 'utf-8')
reader = csv.reader(file, TransformCSV())

def insertsaintdate():
  for row in reader:
      nameentry = row[0]
      dayentry = row [1] 
      monthentry = row [2]
      group = dayentry+"-"+monthentry
      key="feastedsaint|" + group
      value = config.get("cache", key, fallback = None)
      if value is not None:
        nameentry = value+","+nameentry
      config.set("cache", key, nameentry)

###################
# Launch Function #
###################

print ("process saint date")
insertsaintdate()

print ("write config file")
with open(configFileName, 'w') as configfile:
  config.write(configfile)
