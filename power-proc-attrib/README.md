## What's here?

Code to attribute electrical power consumption of the system to
single processes.
Consumption of central components like LED-screen of a laptop is
simply getting attributed to all of the processes.  

![screenshot](screenshot.png)

## Design goals
* Do not employ ebpf code, so work just from userland.  This
  means we are just repeatedly looking at the process table, and
  shortlived processes can use up energy without being attributed
  by us.
* Easy to use, few dependencies

## Requirements/operation basics

* Performance Co-Pilot (PCP): this code communicates with pmcd,
  and pmda-denki to understand the overall consumption of the system.
  Works i.e. with Intel RAPL MSR provided metrics.
  pmda-linux provides details on how many userland computations the
  currently running processes did, the overall electrical consumption
  is then accordingly attributed to single processes.
* some PMDA's are required:
  * pmda-linux, it provides data on used userland cpu cycles
  * pmda-denki, on Intel systems it will provide RAPL readings
  * pmda-lmsensors, on Apple Silicon Mac with Asahi this will
    provide power consumption metrics
  * pmda-openmetrics for getting the data back into PCP.
* With that, the power-attribution-metrics are available in pmcd,
  and can for example be visualized.

## Installation

For example on Fedora43:
```
# (optional)
#  Install pmda-denki version which can provide Intel MSR power
#  metrics, 

# Setup pcp with pmlogger and pmdas, i.e. in execute
dnf -y install pcp-zeroconf pcp-pmda-denki pcp-pmda-openmetrics \
  python3-pcp perl-PCP-PMDA pcp-devel pcp-libs-devel
cd /usr/libexec/pcp/pmdas/denki && ./Install
cd /usr/libexec/pcp/pmdas/openmetrics && ./Install


# Start this code, keep it running, confirm it makes sane output
# about power consumption of the processes to the terminal:
./power.py
# Example:
Sleeping  10 sec..
The processes consumed this many userland shares: 2200
New processes which appeared: 0
System consumption: 8.20 W

+-- process consumption share from overall consumption
|	 +-- process energy consumption
|	 |	     +-- process pid and command
|	 |	     |
1 %	 0.1 W	 sway
1 %	 0.1 W	 /usr/lib64/firefox/firefox -contentproc
1 %	 0.1 W	 swaybar -b
1 %	 0.1 W	 /usr/lib64/firefox/firefox -contentproc
1 %	 0.1 W	 /usr/bin/python3 ./power7.py
1 %	 0.1 W	 /usr/lib64/firefox/firefox -contentproc
1 %	 0.1 W	 dbus-broker --log
1 %	 0.1 W	 /opt/google/chrome/chrome --type=gpu-process
1 %	 0.1 W	 /usr/lib64/firefox/firefox -contentproc
1 %	 0.1 W	 vim README.md
3 %	 0.2 W	 /usr/lib64/firefox/firefox
7 %	 0.6 W	 /usr/libexec/upowerd
10 % 0.8 W	 alacritty
22 % 1.8 W	 python3 /opt/bumblebee-status/bumblebee-status
28 % 2.3 W	 /usr/lib64/firefox/firefox -contentproc
[..]
```

## Bugs/Future
- if looking at gauge metric like battery-power-now, we only 
  consider single values. Higher frequency means higher accuracy
- we do not catch shortlived processes, living between start/end
- lookup specifics of proc.psinfo.utime source
