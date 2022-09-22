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

########################################
def wait_for_wifi():
    global wlan
    max_wait = 10
    while max_wait > 0:
        led.toggle()
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
# window of control; the first lightsleep
# issued will make STOP/RESTART impossible
# so a "breather" here gives time for that to
# happen. Programmed as a 10-second blinkenfest:
for x in range(40) :
    led.toggle()
    utime.sleep_ms(250)
########################################
# Main program loop:
while True :
    led.on()
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid,sspass)
    while (wait_for_wifi() != 3) :
        utime.sleep_ms(1000)
        wlan.connect(ssid,sspass)
    led.on()
    
    # PAYLOAD GOES HERE
    #blink the LED a bit to show activity
    for x in range(20) :
        led.toggle()
        utime.sleep_ms(125)
    #Retrieve and display the Calendar details
    cal_display.getAndDisplayCalendar(calendar_url)        
        
    wlan.disconnect()
    wlan.active(False)
    #https://github.com/orgs/micropython/discussions/9135
    #vital for actually turning wifi off:
    wlan.deinit()
    wlan = None
    led.off()
    #note that the ePaper needs to be "disconnected" before
    #sleep to prevent a dim screen (pin going high?).
    #check ePaper code not only does epd.Sleep() but also
    #epd.reset()/epd.module_exit() before we get to this
    #point:
    machine.idle() 
    machine.lightsleep(refresh_interval_minutes * 60000)
   
    