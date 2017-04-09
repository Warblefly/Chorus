# Chorus
Massively parallel algorithmic composition tool for processing and combining large numbers of recorded sounds

For the interactive community art project and exhibition "Sway" (10th to 23rd April 2017, at O N C A Gallery, Brighton), bringing to visitors the truth about migration in the 21st century, I was asked to think about a soundtrack. My idea, based on the birdsong observations, recording and compositions of Olivier Messiaen among other great composers, was to create a unique, ever-changing soundscape based upon:

1. The genuine recorded songs of migrant birds, processed and parallelized massively in pitch, volume and time;
2. Songs of many cultures, sent to the world for teaching purposes by the British Council World Voice project
3. The contribution of gallery visitors who add new elements to a sculpture: each new element brings an addition to the soundtrack.

To this end, I have created this program (really, a set of functions that the player strings together programmatically) that is a new musical instrument. It efficiently analyses, then processes for pitch, multi-channel pan and dynamics, very large numbers of sounds, with a minimum of human intervention. Finally, the hundreds or thousands of resultant audio files are mixed into a soundscape of almost infinite variety and interest.

The ubiquitous and popular multimedia encoding and processing tool FFmpeg has many functions this musical instrument uses, including an audio mix function. Until today, this was limited to 32 channels. However, today my patch was applied by the developers, to increase this limit to 1024 inputs. On an 8-core 4.6GHz machine fed with audio from a SATA drive running at 6Gbit/s, encoding is barely twice real-time. It is possible that use of an SSD for storing audio would improve this speed enormously.

The patch for FFmpeg is included in this repository, but in the very near future, binary distributions of FFmpeg will include this patch.

The program "Chorus" is dedicated to the "SWAY" exhibition, and to all who fall into the effects of injustice as a result of migration. This includes my own family.

Chorus is released under Version 2 of the GNU General Public Licence.

You need Python 3.6 and a patched FFmpeg to use this. And lots of recorded sounds. And a fast-multiprocessor computer unless you don't mind starting a process, going for a very long walk, and coming back.

Version 0.92. It works.
