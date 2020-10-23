#!/usr/bin/env python
# --------------------------------------------------------
#       waveform analysis
# created on May 13th 2019 by M. Reichmann (remichae@phys.ethz.ch)
# --------------------------------------------------------
from ROOT import TCut, TMultiGraph
from numpy import fft
from src.sub_analysis import SubAnanlysis
from helpers.draw import *
from helpers.fit import ErfLand


class Waveform(SubAnanlysis):
    def __init__(self, pad_analysis):
        super().__init__(pad_analysis, pickle_dir='WF')
        self.NChannels = self.Run.NChannels
        self.NSamples = self.Run.NSamples
        self.Channel = self.Ana.Channel
        self.Polarity = self.Ana.Polarity

        self.Count = 0
        self.StartEvent = self.Ana.StartEvent
        self.BinWidth = self.Ana.DigitiserBinWidth

    def reset(self):
        self.Count = 0

    # ----------------------------------------
    # region GET
    def get_active(self):
        return array([wf for wf in range(self.NChannels) if self.Run.wf_exists(wf)])

    def get_binning(self, bin_size=None):
        return Bins.make(0, self.Run.NSamples * self.BinWidth, choose(bin_size, self.BinWidth))

    def get_trigger_cells(self, redo=False):
        return do_hdf5(self.make_simple_hdf5_path('TC', self.get_cut_name()), self.Run.get_root_vec, redo=redo, var='trigger_cell', cut=self.Cut(), dtype='i2')

    def get_all(self, channel=None, redo=False):
        """ extracts all dut waveforms after all cuts from the root tree and saves it as an hdf5 file """
        def f():
            self.info('Saving signal waveforms to hdf5 ...')
            waveforms = []
            events = self.Ana.get_events(cut=self.Cut())
            self.Ana.PBar.start(events.size)
            for ev in events:  # fastest found method...
                n = self.Tree.Draw('wf{}'.format(self.Channel if channel is None else channel), '', 'goff', 1, ev)
                waveforms.append(self.Ana.Polarity * self.Run.get_root_vec(n, dtype='f2'))
                self.Ana.PBar.update()
            return array(waveforms)
        return do_hdf5(self.make_simple_hdf5_path(suf=self.get_cut_name(), dut=self.Channel if channel is None else channel), f, redo=redo)

    def get_n(self):
        return self.get_all().shape[0]

    def get_cut_name(self):
        return self.Cut().GetName() if not self.Cut().GetName().startswith('All') else ''

    def get_values(self, ind=None, channel=None, n=None):
        ind = choose(ind, choose(range, ..., n, n))
        return array(self.get_all(channel=channel))[ind].flatten()

    def get_times(self, corr=True, ind=None, n=None):
        ind = choose(ind, choose(range, ..., n, n))
        return array(self.get_all_times(corr))[ind].flatten()

    def get_all_times(self, corr=False, redo=False):
        def f():
            self.info('Saving waveforms timings to hdf5 ...')
            self.PBar.start(self.get_trigger_cells().size)
            times = []
            for i, tc in enumerate(self.get_trigger_cells()):
                times.append(self.get_calibrated_times(tc).astype('f2'))
                if not i % 100:
                    self.PBar.update(i)
            self.PBar.finish()
            return array(times)
        t = do_hdf5(self.make_simple_hdf5_path('Times', self.get_cut_name()), f, redo=redo)
        peaks = self.Ana.Peaks.get_from_tree() if corr else []
        return array(t) - (peaks - peaks[0]).reshape(peaks.size, 1) if corr else t

    def get_calibrated_times(self, trigger_cell):
        return self.Run.TCalSum[trigger_cell:trigger_cell + self.Run.NSamples] - self.Run.TCalSum[trigger_cell]

    def get_calibrated_time(self, t, b):
        return self.Run.TCalSum[t + b] - self.Run.TCalSum[t]

    def get_start_event(self, start_event):
        return self.Count + self.StartEvent if start_event is None else start_event

    def get_tree_values(self, n=1, cut=None, start_event=None, t_corr=True, channel=None, raw=False):
        """ return lists of the values and times of the waveform. """
        channel = choose(channel, self.Channel)
        if not self.Run.wf_exists(channel):
            return
        start_event = self.get_start_event(start_event)
        self.info('Starting at event {}'.format(start_event))
        n_events = self.Run.find_n_events(n, self.Cut(cut), start_event)
        self.Tree.SetEstimate(n * 1024)
        n_entries = self.Tree.Draw('wf{ch}:trigger_cell'.format(ch=channel), self.Cut(cut), 'goff', n_events, start_event)
        values = self.Run.get_root_vec(n_entries)
        times = arange(self.Run.NSamples, dtype='u2') * (1 if raw else self.BinWidth)
        if t_corr:
            times = array([v for lst in [self.get_calibrated_times(int(self.Tree.GetV2()[1024 * i])) for i in range(n)] for v in lst])
        self.Tree.SetEstimate()
        self.Count += n_events
        return values, times

    def get_average_rise_time(self, p=.1, redo=False):
        return do_pickle(self.make_simple_pickle_path('RT', int(p * 100)), self.draw_average_rise_time, redo=redo, p=p, show=False)
    # endregion GET
    # ----------------------------------------

    # ----------------------------------------
    # region WAVEFORMS
    def draw(self, n=1, cut=None, start_event=None, t_corr=True, channel=None, show=True, x_range=None, y_range=None, grid=False, x=None, raw=False):
        """ Draws a stack of n waveforms. """
        start_count = deepcopy(self.Count)
        title = '{n}{tc} Waveform{p}'.format(n=n, tc=' Time Corrected' if t_corr else '', p='s' if n > 1 else '')
        values, times = self.get_tree_values(n, cut, start_event, t_corr, channel, raw)
        values = choose(x, values)
        h = self.Draw.histo_2d(times, values, [1024, 0, 512, 2048, -512, 512], title, show=False)
        y_range = ax_range(min(values), max(values), .1, .2) if y_range is None else y_range
        h = Draw.make_tgrapherrors(times, values, title=title) if n == 1 else h
        format_histo(h, x_tit='Time [ns]', y_tit='Signal [mV]', y_off=.5, stats=0, tit_size=.07, lab_size=.06, y_range=y_range, markersize=.5, x_range=x_range)
        self.Draw(h, 'WaveForms{n}'.format(n=n), show, draw_opt='col' if n > 1 else 'apl', lm=.073, rm=.045, bm=.18, w=1.5, h=.5, gridy=grid, gridx=grid)
        return h, self.Count - start_count

    def draw_all(self, corr=False, n=None, x_range=None, y_range=None, ind=None, channel=None, draw_opt=None, show=True):
        n = -1 if n is None else 1024 * n
        values, times = self.get_values(ind, channel)[:n], self.get_times(corr, ind)[:n]
        if values.size > self.Run.NSamples:
            h = self.Draw.histo_2d(times, values, [1024, 0, 512, 2048, -512, 512], 'All Waveforms', show=False)
        else:
            h = Draw.make_tgrapherrors(times, values, title='Single Waveform')
        y_range = ax_range(min(values), max(values), .1, .2) if y_range is None else y_range
        format_histo(h, x_tit='Time [ns]', y_tit='Signal [mV]', y_off=.5, stats=0, tit_size=.07, lab_size=.06, markersize=.5, x_range=x_range, y_range=y_range)
        draw_opt = draw_opt if draw_opt is not None else 'col' if values.size > self.Run.NSamples else 'ap'
        self.Draw(h, show=show, draw_opt=draw_opt, lm=.073, rm=.045, bm=.18, w=1.5, h=.5, grid=1, logz=True)
        return h, n

    def draw_single(self, cut='', event=None, ind=None, x_range=None, y_range=None, draw_opt=None, show=True, show_noise=False):
        h, n = self.draw(n=1, start_event=event, cut=cut, t_corr=True, show=show, grid=True) if ind is None else self.draw_all(False, 1, x_range, y_range, ind, draw_opt=draw_opt, show=show)
        if show_noise:
            self.__draw_noise()
        return h

    def draw_all_single(self, n=1, cut='', start_event=5000):
        activated_wfs = self.get_active()
        self.info('activated wafeforms: {}'.format(activated_wfs))
        wfs = [self.draw(n=n, start_event=start_event, cut=cut, show=False, channel=wf)[0] for wf in activated_wfs]
        c = Draw.canvas('Waveforms', w=2, h=len(wfs) * .5, divide=(1, len(wfs)))
        for i, wf in enumerate(wfs):
            format_histo(wf, title='{} WaveForm'.format(self.Run.DigitizerChannels[activated_wfs[i]]))
            Draw.histo(wf, canvas=c.cd(i + 1), draw_opt='aclp')

    def draw_bucket(self, show=True, t_corr=True, start=100000):
        good = self.draw(1, show=False, start_event=start, t_corr=t_corr)[0]
        bucket = self.draw(1, cut=self.Cut.generate_custom(invert='bucket'), show=False, start_event=start, t_corr=t_corr)[0]
        bad_bucket = self.draw(1, cut=self.Cut.get_bad_bucket(), show=False, t_corr=t_corr, start_event=start)[0]
        mg = TMultiGraph('mg_bw', 'Bucket Waveforms')
        leg = Draw.make_legend(.85, .4, nentries=3)
        names = ['good wf', 'bucket wf', 'both wf']
        for i, gr in enumerate([good, bucket, bad_bucket]):
            format_histo(gr, color=self.Draw.get_color(3), markersize=.5)
            mg.Add(gr, 'lp')
            leg.AddEntry(gr, names[i], 'lp')
        self.Draw(mg, show=show, draw_opt='A', w=1.5, h=0.75, lm=.07, rm=.045, bm=.2, leg=leg)
        format_histo(mg, x_range=ax_range(array(self.Run.IntegralRegions[self.DUT.Number - 1]['signal_e']) * self.BinWidth, None, 0, .3), y_off=.7, x_tit='Time [ns]', y_tit='Signal [mV]')
    # endregion WAVEFORMS
    # ----------------------------------------

    # ----------------------------------------
    # region AVERAGE
    def draw_all_average(self, corr=True, n=100000, ind=None, prof=True, x_range=None, y_range=None, show=True, show_noise=False, redo=False):
        def f():
            t, v = self.get_times(corr, ind, n), self.get_values(ind, n=n)
            bins = self.get_binning() + ([] if prof else self.Ana.Bins.get_pad_ph(4))
            return (self.Draw.profile if prof else self.Draw.histo_2d)(t, v, bins, '{} Waveform'.format('Averaged' if prof else 'Overlayed'), show=False)
        suf = '{}{}'.format('{}{}_'.format(ind.nonzero()[0].size if ind.dtype == bool else len(ind), ind[0]) if ind is not None else '', int(prof))
        p = do_pickle(self.make_simple_pickle_path('AWF', suf), f, redo=redo)
        x_range = ax_range(self.Ana.get_signal_range(), fl=0, fh=1) if x_range is None else x_range
        format_histo(p, x_tit='Time [ns]', y_tit='Pulse Height [mV]', y_off=1.2, stats=0, markersize=.5, x_range=x_range, y_range=y_range)
        self.Draw(p, show=show, draw_opt='' if prof else 'col')
        if show_noise:
            self.__draw_noise(pol=False)
        return p

    def fit_average(self, fit_range=None, n=3, ind=None, show=True):
        max_x = self.Ana.Timing.draw_peaks(show=0).GetListOfFunctions()[1].GetParameter(1)
        h = self.draw_all_average(show=show, ind=ind)
        fit_range = [max_x - 15, max_x + 4] if fit_range is None else fit_range
        c = ErfLand(h, fit_range=fit_range)
        c.fit(n, show)
        format_histo(h, x_range=ax_range(fit_range, fl=.5, fh=.5), stats=0)
        return c

    def draw_average_rise_time(self, p=.1, ind=None, x_range=None, y_range=None, show=True):
        h = self.draw_all_average(show=show, ind=ind, x_range=x_range, y_range=y_range)
        maxval = h.GetBinContent(h.GetMaximumBin()) - self.Ana.get_pedestal().n
        bins = [h.FindFirstBinAbove(ip * maxval) for ip in [1 - p, p]]
        coods = [(h.GetBinCenter(ib), h.GetBinContent(ib), h.GetBinCenter(ib - 1), h.GetBinContent(ib - 1), ib) for ib in bins]
        f1, f2 = [interpolate_two_points(*icood) for icood in coods]
        Draw.add(f1, f2)
        Draw.vertical_line(f1.GetX((1 - p) * maxval), -100, 1e4, name='1')
        Draw.vertical_line(f2.GetX(p * maxval), -100, 1e4, name='2')
        f1.Draw('same')
        f2.Draw('same')
        return f1.GetX((1 - p) * maxval) - f2.GetX(p * maxval)

    def compare_averages(self, ind1=None, ind2=None, x_range=None, normalise=False, show=True):
        """Compare the average waveform at two subsets, choose index ranges acordingly."""
        n = min(100000, self.get_n() // 2)
        ind1, ind2 = choose(ind1, range(n)), choose(ind2, arange(n) + self.get_n() - n)
        leg = Draw.make_legend(nentries=2, w=.25)
        graphs = [self.Draw.make_graph_from_profile(self.draw_all_average(show=False, ind=ind)) for ind in [ind1, ind2]]
        for i, g in enumerate(graphs):
            scale_graph(g, 1 / max(get_graph_y(g)).n) if normalise else do_nothing()
            x_range = ax_range(self.Ana.get_signal_range(), fl=0, fh=1) if x_range is None else x_range
            format_histo(g, color=self.Draw.get_color(2), x_tit='Peak Time [ns]', y_tit='Signal [mV]', x_range=x_range, y_off=1.2)
            leg.AddEntry(g, 'ind{}'.format(i + 1), 'l')
            g.Draw('c') if i else self.Draw(g, draw_opt='ac', show=show, leg=leg, lm=.11)
        update_canvas()

    def draw_average(self, n=100, cut=None, align_peaks=True, show=True, show_noise=False):
        (values, times), peaks = self.get_tree_values(n, self.Cut(cut)), self.get_root_vec(var=self.Ana.PeakName, cut=self.Cut(cut))[:n]
        times -= (peaks[0] - peaks).repeat(self.NSamples) if align_peaks else 0
        self.Draw.profile(times, values, self.get_binning(), 'Averaged Waveform', x_tit='Time [ns]', y_tit='Pulse Height [mv]', stats=0, markersize=.5, show=show)
        if show_noise:
            self.__draw_noise()
    # endregion AVERAGE
    # ----------------------------------------

    def __draw_noise(self, pol=True):
        c = get_last_canvas()
        mean_noise = self.Ana.Pedestal.get_mean()
        legend = Draw.make_legend(w=.1)
        c.cd()
        legend.AddEntry(Draw.horizontal_line(mean_noise.n * (self.Polarity if pol else 1), 0, 700, w=2, style=7, color=2), 'mean pedestal', 'l')
        legend.Draw()
        update_canvas()

    def draw_rise_time(self, cut=None, show=True):
        values = self.get_root_vec(var='rise_time[{}]'.format(self.Channel), cut=self.Cut(cut))
        format_statbox(all_stat=True)
        return self.Draw.distribution(values, Bins.make(0, 10, .1), 'Signal Rise Time', x_tit='Rise Time [ns]', file_name='RiseTime', show=show)

    def draw_fall_time(self, cut=None, show=True):
        values = self.get_root_vec(var='fall_time[{}]'.format(self.Channel), cut=self.Cut(cut))
        format_statbox(all_stat=True)
        return self.Draw.distribution(values, Bins.make(0, 20, .1), 'Signal Fall Time', x_tit='Fall Time [ns]', show=show)

    def draw_rise_time_map(self, res=None, cut=None, show=True):
        cut = self.Ana.Cut.generate_custom(exclude='fiducial') if cut is None else TCut(cut)
        rt, y, x = self.get_root_vec(var=['rise_time[{}]'.format(self.Channel)] + list(self.Cut.get_track_vars(self.DUT.Number - 1, mm=True)), cut=cut)
        format_statbox(entries=True, x=.84)
        p = self.Draw.prof2d(x, y, rt, self.Ana.Bins.get_global(res, mm=True), 'Rise Time Map', show=show, draw_opt='colz')
        format_histo(p, x_tit='track x [cm]', y_tit='track y [cm]', z_tit='Rise Time [ns]', ncont=20, ndivy=510, ndivx=510)
        self.Ana.draw_fid_cut()
        self.Draw.save_plots('RiseTimeMap')

    def draw_fft(self, ind):
        # TODO: finish
        values = fft.fft(self.get_values(ind))
        print(values)
