#!/usr/bin/env pmpython

import sys
from pcp import pmapi
from pcp.pmapi import pmErr
import cpmapi as c_api
import time
import re
import subprocess
import platform

# Christian Horn <chorn@fluxcoil.net>
# Anthony Harivel <aharivel@redhat.com>
# GPLv2
#
# TODO: 
# - we do not catch shortlived processes, living between start/end
# - lookup specifics of proc.psinfo.utime source

# This here is the daemon-component: it's calculating the power-per-process
# consumption and feeding it back to pmcd via 2 files for pmda-openmetrics.
# To have openmetrics pick it up:
#   echo 'file:///tmp/openmetrics_power.txt' > /var/lib/pcp/pmdas/openmetrics/config.d/power.url

measuretime = 30
denkivar = 0
consumptionpowernow = 0

pidutime = {}
pidutimeold = {}
pidpsargs = {}

myhostname = re.sub('.local', '', platform.node())

def check_metric_exists(metric_name):
	try:
		ctx = pmapi.pmContext(c_api.PM_CONTEXT_HOST, "local:")
		pmids = ctx.pmLookupName([metric_name])
		results = ctx.pmFetch(pmids)
		return results.contents.get_numval(0) > 0
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

	# Fetch energy-metric
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

	if (powermetric == 'denki.rapl.sysfs'):
		denkipmids = ctx.pmLookupName('denki.rapl.sysfs')
		denkidescs = ctx.pmLookupDescs(denkipmids)
		denkiresults = ctx.pmFetch(denkipmids)
		atom = ctx.pmExtractValue(denkiresults.contents.get_valfmt(0),
			denkiresults.contents.get_vlist(0, 0), denkidescs[0].contents.type,
			c_api.PM_TYPE_U64)
		denkivar = atom.ull

	if (powermetric == 'hypervisor-pcp'):
		pmout = subprocess.run(['pminfo', '-f', '-h', '192.168.4.1', 'openmetrics.power.proc.consumed'], capture_output=True, text=True)
		for line in pmout.stdout.splitlines():
			# Do we have a qemu-process here?
			if re.match('^    inst.*qemu', line):
				# Is it _our_ process?
				namestr = re.sub('.*guest=', '', line)
				namestr = re.sub(',.*', '', namestr)
				if re.match(myhostname, namestr):
					# print("Found my hostname: ", namestr)
					myconsumptionstr = re.sub('.* ', '', line)
					denkivar = float(myconsumptionstr)

# Initialization


if check_metric_exists('lmsensors.macsmc_hwmon_isa_0000.total_system_power'):
	print("Metric lmsensors.macsmc_hwmon_isa_0000.total_system_power was found, using that.")
	powermetric = 'lmsensors.macsmc_hwmon_isa_0000.total_system_power'
	# This metric is a gauge, no counter
	powermetricgauge = 1
elif check_metric_exists('denki.rapl.msr'):
	print("Metric denki.rapl.msr was found, using that.")
	powermetric = 'denki.rapl.msr'
	# This metric is a counter
	powermetricgauge = 0
elif check_metric_exists('denki.rapl.sysfs'):
	print("Metric denki.rapl.sysfs was found, using that.")
	powermetric = 'denki.rapl.sysfs'
	# This metric is a counter
	powermetricgauge = 0
else:
	print("No physical sensors found, maybe I'm a KVM guest.")
	print("Will try to get my power metric from the hypervisor's pmcd.")
	return_code = subprocess.run(['pminfo', '-h', '192.168.4.1', 'openmetrics.power']).returncode  
	if return_code == 0:  
		print("Looks good, metric openmetrics.power was found.")  
	else:
		print("That did not work out.  So no metrics for system consumption were found. Exiting.")
		exit()
	powermetric = 'hypervisor-pcp'
	powermetricgauge = 1

fetchall()

while True:
	print("Sleeping",measuretime,"sec..")
	time.sleep(measuretime)
	
	outfilepower = open('/tmp/openmetrics_power.txt', 'w', encoding="utf-8")

	# copy over old data from last cycle
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

	print("Number of consumed userland shares:", userlandsum)
	print("New processes which appeared:",newprocs)
	
	if (powermetricgauge == 0):
		# We have a counter metric, need to compute
		if denkivar > denkivarold:
			poweraverage = (denkivar - denkivarold)/measuretime
	else:
		# We have a gauge metric, no need to compute
		poweraverage = denkivar

	print("Overall system consumption:", "{:5.3f}".format(poweraverage),"W")
	
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
		# if ( procconsumed[pid] > 0.1 ):
		if ( procconsumed[pid] > 0 ):
			# trim down command to a maximum of 3 strings, for readability.
			# We need at least 3 so KVM guests can identify themself from the proc list.
			resu = pidpsargs[pid].split(' ')
			if ( len(resu) > 2 ):
				myresu = f"{resu[0]} {resu[1]} {resu[2]}"
			elif ( len(resu) > 1 ):
				myresu = f"{resu[0]} {resu[1]}"
			else:
				myresu = resu[0]

			outstring = f"""proc.consumedpercent {{name="{pid} {myresu}"}} {"{:2.1f}".format(procpercent[pid])}\n"""
			outfilepower.write(outstring)
			outstring = f"""proc.consumed {{name="{pid} {myresu}"}} {"{:5.3f}".format(procconsumed[pid])}\n"""
			outfilepower.write(outstring)

	outfilepower.write(f"""overall {{name="system"}} {"{:5.3f}".format(poweraverage)} \n""")
	outfilepower.close()
