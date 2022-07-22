# Chorus
Massively parallel algorithmic composition tool for processing and combining large numbers of recorded sounds

For the interactive community art project and exhibition "Sway" (10th to 23rd April 2017, at O N C A Gallery, Brighton), bringing to visitors the truth about migration in the 21st century, I was asked to think about a soundtrack. My idea, based on the birdsong observations, recording and compositions of Olivier Messiaen among other great composers, was to create a unique, ever-changing soundscape based upon:

1. The genuine recorded songs of migrant birds, processed and parallelized massively in pitch, volume and time;
2. Songs of many cultures, sent to the world for teaching purposes by the British Council World Voice project
3. The contribution of gallery visitors who add new elements to a sculpture: each new element brings an addition to the soundtrack.

To this end, I have created this program (really, a library of functions that the player strings together programmatically) that is a new musical instrument. 

It efficiently analyses, then processes for pitch, multi-channel pan and dynamics, very large numbers of sounds, with a minimum of human intervention. Finally, the hundreds or thousands of resultant audio files are mixed into a soundscape of almost infinite variety and interest. The number of parallel sounds can quickly exceed a six-figure quantity if the program is run sufficient times.

At the heart of Chorus's processing is the ubiquitous and popular multimedia encoding and processing tool FFmpeg. Many of its funtions are used here, including an audio mix function. The very latest versions of FFmpeg allow up to 1024 audio tracks to be combined using the filter 'amix'. Earlier versions allowed only 32 (for sensible reasons) but the developers have accepted my patch allowing the larger number of inputs. On an 8-core 4.6GHz machine fed with audio from a SATA drive running at 6Gbit/s, mixing and uncompressed writing of 500 input files simultaneously progresses at about three to five times faster than real-time. It is possible that use of an SSD for storing audio would improve this speed enormously.

The program "Chorus" is dedicated to the "SWAY" exhibition, and to all who fall into the effects of injustice as a result of migration. This includes my own family.

Chorus is released under Version 2 of the GNU General Public Licence.

You need Python 3.6 and FFmpeg to use this. And you'll want lots of recorded sounds. And a fast-multiprocessor computer unless you don't mind starting a process, going for a very long walk, and coming back.

Version 0.93. It works.
