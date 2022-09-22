import WaveShareEpaper42
import time
import urequests
import json

defaultCalendarURL="http://docker1.local:24611/json?week"

#This is our assumption of fixed-width font pixel size
CHARWIDTH=8
CHARHEIGHT=8

#Setup globals:
MAXWIDTH=WaveShareEpaper42.EPD_WIDTH
MAXHEIGHT=WaveShareEpaper42.EPD_HEIGHT
#Setup some parameters for formatting output size
#Hdr runs down 0 -> HDRHEIGHT
HDRHEIGHT = CHARHEIGHT*3+1
#Footer runs FTRHEIGHT->WaveShareEPaper42.EPD_HEIGHT
FTRHEIGHT = (CHARHEIGHT+4)
#And this is a lot simpler because it's just the screen cut in two
COLWIDTH=int(MAXWIDTH/2)
COLHEIGHT=MAXHEIGHT-(HDRHEIGHT+FTRHEIGHT)

#Available "drawing area" per column of text:
c1TextWidthOffset = CHARWIDTH
c2TextWidthOffset = COLWIDTH + CHARWIDTH
colTextHeightOffset = HDRHEIGHT + CHARHEIGHT*2+int(CHARHEIGHT/2)

c1Box=[[c1TextWidthOffset,colTextHeightOffset],[COLWIDTH-CHARWIDTH,MAXHEIGHT-(FTRHEIGHT+CHARHEIGHT)]]
c2Box=[[c2TextWidthOffset,colTextHeightOffset],[MAXWIDTH-CHARWIDTH,MAXHEIGHT-(FTRHEIGHT+CHARHEIGHT)]]

colRowsAvail = int((c1Box[1][1]-c1Box[0][1])/CHARHEIGHT)
colColsAvail = int((c1Box[1][0]-c1Box[0][0])/CHARWIDTH) - 2

###########################################################
def getCalendar(calendarURL) :
    try: 
        r = urequests.get(calendarURL)
        if r.status_code >= 200 and r.status_code < 300 :
            #calData = r.content
            #r.close()
            buff=json.loads(r.content)
            r.close() #bad things happen if you don't close the request
            return(buff)
        else :
            rc=r.status_code
            r.close()
            raise IOError(f'GET of (private) URL failed with response code = {rc}')
        #If we got here, we failed. Own it.
        raise IOError(f'Unknown error retrieving {calendarURL}')
    except Exception as err:
        errType = type(err).__name__
        errDumpText(f"Exception retrieving {calendarURL} : {errType}\n{err}")
        import machine
        machine.reset()


###########################################################
def errDumpText(texttodump) :
    epd=WaveShareEpaper42.EPD_4in2()
    #Don't quite understand why but if these two aren't defined
    #we get a black background. Which is ugly
    epd.image1Gray.fill(0xff)
    epd.image4Gray.fill(0xff)
    
    maxCharsPerLine=int(MAXWIDTH/CHARWIDTH)-2*CHARWIDTH
    errLines=list(texttodump[0+i:maxCharsPerLine+i] for i in range(0,len(texttodump),maxCharsPerLine))
    tHeight=int(MAXHEIGHT/2)-len(errLines)*CHARHEIGHT+2
    
    for errLine in errLines :
        epd.image4Gray.text(errLine,centreText(errLine,MAXWIDTH),tHeight,epd.black)
        tHeight += CHARHEIGHT+2
    epd.EPD_4IN2_4GrayDisplay(epd.buffer_4Gray)
    epd.Sleep()
    epd.reset()
    epd.module_exit()

###########################################################
def centreText(txt,maxWidth) :
    tLen = len(txt) * CHARWIDTH
    border = maxWidth - tLen
    if border <= 0 :
        return 0
    else :
        return int(border / 2)

###########################################################
def rightAlign(txt,maxWidth) :
    tLen = (len(txt) * CHARWIDTH) + CHARWIDTH
    spare = maxWidth - tLen
    if spare <= 0 :
        return 0
    else :
        return spare
    
###########################################################
def outputHeadersAndBorders(epd, hdr, lftr, rftr) :
    #Draw boxes to delimit our drawing area
    #NOTE: Boxes are given as (startpoint),(widthxheight)
    #full bounding box
    epd.image4Gray.rect(0, 0, MAXWIDTH,MAXHEIGHT, epd.black)
    #hdr box
    epd.image4Gray.fill_rect(0,0, MAXWIDTH,HDRHEIGHT, epd.grayish)
    #ftr box
    epd.image4Gray.fill_rect(0,MAXHEIGHT-FTRHEIGHT,MAXWIDTH,FTRHEIGHT,epd.grayish)
    #Column Boxes
    epd.image4Gray.rect(0,HDRHEIGHT,COLWIDTH,COLHEIGHT,epd.darkgray)
    epd.image4Gray.rect(COLWIDTH,HDRHEIGHT,COLWIDTH,COLHEIGHT,epd.darkgray)
    
    #page header
    hLen=len(hdr)*CHARWIDTH
    hStart=centreText(hdr,MAXWIDTH)
    epd.image4Gray.text(hdr,hStart,HDRHEIGHT-CHARHEIGHT*2,epd.black)
    epd.image4Gray.hline(hStart,HDRHEIGHT-CHARHEIGHT,hLen,epd.black)
    #column headers
    c1hdr="Today"
    epd.image4Gray.text(c1hdr,centreText(c1hdr,COLWIDTH),HDRHEIGHT+CHARHEIGHT,epd.black)
    c2hdr="Further Ahead"
    epd.image4Gray.text(c2hdr,centreText(c2hdr,COLWIDTH)+COLWIDTH,HDRHEIGHT+CHARHEIGHT,epd.black)
    #footer
    epd.image4Gray.text(lftr,CHARWIDTH,MAXHEIGHT-(FTRHEIGHT-2),epd.black)
    fStart = rightAlign(rftr,MAXWIDTH)   
    epd.image4Gray.text(rftr,fStart,MAXHEIGHT-(FTRHEIGHT-2),epd.black)


###########################################################
def groupEventsByDay(cals,nowts) :
    today=str(time.localtime(nowts)[2])
    evGroup=[ {}, {} ]
    for cal in cals :
        for ev in cals[cal] :
            if (ev['date'] == today) and ((ev['durSecs'] == 0) or (ev['startts']+ev['durSecs'] >= nowts)):
                if cal not in evGroup[0] :
                    evGroup[0][cal] = [ev]
                else :
                    evGroup[0][cal].append(ev)
            else :
                if cal not in evGroup[1] :
                    evGroup[1][cal] = [ev]
                else :
                    evGroup[1][cal].append(ev)
    #Events in each evGroup Cal should be sorted by startts so earlier events come first
    for d in range(len(evGroup)) :
        for c in evGroup[d] :
             evGroup[d][c] = sorted(evGroup[d][c], key = lambda e: e['startts'])
                            
    return evGroup

###########################################################
def trimEventsForSpace(events,rows) :
    #Some Heuristics required here to make the output "fair":
    # 1) Each calendar should have AT LEAST one event
    # 2) Each event should have a MINIMUM of two lines
    # 3) Events occuring NOW are higher priority than those occuring LATER
    cals = len(events)
    #take off a header-line per CAL, then give each event 2 lines:
    evsPossible = int(rows / 2) - cals
    evsInList=0
    for cal in events :
        for ev in events[cal] :
            evsInList += 1
    if evsInList > evsPossible :
        fairShare = int(evsPossible / len(events))
        remainingSpace = evsPossible%len(events)
        for cal in events :
            if len(events[cal]) > fairShare :
                eventsAllocated = fairShare
                if remainingSpace > 0 :
                    eventsAllocated += 1
                    remainingSpace -= 1
                events[cal] = events[cal][:eventsAllocated]
        
    return events

###########################################################
def outputColumn(epd,events,box,today) :
  #reset the offset ptrs:
    lPos= box[0][0]
    rOffset= box[0][1]
    maxTextWidth = int((box[1][0]-box[0][0])/CHARWIDTH) - 1 #because we offset event entries by 1 char
    for cal in events :
        #calendar header
        calName = cal[:colColsAvail]
        epd.image4Gray.text(calName,lPos,rOffset,epd.black)
        rOffset += CHARHEIGHT + 1
        epd.image4Gray.hline(lPos,rOffset,len(calName)*CHARWIDTH,epd.darkgray)
        rOffset += 2
        for ev in events[cal] :
            lStart = lPos + CHARWIDTH
            if ev['durSecs'] == 0 :
                #all-day events. Draw as WHITE on BLACK background
                if today :
                    evTitle = ev['title']
                else :
                    evTitle = " ".join([ev['date'],ev['title']])
                if len(evTitle) > maxTextWidth :
                    #two-line output
                    epd.image4Gray.fill_rect(lStart,rOffset,maxTextWidth*CHARWIDTH,2*(CHARHEIGHT+2),epd.black)
                    epd.image4Gray.text(evTitle[:maxTextWidth],lStart,rOffset+1,epd.white)
                    epd.image4Gray.text(evTitle[maxTextWidth:maxTextWidth*2],lStart,rOffset+CHARHEIGHT+2,epd.white)
                    rOffset += 2*(CHARHEIGHT+2)+2
                else :
                    #one-line output
                    epd.image4Gray.fill_rect(lStart,rOffset,len(evTitle)*CHARWIDTH,(CHARHEIGHT+2),epd.black)
                    epd.image4Gray.text(evTitle,lStart,rOffset+1,epd.white)
                    rOffset += CHARHEIGHT+4
            else :
                #Timed event. Show as 2 lines, first line being start/end times:
                if today :
                    epd.image4Gray.text((f"{ev['start']} - {ev['end']}"),lStart,rOffset+1,epd.black)
                else :
                    epd.image4Gray.text((f"{ev['date']} {ev['start']}"),lStart,rOffset+1,epd.black)
                rOffset+=CHARHEIGHT+2
                epd.image4Gray.text(ev['title'][:maxTextWidth],lStart,rOffset+1,epd.black)
                rOffset+=CHARHEIGHT+4

###########################################################
def displayCalendar(calData) :
    epd=WaveShareEpaper42.EPD_4in2()
    #Don't quite understand why but if these two aren't defined
    #we get a black background. Which is ugly
    epd.image1Gray.fill(0xff)
    epd.image4Gray.fill(0xff)
    
    #Group calendar events by DAY (and trim for size):
    evByDay=groupEventsByDay(calData['cals'],calData['ts'])
    evByDay[0]=trimEventsForSpace(evByDay[0],colRowsAvail)
    evByDay[1]=trimEventsForSpace(evByDay[1],colRowsAvail)
   
    #Page and Column header definitions
    header = " ".join([calData['day'],calData['dom'],calData['month']])
    left_footer = (f"Data as of: {calData['cachetime']}")
    right_footer = (f"Updated at: {calData['time']}")
    outputHeadersAndBorders(epd, header, left_footer, right_footer) 

    #TODAY column output
    outputColumn(epd,evByDay[0],c1Box,True)
    #FURTHER AHEAD column output
    outputColumn(epd,evByDay[1],c2Box,False)
    
    #PRINT THE BUFFER
    epd.EPD_4IN2_4GrayDisplay(epd.buffer_4Gray)
    epd.Sleep()
    
    #If proposing to system.lightsleep(), epd.Sleep() isn't enough
    #one needs some more drastic disconnect:
    epd.reset()
    epd.module_exit()

###########################################################
def getAndDisplayCalendar(calURL=defaultCalendarURL) :
    calData=getCalendar(calURL)
    displayCalendar(calData)                
                
###########################################################
###########################################################
if __name__ == "__main__" :
    getAndDisplayCalendar()