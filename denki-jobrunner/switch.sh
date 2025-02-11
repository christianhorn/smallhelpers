#!/usr/bin/bash

set -x

virsh destroy amd10
virsh undefine amd10

cp virsh-def/def-plain virsh-def/new
sed -ie "s,CPUMODEL,$1," virsh-def/new
virsh define virsh-def/new
virsh start amd10 --console

# virsh list
# virsh start amd10 --console
