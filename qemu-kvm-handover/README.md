## What's here?

Code for experimenting with handover of power information to KVM
guests.  

Where we are: on a recent Intel system, you can
```
dnf -y install pcp pcp-pmda-denki
cd /usr/libexec/pcp/pmdas/denki
./Install
```

..and then you get power metrics with 'pmrep denki.rapl.msr'.
Now we need to assign overall consumed power of the system to
single processes.  If QEMU-KVM guest, hand over that value to
the process.

## Directory contents

Right now, you can run 'power.py' and it will report in 5sec
spans which process used up how much power.

'makemsrcopy.sh' is a bash script intended to make a copy of the
live systems MSR pieces so pmda-denki can be run with modified
root-directory, to use the static data:

```
cd /usr/libexec/pcp/pmdas/denki
vi Install
Use something like this: args="-U root -D appl0 -r /home/chris/Downloads/tmpdir"
./Install
```

Right now that breaks, something is missing.  When I query the
MSR energy values, I do not get sane values:
```
root@kosmos:/var/lib/pcp/pmdas/denki# pminfo -f denki.rapl.msr

denki.rapl.msr
    inst [0 or "package_energy"] value 18374686479671623696
    inst [1 or "cores_energy"] value 18374686479671623696
    inst [2 or "uncore_energy"] value 18374686479671623696
    inst [3 or "dram_energy"] value 18374686479671623696
    inst [4 or "psys_energy"] value 68702699520
```
