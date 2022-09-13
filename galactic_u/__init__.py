# keep the power rail alive by holding VSYS_EN high as early as possible
# ===========================================================================
from galactic_u.constants import *
from machine import Pin

# detect board model based on devices on the i2c bus and pin state
# ===========================================================================
model = "urban" # otherwise it's urban..

# return the module that implements this board type
def get_board():
  if model == "urban":
    import galactic_u.boards.unicorn as board
  return board
  
# set up the activity led
# ===========================================================================
from machine import Timer
activity_led_pin = Pin("LED")
activity_led_pin.off()

# set the brightness of the activity led
def activity_led(brightness):
  activity_led_pin.value(brightness)
  
activity_led_timer = Timer(-1)
activity_led_state = False
def activity_led_callback(t):
  global activity_led_state
  activity_led_pin.value(activity_led_state)
  activity_led_state = not activity_led_state

# set the activity led into pulsing mode
def pulse_activity_led(speed_hz = 1):
  global activity_led_timer, activity_led_state
  activity_led_state = True
  activity_led_timer.deinit()
  activity_led_timer.init(period=int(1000/speed_hz), mode=Timer.PERIODIC, callback=activity_led_callback)

# turn off the activity led and disable any pulsing animation that's running
def stop_activity_led():
  global activity_led_timer
  activity_led_timer.deinit()
  activity_led_pin.off()

# check whether device needs provisioning
# ===========================================================================
import time
from phew import logging
button_pin = Pin(SWITCH_STANDBY_PIN, Pin.IN, Pin.PULL_UP)
needs_provisioning = False
start = time.time()
while not button_pin.value(): # button held for 3 seconds go into provisioning
  if time.time() - start > 3:
    needs_provisioning = True
    break

try:
  import config # fails to import (missing/corrupt) go into provisioning
  if not config.provisioned: # provisioned flag not set go into provisioning
    needs_provisioning = True
except Exception as e:
  logging.error("> missing or corrupt config.py", e)
  needs_provisioning = True

if needs_provisioning:
  logging.info("> entering provisioning mode")
  import galactic_u.provisioning
  # control never returns to here, provisioning takes over completely

# all the other imports, so many shiny modules
import machine, sys, os, json
from machine import RTC, ADC
import phew
import galactic_u.helpers as helpers

# read battery voltage - we have to toggle the wifi chip select
# pin to take the reading - this is probably not ideal but doesn't
# seem to cause issues. there is no obvious way to shut down the
# wifi for a while properly to do this (wlan.disonnect() and
# wlan.active(False) both seem to mess things up big style..)
old_state = Pin(WIFI_CS_PIN).value()
Pin(WIFI_CS_PIN, Pin.OUT, value=True)
sample_count = 10
battery_voltage = 0
for i in range(0, sample_count):
  battery_voltage += (ADC(29).read_u16() * 3.3 / 65535) * 3
battery_voltage /= sample_count
battery_voltage = round(battery_voltage, 3)
Pin(WIFI_CS_PIN).value(old_state)

# jazz up that console! toot toot!
print("       ___            ___            ___          ___          ___            ___       ")
print("      /  /\          /__/\          /__/\        /  /\        /  /\          /  /\      ")
print("     /  /:/_         \  \:\         \  \:\      /  /:/       /  /::\        /  /::\     ")
print("    /  /:/ /\         \  \:\         \  \:\    /  /:/       /  /:/\:\      /  /:/\:\    ")
print("   /  /:/ /:/_    _____\__\:\    ___  \  \:\  /__/::\      /  /:/~/:/     /  /:/  \:\   ")
print("  /__/:/ /:/ /\  /__/::::::::\  /___\  \__\:\ \__\/\:\__  /__/:/ /:/___  /__/:/ \__\:\  ")
print("  \  \:\/:/ /:/  \  \:\~~~__\/  \  \:\ |  |:|    \  \:\/\ \  \:\/:::::/  \  \:\ /  /:/  ")
print("   \  \::/ /:/    \  \:\         \  \:\|  |:|     \__\::/  \  \::/~~~`    \  \:\  /:/   ")
print("    \  \:\/:/      \  \:\         \  \:\__|:|     /  /:/    \  \:\         \  \:\/:/    ")
print("     \  \::/        \  \:\         \  \::::/     /__/:/      \  \:\         \  \::/     ")
print("      \__\/          \__\/          `~~~~~`      \__\/        \__\/          \__\/      ")
print("")
print("    -  --  ---- -----=--==--===  hey galactic, let's go!  ===--==--=----- ----  --  -     ")
print("")



def connect_to_wifi():
  if phew.is_connected_to_wifi():
    logging.info(f"> already connected to wifi")
    return True

  wifi_ssid = config.wifi_ssid
  wifi_password = config.wifi_password

  logging.info(f"> connecting to wifi network '{wifi_ssid}'")
  ip = phew.connect_to_wifi(wifi_ssid, wifi_password, timeout_seconds=30)

  if not ip:
    logging.error(f"! failed to connect to wireless network {wifi_ssid}")
    return False

  logging.info("  - ip address: ", ip)

  return True

# log the error, blink the warning led, and go back to sleep
def halt(message):
  logging.error(message)
  sleep()

# returns True if we've used up 90% of the internal filesystem
def low_disk_space():
  if not phew.remote_mount: # os.statvfs doesn't exist on remote mounts
    return (os.statvfs(".")[3] / os.statvfs(".")[2]) < 0.1   
  return False

# returns True if the rtc clock has been set
def is_clock_set():
  return RTC().datetime()[0] > 2020 # year greater than 2020? we're golden!

# connect to wifi and attempt to fetch the current time from an ntp server
def sync_clock_from_ntp():
  from phew import ntp
  if not connect_to_wifi():
    return False
  timestamp = ntp.fetch()
  if not timestamp:
    return False  
  RTC().datetime(timestamp) # set the time on the rtc chip
  return True

def startup():
  # write startup banner into log file
  logging.debug("> performing startup")

  # give each board a chance to perform any startup it needs
  # ===========================================================================
  board = get_board()
  if hasattr(board, "startup"):
    board.startup()

  # also immediately turn on the LED to indicate that we're doing something
  logging.debug("  - turn on activity led")
  pulse_activity_led(0.5)

def sleep():
  logging.info("> going to sleep")

  # make sure the rtc flags are cleared before going back to sleep
  logging.debug("  - clearing and disabling timer and alarm")
 
  # disable the vsys hold, causing us to turn off
  logging.info("  - shutting down")
 
  # if we're still awake it means power is coming from the USB port in which
  # case we can't (and don't need to) sleep.
  stop_activity_led()

  # if running via mpremote/pyboard.py with a remote mount then we can't
  # reset the board so just exist
  if phew.remote_mount:
    sys.exit()

  # we'll wait here until the rtc timer triggers and then reset the board
  logging.debug("  - on usb power (so can't shutdown) halt and reset instead")
  while True:    
    time.sleep(0.25)

    if not button_pin.value(): # allow button to force reset
      break

  logging.debug("  - reset")

  # reset the board
  machine.reset()