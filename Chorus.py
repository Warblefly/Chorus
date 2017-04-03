### IMPORTANT
### CONFIGURATION
### PLEASE CHANGE THE FFMPEG VARIABLE TO POINT TO YOUR FFMPEG PROGRAM

# Samplerate for all processed audio including final mix
SAMPLERATE = 48000

# Path to the directory containing your FFmpeg and FFprobe executables
FFMPEG = r"c:/Program Files/ffmpeg/bin/"

# How many audio channels will the final mix contain?
CHANNELS = 2

# How long is the fade between volume levels (including mute)?
FADE = 0.5

# Which file extensions (case-insentitive) do we consider to be audio files?
EXTS = [".m4a", ".mp4", ".wav", ".aiff", ".aif", ".mp3", ".mp2", ".webm", ".ogg", ".vorbis", ".opus", ".flac"]

# How will the slow-down/speed-up sample rate be described in metadata?
METADATA = "-metadata comment=\"via samplerate %d\""

# How should FFmpeg process each incoming file to get it to a standard format?
PROCORIG = "aformat=channel_layouts=mono,highpass=f=200,silenceremove=1:0:-50dB:-1:0:-50dB,aresample=%d,dynaudnorm"

# How should FFmpeg process each standardized file for pitch?
PROCPITCH = "silenceremove=1:0:-50dB:-1:0:-50dB,asetrate=%d,aresample=%d"

# Which codec is to be used for standardized files?
MONOCODEC = "-vn -acodec libopus"

# Which codec is to be used for panned and mixed files including the final output?
STEREOCODEC = "-vn -acodec libopus -ac 2"

# End of user-definable variables
#################################


import logging, random, math, argparse, subprocess, json, os, concurrent.futures, itertools

logging.basicConfig(level=logging.ERROR, format='%(funcName)s - %(levelname)s - %(message)s')

def ffmpegEscape(input):
    return(input.replate("\\", "\\\\").replace(":", ":\\:"))

def makeDurList(time, shortest=1, longest=20):
    logging.debug("Durations totalling %s to be calculated" % time)

    durList = list()
    totalDur = 0
    while totalDur <= time:
        duration = random.uniform(shortest, longest)
        durList.append(duration)
        totalDur += duration
        logging.debug("Appending %s seconds" % duration)

    overTime = totalDur - time
    durList[-1] -= overTime

    logging.debug("List of durations:" % durList)
    logging.debug("Check: total durations in list is %s" % sum(durList))
    return(durList) 

def makeVolumeList(count, quietest=-24, loudest=0):
    # These are multichannel values
    volumeList = [None] * count
    for i in range(count):
        volumeList[i] = [None] * CHANNELS
        for c in range(CHANNELS):
            volumeList[i][c] = random.uniform(quietest, loudest)
            # Some of the volumes need to be set to zero
        if random.random() > 0.75:
            for c in range(CHANNELS):
                volumeList[i][c] = 0 - math.inf
    logging.debug("List of volumes: %s" % volumeList)
    return(volumeList)

def makePitchList(count, lowest=1/20, highest=1/2):
    pitchList = [None] * count
    for i in range(count):
        pitchList[i] = random.uniform(lowest, highest) * SAMPLERATE
    logging.debug("List of pitches: %s" % pitchList)
    return(pitchList)

def clipLength(filename):
    dos_command=[FFMPEG+"ffprobe.exe", "-v", "quiet", "-hide_banner", "-print_format", "json", "-show_streams", "-select_streams", "a:0", filename]
    jReturn = json.loads(subprocess.run(dos_command, check=True, stdout=subprocess.PIPE).stdout)
    duration = jReturn['streams'][0]['duration']
    logging.debug("Found an audio track of duration %s" % duration)
    return(int(float(duration)))

def deltaVolFormula(v1, v2, t1, t2):
    # Calculates the FFmpeg formula string for creating a smooth
    # slope between one volume and another, given the volumes
    # required at either end of the slope (v1 and v2), and the time in seconds
    # at each end of the slope (t1 and t2)
    formula = "if(between(t,%f,%f),%f-((%f-%f)/(%f-%f))*(%f-t),1):eval=frame" % (t1, t2, v1, v2, v1, t2, t1, t1)
    return(formula)

def standardiseDirectory(pathname, destination="%s/PROCESSED"):
    destination = destination % pathname
    # Using parallel processing...
    # Go through a directory of audio files, and convert each to a file
    # in standardized format. All are in mono at SAMPLERATE samples/sec.
    os.makedirs(destination, exist_ok=True)
    
    fileList = filterAudioFiles(os.listdir(pathname))
    commands = list()

    for fileName in fileList:
        fullFileName = pathname + '/' + fileName
        
        # First, original pitch
        commands.append("\"" + FFMPEG + "ffmpeg\" -y -i \"%s\" " % fullFileName + " -af " + PROCORIG % SAMPLERATE + " " + MONOCODEC \
                  + " " + METADATA % SAMPLERATE + " \"" + destination + "/" + fileName + ".opus\"")
        
    with concurrent.futures.ProcessPoolExecutor() as executor:
        for command in commands:
            logging.debug(command)
            try:
                future = executor.submit(subprocess.call, command)
            except Exception:
                logging.debug("This should never be reached")

def pitchShiftDirectory(pathname, variants=8):
    # Now let's make the files at lower pitches
    commands = list()
    fileList = filterAudioFiles(os.listdir(pathname))

    for fileName in fileList:
        fullFileName = pathname + '/' + fileName
        pitchList = makePitchList(variants)
        for pitch in pitchList:
            commands.append("\"" + FFMPEG + "ffmpeg\" -y -i \"%s\" " % fullFileName \
                            + " -af " + PROCPITCH % (pitch, SAMPLERATE) + " " + MONOCODEC \
                            + " " + METADATA % pitch + " \"" + pathname + "/" + os.path.splitext(fileName)[0] + "-%d" % pitch + ".opus\"")

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for command in commands:
            logging.debug(command)
            try:
                future = executor.submit(subprocess.call, command)
            except Exception:
                logging.debug("This should never be reached")

def filterAudioFiles(fileList):
    outputList = list()
    for fileName in fileList:
        if (os.path.splitext(fileName)[1].lower() in EXTS):
            outputList.append(fileName)
    return(outputList)

def makeVolumeAndTimeNodeList(pathname, destination="%s/VOLUMEPROCESSED"):
# Now create a list containing:
# [0] Filename
# [1] Duration
# [2] durationList
# [3] volumeList

# At each position in the durationList, process the volume according to the figure in the parallel volumeList item
# at each node generate two subnodes
# FIRST with time-0.5s and previous level
# SECOND with time+0.5s and this level


    destination = destination % pathname
    os.makedirs(destination, exist_ok=True)

    nodeList = list()
    fileList = filterAudioFiles(os.listdir(pathname))
    for fileName in fileList:
        fileDict = dict()
        # This is the position in the file we are dealing with
        timePos = 0
        fileDict['Name'] = pathname + "/" + fileName
        fileDict['Duration'] = clipLength(pathname + "/" + fileName)
        durationList = makeDurList(fileDict['Duration'])

        # Remember: volumeList is a list of lists; each list corresponds to
        # the multiple channel values at each volume change point
        # so these volumes also deal with panning
        volumeList = makeVolumeList(len(durationList))

        processedVolumeList = list()
        # We're going to take each volume point except the start and the end points,
        # and generate a new list incorporating not only these points, but
        # fades of duration FADE between one point and the next.
        # Remember: valueList contains a list, whose members are the channel volumes
        for i, valueList in enumerate(volumeList):
            if i == 0:
                # There is no previous volume to append
                processedVolumeList.append(valueList)
            if i > 0:
                # This takes the PREVIOUS volume, appends it to the processedVolumeList,
                # then appends the CURRENT volume
                processedVolumeList.append(volumeList[i-1])
                processedVolumeList.append(valueList)
        # At the end of the list of volumes, we need to add the last volume
        # again, because this is the closing volume
        processedVolumeList.append(valueList)
        fileDict['Volumes'] = processedVolumeList

        timesList = list()
        # Now, using those volumes in processedVolumeList,
        # we're going to generate a list of times where each volume
        # is to be applied.
        for i, time in enumerate(durationList):
            if i == 0:
                # There is no beginning time for this transition
                # because this is the initial volume.
                timesList.append(0)
            # The OLD volume begins to be left FADE time before
            # the NEW volume begins.
            timePos += time
            if i != len(durationList)-1:
                # There's no fade at the end (-1 because the
                # length of a list with a zeroeth element only
                # is 1
                timesList.append(timePos - FADE)
            timesList.append(timePos)
        fileDict['Times'] = timesList

        # Append the command dictionary for this file to the overall list of nodes
        nodeList.append(fileDict)
        logging.debug("Appending %s" % fileDict)
        logging.debug("Length of volumes is %s" % len(fileDict['Volumes']))
        logging.debug("Length of times is %s" % len(fileDict['Times']))
        nodeList.append(fileDict)
    return(nodeList)

def makeFFmpegVolumeCommand(fileDict):
    # Returns a list of lists, containing the strings required to pass to FFmpeg,
    # one string per channel, to adjust the volume levels as required
    # Each returned list item corresponds to the set of volume commands required,
    # one string per channel, at the corresponding time.
    volumeCommandList = list()
    for volumeList, time in itertools.izip(fileDict['Volumes'], fileDict['Times']):
        # Because the lists have been prepared by makeVolumeAndTimeNodeList()
            


def makeStereoPanned(fileDict):
    # Structure of fileDict is:
    # [0] Filename
    # [1] Duration
    # [2] durationList
    # [3] volumeList




class Birdsong:
   def __init__(self, filename):
        self.filename = filename
        self.duration = clipLength(self.filename)
        self.durList = makeDurList(self.duration)
        self.volumeList = makeVolumeList(len(self.durList))
        # self.pitchList = makePitchList(len(self.durList))

           
#testfile = Birdsong("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/Hirundo rustica-04.mp3")

#print("File duration is: %s" % testfile.duration)
#print("File duration_list is: %s" % testfile.durList)
#print("File volume list is: %s" % testfile.volumeList)
# print("File pitch list is: %s" % testfile.pitchList)

#print(deltaVolFormula(v1=6, v2=1, t1=3, t2=5))

standardiseDirectory("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/")
pitchShiftDirectory("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/PROCESSED")
renderList = makeVolumeAndTimeNodeList("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/PROCESSED")
print("Renderlist is %s" % renderList)

