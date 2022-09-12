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

# take a reading from the onboard sensors
reading = galactic.get_sensor_readings()

# here you can customise the sensor readings by adding extra information
# or removing readings that you don't want, for example:
# 
#   del readings["temperature"]        # remove the temperature reading
#
#   readings["custom"] = my_reading()  # add my custom reading value

# is an upload destination set?
if galactic.config.destination:
  # if so cache this reading for upload later
  galactic.cache_upload(reading)

  # if we have enough cached uploads...
  if galactic.is_upload_needed():
    galactic.logging.info(f"> {galactic.cached_upload_count()} cache files need uploading")
    if not galactic.upload_readings():
      galactic.halt("! reading upload failed")
else:
  # otherwise save reading to local csv file (look in "/readings")
  galactic.save_reading(reading)

# go to sleep until our next scheduled reading
galactic.sleep()