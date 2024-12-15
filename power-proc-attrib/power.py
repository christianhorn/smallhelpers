#!/usr/bin/env pmpython

import sys
from pcp import pmapi
from pcp.pmapi import pmErr
import cpmapi as c_api
import time
import re

# TODO: fetch consumption metric as float
#	   if looking at gauge metric like battery-power-now, we only
#		   consider the last value right now.
#	   we do not catch shortlived processes, living between start/end
#	   lookup specifics of proc.psinfo.utime source

measuretime = 60

procdict = {}
procdictold = {}
denkivar = 0
consumptionpowernow = 0

def fetchall():
	global denkivar
	global consumptionpowernow

	print("debug0")
	# Setup context, initiate fetching
	ctx = pmapi.pmContext()
	pmids = ctx.pmLookupName('proc.psinfo.utime')
	descs = ctx.pmLookupDescs(pmids)
	results = ctx.pmFetch(pmids)
	allpids = ctx.pmGetInDom(descs[0])[1]

	# Fetch energy-value for rapl-msr-psys_energy
	denkipmids = ctx.pmLookupName('denki.raplmsr')
	denkidescs = ctx.pmLookupDescs(denkipmids)
	denkiresults = ctx.pmFetch(denkipmids)
	atom = ctx.pmExtractValue(denkiresults.contents.get_valfmt(0),
		denkiresults.contents.get_vlist(0, 4), denkidescs[0].contents.type,
		c_api.PM_TYPE_U32)
	denkivar = atom.ul

	print("debug0.5")
	# Take snapshot of the userland-counters of all processes
	cnt = 0
	# procdict = {}
	for process in allpids:
		atom = ctx.pmExtractValue(results.contents.get_valfmt(0),
			results.contents.get_vlist(0, cnt), descs[0].contents.type,
			c_api.PM_TYPE_U32)
		cnt += 1
		if atom.ul != 0:
			procshort = re.sub('/.*/','',process)
			procshort = re.sub('^.* ','',procshort)
			procshort = re.sub('^./','',procshort)
			if procshort in procdict:
				procdict[procshort] += atom.ul
			else:
				procdict[procshort] = atom.ul

	print("debug0.7")
	# Fetch denki.bat.power_now -i 0
	denkipmids = ctx.pmLookupName('denki.bat.power_now')
	denkidescs = ctx.pmLookupDescs(denkipmids)
	denkiresults = ctx.pmFetch(denkipmids)
	atom = ctx.pmExtractValue(denkiresults.contents.get_valfmt(0),
		denkiresults.contents.get_vlist(0, 0), denkidescs[0].contents.type,
		c_api.PM_TYPE_U32)
	consumptionpowernow = atom.ul
	print("debug1")

fetchall()

while True:
	print("Sleeping ",measuretime,"sec..")
	time.sleep(measuretime)
	
	# copy over all data, for next cycle
	procdictold = procdict.copy()
	denkivarold = denkivar

	fetchall()

	# How many userland shares were worked in the timespan?
	userlandsum = 0
	newprocs = 0
	for key in procdict.keys():
		if procdict[key] != 0:
			if key in procdictold:
				if procdict[key] != procdictold[key]:
					userlandsum += procdict[key] - procdictold[key]
			else:
				newprocs += 1
	print("The processes consumed this many userland shares:",userlandsum)
	print("New processes which appeared:",newprocs)
	
	if denkivar > denkivarold:
		consumptionmsr = (denkivar - denkivarold)/measuretime
	print("System consumption, calculated based on RAPL MSR:",
		"{:2.2f}".format(consumptionmsr),"W")
	print("System consumption, calculated based on power_now::",
		"{:2.2f}".format(consumptionpowernow),"W")
	
	# So, how many percent of the overall shares had each process?
	procpercent = {}
	procconsumedbat = {}
	procconsumedmsr = {}
	for key in procdict.keys():
		if procdict[key] != 0:
			if key in procdictold:
				if procdict[key] != procdictold[key]:
					procpercent[key] = int(100*(procdict[key] - procdictold[key])/userlandsum)
					procconsumedbat[key] = int(100*(procdict[key] - procdictold[key])/userlandsum) * consumptionpowernow / 100
					procconsumedmsr[key] = int(100*(procdict[key] - procdictold[key])/userlandsum) * consumptionmsr / 100
	
	sorted_items = sorted(procpercent.items(), key=lambda kv: (kv[1], kv[1]))
	
	print("")
	print("+-- process consumption share from overall consumption")
	print("|	+-- process energy consumption based on bat-powernow metric")
	print("|	|	+-- process energy consumption based on RAPL MSR metric")
	print("|	|	|	   +-- process pid and command")
	print("|	|	|	   |")
	for key in sorted_items:
		# print(key)
		# print(key[1],"%\t",key[0])
		if key[1] >= 1:
			print(key[1],"%\t",
				"{:2.2f}".format(procconsumedbat[key[0]]),"W\t",
				"{:2.2f}".format(procconsumedmsr[key[0]]),"W\t",key[0])
	
	# powermsr {process="firefox"} 123
	with open('/tmp/openmetrics_power','w') as f:
		print('powermsrfull {p="psys"} ' + "{:2.2f}".format(consumptionmsr), file=f)
		print('powerbatfull {p="psys"} ' + "{:2.2f}".format(consumptionpowernow), file=f)
		for key in sorted_items:
			if key[1] >= 1:
				print('powermsr {p="' + str(key[0]) + '"} ' + "{:2.2f}".format(procconsumedmsr[key[0]]), file=f)
				print('powerbat {p="' + str(key[0]) + '"} ' + "{:2.2f}".format(procconsumedbat[key[0]]), file=f)

