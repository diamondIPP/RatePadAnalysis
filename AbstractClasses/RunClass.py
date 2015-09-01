from Helper.Initializer import initializer
from Runinfos.RunInfo import RunInfo
from DiamondClass import Diamond
from Elementary import Elementary
from datetime import datetime as dt
import ROOT
import os
import ConfigParser
import json
import copy

default_info =  {
        "persons on shift": "-",
        "run info": "-",
        "type": "signal",
        "configuration": "signal",
        "mask": "-",
        "masked pixels": 0,
        "diamond 1": "CH_0",
        "diamond 2": "CH_3",
        "hv dia1": 0,
        "hv dia2": 0,
        "for1": 0,
        "for2": 0,
        "fs11": 0,
        "fsh13": 0,
        "quadrupole": "-",
        "analogue current": 0,
        "digital current": 0,
        "begin date": "2999-03-14T15:26:53Z",
        "trim time": "-:-:-",
        "config time": "-:-:-",
        "start time": "2999-03-14T15:26:53Z",
        "trig accept time": "-:-:-",
        "opening time": "-:-:-",
        "open time": "-:-:-",
        "stop time": "2999-03-14T16:26:53Z",
        "raw rate": 0,
        "prescaled rate": 0,
        "to TLU rate": 0,
        "pulser accept rate": 0,
        "cmspixel events": 0,
        "drs4 events": 0,
        "datacollector events": 0,
        "aimed flux": 0,
        "measured flux": 0,
        "user comments": "-",
        "is good run": True
}

class Run(Elementary):
    '''

    '''

    current_run = {}
    operationmode = ''
    TrackingPadAnalysis = {}

    def __init__(self, run_number, diamonds=3, validate = False, verbose = False):
        '''

        :param run_number: number of the run
        :param diamonds: 0x1=ch0; 0x2=ch3
        :param validate:
        :param verbose:
        :return:
        '''
        Elementary.__init__(self, verbose=verbose)

        self.run_number = -1
        self.LoadConfig()

        if validate:
            self.ValidateRuns()

        if run_number != None:
            assert(run_number > 0), "incorrect run_number"
            self.SetRun(run_number)
        else:
            self.LoadRunInfo()
        self._LoadTiming()
        self.diamondname = {
            0: str(self.RunInfo["diamond 1"]),
            3: str(self.RunInfo["diamond 2"])
        }
        self.bias = {
            0: self.RunInfo["hv dia1"],
            3: self.RunInfo["hv dia2"]
        }
        self.SetChannels(diamonds)
        self.IsMonteCarlo = False

    def LoadConfig(self):
        machineConfigParser = ConfigParser.ConfigParser()
        machineConfigParser.read('Configuration/Machineconfig.cfg')
        self.operationmode = machineConfigParser.get('EXEC-MACHINE','operationmode')
        self.ShowAndWait = False
        runConfigParser = ConfigParser.ConfigParser()
        runConfigParser.read("Configuration/RunConfig_"+self.TESTCAMPAIGN+".cfg")
        self.filename = runConfigParser.get('BASIC', 'filename')
        self.treename = runConfigParser.get('BASIC', 'treename')
        self.sshrunpath = runConfigParser.get('BASIC', 'runpath')
        self.runinfofile = runConfigParser.get('BASIC', 'runinfofile')
        self._runlogkeyprefix = runConfigParser.get('BASIC', 'runlog_key_prefix')
        self.runplaninfofile = runConfigParser.get('BASIC', 'runplaninfofile')

    def LoadRunInfo(self):
        self.RunInfo = {}
        try:
            f = open(self.runinfofile, "r")
            data = json.load(f)
            f.close()
            self.allRunKeys = copy.deepcopy(data.keys())
            loaderror = False
        except IOError:
            print "\n-------------------------------------------------"
            print "WARNING: unable to load json file:\n\t{file}".format(file=self.runinfofile)
            print "-------------------------------------------------\n"
            loaderror = True

        if self.run_number >= 0:
            if not loaderror:
                self.RunInfo = data.get(str(self.run_number)) # may:  = data.get("150800"+str(self.run_number).zfill(3))
                if self.RunInfo == None:
                    # try with run_log key prefix
                    self.RunInfo = data.get(self._runlogkeyprefix+str(self.run_number).zfill(3))
                if self.RunInfo == None:
                    print "INFO: Run not found in json run log file. Default run info will be used."
                    self.RunInfo = default_info
                else:
                    self.RenameRunInfoKeys()
            else:
                self.RunInfo = default_info
            self.current_run = self.RunInfo
        else:
            self.RunInfo = default_info
            return 0

    def CreateROOTFile(self, do_tracking=True):

        rawFolder = "/data/psi_2015_08/raw"
        rawPrefix = "run15080"
        eudaqFolder = "/home/testbeam/testing/mario/eudaq-drs4"
        trackingFolder = "/home/testbeam/sdvlp/TrackingTelescope"

        converter_cmd = "{eudaq}/bin/Converter.exe -t drs4tree -c {eudaq}/conf/converter.conf {rawfolder}/{prefix}{run}.raw".format(eudaq=eudaqFolder, rawfolder=rawFolder, prefix=rawPrefix, run=str(self.run_number).zfill(4))
        print "\n\nSTART CONVERTING RAW FILE..."
        print converter_cmd
        os.system(converter_cmd)

        noTracksROOTFile = eudaqFolder+"/bin/test{prefix}{run}.root".format(prefix=rawPrefix, run=str(self.run_number).zfill(4))
        if not do_tracking:
            # move to data folder:
            os.system("mv "+noTracksROOTFile+" "+self.TrackingPadAnalysis['ROOTFile'])
            self._LoadROOTFile(self.TrackingPadAnalysis['ROOTFile'])
            print "INFO ROOT File generated with NO Tracking information"

        if self.TESTCAMPAIGN == "201508":
            tracking_cmd_number = 9
        elif self.TESTCAMPAIGN == "201505":
            tracking_cmd_number = 7
        else:
            tracking_cmd_number = 0
            assert(False), "Error. unknown TESTCAMPAIGN"

        tracking_cmd = "{trackingfolder}/TrackingTelescope {root} 0 {nr}".format(trackingfolder=trackingFolder, root=noTracksROOTFile, nr=tracking_cmd_number)
        print "\n\nSTART TRACKING..."
        print tracking_cmd
        os.system(tracking_cmd)

        tracksROOTFile = trackingFolder+"/test{prefix}{run}_withTracks.root"

        # move to data folder:
        os.system("mv "+tracksROOTFile+" "+self.TrackingPadAnalysis['ROOTFile'])

        # delete no tracks file:
        os.system("rm "+noTracksROOTFile)


    def _LoadTiming(self):
        try:
            self.logStartTime = dt.strptime(self.RunInfo["start time"][:10]+"-"+self.RunInfo["start time"][11:-1], "%Y-%m-%d-%H:%M:%S")
            self.logStopTime = dt.strptime(self.RunInfo["stop time"][:10]+"-"+self.RunInfo["stop time"][11:-1], "%Y-%m-%d-%H:%M:%S")
            self.logRunTime = self.logStopTime - self.logStartTime
            noerror = True
        except:
            try:
                self.logStartTime = dt.strptime(self.RunInfo["start time"][:10]+"-"+self.RunInfo["start time"][11:-1], "%H:%M:%S")
                self.logStopTime = dt.strptime(self.RunInfo["stop time"][:10]+"-"+self.RunInfo["stop time"][11:-1], "%H:%M:%S")
                self.logRunTime = self.logStopTime - self.logStartTime
                noerror = True
            except:
                noerror = False
        if noerror:
            self.VerbosePrint("Timing string translated successfully")
        else:
            print "INFO: The timing information string from run info couldn't be translated"


    def RenameRunInfoKeys(self):

        try:
            for key in default_info.keys():
                tmp = self.RunInfo[key]
                del tmp
        except KeyError:
            rename = True
        else:
            rename = False

        if rename:
            KeyConfigParser = ConfigParser.ConfigParser()
            KeyConfigParser.read("Configuration/RunInfoKeyConfig_"+self.TESTCAMPAIGN+".cfg")
            Persons =           KeyConfigParser.get("KEYNAMES", "Persons")
            Runinfo =           KeyConfigParser.get("KEYNAMES", "Runinfo")
            Typ =               KeyConfigParser.get("KEYNAMES", "Typ")
            Configuration =     KeyConfigParser.get("KEYNAMES", "Configuration")
            Mask =              KeyConfigParser.get("KEYNAMES", "Mask")
            Masked_pixels =     KeyConfigParser.get("KEYNAMES", "Masked_pixels")
            DiamondName1 =      KeyConfigParser.get("KEYNAMES", "DiamondName1")
            DiamondName2 =      KeyConfigParser.get("KEYNAMES", "DiamondName2")
            DiamondHV1 =        KeyConfigParser.get("KEYNAMES", "DiamondHV1")
            DiamondHV2 =        KeyConfigParser.get("KEYNAMES", "DiamondHV2")
            FOR1 =              KeyConfigParser.get("KEYNAMES", "FOR1")
            FOR2 =              KeyConfigParser.get("KEYNAMES", "FOR2")
            FS11 =              KeyConfigParser.get("KEYNAMES", "FS11")
            FSH13 =             KeyConfigParser.get("KEYNAMES", "FSH13")
            Quadrupole =        KeyConfigParser.get("KEYNAMES", "Quadrupole")
            AnalogCurrent =     KeyConfigParser.get("KEYNAMES", "AnalogCurrent")
            DigitalCurrent =    KeyConfigParser.get("KEYNAMES", "DigitalCurrent")
            BeginDate =         KeyConfigParser.get("KEYNAMES", "BeginDate")
            TrimTime =          KeyConfigParser.get("KEYNAMES", "TrimTime")
            ConfigTime =        KeyConfigParser.get("KEYNAMES", "ConfigTime")
            StartTime =         KeyConfigParser.get("KEYNAMES", "StartTime")
            TrigAcceptTime =    KeyConfigParser.get("KEYNAMES", "TrigAcceptTime")
            OpeningTime =       KeyConfigParser.get("KEYNAMES", "OpeningTime")
            OpenTime =          KeyConfigParser.get("KEYNAMES", "OpenTime")
            StopTime =          KeyConfigParser.get("KEYNAMES", "StopTime")
            RawRate =           KeyConfigParser.get("KEYNAMES", "RawRate")
            PrescaledRate =     KeyConfigParser.get("KEYNAMES", "PrescaledRate")
            ToTLURate =         KeyConfigParser.get("KEYNAMES", "ToTLURate")
            PulserAcceptedRate =KeyConfigParser.get("KEYNAMES", "PulserAcceptedRate")
            CMSPixelEvents =    KeyConfigParser.get("KEYNAMES", "CMSPixelEvents")
            DRS4Events =        KeyConfigParser.get("KEYNAMES", "DRS4Events")
            DataCollectorEvents = KeyConfigParser.get("KEYNAMES", "DataCollectorEvents")
            AimedFlux =         KeyConfigParser.get("KEYNAMES", "AimedFlux")
            MeasuredFlux =      KeyConfigParser.get("KEYNAMES", "MeasuredFlux")
            UserComment =       KeyConfigParser.get("KEYNAMES", "UserComment")
            IsGoodRun =         KeyConfigParser.get("KEYNAMES", "IsGoodRun")

            runinfo = copy.deepcopy(default_info)
            print self.RunInfo

            if Persons != "-1":             runinfo["persons on shift"] =   self.RunInfo[Persons]
            if Runinfo != "-1":             runinfo["run info"] =           self.RunInfo[Runinfo]
            if Typ != "-1":                 runinfo["type"] =               self.RunInfo[Typ]
            if Configuration != "-1":       runinfo["configuration"] =      self.RunInfo[Configuration]
            if Mask != "-1":                runinfo["mask"] =               self.RunInfo[Mask]
            if Masked_pixels != "-1":       runinfo["masked pixels"] =      self.RunInfo[Masked_pixels]
            if DiamondName1 != "-1":        runinfo["diamond 1"] =          self.RunInfo[DiamondName1]
            if DiamondName2 != "-1":        runinfo["diamond 2"] =          self.RunInfo[DiamondName2]
            if DiamondHV1 != "-1":          runinfo["hv dia1"] =            self.RunInfo[DiamondHV1]
            if DiamondHV2 != "-1":          runinfo["hv dia2"] =            self.RunInfo[DiamondHV2]
            if FOR1 != "-1":                runinfo["for1"] =               self.RunInfo[FOR1]
            if FOR2 != "-1":                runinfo["for2"] =               self.RunInfo[FOR2]
            if FS11 != "-1":                runinfo["fs11"] =               self.RunInfo[FS11]
            if FSH13 != "-1":               runinfo["fsh13"] =              self.RunInfo[FSH13]
            if Quadrupole != "-1":          runinfo["quadrupole"] =         self.RunInfo[Quadrupole]
            if AnalogCurrent != "-1":       runinfo["analogue current"] =   self.RunInfo[AnalogCurrent]
            if DigitalCurrent != "-1":      runinfo["digital current"] =    self.RunInfo[DigitalCurrent]
            if BeginDate != "-1":           runinfo["begin date"] =         self.RunInfo[BeginDate]
            if TrimTime != "-1":            runinfo["trim time"] =          self.RunInfo[TrimTime]
            if ConfigTime != "-1":          runinfo["config time"] =        self.RunInfo[ConfigTime]
            if StartTime != "-1":           runinfo["start time"] =         self.RunInfo[StartTime]
            if TrigAcceptTime != "-1":      runinfo["trig accept time"] =   self.RunInfo[TrigAcceptTime]
            if OpeningTime != "-1":         runinfo["opening time"] =       self.RunInfo[OpeningTime]
            if OpenTime != "-1":            runinfo["open time"] =          self.RunInfo[OpenTime]
            if StopTime != "-1":            runinfo["stop time"] =          self.RunInfo[StopTime]
            if RawRate != "-1":             runinfo["raw rate"] =           self.RunInfo[RawRate]
            if PrescaledRate != "-1":       runinfo["prescaled rate"] =     self.RunInfo[PrescaledRate]
            if ToTLURate != "-1":           runinfo["to TLU rate"] =        self.RunInfo[ToTLURate]
            if PulserAcceptedRate != "-1":  runinfo["pulser accept rate"] = self.RunInfo[PulserAcceptedRate]
            if CMSPixelEvents != "-1":      runinfo["cmspixel events"] =    self.RunInfo[CMSPixelEvents]
            if DRS4Events != "-1":          runinfo["drs4 events"] =        self.RunInfo[DRS4Events]
            if DataCollectorEvents != "-1": runinfo["datacollector events"]=self.RunInfo[DataCollectorEvents]
            if AimedFlux != "-1":           runinfo["aimed flux"] =         self.RunInfo[AimedFlux]
            if MeasuredFlux != "-1":        runinfo["measured flux"] =      self.RunInfo[MeasuredFlux]
            if UserComment != "-1":         runinfo["user comments"] =      self.RunInfo[UserComment]
            if IsGoodRun != "-1":           runinfo["is good run"] =        self.RunInfo[IsGoodRun]

            self.RunInfo = runinfo

    def ValidateRuns(self, list_of_runs = None):
        if list_of_runs != None:
            runs = list_of_runs
        else:
            runs = RunInfo.runs.keys() # list of all runs
        self.VerbosePrint("Validating runs: ",runs)
        for run in runs:
            self.ValidateRun(run)

    def ValidateRun(self,run_number):
        self.SetRun(run_number)
        if not os.path.exists(self.TrackingPadAnalysis['ROOTFile']):
            #del RunInfo.runs[run_number]
            print "INFO: path of run number ",run_number, " not found."
            return False
        else:
            return True

    def ResetMC(self):
        pass

    def SetRun(self, run_number, validate = False, loadROOTFile = True):
        if validate:
            boolfunc = self.ValidateRun
        else:
            boolfunc = lambda run: True
        assert(run_number > 0), "incorrect run_number"
        if True or run_number in RunInfo.runs and boolfunc(run_number):
            self.run_number = run_number
            self.LoadRunInfo()

            if self.operationmode == "local-ssh":
                fullROOTFilePath = '/Volumes'+self.sshrunpath+'/'+self.filename+str(run_number).zfill(3)+'.root'
                self.TrackingPadAnalysis['ROOTFile'] = fullROOTFilePath

            if self.operationmode == "ssh":
                fullROOTFilePath = self.sshrunpath+'/'+self.filename+str(run_number).zfill(3)+'.root'
                self.TrackingPadAnalysis['ROOTFile'] = fullROOTFilePath

            if self.operationmode == "local":
                self.TrackingPadAnalysis['ROOTFile'] = 'runs/run_'+str(run_number)+'/'+self.filename+str(run_number).zfill(3)+'.root'


 #           self.RunInfo = self.current_run.copy()
            #a = self.current_run.__dict__
#            self.diamond = Diamond( self.current_run['diamond'])

            self.ResetMC()
            #self.diamond = diamond # diamond is of type Diamond
            #RunInfo.__init__(self,*args)

            if loadROOTFile:
                self._LoadROOTFile(fullROOTFilePath)

            #self.diamond.SetName(self.runs[0]['diamond'])
            return True
        else:
            return False

    def SetChannels(self, diamonds):
        assert(diamonds>=1 and diamonds<=3), "invalid diamonds number: 0x1=ch0; 0x2=ch3"
        self.analyzeCh = {
            0: self._GetBit(diamonds, 0),
            3: self._GetBit(diamonds, 1)
        }

    def GetChannels(self):
        return [i for i in self.analyzeCh.keys() if self.analyzeCh[i]]

    def GetDiamondName(self, channel):
        return self.diamondname[channel]

    def ShowRunInfo(self):
        print "RUN INFO:"
        print "\tRun Number: \t", self.run_number, " (",self.RunInfo["type"],")"
        print "\tDiamond1:   \t", self.diamondname[0], " (",self.bias[0],") | is selected: ", self.analyzeCh[0]
        print "\tDiamond2:   \t", self.diamondname[3], " (",self.bias[3],") | is selected: ", self.analyzeCh[3]

    def DrawRunInfo(self, channel=None, canvas=None, diamondinfo=True, showcut=False, comment=None, infoid="", userWidth=None, userHeight=None):
        if userHeight!= None: assert(userHeight>=0 and userHeight<=0.8), "choose userHeight between 0 and 0.8 or set it to 'None'"
        if userWidth!= None: assert(userWidth>=0 and userWidth<=0.8), "choose userWidth between 0 and 0.8 or set it to 'None'"
        if canvas != None:
            canvas.cd()
            pad = ROOT.gROOT.GetSelectedPad()
        else:
            print "Draw run info in current pad"
            pad = ROOT.gROOT.GetSelectedPad()
            if pad:
                # canvas = pad.GetCanvas()
                # canvas.cd()
                # pad.cd()
                pass
            else:
                print "ERROR: Can't access active Pad"

        lines = 1
        width = 0.25
        if diamondinfo:
            lines += 1
        if showcut and hasattr(self, "analysis"):
            lines += 1
            width = 0.6
        if comment != None:
            lines += 1
            width = max(0.4, width)
        height = (lines-1)*0.03

        if not hasattr(self, "_runInfoLegends"):
            self._runInfoLegends = {}

        if channel != None and channel in [0,3]:
            # user height and width:
            userheight = height if userHeight==None else userHeight - 0.04
            userwidth = width if userWidth==None else userWidth

            self._runInfoLegends[str(channel)+infoid] = ROOT.TLegend(0.1, 0.86-userheight, 0.1+userwidth, 0.9)
            self._runInfoLegends[str(channel)+infoid].SetMargin(0.05)
            self._runInfoLegends[str(channel)+infoid].AddEntry(0, "Run{run} Ch{channel} ({rate})".format(run=self.run_number, channel=channel, rate=self._GetRateString()), "")
            if diamondinfo: self._runInfoLegends[str(channel)+infoid].AddEntry(0, "{diamond} ({bias:+}V)".format(diamond=self.diamondname[channel], bias=self.bias[channel]), "")
            if showcut and hasattr(self, "analysis"): self._runInfoLegends[str(channel)+infoid].AddEntry(0, "Cut: {cut}".format(cut=self.analysis.cut.format(channel=channel)), "")
            if comment != None: self._runInfoLegends[str(channel)+infoid].AddEntry(0, comment, "")
            self._runInfoLegends[str(channel)+infoid].Draw("same")
        else:
            if comment != None:
                lines = 2
            else:
                lines = 1
                width = 0.15
            height = lines*0.05
            # user height and width:
            userheight = height if userHeight==None else userHeight
            userwidth = width if userWidth==None else userWidth

            self._runInfoLegends["ch12"+infoid] = ROOT.TLegend(0.1, 0.9-userheight, 0.1+userwidth, 0.9)
            self._runInfoLegends["ch12"+infoid].SetMargin(0.05)
            self._runInfoLegends["ch12"+infoid].AddEntry(0, "Run{run} ({rate})".format(run=self.run_number, rate=self._GetRateString()), "")
            if comment != None: self._runInfoLegends["ch12"+infoid].AddEntry(0, comment, "")
            self._runInfoLegends["ch12"+infoid].Draw("same")
            pad.Modified()

    def _GetRateString(self):
        rate = self.RunInfo["measured flux"]
        if rate>1000:
            unit = "MHz"
            rate = round(rate/1000.,1)
        else:
            unit = "kHz"
            rate = int(round(rate,0))
        return "{rate:>3}{unit}".format(rate=rate, unit=unit)

    def GetChannelName(self, channel):
        self.tree.GetEntry(1)
        return self.tree.sensor_name[channel]

    def _LoadROOTFile(self, fullROOTFilePath):
        print "LOADING: ", fullROOTFilePath
        self.rootfile = ROOT.TFile(fullROOTFilePath)
        self.tree = self.rootfile.Get(self.treename) # Get TTree called "track_info"
        if not (bool(self.tree) and bool(self.rootfile)):
            print "\n\nCould not load root file!"
            print "\t>> "+fullROOTFilePath
            answer = raw_input("generate ROOT file instead? (y/n): ")
            if answer == "y":
                tracking = raw_input("generate tracking information? (y/n): ")
                if tracking == "y":
                    self.CreateROOTFile()
                else:
                    self.CreateROOTFile(do_tracking=False)
        #assert(bool(self.tree) and bool(self.rootfile)), "Could not load root file: \n\t"+fullROOTFilePath
