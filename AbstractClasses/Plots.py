# ==============================================
# IMPORTS
# ==============================================
from ROOT import TGraphErrors, TCanvas, TH1D, TH2D, gStyle, TH1F, gROOT, gErrorIgnoreLevel, kError,TLegend, TCut, TGraph, TProfile2D, TH2F, TProfile, TCutG, kRed, kBlack, kPink, kBlue, kViolet ,kMagenta, kTeal, kGreen, kOrange, TF1, TPie, gPad, TLatex, THStack
# from TelescopeAnalysis import Analysis
# from CurrentInfo import Currents
# from numpy import array
from math import sqrt, ceil, log
from Elementary import Elementary
import os
# from argparse import ArgumentParser
# from Extrema import Extrema2D
# from ChannelCut import ChannelCut
# from time import time, sleep
# from collections import OrderedDict
# from sys import stdout
from copy import deepcopy

__author__ = 'DA'


# ==============================================
# MAIN CLASS
# ==============================================

class Plots(Elementary):
    def __init__(self, num_entries, run=None, num_devices=7, binning=-1, roc_tel=[0,1,2,3], roc_d1=4, roc_d2=5, roc_si=6):
        Elementary.__init__(self)
        # gStyle.SetPalette(53)  # kDarkBodyRadiator
        gStyle.SetPalette(55)  # kRainBow
        gStyle.SetNumberContours(999)
        self.run = run
        self.runinfo = self.run.RunInfo
        self.binning = binning
        self.num_devices = num_devices
        self.num_entries = num_entries
        self.plot_settings = {
            'ph1DbinsD4': 80,
            'ph1DminD4': 0,
            'ph1DmaxD4': 30000,
            'ph1DbinsD5': 80,
            'ph1DminD5': 0,
            'ph1DmaxD5': 60000,
            'ph1DbinsSi': 160,
            'ph1DminSi': 0,
            'ph1DmaxSi': 90000,
            'nEventsAv': 20000,
            'event_bins': max(int(ceil(float(self.num_entries)/10)), 200),
            'event_min': 0,
            'event_max': self.num_entries,
            'maxphplots': int(ceil(8*self.num_entries/100)),  ## for landau histograms histograms
            'nBinsX': 52,  #80 # 277 #240
            'xmin': -3900,
            'xmax': 3900,
            'nBinsY': 80,  #120 # 415 #360
            'ymin': -4000,
            'ymax': 4000,
            'nBinCol': 51,
            'minCol': 0,
            'maxCol': 51,
            'nBinRow': 79,
            'minRow': 0,
            'maxRow': 79,
            'num_diff_cluster_sizes': 4,
            'chi2_1Dbins': 60,
            'chi2_1Dmin': 0,
            'chi2_1Dmax': 30,
            'angle_1Dbins': 60,
            'angle_1Dmin': -3,
            'angle_1Dmax': 3,
            'rhit_1Dbins': 100,
            'rhit_1Dmin': 0,
            'rhit_1Dmax': 10
        }
        self.plot_settings['event_bins'] = int(ceil(float(self.num_entries)/5000)) if self.num_entries <= 100000 else \
            int(ceil(float(self.num_entries)/100)) if self.num_entries <= 500000 else int(ceil(float(self.num_entries)/self.plot_settings['nEventsAv']))
        self.plot_settings['deltaX'] = float(self.plot_settings['xmax']-self.plot_settings['xmin'])/self.plot_settings['nBinsX']
        self.plot_settings['deltaY'] = float(self.plot_settings['ymax']-self.plot_settings['ymin'])/self.plot_settings['nBinsY']
        self.roc_tel, self.roc_d1, self.roc_d2, self.roc_si = roc_tel, roc_d1, roc_d2, roc_si
        self.save_dir = './'

    def create_TGraphErrors(self, title='tgraph', xTitle='X', yTitle='Y', linecolor=kBlack, markercolor=kBlack):
        graph = TGraphErrors()
        graph.SetNameTitle(title,title)
        graph.SetLineColor(linecolor)
        graph.SetMarkerColor(markercolor)
        graph.GetXaxis().SetTitle(xTitle)
        graph.GetYaxis().SetTitle(yTitle)
        return (graph)

    def create_1D_histogram(self, type='landau', name='histo', title='histo', xTitle='X', yTitle='Y', color=kBlack, min_val=0, roc=4):
        if type is 'landau' or type is 'landaus':
            ph1Dbins = self.plot_settings['ph1DbinsD4'] if roc is self.roc_d1 else self.plot_settings['ph1DbinsD5'] if roc is self.roc_d2 else self.plot_settings['ph1DbinsSi']
            ph1Dmin = self.plot_settings['ph1DminD4'] if roc is self.roc_d1 else self.plot_settings['ph1DminD5'] if roc is self.roc_d2 else self.plot_settings['ph1DminSi']
            ph1Dmax = self.plot_settings['ph1DmaxD4'] if roc is self.roc_d1 else self.plot_settings['ph1DmaxD5'] if roc is self.roc_d2 else self.plot_settings['ph1DmaxSi']
        elif type is 'chi2':
            ph1Dbins = self.plot_settings['chi2_1Dbins']
            ph1Dmin = self.plot_settings['chi2_1Dmin']
            ph1Dmax = self.plot_settings['chi2_1Dmax']
        elif type is 'angle':
            ph1Dbins = self.plot_settings['angle_1Dbins']
            ph1Dmin = self.plot_settings['angle_1Dmin']
            ph1Dmax = self.plot_settings['angle_1Dmax']
        elif type is 'rhit':
            ph1Dbins = self.plot_settings['rhit_1Dbins']
            ph1Dmin = self.plot_settings['rhit_1Dmin']
            ph1Dmax = self.plot_settings['rhit_1Dmax']
        histo1D = TH1D(name, title, int(ph1Dbins + 1), ph1Dmin - float(ph1Dmax - ph1Dmin)/(2*ph1Dbins),
                       ph1Dmax + float(ph1Dmax - ph1Dmin)/(2*ph1Dbins))
        self.set_1D_options(type, histo1D, xTitle, yTitle, color, min_val)
        return (histo1D)

    def create_1D_profile(self, type='event', name='histo', title='histo', xTitle='X', yTitle='Y', color=kBlack, min_val=0, roc=4):
        nbins = int(ceil(float(self.plot_settings['event_max'] - self.plot_settings['event_min'])/self.plot_settings['nEventsAv']))
        xmin = self.plot_settings['event_min']
        xmax = self.plot_settings['event_max']
        histo1D = TProfile(name, title, int(nbins + 1), xmin - float(xmax - xmin)/(2*nbins), xmax + float(xmax - xmin)/(2*nbins))
        self.set_1D_options(type, histo1D, xTitle, yTitle, color, min_val, roc)
        return (histo1D)

    def set_1D_options(self, type='event', histo='histo', xTitle='X', yTitle='Y', color=kBlack, min_val=0, roc=4):
        histo.GetXaxis().SetTitle(xTitle)
        histo.GetYaxis().SetTitle(yTitle)
        histo.GetYaxis().SetTitleOffset(1.3)
        if type is 'event':
            if roc is self.roc_d1:
                histo.SetMaximum(self.plot_settings['ph1DmaxD4'])
            elif roc is self.roc_d2:
                histo.SetMaximum(self.plot_settings['ph1DmaxD5'])
            else:
                histo.SetMaximum(self.plot_settings['ph1DmaxSi'])
        histo.SetMinimum(min_val)
        histo.SetLineColor(color)
        histo.SetLineWidth(3*gStyle.GetLineWidth())
        if type is 'landaus':
            histo.SetFillColor(color)

    def create_2D_profile(self, type='spatial', name='histo', title='histo', xTitle='X', yTitle='Y', zTitle='Z', min_val=0, max_val=-1):
        xbins = self.plot_settings['nBinsX'] if type is 'spatial' else self.plot_settings['nBinCol']
        xmin = self.plot_settings['xmin'] if type is 'spatial' else self.plot_settings['minCol']
        xmax = self.plot_settings['xmax'] if type is 'spatial' else self.plot_settings['maxCol']
        ybins = self.plot_settings['nBinsY'] if type is 'spatial' else self.plot_settings['nBinRow']
        ymin = self.plot_settings['ymin'] if type is 'spatial' else self.plot_settings['minRow']
        ymax = self.plot_settings['ymax'] if type is 'spatial' else self.plot_settings['maxRow']
        histo2D = TProfile2D(name, title, int(xbins + 1), xmin - float(xmax-xmin)/(2*xbins),
                             xmax + float(xmax-xmin)/(2*xbins), int(ybins + 1), ymin - float(ymax-ymin)/(2*ybins),
                             ymax + float(ymax-ymin)/(2*ybins))
        self.set_2D_options(histo2D, xTitle, yTitle, zTitle, min_val, max_val)
        return histo2D

    def create_2D_histogram(self, type='spatial', name='histo', title='histo', xTitle='X', yTitle='Y', zTitle='Z', min_val=0, max_val=-1, roc=4):
        if type is 'spatial':
            xbins = self.plot_settings['nBinsX']
            xmin = self.plot_settings['xmin']
            xmax = self.plot_settings['xmax']
            ybins = self.plot_settings['nBinsY']
            ymin = self.plot_settings['ymin']
            ymax = self.plot_settings['ymax']
        elif type is 'pixel':
            xbins = self.plot_settings['nBinCol']
            xmin = self.plot_settings['minCol']
            xmax = self.plot_settings['maxCol']
            ybins = self.plot_settings['nBinRow']
            ymin = self.plot_settings['minRow']
            ymax = self.plot_settings['maxRow']
        elif type is 'correlpixcol':
            xbins = self.plot_settings['nBinCol']
            xmin = self.plot_settings['minCol']
            xmax = self.plot_settings['maxCol']
            ybins = self.plot_settings['nBinCol']
            ymin = self.plot_settings['minCol']
            ymax = self.plot_settings['maxCol']
        elif type is 'correlpixx':
            xbins = self.plot_settings['nBinsX']
            xmin = self.plot_settings['xmin']
            xmax = self.plot_settings['xmax']
            ybins = self.plot_settings['nBinsX']
            ymin = self.plot_settings['xmin']
            ymax = self.plot_settings['xmax']
        elif type is 'correlpixrow':
            xbins = self.plot_settings['nBinRow']
            xmin = self.plot_settings['minRow']
            xmax = self.plot_settings['maxRow']
            ybins = self.plot_settings['nBinRow']
            ymin = self.plot_settings['minRow']
            ymax = self.plot_settings['maxRow']
        elif type is 'correlpixy':
            xbins = self.plot_settings['nBinsY']
            xmin = self.plot_settings['ymin']
            xmax = self.plot_settings['ymax']
            ybins = self.plot_settings['nBinsY']
            ymin = self.plot_settings['ymin']
            ymax = self.plot_settings['ymax']
        else:
            xbins = self.plot_settings['event_bins']
            xmin = self.plot_settings['event_min']
            xmax = self.plot_settings['event_max']
            ybins = self.plot_settings['ph1DbinsD4'] if roc is self.roc_d1 else self.plot_settings['ph1DbinsD5'] if roc is self.roc_d2 else self.plot_settings['ph1DbinsSi']
            ymin = self.plot_settings['ph1DminD4'] if roc is self.roc_d1 else self.plot_settings['ph1DminD5'] if roc is self.roc_d2 else self.plot_settings['ph1DminSi']
            ymax = self.plot_settings['ph1DmaxD4'] if roc is self.roc_d1 else self.plot_settings['ph1DmaxD5'] if roc is self.roc_d2 else self.plot_settings['ph1DmaxSi']
        histo2D = TH2D(name, title, int(xbins + 1), xmin - float(xmax-xmin)/(2*xbins), xmax + float(xmax-xmin)/(2*xbins),
                       int(ybins + 1), ymin - float(ymax-ymin)/(2*ybins), ymax + float(ymax-ymin)/(2*ybins))
        self.set_2D_options(histo2D, xTitle, yTitle, zTitle, min_val, max_val)
        return histo2D

    def set_2D_options(self, histo, xTitle='X', yTitle='Y', zTitle='Z', min_val=0, max_val=-1):
        histo.GetXaxis().SetTitle(xTitle)
        histo.GetYaxis().SetTitle(yTitle)
        histo.GetZaxis().SetTitle(zTitle)
        histo.GetYaxis().SetTitleOffset(1.3)
        histo.GetZaxis().SetTitleOffset(1.4)
        histo.GetZaxis().CenterTitle(True)
        if min_val is not 'auto': histo.SetMinimum(min_val)
        if max_val is not -1: histo.SetMaximum(max_val)


    def save_individual_plots(self, histo, name, title, tcutg=None, draw_opt='', opt_stats=0, path='./', verbosity=False, opt_fit=0, addElem='', clone=False, doLogZ=False):
        if verbosity: self.print_banner('Saving {n}...'.format(n=name))
        gROOT.SetBatch(True)
        blabla = gROOT.ProcessLine("gErrorIgnoreLevel = {f};".format(f=kError))
        c0 = TCanvas('c_{n}'.format(n=name), title, 2100, 1500)
        c0.SetLeftMargin(0.1)
        c0.SetRightMargin(0.2)
        histo.SetStats(1)
        gStyle.SetOptFit(opt_fit)
        gStyle.SetOptStat(opt_stats)
        if addElem is not '':
            gStyle.SetStatX(0.4)
            gStyle.SetStatY(0.9)
            gStyle.SetStatW(0.15)
            gStyle.SetStatH(0.15)
        else:
            gStyle.SetStatX(0.8)
            gStyle.SetStatY(0.9)
            gStyle.SetStatW(0.15)
            gStyle.SetStatH(0.15)
        c0.cd()
        histo.Draw(draw_opt)
        if addElem is not '':
            c0.Update()
            st = c0.GetPrimitive('stats') if not clone else c0.GetPrimitive('stats')
            st.SetName('mystats') if not clone else st.SetName('mystats')
            lines = st.GetListOfLines()
            text = TLatex(0, 0, 'Correlation coef     {val}'.format(val=addElem))
            lines.Add(text)
            #st.AddText('Correlation coef     {val}'.format(val=addElem))
            histo.SetStats(0)
            st.Draw()
            c0.Modified()
        if tcutg is not None:
            tcutg.Draw('same')
        if not os.path.isdir('{dir}/Plots'.format(dir=path)):
            os.makedirs('{dir}/Plots'.format(dir=path))
        if not os.path.isdir('{dir}/Root'.format(dir=path)):
            os.makedirs('{dir}/Root'.format(dir=path))
        if doLogZ: c0.SetLogz()
        c0.Update()
        c0.Modified()
        c0.SaveAs('{dir}/Root/c_{n}.root'.format(dir=path, n=name))
        c0.SaveAs('{dir}/Plots/c_{n}.png'.format(dir=path, n=name))
        c0.Close()
        gROOT.SetBatch(False)
        if verbosity: self.print_banner('{n} save -> Done'.format(n=name))
        del c0

    def save_cuts_distributions(self, histo1, histo2, name, title, draw_opt='', opt_stats=0, path='./', verbosity=False, histo3='', doLogY=False):
        if verbosity: self.print_banner('Saving {n}'.format(n=name))
        gROOT.SetBatch(True)
        blabla = gROOT.ProcessLine("gErrorIgnoreLevel = {f};".format(f=kError))
        c0 = TCanvas('c_{n}'.format(n=name), title, 2100, 1500)
        c0.SetLeftMargin(0.1)
        c0.SetRightMargin(0.1)
        histo1.SetStats(0)
        histo2.SetStats(1)
        gStyle.SetOptStat(opt_stats)
        gStyle.SetStatX(0.8)
        gStyle.SetStatY(0.9)
        gStyle.SetStatW(0.15)
        gStyle.SetStatH(0.15)
        c0.cd()
        histo1.Draw(draw_opt)
        histo2.Draw(draw_opt+'SAME')
        if histo3 != '':
            histo3.Draw(draw_opt+'SAME')
        c0.Update()
        c0.BuildLegend(0.65, 0.7, 0.9, 0.9)
        if not os.path.isdir('{dir}/Plots'.format(dir=path)):
            os.makedirs('{dir}/Plots'.format(dir=path))
        if not os.path.isdir('{dir}/Root'.format(dir=path)):
            os.makedirs('{dir}/Root'.format(dir=path))
        if doLogY: c0.SetLogy()
        c0.Update()
        c0.Modified()
        c0.SaveAs('{dir}/Root/c_{n}.root'.format(dir=path, n=name))
        c0.SaveAs('{dir}/Plots/c_{n}.png'.format(dir=path, n=name))
        c0.Close()
        gROOT.SetBatch(False)
        if verbosity: self.print_banner('{n} save -> Done'.format(n=name))
        del c0

    def save_cuts_overlay(self, histo0, histo1, histo2, histo3, histo4, histo5, histo6, histo7, name, title, draw_opt='', opt_stats=0, path='./', verbosity=False):
        if verbosity: self.print_banner('Saving {n}'.format(n=name))
        gROOT.SetBatch(True)
        blabla = gROOT.ProcessLine("gErrorIgnoreLevel = {f};".format(f=kError))
        c0 = TCanvas('c_{n}'.format(n=name), title, 2100, 1500)
        c0.SetLeftMargin(0.1)
        c0.SetRightMargin(0.1)
        histo1.SetStats(0)
        histo2.SetStats(1)
        gStyle.SetOptStat(opt_stats)
        gStyle.SetStatX(0.8)
        gStyle.SetStatY(0.9)
        gStyle.SetStatW(0.15)
        gStyle.SetStatH(0.15)
        c0.cd()
        s1 = THStack('s_{n}'.format(n=name), 's_{n}'.format(n=name))
        s1.Add(histo0)
        s1.Add(histo1)
        s1.Add(histo2)
        s1.Add(histo3)
        s1.Add(histo4)
        s1.Add(histo5)
        s1.Add(histo6)
        s1.Add(histo7)
        s1.Draw('nostack')
        c0.Update()
        c0.SetLogy()
        c0.BuildLegend(0.65, 0.7, 0.9, 0.9)
        if not os.path.isdir('{dir}/Plots'.format(dir=path)):
            os.makedirs('{dir}/Plots'.format(dir=path))
        if not os.path.isdir('{dir}/Root'.format(dir=path)):
            os.makedirs('{dir}/Root'.format(dir=path))
        c0.SaveAs('{dir}/Root/c_{n}.root'.format(dir=path, n=name))
        c0.SaveAs('{dir}/Plots/c_{n}.png'.format(dir=path, n=name))
        c0.Close()
        gROOT.SetBatch(False)
        if verbosity: self.print_banner('{n} save -> Done'.format(n=name))
        del c0

    def check_plot_existence(self, path, name):
        if os.path.isfile('{p}/Plots/{n}.png'.format(p=path, n=name)):
            return True
        else:
            return False