# bumblebee-status msrpower metric

## What's this?

This is a mobule to display the electrical power consumption in the 
bumblebee-status bar.

The 'battery' module already has a setting to show consumption, but it's
not using the cpus MSR-register as source.

This here is the newer version, it relies on pcp-pmda-summary.

The MSR-registers can not be read by normal users, I'm using Performance
Co-Pilot (PCP) to read the metric, and then get it from there.

![screenshot-msrpower](screenshot-msrpower.png)

## Setup

Normal setup of bumblebee-status, as root:
```
cd /opt
git clone https://github.com/tobi-wan-kenobi/bumblebee-status
```

PCP pmda-denki is not yet able to read MSR registers, that's requested 
[in this pull request](https://github.com/performancecopilot/pcp/pull/2106).
As a workaround, you can build PCP with that PR.

Once the request is accepted, do a normal setup of PCP with pmda-denki, for example on Fedora 
or RHEL:
```
dnf install pcp pcp-pmda-denki pcp-pmda-summary
systemctl enable --now pmcd
cd /var/lib/pcp/pmdas/denki
./Install
```

As user now verify that pmda-denki is offering the metric:
```
$ pmrep denki.rapl.msr -i psys_energy
  d.raplmsr
  psys_ener
         /s
        N/A
      9.976
      8.000
      7.999
      7.999
      [...]
```

If that looks good, setup the module:
```
cd ~/Downloads
git clone https://github.com/christianhorn/smallhelpers
mkdir -p ~/.config/bumblebee-status/modules
cp smallhelpers/bumblebee-status-msrpower-metric/msrpower.py ~/.config/bumblebee-status/modules/
```

Now as root, setup pmda-summary.  It will do caching of the denki.rapl.msr
metrics for us, so we can then query a metric which can immediately return
a value.  First, add the following 2 lines to /etc/pcp/summary/expr.pmie:
```
summary.rapl.msr =
           denki.rapl.msr #'psys_energy';
```

Then execute these steps as root:
```
cd /usr/libexec/pcp/pmdas/summary/
echo '@ summary.rapl.msr Power averaged' >>help
echo 'Power averaged' >>help

cp ~chris/Downloads/bumblebee-status-msrpower-metric/pmns .
systemctl enable --now pmie
./Install
```

When asked for a a timespan, hit "return".  Then we can query the new
metric:
```
[chris@космос ~]$ pmrep summary.rapl.msr
  s.r.msr
    / sec
    9.701
    9.701
    9.701
    9.701
```

Modify sway config:
```
vi ~/.config/sway.config
[...]
bar {
    position top

    # When the status_command prints a new line to stdout, swaybar updates.
    # The default just shows the current date and time.
    # status_command while date +'%Y-%m-%d %l:%M:%S %p'; do sleep 1; done

    status_command /opt/bumblebee-status/bumblebee-status -m msrpower

    colors {
        statusline #ffffff
        background #323232
        inactive_workspace #32323200 #32323200 #5c5c5c
    }
}
[...]
```

I use this right now:
```
    status_command /opt/bumblebee-status/bumblebee-status \
      -m traffic pipewire cpu memory msrpower sensors2 battery weather datetimetz time \
      -p cpu.format={:.00f}% \
        traffic.exclude=virbr,lo,redhat,nebula traffic.showname=False traffic.format={:.0f} \
        time.format="日本 %H:%M" \
        datetimetz.format="独 %H:%M" datetimetz.timezone="Europe/Berlin" \
        memory.format="{used}" \
        sensors2.showtemp=false sensors2.showcpu=false  sensors2.field_exclude=fan2 \
        traffic.interval=5s cpu.interval=5s sensors2.interval=5s \
        memory.interval=1m weather.interval=30m battery.interval=1m \
     -t powerline
```

Then have sway reread the changed config in pushing ctrl+superkey+c .
To debug, execute '/opt/bumblebee-status/bumblebee-status -m msrpower'
on the command line.

## Bugs

* This code might also fit as extension of the existing 'battery' module, 
  but as PCP is required here for actually reading the metric, I feel like
  that's to specific to be added to 'battery'.
