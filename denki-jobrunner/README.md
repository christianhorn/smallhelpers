# denki-jobrunner

## What's this?

Helper scripts to run workloads on a system, and measure the energy
consumption.  This is to be executed on a 'control system', which has
Ansible-engine installed.  

run\_jobs.py should be modified as required.  It will first run 
Ansible playbooks to prepare the control system itself, as well as the
'system under test' (SUT), which is to run the work loads.

The actual jobs to be run are in directory 'files'.  File
httpd-2.4.57.tar.bz2 should also be placed in that directory. 
3 methods for measuring power are available, all of these
have certain requirements:

* RAPL: available on recent x86 arch cpus
* Battery: requires a system with battery, and while measurement
  the system has to run on battery
* Tasmota: this is using metrics from a smart plug.  These are
  available for home use (mostly wlan connected) or enterprise
  grade (rj45 connector).

You should review all scripts and playbooks to get a better
understanding before using these scripts.
