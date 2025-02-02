# pylint: disable=C0111,R0903

"""Displays the current power consumption

https://bumblebee-status.readthedocs.io/en/main/development/module.html

"""

import core.widget
import core.module
import subprocess

class Module(core.module.Module):
    @core.decorators.every(seconds=59)  # ensures one update per minute
    def __init__(self, config, theme):
        # super().__init__(config=config, theme)
        super().__init__(config=config, theme=theme, widgets=core.widget.Widget(self.msrpower))

    def msrpower(self, widgets):
        # return "42"
        output = subprocess.getoutput("pmrep denki.rapl.msr -i psys_energy -t 3 -s 2 | tail -n 1")
        # strip whitespaces, convert to proper float, then to integer
        output = int(float(output.strip()))
        # return 'Cons ' + str(output) + 'W'
        return '🔌 ' + str(output) + 'W'


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
