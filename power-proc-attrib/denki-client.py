#!/usr/bin/env pmpython

from pcp import pmapi
from pcp.pmapi import pmErr
import cpmapi as c_api
import time
import re
import subprocess

from ctypes import c_int, c_char_p, POINTER, byref

# Christian Horn <chorn@fluxcoil.net>
# GPLv2
#
# TODO: 
# - if looking at gauge metric like RAPL/system, we only consider single values.
#	Higher frequency means higher accuracy
# - we do not catch shortlived processes, living between start/end
# - lookup specifics of proc.psinfo.utime source

measuretime = 30

# pidutime = {}
# pidutimeold = {}
pidpsargs = {}
pidconsumed = {}
pidpercent = {}

def check_metric_exists(metric_name):
	try:
		ctx = pmapi.pmContext(c_api.PM_CONTEXT_HOST, "local:")
		pmids = ctx.pmLookupName([metric_name])
		return True
	except pmapi.pmErr:
		return False

def fetchall():
	global poweroverall

	# Setup context, initiate fetching
	ctx = pmapi.pmContext()
	metrics = [
		'openmetrics.power.overall',
		'openmetrics.power.proc.consumedpercent'
	]
	pmids = ctx.pmLookupName(metrics)
	descs = ctx.pmLookupDescs(pmids)
	results = ctx.pmFetch(pmids)

	atom = ctx.pmExtractValue(
		results.contents.get_valfmt(0),
		results.contents.get_vlist(0, 0),
		descs[0].contents.type,
		c_api.PM_TYPE_FLOAT
	)
	poweroverall = atom.f
	# print("numval0:", results.contents.get_numval(0) )

	# pmoutlist.clear()
	pmout = subprocess.run(['pminfo', '-f' ,'openmetrics.power.proc.consumedpercent'], capture_output=True, text=True)
	for line in pmout.stdout.splitlines():
		if re.match('^    inst', line):
			# pmoutlist.append(line)
			psargs = re.sub('.*name:[\\d]+ ', '', line)
			psargs = re.sub('".*', '', psargs)
			procperc = re.sub('.* ', '', line)
			pid = re.sub('.*name:', '', line)
			pid = re.sub(' .*', '', pid)
			# print(f"psargs {psargs} : procperc: {procperc} pid: {pid}")

			pidpsargs[pid] = psargs
			pidpercent[pid] = int(procperc)

	pmout = subprocess.run(['pminfo', '-f' ,'openmetrics.power.proc.consumed'], capture_output=True, text=True)
	for line in pmout.stdout.splitlines():
		if re.match('^    inst', line):
			procconsumed = re.sub('.* ', '', line)
			pid = re.sub('.*name:', '', line)
			pid = re.sub(' .*', '', pid)
			# print(f"psargs {psargs} : procperc: {procperc} pid: {pid}")

			pidconsumed[pid] = float(procconsumed)

# Initialization

if not check_metric_exists('openmetrics.power.overall'):
	print("Metric openmetrics.power.overall was not found, exiting.")
	exit()
if not check_metric_exists('openmetrics.power.proc.consumedpercent'):
	print("Metric openmetrics.power.proc.consumedpercent was not found, exiting.")
	exit()

while True:
	pidpsargs = {}
	pidpercent = {}
	pidconsumed = {}
	print("debug 1")
	fetchall()
	print("debug 2")

	print("System consumption:", "{:2.2f}".format(poweroverall),"W")
	
	# Computation and output of the full percentages
	# sorted_items = sorted(procpercent.items(), key=lambda kv: (kv[1], kv[1]))
	sorted_items = sorted(pidpercent.items(), key=lambda kv: (kv[1], kv[1]))
	print("")
	print("+-- process consumption share from overall consumption")
	print("|	 +-- process energy consumption")
	print("|	 |	 +-- process pid and command")
	print("|	 |	 |")

	for key in sorted_items:
		if key[1] >= 1:
			# trim down command to one or 2 strings, for readability
			resu = pidpsargs[key[0]].split(' ')
			if ( len(resu) > 1 ):
				myresu = f"{resu[0]} {resu[1]}"
			else:
				myresu = resu[0]
			print(key[1],"%\t",
				"{:2.1f}".format(pidconsumed[key[0]]),"W\t",myresu)

	print("Sleeping ",measuretime,"sec..")
	time.sleep(measuretime)
