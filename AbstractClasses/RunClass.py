from Helper.Initializer import initializer
from Runinfos.RunInfo import RunInfo
from DiamondClass import Diamond
import os
import ConfigParser

class Run(object):

    run_number = -1
    current_run = {}
    operationmode = ''
    #TrackingPadAnalysis.ROOTFile = '' # filepath
    TrackingPadAnalysis = {}

    def __init__(self,run_number=None):
        self.runinfo = RunInfo.load('Runinfos/runs.json')
        self.ValidateRuns()

        if run_number is not None:
            assert(run_number > 0), "incorrect run_number"
            self.run_number = run_number

            self.SetRun(run_number)

    def ValidateRuns(self):

        runs = RunInfo.runs.keys()
        for run in runs:
            self.SetRun(run)
            if not os.path.exists(self.TrackingPadAnalysis['ROOTFile']):
                del RunInfo.runs[run]
                print "INFO: path of run number ",run, " not found."

    def SetRun(self,run_number):

        assert(run_number > 0), "incorrect run_number"
        if run_number in RunInfo.runs:
            self.run_number = run_number

            parser = ConfigParser.ConfigParser()
            parser.read('Configuration/Machineconfig.cfg')
            operationmode = parser.get('EXEC-MACHINE','operationmode')

            if operationmode == "local-ssh":
                self.TrackingPadAnalysis['ROOTFile'] = '/Volumes/scratch/PAD-testbeams/PSI_sept_14/software/TrackingPadAnalysis/results/runs/run_'+str(run_number)+'/track_info.root'

            if operationmode == "ssh":
                self.TrackingPadAnalysis['ROOTFile'] = '/scratch/PAD-testbeams/PSI_sept_14/software/TrackingPadAnalysis/results/runs/run_'+str(run_number)+'/track_info.root'

            if operationmode == "local":
                self.TrackingPadAnalysis['ROOTFile'] = 'runs/run_'+str(run_number)+'/track_info.root'

            self.run_number = run_number
            self.current_run = RunInfo.runs[run_number].__dict__ # store dict containing all run infos
            #a = self.current_run.__dict__
            self.diamond = Diamond( self.current_run['diamond'])



            #self.diamond = diamond # diamond is of type Diamond
            #RunInfo.__init__(self,*args)

            #self.diamond.SetName(self.runs[0]['diamond'])
            return True
        else:
            return False
