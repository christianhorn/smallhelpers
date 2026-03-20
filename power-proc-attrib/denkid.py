#!/usr/bin/env pmpython

import sys
from pcp import pmapi
from pcp.pmapi import pmErr
import cpmapi as c_api
import time
import re

# Christian Horn <chorn@fluxcoil.net>
# GPLv2
#
# TODO: 
# - if looking at gauge metric like battery-power-now, we only consider single values.
#	Higher frequency means higher accuracy
# - we do not catch shortlived processes, living between start/end
# - lookup specifics of proc.psinfo.utime source

# This here is the daemon-component: it's calculating the power-per-process
# consumption and feeding it back to pmcd via 2 files for pmda-openmetrics:

# To pick up: 
# echo 'file:///tmp/openmetrics_power.txt' > /var/lib/pcp/pmdas/openmetrics/config.d/power.url

measuretime = 30
denkivar = 0
consumptionpowernow = 0

pidutime = {}
pidutimeold = {}
pidpsargs = {}

def check_metric_exists(metric_name):
	try:
		ctx = pmapi.pmContext(c_api.PM_CONTEXT_HOST, "local:")
		pmids = ctx.pmLookupName([metric_name])
		return True
	except pmapi.pmErr:
		return False

def fetchall():
	global denkivar
	global consumptionpowernow

	# Setup context, initiate fetching
	ctx = pmapi.pmContext()
	utimemetrics = [
		'proc.psinfo.pid',
		'proc.psinfo.utime',
		'proc.psinfo.psargs'
	]
	pmids = ctx.pmLookupName(utimemetrics)
	descs = ctx.pmLookupDescs(pmids)
	results = ctx.pmFetch(pmids)

	# TODO: would be nice if we could go without this loop.
	# Currently we need it to get the elements in all 3 lists to match up.
	while ( ( results.contents.get_numval(0) != results.contents.get_numval(1) ) or 
			( results.contents.get_numval(0) != results.contents.get_numval(2) ) ):
		print("### Fetching data again ###")
		time.sleep(1)
		results = ctx.pmFetch(pmids)

	# Take snapshot of the userland-counters of all processes
	for line in range( results.contents.get_numval(0) ):
		# grab the pid, we need it as key for the dicts
		atom = ctx.pmExtractValue(
			results.contents.get_valfmt(0),
			results.contents.get_vlist(0, line),
			descs[0].contents.type,
			c_api.PM_TYPE_U32
		)
		pid = atom.ul

		# grab the utime
		atom = ctx.pmExtractValue(
			results.contents.get_valfmt(1),
			results.contents.get_vlist(1, line),
			descs[1].contents.type,
			c_api.PM_TYPE_U32
		)
		utime = atom.ul

		# grab the process details.  We need these to construct a proper identifier.
		# Simple pid's will get reused, but "pid / command string" not.
		atom = ctx.pmExtractValue(
			results.contents.get_valfmt(2),
			results.contents.get_vlist(2, line),
			descs[2].contents.type,
			c_api.PM_TYPE_STRING
		)
		psargs = atom.cp.decode('utf-8')

		# print(f"{pid} / {utime} / {psargs}")
		pidutime[pid] = utime
		pidpsargs[pid] = psargs

	# Fetch energy-value
	if (powermetric == 'lmsensors.macsmc_hwmon_isa_0000.total_system_power'):
		denkipmids = ctx.pmLookupName('lmsensors.macsmc_hwmon_isa_0000.total_system_power')
		denkidescs = ctx.pmLookupDescs(denkipmids)
		denkiresults = ctx.pmFetch(denkipmids)
		atom = ctx.pmExtractValue(denkiresults.contents.get_valfmt(0),
			denkiresults.contents.get_vlist(0, 0), denkidescs[0].contents.type,
			c_api.PM_TYPE_FLOAT)
		denkivar = atom.f

	if (powermetric == 'denki.rapl.msr'):
		denkipmids = ctx.pmLookupName('denki.rapl.msr')
		denkidescs = ctx.pmLookupDescs(denkipmids)
		denkiresults = ctx.pmFetch(denkipmids)
		atom = ctx.pmExtractValue(denkiresults.contents.get_valfmt(0),
			denkiresults.contents.get_vlist(0, 4), denkidescs[0].contents.type,
			c_api.PM_TYPE_U32)
		denkivar = atom.ul

# Initialization

powermetric = 'none'
if check_metric_exists('lmsensors.macsmc_hwmon_isa_0000.total_system_power'):
	print("Metric lmsensors.macsmc_hwmon_isa_0000.total_system_power was found, using that.")
	powermetric = 'lmsensors.macsmc_hwmon_isa_0000.total_system_power'
	# This metric is a gauge, no counter
	powermetricgauge = 1

if check_metric_exists('denki.rapl.msr'):
	print("Metric denki.rapl.msr was found, using that.")
	powermetric = 'denki.rapl.msr'
	# This metric is a counter
	powermetricgauge = 0

if ( powermetric == 'none' ): 
	print("No usable power consumption metrics found!")
	exit()

fetchall()

while True:
	print("Sleeping ",measuretime,"sec..")
	time.sleep(measuretime)
	
	outfilepower = open('/tmp/openmetrics_power.txt', 'w', encoding="utf-8")

	# copy over all data, for next cycle
	pidutimeold = pidutime.copy()
	denkivarold = denkivar

	pidutime = {}
	fetchall()

	# Create a summary for each process name, i.e. count up
	# multiple firefox threads
	procshortdict = {}
	userlandsum = 0
	newprocs = 0

	for pid in pidutime.keys():
		if pid in pidutimeold:
			if pidutime[pid] != pidutimeold[pid]:
				userlandsum += pidutime[pid] - pidutimeold[pid]
		else:
			newprocs += 1

	print("The processes consumed this many userland shares:",userlandsum)
	print("New processes which appeared:",newprocs)
	
	if (powermetricgauge == 0):
		# We have a counter metric, need to compute
		if denkivar > denkivarold:
			poweraverage = (denkivar - denkivarold)/measuretime
	else:
		# We have a gauge metric, no need to compute
		poweraverage = denkivar

	print("Overall system consumption:", "{:2.2f}".format(poweraverage),"W")
	
	# So, how many percent of the overall shares had each process?
	procpercent = {}
	procconsumed = {}
	for pid in pidutime.keys():
		if pid in pidutimeold:
			if pidutime[pid] != pidutimeold[pid]:
				pidutimediff = pidutime[pid] - pidutimeold[pid]
				procpercent[pid] = int( 100 * pidutimediff / userlandsum)
				procconsumed[pid] = procpercent[pid] * poweraverage / 100
	
	for pid in procpercent.keys():
		# print("debug:", pidpsargs[pid])

		if ( procconsumed[pid] > 0.1 ):
			# trim down command to one or 2 strings, for readability
			resu = pidpsargs[pid].split(' ')
			if ( len(resu) > 1 ):
				myresu = f"{resu[0]} {resu[1]}"
			else:
				myresu = resu[0]

			outstring = f"""proc.consumedpercent {{name="{pid} {myresu}"}} {"{:2.1f}".format(procpercent[pid])}\n"""
			outfilepower.write(outstring)
			outstring = f"""proc.consumed {{name="{pid} {myresu}"}} {"{:5.1f}".format(procconsumed[pid])}\n"""
			outfilepower.write(outstring)

	outfilepower.write(f"""overall {{name="system"}} {"{:5.2f}".format(poweraverage)} \n""")
	outfilepower.close()
