#!/usr/bin/python

import socket
import subprocess
import shutil
import sys
import os
import urllib2
import fcntl
import struct
import json
import ConfigParser
import StringIO
from time import sleep

class WiFi():

  CONFIG_FILE = "/etc/coderbot_wifi.conf"
  HOSTAPD_CONF_FILE = "/etc/hostapd/hostapd.conf"
  adapters = ["RT5370", "RTL8188CUS", "RT3572"] 
  hostapds = {"RT5370": "hostapd.RT5370", "RTL8188CUS": "hostapd.RTL8188"}
  web_url = "http://coderbotsrv.appspot.com/register_ip"
  wifi_client_conf_file = "/etc/wpa_supplicant/wpa_supplicant.conf"
  _config = {}

  @classmethod
  def load_config(cls):
    f = open(cls.CONFIG_FILE)
    cls._config = json.load(f)
    return cls._config

  @classmethod
  def save_config(cls):
    f = open(cls.CONFIG_FILE, 'w')
    json.dump(cls._config, f)
    return cls._config

  @classmethod
  def get_config(cls):
    return cls._config

  @classmethod
  def get_adapter_type(cls):
    lsusb_out = subprocess.check_output("lsusb")
    for a in cls.adapters:
      if a in lsusb_out:
        return a
    return None
    
  @classmethod
  def start_hostapd(cls):
    try:
      print "starting hostapd..."
      os.system("sudo service hostapd restart")
    except subprocess.CalledProcessError as e:
      print e.output

  @classmethod
  def stop_hostapd(cls):
    try:
      os.system("sudo service hostapd stop")
    except subprocess.CalledProcessError as e:
      print e.output

  @classmethod
  def set_hostapd_params(cls, wssid, wpsk):
    config = ConfigParser.ConfigParser()
    # configparser requires sections like '[section]'
    # open hostapd.conf with dummy section '[hostapd]'
    try:
      with open(cls.HOSTAPD_CONF_FILE) as f:
        conf_str = '[hostapd]\n' + f.read()
        conf_fp = StringIO.StringIO(conf_str)
        config.readfp(conf_fp)
    except IOError as e:
      print e
      return
    
    if len(str(wpsk)) < 8:
      wpsk='coderbot'
    
    config.set('hostapd','ssid',str(wssid))
    config.set('hostapd','wpa_passphrase',str(wpsk))

    try:
      with open(cls.HOSTAPD_CONF_FILE, 'wb') as f:
        conf_items = config.items('hostapd')
        for (key,value) in conf_items:
          f.write("{0}={1}\n".format(key, value))
        f.write("\n")
    except IOError as e:
      print e

  @classmethod
  def get_ipaddr(cls, ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])
    ipaddr = socket.gethostbyname(socket.gethostname())
    return ipaddr

  @classmethod
  def register_ipaddr(cls, ipaddr, botname):
    try:
      ret = urllib2.urlopen(cls.web_url + "?name=" + botname + "&ipaddr=" + ipaddr)
      print str(ret.getcode())
      if ret.getcode() != 200:
        raise Exception()
    except URLError as e:
      print e
      raise
    print botname, ": ", ipaddr

  @classmethod
  def start_service(cls):
    config = cls.load_config()
    if config["wifi_mode"] == "ap":
      print "starting as ap..."
      cls.start_as_ap()
    elif config["wifi_mode"] == "client":
      print "starting as client..."
      try:
        cls.start_as_client()
      except:
        print "Unable to register ip, revert to ap mode"
        cls.start_as_ap()
    elif config["wifi_mode"] == "local_client":
      print "starting as local client..."
      try:
        cls.start_as_local_client()
      except:
        print "Unable to connect to WLAN, rever to ap mode"
        cls.start_as_ap()

def main():
  w = WiFi()

  print 'Testing Client Connection...'
  print 'Wait 3 seconds before checking connection to router...'
  sleep(3)
  print 'pinging router...'
  #ping hub router
  response = os.system('ping -c 1 192.168.0.1')
  #healthy response is 0

  if response == 0:
    print 'Router has been found, staying on client mode'
  else:
    print 'Router not found, switching to AP mode'
    #setup hotspot
    shutil.copy("/etc/network/interfaces_ap", "/etc/network/interfaces")
    print 'restart networking...'
    os.system('sudo service networking restart')
    w.start_hostapd()
    print 'Waiting for hostapd to startup'
    sleep(3)
    print 'copying client interfaces back for next time'
    shutil.copy("/etc/network/interfaces_cli", "/etc/network/interfaces")
  
  if len(sys.argv) > 2 and sys.argv[1] == "updatecfg":
    if len(sys.argv) > 2 and sys.argv[2] == "ap":
      if len(sys.argv) > 3:
        w.set_hostapd_params(sys.argv[3], sys.argv[4])
      #w.set_start_as_ap()
      #w.start_as_ap()
    elif len(sys.argv) > 2 and sys.argv[2] == "hub":
      if len(sys.argv) > 3:
        w.set_client_params(sys.argv[3], sys.argv[4])
      #w.set_start_as_client()
      #w.stop_hostapd()
      #try:
      #  w.start_as_client()
      #except:
      #  print "Unable to register ip, revert to ap mode"
      #  w.start_as_ap()
    elif len(sys.argv) > 2 and sys.argv[2] == "local_client":
      if len(sys.argv) > 3:
        w.set_client_params(sys.argv[3], sys.argv[4])
      w.set_start_as_client()
      try:
        w.start_as_local_client()
      except:
        print "Unable to connect to WLAN, revert to ap mode"
        w.start_as_ap()
      
  #else:
  #  w.start_service()

if __name__ == "__main__":
  main()

