### IMPORTANT
### CONFIGURATION
### PLEASE CHANGE THE FFMPEG VARIABLE TO POINT TO YOUR FFMPEG PROGRAM

# Samplerate for all processed audio including final mix
SAMPLERATE = 48000

# Path to the directory containing your FFmpeg and FFprobe executables
FFMPEG = r"c:/Program Files/ffmpeg/bin/"

# How many audio channels will the final mix contain?
CHANNELS = 2

# How long is the shortest piece of audio?
SHORTEST = 1

# How long is the longest piece of audio?
LONGEST = 19

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
MONOCODEC = "-vn -acodec pcm_s16le"

# Which codec is to be used for panned and mixed files including the final output?
STEREOCODEC = "-vn -acodec pcm_s16le -ac 2"

COMPRESSEDCODEC = "-vn -acodec pcm_s16le "

# Where shall the temporary files for FFmpeg commands be stored?
# Put them somewhere visible if you wish to debug them.

TEMPLOCATION="E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/PROCESSED/tmp"

# End of user-definable variables
#################################


import logging, random, math, argparse, subprocess, json, os, concurrent.futures, itertools, pprint, copy, tempfile, string

logging.basicConfig(level=logging.DEBUG, format='%(funcName)s - %(levelname)s - %(message)s')

# Make sure our temporary files will work
os.makedirs(TEMPLOCATION, exist_ok=True)
tempfile.tempdir=TEMPLOCATION

def ffmpegEscape(input):
    return(input.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'"))

def makeDurList(time, shortest=1, longest=10):
    # logging.debug("Durations totalling %s to be calculated" % time)

    durList = list()
    totalDur = 0
    while totalDur <= time:
        duration = random.uniform(shortest, longest)
        durList.append(duration)
        totalDur += duration
        # logging.debug("Appending %s seconds" % duration)

    overTime = totalDur - time
    durList[-1] -= overTime

    #logging.debug("List of durations:" % durList)
    #logging.debug("Check: total durations in list is %s" % sum(durList))
    return(durList) 

def makeVolumeList(count, quietest=-24, loudest=0):
    # These are multichannel values
    volumeList = [None] * count
    for i in range(count):
        volumeList[i] = [None] * CHANNELS
        for c in range(CHANNELS):
            volumeList[i][c] = random.uniform(quietest, loudest)
            # Some of the volumes need to be set to zero
        if random.random() > 0.5:
            for c in range(CHANNELS):
                volumeList[i][c] = 0 - math.inf
    # logging.debug("List of volumes: %s" % volumeList)
    return(volumeList)

def makePitchList(count, lowest=1/20, highest=1/2):
    pitchList = [None] * count
    for i in range(count):
        pitchList[i] = random.uniform(lowest, highest) * SAMPLERATE
    #logging.debug("List of pitches: %s" % pitchList)
    return(pitchList)

def clipLength(filename):
    dos_command=[FFMPEG+"ffprobe.exe", "-v", "quiet", "-hide_banner", "-print_format", "json", "-show_streams", "-select_streams", "a:0", filename]
    jReturn = json.loads(subprocess.run(dos_command, check=True, stdout=subprocess.PIPE).stdout)
    duration = jReturn['streams'][0]['duration']
    #logging.debug("Found an audio track of duration %s seconds" % duration)
    return(int(float(duration)))

def clipLengthSamples(filename):
    dos_command=[FFMPEG+"ffprobe.exe", "-v", "quiet", "-hide_banner", "-print_format", "json", "-show_streams", "-select_streams", "a:0", filename]
    jReturn = json.loads(subprocess.run(dos_command, check=True, stdout=subprocess.PIPE).stdout)
    duration = jReturn['streams'][0]['duration_ts']
    #logging.debug("Found an audio track of duration %s samples" % duration)
    return(int(float(duration)))

def deltaVolFormula(v1, v2, t1, t2):
    if math.isinf(v1):
        v1 = -999
    if math.isinf(v2):
        v2 = -999
        v1 = round(v1)
        v2 = round(v2)
        t1 = round(t1, 1)
        t2 = round(t2, 1)
    # Calculates the FFmpeg formula string for creating a smooth
    # slope between one volume and another, given the volumes
    # required at either end of the slope (v1 and v2), and the time in seconds
    # at each end of the slope (t1 and t2)
    formula = "'if(between(t,%.1f,%.1f),%.0fdB-((%.0fdB-%.0fdB)/(%.1f-%.1f))*(%.1f-t),1)':eval=frame" % (t1, t2, v1, v2, v1, t2, t1, t1)
    return(formula)

def standardiseDirectory(pathname, destination="%s/PROCESSED"):
    destination = destination % pathname
    # Using parallel processing...
    # Go through a directory of audio files, and convert each to a file
    # in standardized format. All are in mono at SAMPLERATE samples/sec.
    # Also (sadly, for reasons associated with the practicality of processing long
    # files requiring many volume variations) we truncate each file
    # to nine minutes.
    
    os.makedirs(destination, exist_ok=True)
    
    fileList = filterAudioFiles(os.listdir(pathname))
    commands = list()

    for fileName in fileList:
        fullFileName = pathname + '/' + fileName
        
        # First, original pitch
        commands.append("\"" + FFMPEG + "ffmpeg\" -y -i \"%s\" " % fullFileName + " -af " + PROCORIG % SAMPLERATE + " " + MONOCODEC \
                  + " " + METADATA % SAMPLERATE + "  \"" + destination + "/" + fileName + ".wav\"")
        
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for command in commands:
            # logging.debug(command)
            try:
                future = executor.submit(subprocess.call, command)
            except Exception:
                # logging.debug("This should never be reached")
                pass
    return()

def pitchShiftDirectory(pathname, variants=8):
    # Now let's make the files at lower pitches
    commands = list()
    fileList = filterAudioFiles(os.listdir(pathname))

    for fileName in fileList:
        fullFileName = pathname + '/' + fileName
        pitchList = makePitchList(variants)
        for pitch in pitchList:
            #commands.append("echo HELLO > output")
            commands.append("\"" + FFMPEG + "ffmpeg\" -y -i \"%s\" " % fullFileName \
                            + " -af " + PROCPITCH % (pitch, SAMPLERATE) + " " + MONOCODEC \
                            + " -t 07:00 " + METADATA % pitch + " \"" + pathname + "/" + os.path.splitext(fileName)[0] + "-%d" % pitch + ".wav\"")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for command in commands:
            # (command)
            #subprocess.run(command)
            try:
                future = executor.submit(subprocess.run, command)
            except Exception:
                # logging.debug("This should never be reached")
                pass
    return()

def filterAudioFiles(fileList):
    outputList = list()
    for fileName in fileList:
        if (os.path.splitext(fileName)[1].lower() in EXTS):
            outputList.append(fileName)
    return(outputList)

def makeVolumeAndTimeNodeList(pathname, destination="%s/VOLUMEPROCESSED"):
# Now create a dictionary containing:
# Filename
# Duration
# durationList
# volumeList

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
        # logging.debug("Volumes: %s" % fileDict['Volumes'])

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
        # nodeList.append(fileDict)
        # logging.debug("Appending %s" % fileDict)
        # logging.debug("Length of volumes is %s" % len(fileDict['Volumes']))
        # logging.debug("Length of times is %s" % len(fileDict['Times']))
        nodeList.append(fileDict)
    return(nodeList)

def makeFFmpegVolumeCommands(fileDict):
    # Returns a list of lists, containing the strings required to pass to FFmpeg,
    # one string per channel, to adjust the volume levels as required
    # Each returned list item corresponds to the set of volume commands required,
    # one string per channel, at the corresponding time.
    FFmpegVolumeCommands = list()
    # Create per-channel lists of volumes
    timesList = fileDict["Times"]
    channel = 0
    while channel < CHANNELS:
        channelVolumesList = list()
        
        for volumeItem in fileDict["Volumes"]:
            channelVolumesList.append(volumeItem[channel])

        volumeCommandList = list()
        # logging.debug("Channel % d" % channel)
        # logging.debug("Volumes: %s" % channelVolumesList)
        
        # Because the lists have been prepared by makeVolumeAndTimeNodeList()
        # and therefore contain duplicate entries in the expected places,
        # we now create for each pair of values an appropriate FFmpeg volume
        # command. This is slightly inefficient, because two identical volumes will
        # still be the subjects of mathematics to calculate the slope (exactly 0)
        # between the two values. But, for today, it saves my programming time.

        nodeList = list(zip(channelVolumesList, timesList))
        # pprint.pprint(nodeList)
        for i, node in enumerate(nodeList):
            # pprint.pprint(node)
            v1 = nodeList[i][0]
            try:
                v2 = nodeList[i+1][0]
            except Exception:
                v2 = v1
            t1 = nodeList[i][1]
            try:
                t2 = nodeList[i+1][1]
            except Exception:
                t2 = t1
            volumeCommand = deltaVolFormula(v1, v2, t1, t2)
          # logging.debug("Command is: %s" % volumeCommand)
            volumeCommandList.append(volumeCommand)
            # At this point, one whole channel's volume commands have been calculated.
        FFmpegVolumeCommands.append(volumeCommandList)
        channel += 1
        
    return(FFmpegVolumeCommands)

def fullFFmpegCommand(filename, volumeCommands):

    # Two things go on here. We create a filter whose commands get put into a file with a
    # suitable temporary file name. Then we create an FFmpeg command to process the file
    # whilst reading its filter commands from the temporary file we just created. This is to
    # work around the limitation of DOS commands having a maximum of just 8191 characters.

    command = "\"" + FFMPEG + "/ffmpeg\" -i \"" + filename + "\" -filter_complex_script \""

    script = ''
    # Split the audio into the required number of channels
    script += "[0:a]aformat=sample_fmts=flt,asplit=" + str(CHANNELS)
    for channel in range(CHANNELS):
        channelLabel = "[" + str(channel) + "]"
        script += channelLabel
    script +=";"

    # Now here come the volume commands, one set of commands per channel
    # The variable "volumeCommands" has the structure
    # [ [channel1command1, channel1command2, channel1command3, ... ] [channel2command1, ...] ... ]

    channel = 0
    for channelCommands in volumeCommands:
        script += "[" + str(channel) + "]"
        for channelNode in channelCommands:
            script += "volume=" + channelNode + ","
        # No more volume commands: take off the final comma and add an output format and pad
        # For some reason, the pcm_s16le codec doesn't read the output channels format of the
        # 'volume' filter correctly without this help.
        script = script[0:-1] + ",aformat=channel_layouts=mono" + "[" + str(channel) + "op]" + ";"
        channel += 1

    # Now the output of the volume commands must be recombined into the correct number of
    # output channels

    for channel in range(CHANNELS):
        script += "[" + str(channel) + "op" + "]"

    script += "amerge=inputs=" + str(CHANNELS) + "[out0]"

    # Now write the script to a temporary file
    tempHandle = tempfile.NamedTemporaryFile(delete=False)
    name = tempHandle.name
    logging.debug("Temp file is: %s" % name)
    tempHandle.write(script.encode('utf-8'))
    tempHandle.close()

    command += name + "\" -map \"[out0]\" "

    # That's the filter done. Now to encode the audio.
    outputFile = os.path.dirname(filename) + "/VOLUMEPROCESSED/" + os.path.basename(filename)
    command += COMPRESSEDCODEC + "\"%s\"" % outputFile

    # parameters = {"Command": command, "Filter" : name}
    logging.debug("FFmpeg command is: %s" % command)
    return(command)   

def repitchRenderList(renderList):
    commandsToRunList = list()
    for render in renderList:
        commandList = makeFFmpegVolumeCommands(render)
        logging.debug("Processing %s" % render['Name'])
        commandsToRunList.append(fullFFmpegCommand(render['Name'], commandList))

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for command in commandsToRunList:
            try:
                future = executor.submit(subprocess.run, command)
            except Exception:
                # logging.debug("This should never be reached")
                pass
        
    return()

def mixDirectoryFiles(directory, count=999999, renderDuration=3600):
    # Mixes all the audio files in a single cirectory into one file
    # Count determines how many files get mixed,
    # Duration is the duration of the output mix
    
    # Start with a list of all the audio files we're interested in
    fileList = filterAudioFiles(os.listdir(directory))

    # Never request more files to mix than there are files available
    number = len(fileList)
    if count > number:
        count = number

    outputFile = directory + "/" + "MIX-" + str(count) + "-" + str(renderDuration) + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=9)) + '.wav'

    # Create a list of dictionaries.
    # Each dictionary corresponds to a file.
    # The dictionary has keys: Name, Duration, LoopPoint
    logging.debug("We have %d files." % count)
    fileDictionaryList = list()
    # Only mix as many files as we're instructed to
    for item in random.sample(fileList, count):
        fileDictionary = dict()
        fileDictionary['Name'] = item
        duration = clipLength(directory + "/" + item)
        fileDictionary['Duration'] = duration
        loopPoint = random.randint(0, duration-1)
        fileDictionary['LoopPoint'] = loopPoint
        fileDictionaryList.append(fileDictionary)

    # Start to build FFmpeg command
    
    command = '"' + FFMPEG + 'ffmpeg" -f lavfi -i "anullsrc" -filter_complex_script "'

    script = ''

    # Write the filter for all the input files
    for i, fileDictionary in enumerate(fileDictionaryList):
        script += "amovie='" + ffmpegEscape(directory + "/" + fileDictionary['Name']) + "'"
        script += ":loop=0:seek_point=" + str(fileDictionary['LoopPoint'])
        script += "[" + str(i) + "];"

    # Now merge the input files together
    for i, fileDictionary in enumerate(fileDictionaryList):
        script += "[" + str(i) + "]"
    # The end of the command resets the timestamps because we are looping over
    # incoming audio and, therefore, losing the original timestamps which
    # harms FFmpeg's ability to time its own output.
    script += "amix=inputs=" + str(i+1) + ",asetpts=N/SR/TB,dynaudnorm,bs2b[out0]"

    # Now write the script to a temporary file
    tempHandle = tempfile.NamedTemporaryFile(delete=False)
    name = tempHandle.name
    logging.debug("Temp file is: %s" % name)
    tempHandle.write(script.encode('utf-8'))
    tempHandle.close()

    command += name + '" -map "[out0]" -ac ' + str(CHANNELS) + ' -t ' + str(renderDuration) + ' -acodec pcm_s16le "' + outputFile + '"'

    print(command)
    subprocess.run(command)
    return()
    
    

    

# TESTING OR YOUR MAIN COMMANDS BEGIN HERE
   
standardiseDirectory("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/")
pitchShiftDirectory("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/PROCESSED")
renderList = makeVolumeAndTimeNodeList("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/PROCESSED")

result = repitchRenderList(renderList)

result = mixDirectoryFiles("E:/Users/john/Documents/REAPER Media/CROSSINGS/SOURCES/PROCESSED/VOLUMEPROCESSED")
pprint.pprint(result)

