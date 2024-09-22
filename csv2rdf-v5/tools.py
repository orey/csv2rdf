import csv

LOG = "run.log"
FIRST = True

#============================================ myprint
def myprint(str):
    '''
    print to console and into a log file
    '''
    global FIRST
    if FIRST:
        with open(LOG, "w",encoding='utf-8') as logfile:
            logfile.write(str + '\n')
        FIRST = False
    else:
        with open(LOG, "a",encoding='utf-8') as logfile:
            logfile.write(str + '\n')
    print(str)
        

#============================================ interrupt
def interrupt(obj):
    '''
    Manual breakpoint
    '''
    print(obj)
    resp = input("Continue? ")
    if resp.upper() in ["N","NO"]:
        print("Goodbye!")
        exit(0)


#=========================================== count lines in csv file
def countLinesInCSVFile(file):
    newreader = csv.reader(open(source.file, "r", encoding='utf-8', errors='ignore'), delimiter=delim)
    nblines = 0
    for i, row in enumerate(newreader):
        nblines += 1
    return nblines

        
#============================================ Timer
class Timer():
    def __init__(self):
        self.start = time.time()
    def stop(self):
        self.stop = time.time()
        print("\nTreatment duration: "
              + str((round(self.stop-self.start))//60)
              + " minutes and "
              + str((round(self.stop-self.start))%60)
              + " seconds\n")
        

