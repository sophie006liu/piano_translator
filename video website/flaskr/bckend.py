from logging import raiseExceptions
import os
import cv2
import math

# Creates [left, right] bounds for 88 keys by iterating through pixels in keyRow
# keyThreshold - Intensity of pixel to differentiate between black/white, default 75
# keyLength - Minimum width required for key, default 3
def CreateKeyGroups(row, width, keyThreshold, keyLength):
    dark = True # True if last pixel was black
    keyGroups = [[0]] # Bounds for keys
    for i in range(len(row)):
        # Row changes from light to dark or dark to light
        if (dark and row[i]>=keyThreshold) or (not dark and row[i]<keyThreshold):
            if (i-keyGroups[-1][0]<keyLength):
                keyGroups.pop()
            else:
                keyGroups[-1].append(i-1)
            keyGroups.append([i])
            dark = not dark
    if(width-keyGroups[-1][0]<keyLength):
        keyGroups.pop()
    else:
        keyGroups[-1].append(width)
    return keyGroups

# Detects which keys are pressed in noteRow, returns boolean array of 88
# noteBuffer - Deciding horizontal range of solid pixels within key length that is needed to be counted as pressed, default 1
# noteYRange - Deciding vertical range of solid pixels within key length that is needed to be counted as pressed, default 5
# noteThreshold - Intensity of pixel to differentiate between black/white, default 70
def GetNotes(frame,noteRow, keyGroups, noteBuffer, noteYRange, noteThreshold):
    noteArray = ["end"] * 88 # Tracks whether key is active on current frame

    # Sets value of noteArray
    for keyGroupNum in range(len(keyGroups)):
        noteContinue=True
        noteStart=True
        for j in range(keyGroups[keyGroupNum][0]+noteBuffer,keyGroups[keyGroupNum][1]+1-noteBuffer):
            if frame[noteRow][j]<noteThreshold:
                noteStart = False
        for i in range(noteRow+1,noteRow+1+noteYRange):
            for j in range(keyGroups[keyGroupNum][0]+noteBuffer,keyGroups[keyGroupNum][1]+1-noteBuffer):
                if frame[i][j]<noteThreshold:
                    noteContinue = False
        if noteContinue:
            noteArray[keyGroupNum]="continue"
        elif noteStart:
            noteArray[keyGroupNum]="start"
    
    return noteArray

# Updates noteList (list of notes) with noteArray (which keys are currently pressed)
# Also takes noteActive (which keys were pressed in last frame) and timestamp
def UpdateNotes(noteList, noteArray, noteActive, timestamp):
    # Cycle through noteArrray and update entries of noteList and noteActive
    for i in range(88):
        if (noteArray[i]=="start" or noteArray[i]=="continue") and noteActive[i]==-1: # Start of note
            noteActive[i]=timestamp
        elif noteArray[i]=="start" and noteActive[i]!=-1: # Start new note without first note ending
            noteList.append([i,noteActive[i],timestamp])
            noteActive[i]=timestamp
        elif noteArray[i]=="continue" and noteActive[i]!=-1: # Continuation of note
            pass
        elif noteArray[i]=="end" and noteActive[i]==-1: # Do nothing
            pass
        elif noteArray[i]=="end" and noteActive[i]!=-1: # End of note
            noteList.append([i,noteActive[i],timestamp])
            noteActive[i]=-1
        else:
            Exception("noteArray, noteActive combo not found")

def DrawKeyGroups(frame,keyGroups,height,keyThreshold,row):
    counter = 0
    for pair in keyGroups:
        counter += 1
        if (counter%2==0):
            color = (255,0,0)
        else:
            color = (0,255,0)
        cv2.rectangle(frame,(pair[0], height-40),(pair[1],height),color,-1)
    cv2.imwrite("Frames/KeyGroups "+str(round(row,2))+" "+str(keyThreshold)+"Drawn.png", frame)

# Draws images of frames being read
def DrawReader(frame,noteArray,keyGroups,noteRow,height,timestamp):
    counter = 0
    for pair in keyGroups:
        counter += 1
        if (counter%2==0):
            color = (255,0,0)
        else:
            color = (0,255,0)
        cv2.rectangle(frame,(pair[0], height-40),(pair[1],height),color,-1)

    for i in range(len(keyGroups)):
        if noteArray[i]=="start":
            color = (255,255,0)
        elif noteArray[i]=="continue":
            color = (0,255,0)
        else:
            color = (255,0,0)
        cv2.rectangle(frame,(keyGroups[i][0],noteRow),(keyGroups[i][1],noteRow+10),color,-1)
    cv2.imwrite("Frames/"+str(round(timestamp,2))+" Drawn.png", frame)

# Counts length of notes, finds most common length, calcs tempo and tempoLength
def CalcNoteLength(noteList):
    # Counts length of notes
    noteLengths={}
    for note in noteList:
        noteLength = round(note[2]-note[1],0)
        if noteLength not in noteLengths:
            noteLengths[noteLength]=0
        noteLengths[noteLength]+=1

    # Finds most common length
    noteLengthsList = list(noteLengths.items())
    noteLengthsList.sort(key = lambda x:x[1],reverse=True)
    print(noteLengthsList)
    tempoLength = noteLengthsList[0][0]
    tempoBPM = 60000/tempoLength
    while (tempoBPM<100 or tempoBPM>199):
        if tempoBPM<100:
            tempoBPM *= 2
        else:
            tempoBPM /= 2
        tempoLength = 60000/tempoBPM
    print("TEMPO LENGT"+str(tempoLength)) 
    print("TEMPO BPM"+str(tempoBPM))
    return (tempoBPM, tempoLength)

# Takes (noteIndex, startTime, endTime) array
# Converts to (noteIndex, starting beat number, beat duration) in terms of quarter notes
def NoteTranslation(noteList, tempoLength, startFrame):
    beatList = []

    baseLength = tempoLength/4 # Length of signle beat, turned to length of sixteenth note

    for i in range(len(noteList)):
        # Translate note name
        # noteName = sharpNames[noteList[i][0]%12]

        # Round note start to 16th note
        noteStart = noteList[i][1] - startFrame
        noteStartRounded = round(noteStart / baseLength) / 4

        # Round note length to 16th note
        noteLength = (noteList[i][2]-noteList[i][1])
        noteLengthRounded = round(noteLength / baseLength) / 4

        beatList.append([noteList[i][0],noteStartRounded,noteLengthRounded])

    return beatList

# Writes XML intro to output
def CreateXmlIntro(output,name, author):
    intro = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
        '<score-partwise version="4.0">',
        '  <movement-title>'+name+'</movement-title>',
        '  <identification>',
        '    <creator type="composer">'+author+'</creator>',
        '  </identification>',
        '  <part-list>',
        '   <score-part id="P1">',
        '      <part-name>Music</part-name>',
        '    </score-part>',
        '  </part-list>',
        '  <!--=========================================================-->',
        '  <part id="P1">'
    ]
    for line in intro:
        output.write(line+"\n")

# Writes XML attributes (for measure 1) to output
def CreateXmlAttributes(output,sharpIndex):
    attr = [ 
        '      <attributes>',
        '        <divisions>8</divisions>',
        '        <key>',
        '          <fifths>'+str(sharpIndex)+'</fifths>',
        '          <mode>major</mode>',
        '        </key>',
        '        <time>',
        '          <beats>4</beats>',
        '          <beat-type>4</beat-type>',
        '        </time>',
        '        <staves>2</staves>',
        '        <clef number="1">',
        '          <sign>G</sign>',
        '          <line>2</line>',
        '        </clef>',
        '        <clef number="2">',
        '          <sign>F</sign>',
        '          <line>4</line>',
        '        </clef>',
        '      </attributes>'
    ]
    for line in attr:
        output.write(line+"\n")

# Writes XML end to output
def CreateXmlEnd(output):
    end = [
        '  </part>',
        '</score-partwise>'
    ]
    for line in end:
        output.write(line)

# Converts note to XML, writes note  to output
def CreateXmlNote(output,note,staff,noteNames):
    xmlNotes = []

    # Find note pitch
    sharpBases = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
    flatBases = ["A","Bb","B","C","Db","D","Eb","E","F","Gb","G","Ab"]
    sharpBool = True if noteNames[1][0]=="A" else False

    # Converts XML duration to note type (True if note type is dotted)
    XmlNoteDict = {1:("32nd",False), 2:("16th",False), 3:("16th",True),4:("eighth",False), 6:("eighth",True), 
                    8:("quarter",False),12:("quarter",True),16:("half",False),24:("half",True),32:("whole",False)}

    rest = (note[0]==-1)
    
    noteName = noteNames[note[0]%12] # Pitch displayed on music
    step = noteName[0]
    accidental = noteName[1] if len(noteName)==2 else None

    if sharpBool:
        noteBase = sharpBases[note[0]%12] # Actual pitch
        alter = 0 if len(noteBase)==1 else 1
    else:
        noteBase = flatBases[note[0]%12] # Actual pitch
        alter = 0 if len(noteBase)==1 else -1
    
    octave = math.floor((note[0]+9)/12)
    voice = note[4]

    # Find note type
    duration = note[1]*8
    noteType, dotted = XmlNoteDict[note[1]*8]
    
    if(note[2]>0): # Backup for chords or notes that start between other notes
        xmlNotes.append('      <backup>')
        xmlNotes.append('        <duration>'+str(int(round(note[2]*8,0)))+'</duration>')
        xmlNotes.append('      </backup>')

    xmlNotes.append('      <note>')
    if (rest): # Sets note type to rest
        xmlNotes.append('        <rest/>')
    else: # Sets pitch of note
        xmlNotes.append('        <pitch>')
        xmlNotes.append('          <step>'+str(step)+'</step>')
        xmlNotes.append('          <alter>'+str(alter)+'</alter>')
        xmlNotes.append('          <octave>'+str(octave)+'</octave>')
        xmlNotes.append('        </pitch>')

    xmlNotes.append('        <duration>'+str(int(round(duration)))+'</duration>')
    xmlNotes.append('        <voice>'+str(voice)+'</voice>')
    xmlNotes.append('        <type>'+str(noteType)+'</type>')

    # Includes dots for dotted notes
    if(dotted): 
        xmlNotes.append('        <dot/>')
    xmlNotes.append('        <staff>'+str(staff)+'</staff>')

    # Includes notations for accidentals & ties
    if(note[3] or accidental):
        xmlNotes.append('        <notations>')
        if(note[3]=="stop" or note[3]=="continue"):
            xmlNotes.append('          <tied type="stop"/>')
        if(note[3]=="start" or note[3]=="continue"):
            xmlNotes.append('          <tied type="start"/>')
        if(accidental=="N"):
            xmlNotes.append('          <accidental-mark>natural</accidental-mark>')
        elif(accidental=="#"):
            xmlNotes.append('          <accidental-mark>sharp</accidental-mark>')
        elif(accidental=="b"):
            xmlNotes.append('          <accidental-mark>flat</accidental-mark>')
        xmlNotes.append('        </notations>')

    xmlNotes.append('      </note>')

    for line in xmlNotes:
        output.write(line+"\n")

# Splits beat list into arrays for leftHand and rightHand
def SplitHands(beatList):
    leftHand =[]
    rightHand = []

    for beat in beatList:
        if(beat[0]>=39): # Compares to middle C
            rightHand.append(beat)
        else:
            leftHand.append(beat)

    return (leftHand,rightHand)

# Splits beats into appropriate lengths (5 beats = quarter note + eight note)
def SplitBeats(beatInfo):
    beatCount = beatInfo[1]*8

    # Converts XML duration to note type (True if note type is dotted)
    XmlNoteDict = {1:("32nd",False), 2:("16th",False), 3:("16th",True),4:("eighth",False), 6:("eighth",True), 
                    8:("quarter",False),12:("quarter",True),16:("half",False),24:("half",True),32:("whole",False)}

    if beatCount in XmlNoteDict:
        return [beatInfo]

    beatValues = list(XmlNoteDict.keys())
    beatValues.sort(reverse=True)

    beatBreakdown = []
    while(beatCount>0):
        if beatCount in beatValues:
            beatBreakdown.append(beatCount/8)
            beatCount=0
            break
        for beatValue in beatValues:
            if beatValue<=beatCount:
                beatCount-=beatValue
                beatBreakdown.append(beatValue/8)
                break

    newBeats = []
    for i in range(len(beatBreakdown)):
        if i==0:
            if(beatInfo[3]=="stop"): # Slur started in previous measure
                newBeats.append((beatInfo[0],beatBreakdown[i],beatInfo[2],"continue",beatInfo[4]))
            else: # Start tied
                newBeats.append((beatInfo[0],beatBreakdown[i],beatInfo[2],"start",beatInfo[4]))
        else:
            if(i==len(beatBreakdown)-1 and beatInfo[3]!="start"): # Slur contained in measure
                newBeats.append((beatInfo[0],beatBreakdown[i],0,"stop",beatInfo[4]))
            else:
                newBeats.append((beatInfo[0],beatBreakdown[i],0,"continue",beatInfo[4])) # Slur continues (beyond measure)
    
    return newBeats

# Converts (noteIndex, starting beat number, beat duration) to list of measures
# Each measure contains entries of (noteIndex, beat duration, takeback, ties, voice)
def BeatTranslation(beatList, timeSig, measureCount,voiceBase):

    measures = [[] for _ in range(measureCount)] # Measures that will be returned
    measureBeats = [[] for _ in range(measureCount)]

    beatsFilled = [0] * measureCount # Non-empty beats at measure i
    beatsAt = [0] * measureCount # Current pointer for beats at measure i
    voice = voiceBase
  
    # Adds each entry to corresponding measures
    for beat in beatList:
        measureNum = math.floor(beat[1]//timeSig[0]) # Measure number
        beatNum = beat[1]%(timeSig[0]) # Beat number
        takeback, tied = 0, None

        # Check if rests need to be inserted
        if beatNum>beatsAt[measureNum]: 
            measures[measureNum].extend(SplitBeats((-1,beatNum-beatsAt[measureNum],0,None,voice)))
            beatsAt[measureNum]=beatNum
        
        # Check if need to insert takeback because pointer too far ahead
        if beatNum<beatsAt[measureNum]:
            takeback = beatsAt[measureNum] - beatNum 
            voice = (voice+2)%8

        # Check if notes need to be extended to next measure
        if beatNum + beat[2] > timeSig[0]:
            extendBeats = beatNum + beat[2] - timeSig[0]
            extraMeasureNum = measureNum + 1
            while(extendBeats>0):
                if extendBeats<=timeSig[0]:
                    tied = "stop"
                else:
                    tied = "continue"
                measures[extraMeasureNum].extend(SplitBeats((beat[0],min(4,extendBeats),takeback,tied, voice)))

                beatsFilled[extraMeasureNum] = min(4,extendBeats)
                beatsAt[extraMeasureNum] = min(4,extendBeats)
                extendBeats -= min(4,extendBeats)
                extraMeasureNum += 1

        # Add notes to measure
        if beatNum+beat[2]>timeSig[0]: # Extends past measureNum
            tied = "start"
            measures[measureNum].extend(SplitBeats((beat[0],timeSig[0]-beatNum,takeback,"start", voice)))
        else: # Doesn't extend past measureNum
            measures[measureNum].extend(SplitBeats((beat[0],beat[2],takeback,tied, voice)))

        beatsFilled[measureNum]=min(max(beatNum+beat[2],beatsFilled[measureNum]),timeSig[0])
        beatsAt[measureNum]=min(beatNum+beat[2],timeSig[0])
        measureBeats[measureNum].append(beat)
        
    
    for i in range(len(measures)):
        if beatsAt[i] < timeSig[0]:
            measures[i].extend(SplitBeats((-1,timeSig[0]-beatsAt[i],0,None,voice)))
    return measures

# Converts measures into XML, writes to output
def CreateXmlMeasures(output,leftHandBeats,rightHandBeats, sharpIndex, timeSig):

    sharpArray = ["F","C","G","D","A","E","B"]
    sharpBases = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
    flatBases = ["A","Bb","B","C","Db","D","Eb","E","F","Gb","G","Ab"]
    newNoteNames = []

    if sharpIndex == 0:
        newNoteNames = sharpBases.copy()
    elif sharpIndex>0:
        sharps = set(sharpArray[0:sharpIndex])
        for noteName in sharpBases:
            if noteName[0] in sharps:
                if len(noteName)==1:
                    newNoteNames.append(noteName+"N")
                else:
                    newNoteNames.append(noteName[0])
            else:
                newNoteNames.append(noteName)
    else:
        flats = set(sharpArray[len(sharpArray)+sharpIndex:len(sharpArray)])
        for noteName in flatBases:
            if noteName[0] in flats:
                if len(noteName)==1:
                    newNoteNames.append(noteName+"N")
                else:
                    newNoteNames.append(noteName[0])
            else:
                newNoteNames.append(noteName)


    # Create measure
    for measureNum in range(len(leftHandBeats)):

        output.write('    <measure number="'+str(measureNum+1)+'">\n') 

        # Add attributes (clef, time signature, etc.) for first measure
        if (measureNum==0):
            CreateXmlAttributes(output,sharpIndex)

        # Write right hand notes
        for note in rightHandBeats[measureNum]:
            CreateXmlNote(output,note,1,newNoteNames)
        
        # Backup to write left hand notes
        output.write('      <backup>\n')
        output.write('        <duration>'+str(int(round(timeSig[0]*8)))+'</duration>\n')
        output.write('      </backup>\n')

        # Write left hand notes
        for note in leftHandBeats[measureNum]:
            CreateXmlNote(output,note,2,newNoteNames)

        output.write('    </measure>\n')     

def process(filename, keyFrame, startFrame, lastFrame, tempo, key, 
            title, composer, noteThreshold):
            
    filename = "static/uploads/"+filename

    cap = cv2.VideoCapture(filename) # VideoCapture is a datatype constructor
    cap.open(filename) # Open video

    # Check if video opened
    if (cap.isOpened() == False):
        print("Error opening video File")

    # Variables - Image detection
    height, width = 0,0 # Stats
    keyRow = -1 # Y pos used to calculate keys
    noteRow = 200 # Y pos used to calculate notes
    keyGroups = [] # Holds (start x, end x) for 88 notes
    noteList = [] # Holds (note type, start time, end time)
    noteActive = {} # Dict for which notes were active last frame

    keyThreshold = 60 # Threshold for differentiating white/black keys
    keyLength = 3 # Minimum length for white/black key
    noteBuffer = 1 # Pixels on either side of X bounds ignored for note considerations
    noteYRange = 2 # Pixels in Y direction needed to be considered a note

    for i in range(88):
        noteActive[i]=-1

    # Variables - Image detection start
    keyFrameActive = True

    # Variables - Music characteristics
    tempoLength = 60000/tempo
    measureCount = 0
    timeSig = [4,4]


    if not os.path.isdir("Frames"):
        os.makedirs("Frames")

    # Iterating through the frames
    while (cap.isOpened()):

        ret, frame = cap.read() # ret is false if no frames have been grabbed
        
        timestamp = cap.get(cv2.CAP_PROP_POS_MSEC)
        if timestamp<keyFrame or (timestamp<startFrame and not keyFrameActive):
            continue
            
        if timestamp > lastFrame:
            break

        if ret == True: # Frame grabbed
            
            frameBW = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Converts frame to black/white

            # Updates global variables based on measurement from key frame
            if keyFrameActive:
                height, width, _ = frame.shape
                # Testing row which keyboard can be read
                if keyRow==-1:
                    for i in range(1,height//10): 
                        keyRow = height - 10*i
                        keyGroups = CreateKeyGroups(frameBW[keyRow], width, keyThreshold, keyLength)
                        DrawKeyGroups(frameBW,keyGroups,height,keyThreshold,keyRow)
                        if len(keyGroups)>70: # 73 is the length when E-F and B-C read as one key

                            # Testing key threshold for which all 88 keys of keyboard can be read
                            for i in range(1,100):
                                keyGroups = CreateKeyGroups(frameBW[keyRow], width, 5*i, keyLength)
                                if len(keyGroups)==88: # 73 is the length when E-F and B-C read as one key
                                    break
                                DrawKeyGroups(frameBW,keyGroups,height,i,keyRow)
                        if(len(keyGroups)==88):
                            break
                        noteRow = height//2
                else:
                    keyGroups = CreateKeyGroups(frameBW[keyRow], width, keyThreshold, keyLength)
               
                if(len(keyGroups)!=88):
                    raise Exception("Keyboard cannot be read")
                keyFrameActive = False

                if timestamp<startFrame:
                    continue

            noteArray = GetNotes(frameBW,noteRow, keyGroups, noteBuffer, noteYRange, noteThreshold) # Checks which notes are pressed
            UpdateNotes(noteList, noteArray, noteActive, timestamp) # Updates noteArray
            #DrawReader(frameBW,noteArray,keyGroups,noteRow,height,timestamp) # Creates debug images

            # Press 'q' to terminate
            if cv2.waitKey(1) & 0xFF == ord('q'): 
                break
        
        else: # No frame grabbed, break
            break

    if tempo < 0: # Sets tempo, tempoLength if not set by user
        (tempo, tempoLength) = CalcNoteLength(noteList)
    else:
        tempoLength = 60000/tempo
    beatList = NoteTranslation(noteList,tempoLength,startFrame) # Translates note list into beat sequence

    measureCount = math.ceil((beatList[-1][1]+beatList[-1][2])/timeSig[0]) # Calculates number of measures

    leftHand, rightHand = SplitHands(beatList)
    leftHand.sort(key=lambda x:(x[1],x[2],x[0])) # Sorts by start time, then beat length, then note ascending 
    rightHand.sort(key=lambda x:(x[1],x[2],x[0])) # Sorts by start time, then beat length, then note ascending 


    # Testing
    leftHandBeats = BeatTranslation(leftHand,timeSig,measureCount,0)
    rightHandBeats = BeatTranslation(rightHand,timeSig,measureCount,1)

    output = open("static/outputfile/out.musicxml",'w')
    #output = open("out.musicxml",'w')
    CreateXmlIntro(output,title,composer)
    CreateXmlMeasures(output,leftHandBeats,rightHandBeats,key, timeSig)
    CreateXmlEnd(output)

    cap.release() # Closes the video file
    cv2.destroyAllWindows() # Destroys windows?

    return tempo

def main(filename, keyFrame, startFrame, lastFrame, tempo, key, 
            title, composer, noteThreshold):
    errorMessage = None
    try:
        tempo = process(filename, keyFrame, startFrame, lastFrame, tempo, key, 
            title, composer, noteThreshold)
    except Exception as error:
        errorMessage = repr(error)
        tempo = -1
  
    return (errorMessage,tempo)

