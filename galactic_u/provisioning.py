import network, os, json, time, machine, sys

import galactic_u.helpers as helpers
import galactic_u
from phew import logging, server, redirect, serve_file, render_template, access_point
from galactic import GalacticUnicorn
from picographics import PicoGraphics, DISPLAY_GALACTIC_UNICORN as DISPLAY

gu = GalacticUnicorn()
graphics = PicoGraphics(DISPLAY)

FOREGROUND = (230, 210, 250)
BACKGROUND = (20, 20, 120)


def draw_text(text, fg, bg, x, y):
  fg_pen = graphics.create_pen(fg[0], fg[1], fg[2])
  bg_pen = graphics.create_pen(bg[0], bg[1], bg[2])

  graphics.set_pen(bg_pen)
  graphics.clear()

  graphics.set_pen(fg_pen)
  graphics.text(text, x, y, wordwrap=100, scale=1)

  gu.update(graphics)


DOMAIN = "pico.wireless"

# create fresh config file if missing
if not helpers.file_exists("config.py"):
  helpers.copy_file("galactic_u/config_template.py", "config.py")

# write the current values in config to the config.py file
def write_config():
  lines = []
  with open("config.py", "r") as infile:
    lines = infile.read().split("\n")

  for i in range(0, len(lines)):
    line = lines[i]
    parts = line.split("=", 1)
    if len(parts) == 2:
      key = parts[0].strip()
      if hasattr(config, key):
        value = getattr(config, key)
        lines[i] = f"{key} = {repr(value)}"

  with open("config.py", "w") as outfile:
    outfile.write("\n".join(lines))

import config


# detect which board type we are provisioning
model = galactic_u.model
logging.info("> auto detecting board type")
logging.info("  -", model)


# put board into access point mode
logging.info("> going into access point mode")
ap_name = f"galactic_u {model[:1].upper()}{model[1:]} Setup"
ap = access_point(ap_name)
logging.info("  -", ap.ifconfig()[0])

draw_text(ap_name, FOREGROUND, BACKGROUND, 0, -1)


# dns server to catch all dns requests
logging.info("> starting dns server...")
from phew import dns
dns.run_catchall(ap.ifconfig()[0])

logging.info("> creating web server...")


@server.route("/wrong-host-redirect", methods=["GET"])
def wrong_host_redirect(request):
  # if the client requested a resource at the wrong host then present 
  # a meta redirect so that the captive portal browser can be sent to the correct location
  body = f"<!DOCTYPE html><head><meta http-equiv=\"refresh\" content=\"0;URL='http://{DOMAIN}/provision-welcome'\" /></head>"
  return body


@server.route("/provision-welcome", methods=["GET"])
def provision_welcome(request):
  draw_text("Welcome!", FOREGROUND, BACKGROUND, 0, -1)
  response = render_template("galactic_u/html/welcome.html", board=model)
  return response


@server.route("/provision-step-1-nickname", methods=["GET", "POST"])
def provision_step_1_nickname(request):
  if request.method == "POST":
    config.nickname = request.form["nickname"]
    write_config()
    return redirect(f"http://{DOMAIN}/provision-step-2-wifi")
  else:
    draw_text("Step 1: Nickname", FOREGROUND, BACKGROUND, 0, -1)
    return render_template("galactic_u/html/provision-step-1-nickname.html", board=model)


@server.route("/provision-step-2-wifi", methods=["GET", "POST"])
def provision_step_2_wifi(request):
  if request.method == "POST":
    config.wifi_ssid = request.form["wifi_ssid"]
    config.wifi_password = request.form["wifi_password"]
    write_config()
    return redirect(f"http://{DOMAIN}/provision-step-5-done")
  else:
    draw_text("Step 2: WiFi", FOREGROUND, BACKGROUND, 0, -1)
    return render_template("galactic_u/html/provision-step-2-wifi.html", board=model)
  

@server.route("/provision-step-5-done", methods=["GET", "POST"])
def provision_step_5_done(request):
  config.provisioned = True
  write_config()

  # a post request to the done handler means we're finished and
  # should reset the board
  if request.method == "POST":
    machine.reset()
    return

  draw_text("Step 5: Done", FOREGROUND, BACKGROUND, 0, -1)
  return render_template("galactic_u/html/provision-step-5-done.html", board=model)
    

@server.route("/networks.json")
def networks(request):
  networks = []
  for network in ap.scan():
    network = network[0].decode("ascii").strip()
    if network != "":
      networks.append(network)
  networks = list(set(networks)) # remove duplicates
  return json.dumps(networks), 200, "application/json"


@server.catchall()
def catchall(request):
  # requested domain was wrong
  if request.headers.get("host") != DOMAIN:
    return redirect(f"http://{DOMAIN}/wrong-host-redirect")

  # check if requested file exists
  file = f"galactic_u/html{request.path}"
  if helpers.file_exists(file):
    return serve_file(file)

  return "404 Not Found Buddy!", 404
  

# wait for a client to connect
logging.info("> waiting for a client to connect")
galactic_u.pulse_activity_led(5)
while len(ap.status("stations")) == 0:
  time.sleep(0.01)
logging.info("  - client connected!", ap.status("stations")[0])

logging.info("> running provisioning application...")
server.run(host="0.0.0.0", port=80)