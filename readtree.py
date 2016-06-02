#!/usr/bin/python
from ROOT import TFile, gROOT, TGraph, TH2F, gStyle, TCanvas
from sys import argv
from numpy import mean
from sys import stdout

print argv
f = TFile(argv[1])

macro = f.Get('region_information')
regions = [str(line) for line in macro.GetListOfLines()]
channels = []
for i, line in enumerate(regions):
    if 'Sensor Names' in line:
        channels = regions[i + 1].strip(' ').split(',')
print channels
t = f.Get('tree')
histos = []
count = 0
bla = 5


def draw_waveforms(n=1000, start_event=0, cut_string=None, show=True, add_buckets=False, fixed_range=None, ch=None):
    """
    Draws stacked waveforms.
    :param n: number of waveforms
    :param cut_string:
    :param start_event: event to start
    :param show:
    :param ret_event: return number of valid events if True
    :param add_buckets: draw buckets and most probable peak values if True
    :param fixed_range: fixes x-range to given value if set
    :return: histo with waveform
    """
    gROOT.SetBatch(1)
    channel = ch
    start = start_event
    if not wf_exists(channel):
        return
    cut = cut_string
    n_events = find_n_events(n, cut, start)
    print n_events
    h = TH2F('wf', 'Waveform', 1024, 0, 1024, 1000, -500, 500)
    h.SetStats(0)
    gStyle.SetPalette(55)
    t.Draw('wf{ch}:Iteration$>>wf'.format(ch=channel), cut, 'goff', n_events, start)
    h = TGraph(t.GetSelectedRows(), t.GetV2(), t.GetV1()) if n == 1 else h
    if fixed_range is None and n > 1:
        h.GetYaxis().SetRangeUser(-500 + h.FindFirstBinAbove(0, 2) / 50 * 50, -450 + h.FindLastBinAbove(0, 2) / 50 * 50)
    elif fixed_range:
        assert type(fixed_range) is list, 'Range has to be a list!'
        h.GetYaxis().SetRangeUser(fixed_range[0], fixed_range[1])
    if show:
        gROOT.SetBatch(0)
    c = TCanvas('c', 'WaveForm', 1000, 500)
    c.SetRightMargin(.045)
    format_histo(h, x_tit='DRS4 Bin Number', y_tit='Signal [au]', markersize=.4, x_off=1, y_off=0.43)
    draw_option = 'scat' if n == 1 else 'col'
    h.Draw(draw_option)
    gROOT.SetBatch(0)
    histos.append([c, h])
    return h, n_events

def show_single_waveforms(n=1, cut='', start_event=0):
    global count
    start =  start_event + count
    activated_wfs = [wf for wf in xrange(4) if wf_exists(wf)]
    print 'activated wafeforms:', activated_wfs
    print 'Start at event number:', start
    wfs = [draw_waveforms(n=n, start_event=start, cut_string=cut, show=False, ch=wf) for wf in activated_wfs]
    n_wfs = len(activated_wfs)
    cs =  {c.GetName(): c for c in gROOT.GetListOfCanvases()}
    if not 'c_wfs' in cs:
        c = TCanvas('c_wfs', 'Waveforms', 2000, n_wfs * 500)
        c.Divide(1, n_wfs)
    else:
        c = cs['c_wfs']
    for i, wf in enumerate(wfs, 1):
        wf[0].SetTitle('{nam} WaveForm'.format(nam=channels[activated_wfs[i - 1]]))
        wf[0].GetXaxis().SetTitleSize(.06)
        wf[0].GetYaxis().SetTitleSize(.06)
        wf[0].GetXaxis().SetLabelSize(.06)
        wf[0].GetYaxis().SetLabelSize(.06)
        pad = c.cd(i)
        pad.SetMargin(.05, .05, .1, .1)
        wf[0].Draw('alp')
    histos.append([c, wfs])
    cnt = wfs[0][1]
    # if cnt is None:
    #     return
    count += cnt

def find_n_events(n_events, cut, start):
    """
    Finds the amount of events from the startevent that are not subject to the cut.
    :param n_events: number of wanted events
    :param cut:
    :param start:
    :return: actual number of events s.t. n_events are drawn
    """
    if n_events < 2:
        return find_single_event(cut, start)
    print 'Finding the correct number of events',
    n = mean([t.Draw('1', cut, 'goff', n_events, start + i * n_events) for i in xrange(4)])
    new_events = n_events
    ratio = n_events / n if n else 100
    # print '\nratio', ratio
    print
    i = 1
    while n != n_events:
        diff = n_events - n
        print n, diff, new_events
        if abs(diff) > 2 or n_events < 2:
            new_events += int(diff * ratio)
        else:
            new_events += int(diff * (ratio / i))
        # print '\b.',
        stdout.flush()
        n = t.Draw('1', cut, 'goff', new_events, start)
        i += 1
    print
    return new_events

def find_single_event(cut, start):
    n_events = t.Draw('event_number', cut, 'goff')
    evt_nmbrs = [t.GetV1()[i] for i in xrange(n_events)]
    for nr in evt_nmbrs:
        if start <= nr:
            return int(nr - start + 1)

    # print 'all cut events', all_cut_events
    # ratio = int(t.GetEntries() / float(all_cut_events) / 4.)
    # ratio = 1 if not ratio else ratio
    # new_events = ratio
    # n = t.Draw('1', cut, 'goff', new_events, start)
    # print 'Start Values:', ratio, n
    # while n != 1:
    #     diff = 1 - n
    #     print n, diff, new_events
    #     new_events += int(diff * ratio)
    #     n = t.Draw('1', cut, 'goff', new_events, start)
    # return new_events


def wf_exists(channel):
    wf_exist = True if t.FindBranch('wf{ch}'.format(ch=channel)) else False
    if not wf_exist:
        print 'The waveform for channel {ch} is not stored in the tree'.format(ch=channel)
    return wf_exist

def format_histo(histo, name='', title='', x_tit='', y_tit='', z_tit='', marker=20, color=1, markersize=1., x_off=1., y_off=1., z_off=1., lw=1, fill_color=0, stats=True):
    h = histo
    h.SetTitle(title) if title else h.SetTitle(h.GetTitle())
    h.SetName(name) if name else h.SetName(h.GetName())
    if not stats:
        h.SetStats(0)
    # markers
    try:
        h.SetMarkerStyle(marker)
        h.SetMarkerColor(color) if color is not None else h.SetMarkerColor(h.GetMarkerColor())
        h.SetMarkerSize(markersize)
    except AttributeError or ReferenceError:
        pass
    # lines/fill
    try:
        h.SetLineColor(color) if color is not None else h.SetLineColor(h.GetLineColor())
        h.SetFillColor(fill_color)
        h.SetLineWidth(lw)
    except AttributeError or ReferenceError:
        pass
    # axis titles
    try:
        h.GetXaxis().SetTitle(x_tit) if x_tit else h.GetXaxis().GetTitle()
        h.GetXaxis().SetTitleOffset(x_off)
        h.GetYaxis().SetTitle(y_tit) if y_tit else h.GetYaxis().GetTitle()
        h.GetYaxis().SetTitleOffset(y_off)
        h.GetZaxis().SetTitle(z_tit) if z_tit else h.GetZaxis().GetTitle()
        h.GetZaxis().SetTitleOffset(z_off)
    except AttributeError or ReferenceError:
        pass
