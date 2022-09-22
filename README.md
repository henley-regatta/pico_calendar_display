# pico_calendar_display

Python project to display Calendar data on a Raspberry Pi Pico W with an
e-Paper display

A Companion project to
[icscalserv](https://github.com/henley-regatta/icscalserv) (and, in fact,
the reason that project was created...).

## Resources Required

This is a project using MicroPython on the Pi Pico W. It was built with
the following resources:

  * [Raspberry Pi Pico W (2022; FCC ID 2ABCB-PicoW)](https://www.raspberrypi.com/news/raspberry-pi-pico-w-your-6-iot-platform/)
  * [WaveShare 4.2inch e-Paper Module (400x300) Rev 2.1](https://www.waveshare.com/4.2inch-e-paper-module.htm)
  * [MicroPython Build for PiPico W rp2-pico-w-20220919-unstable-v1.19.1-428-gb41aaaa8a.uf2](https://micropython.org/resources/firmware/rp2-pico-w-20220919-unstable-v1.19.1-428-gb41aaaa8a.uf2)

(note that any _recent_ MicroPython build for PiPico W - certainly
anything v1.19.1 or above issued after 20220630, which was when
`machine.lightsleep()` functionality was added- ought to work.)

## Installation

  1. Setup your [icscalserv](https://github.com/henley-regatta/icscalserv) instance and take a note of it's data URL
  1. `git clone https://github.com/henley-regatta/pico_calendar_display.git` to get a local copy of this repository
  1. [Wire up ePaper display to Pi Pico W](https://www.guided-naafi.org//howto/2022/09/16/Wiring_ePaperToRasPiPicoW.html) - reference since I had some fun with pinouts etc
  1. Load the MicroPython build onto the PiPico W
  1. Edit **main.py** to change:
      * `ssid` to the value of the wireless network to connect to
      * `sspass` to the WPA wireless password value
      * `calendar_url` to the URL of the calendar server you'll pull data from
      * `refresh_interval_minutes` to either the calendar server refresh interval or some multiple thereof
  1. Use [Thonny](https://thonny.org/) or [rshell](https://github.com/dhylands/rshell) to copy the python files to the Pico's internal storage
      * Do not rename the existing files or, if you do, be prepared to update the cross-references
  1. Since `main.py` is automatically called on boot, reset/restart the pico (e.g. `machine.reset()` in the REPL, or just unplug/replug it...)

## Does it work and what does it look like?
Yes. Yes it does. It looks like this:
![Example of code running on bench showing current calendar data](/example_output.jpg)

## Getting Control back of your Pi Pico W

I've found that once `machine.lightsleep()` has been called, whether it's
actually sleeping or not, it's impossible to wrestle back control of the
MicroPython environment by getting back to the REPL - Ctrl-F2 (STOP) in
Thonny just errors-out. Once this happens it's unplug the Pico and replug
it in again.

This is why there's a 10-second LED blinker at the start of the `main.py`
execution; that's enough time (if Thonny is already launched!) to let you
STOP and get back to the REPL to make changes if you need to.

## Memory Management

As I was ready to push this out and declare "Done" I found it was crashing
when booted from scratch. After doing some tracing I found that it was
dying out-of-memory when retrieving the calendar. And with some judicious
use of `gc.mem_free()` it became obvious that it's all used in allocating
the `gpd` object that controls the e-Paper. There's some wierdness in that
library in that it allocates both a 1-bit-per-pixel array (`Image1Gray`)
and a 2-bit-per-pixel / 4 colour array (`Image4Gray`), but then _never
uses the 1-bit ImageBuffer_. That's 15K of memory (out of about 150K, 10%)
apparently wasted. So I've commented it out; _apparently_ without ill
effect but days are early.

This does highlight one of the major limitations of this hardware solution
though - memory size is critical. The ability of this particular hardware
combination to "scale" - either to larger calendar sizes, or even to
larger display sizes (bigger Frame Buffers) is limited. I suspect at some
point I'm going to need to ditch the Python environment and start on C
development to have greater control over memory consumption.

As a legacy of all this tracing/debugging, there's still a bunch of manual
`gc.collect()` statements strewn around the code base. These are
_probably_ unnecessary but at this point I'm not willing to risk it by
removing them...

Also, the free heap size is in the footer where no doubt it'll confuse
someone reading the screen...

## Low-power / Sleep modes on the Pi Pico w with an ePaper display attached

Probably the biggest headache in all of this was getting the Pico W to do
a low-powered sleep whilst still refreshing the display. The code in
`main.py` was very much arrived at as a trial-and-error way of getting
there. An embedded installation would _probably_ want to get rid of the
`led.toggle()` / `led.on()` calls but I found them useful for debugging,
especially as any _other_ sorts of output - like `print()` - interferes
with the sleep processes used.

The Network connect/sleep code probably isn't as robust as it could be but
it does appear to work OK in testing over periods of multiple hours.
Again, the specific init and (more importantly) de-init code used was
found to be necessary in order to get successful low-power sleep via
`system.lightsleep()`. By all accounts the call to `wlan.deinit()`
shouldn't be necessary if `wlan.active(False)` has been called, but ([per
discussions](https://github.com/orgs/micropython/discussions/9135)) it is.
Similarly, the deconstruction of `wlan=None` is prophylactic against
memory leaks given the re-initialisation done at the start of the loop.

The ePaper display's specs warn of all sorts of dire consequences of
leaving the display in a hi-power state, and strongly recommend calling
`epd.Sleep()` after every refresh. Except that when a lower-power mode is
active, _something_ causes the epaper to dim after a minute or so (the
whole screen looks like it's been written in `epd.grayish` no matter what
values were used) if this method alone is used. I found it necessary to
augment the call to `epd.Sleep()` with additional de-initialising calls to
`epd.reset()` and `epd.module_exit()` at the end of each loop to avoid
this. Frankly this is voodoo programming; one of those calls might be
enough but since both of them have the desired effect and (so far) seem to
avoid memory leaks I've left 'em both in.


In many ways it's a shame `system.deepsleep()` isn't (yet?) implemented
properly on PiPico as that would have a much more beneficial effort from a
"code cleanliness" perspective; awakening from deepsleep() is _exactly_
like doing a timed `machine.reset()` which would clear memory and state
and all sorts (one way to eliminate possible memory leaks...). I fear the
ePaper may still need it's special handling to avoid damage / fading
though.

## A note on the WavePaper library

I had to adapt the WavePaper library because as shipped it issues a bunch
of `print()` statements on busy/release. It's a known problem that print
interferes with any attempt to do a low-power mode (`machine.lightsleep()`
being used by this project) so I stripped them out.

I'm fairly sure I'm allowed to do this - the licence permits modifications
and I've retained the original copyright notice.

The original repository for the examples is at:
  * [waveshare/Pico_ePaper_Code](https://github.com/waveshare/Pico_ePaper_Code)

You will wish to note that I've used the library that's specific to my
actual display - the 4.2" 400x300 board with embedded controller, embodied
in the source file `Pico-ePaper-4.2py`. I believe from a casual inspection
that using _any_ of the available demo files as a source should be a
fairly simple drop-in replacement as they all follow the same general
pattern, although you'll want to change the display code to take advantage
e.g. of more colours available.

If I was going to do this myself, I'd use the following approach:

  1. Find the library from the samples provided that matched my display
  1. Copy it to a local version (e.g. "`WaveShareEpaper75.py`")
  1. Go through that library and comment out all `print()` statements
  1. Edit the main `cal_display.py` file in this repository and change references from `WaveShareEpaper42` to `WaveShareEpaper75`

The actual display code in `cal_display.py` _ought_ to be agnostic to
changes in resolution, scaling appropriately, but of course I've had
little chance to verify that...