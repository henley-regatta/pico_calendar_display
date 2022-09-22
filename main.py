import utime
import machine
import cal_display
led = machine.Pin("LED", machine.Pin.OUT)

import network
ssid = 'NOTAREALNETWORKSSID'
sspass = 'MySuperSecretNetworkSSIDPassword'

#URL for the Calendar details to be retrived:
calendar_url="http://docker1.local:24611/json?week"

#Refresh rate for the display, in minutes.
#NOTE: synchronise this with the calendar data refresh
#      interval for best results; probably no need to go
#      below 10-15 minutes under most circumstances....
refresh_interval_minutes = 30

#Refresh rate for the display, in minutes.
#NOTE: synchronise this with the calendar data refresh
#      interval for best results; probably no need to go
#      below 10-15 minutes under most circumstances....
refresh_interval_minutes = 30

########################################
def wait_for_wifi():
    global wlan
    max_wait = 10
    while max_wait > 0:
        cal_display.blinkLED(1,100)
        s=wlan.status()
        if s < 0 or s >= 3:
            break
        max_wait -= 1
        utime.sleep_ms(1000)
    return s

########################################
########################################
########################################
# This is important in giving a
# window of control - once we get to
# system.lightsleep() we lose control of
# REPL - this isn't just diagnostics it's
# an opportunity to break out
cal_display.blinkLED(10,250)
cal_display.errDumpText(f"Refresh every {refresh_interval_minutes} minutes for {calendar_url} connecting to {ssid}")
########################################
# Main program loop:
while True :
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid,sspass)
    while (wait_for_wifi() != 3) :
        utime.sleep_ms(1000)
        wlan.connect(ssid,sspass)
    
    #Indicator of connection established:
    cal_display.blinkLED(2,1000)
  
    # PAYLOAD GOES HERE
    #Retrieve and display the Calendar details
    cal_display.getAndDisplayCalendar(calendar_url)
    
    #Indicator of display complete:
    cal_display.blinkLED(10,100)
    
    wlan.disconnect()
    wlan.active(False)
    #https://github.com/orgs/micropython/discussions/9135
    #vital for actually turning wifi off:
    wlan.deinit()
    wlan = None
    cal_display.blinkLED(1,10) ##effectively an "off"
    #note that the ePaper needs to be "disconnected" before
    #sleep to prevent a dim screen (pin going high?).
    #check ePaper code not only does epd.Sleep() but also
    #epd.reset()/epd.module_exit() before we get to this
    #point:
    machine.idle() 
    machine.lightsleep(refresh_interval_minutes * 60000)
   
    