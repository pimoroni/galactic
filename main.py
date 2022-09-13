# Galactic - wireless environmental monitoring and logging
#
# On first run Enviro will go into provisioning mode where it appears
# as a wireless access point called "Enviro <board type> Setup". Connect
# to the access point with your phone, tablet or laptop and follow the
# on screen instructions.
#
# The provisioning process will generate a `config.py` file which 
# contains settings like your wifi username/password, how often you
# want to log data, and where to upload your data once it is collected.
#
# You can use galactic out of the box with the options that we supply
# or alternatively you can create your own firmware that behaves how
# you want it to - please share your setups with us! :-)
#
# Need help? check out https://pimoroni.com/galactic-guide
#
# Happy data hoarding folks,
#
#   - the Pimoroni pirate crew

# import galactic firmware, this will trigger provisioning if needed
import galactic_u as galactic

# initialise galactic
galactic.startup()

# now that we know the device is provisioned import the config
try:
  import config
except:
  galactic.halt("! failed to load config.py")

# if the clock isn't set...
if not galactic.is_clock_set():
  galactic.logging.info("> clock not set, synchronise from ntp server")
  if not galactic.sync_clock_from_ntp():
    # failed to talk to ntp server go back to sleep for another cycle
    galactic.halt("! failed to synchronise clock")
  galactic.logging.info("  - rtc synched")      

# check disk space...
if galactic.low_disk_space():
  # less than 10% of diskspace left, this probably means cached results
  # are not getting uploaded so warn the user and halt with an error
  galactic.halt("! low disk space")

# go to sleep until our next scheduled reading
#galactic.sleep()

import time
time.sleep(5)

import scenes.lava_lamp