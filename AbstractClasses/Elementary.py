import re
from copy import deepcopy
from glob import glob
from shutil import copyfile
from ConfigParser import ConfigParser
from json import loads
from Utils import *
from screeninfo import get_monitors
from numpy import array, ndarray
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar
from sys import stdout
from os.path import dirname
from Draw import Draw

from ROOT import gROOT, TGraphErrors, TGaxis, TLatex, TGraphAsymmErrors, TSpectrum, TF1, TMath, TCanvas, gStyle, TLegend, TArrow, TPad, TCutG, TLine, kGreen, kOrange, kViolet, kYellow, kRed, kBlue, \
    kMagenta, kAzure, kCyan, kTeal

# global test campaign and resolution
tc = None
res = None


class Elementary(Draw):
    """
    The Elementary class provides default behaviour objects in the analysis framework and is the Mother of all myPadAnalysis objects.
    It provides, among other things, a verbose printing method or a save plot method containing a global save directory handling.
    """

    def __init__(self, testcampaign=None, verbose=False, resolution=None):

        self.verbose = verbose

        self.Dir = self.get_program_dir()
        self.MainConfigParser = self.load_main_config()
        Draw.__init__(self, config=self.MainConfigParser, prog_dir=self.Dir)

        # test campaign
        self.TESTCAMPAIGN = None
        self.SubSet = None
        self.set_global_testcampaign(testcampaign)
        self.TCString = self.generate_tc_str()
        self.ResultsDir = self.generate_results_directory()

        # read configuration files
        self.run_config_parser = self.load_run_config()
        self.ana_config_parser = self.load_ana_config()

        self.PickleDir = join(self.Dir, self.MainConfigParser.get('SAVE', 'pickle_dir'))
        self.DataDir = self.MainConfigParser.get('MAIN', 'data_dir')
        self.TCDir = self.generate_tc_directory()
        self.Felix = self.MainConfigParser.getboolean('SAVE', 'felix')
        self.set_titles()

        # progress bar
        self.Widgets = ['Progress: ', Percentage(), ' ', Bar(marker='>'), ' ', ETA(), ' ', FileTransferSpeed()]
        self.ProgressBar = None

        # screen resolution
        self.Res = self.load_resolution(resolution)

        # container for the ROOT objects
        self.ROOTObjects = []

        # colors
        self.count = 0
        self.colors = self.create_colorlist()
        self.FillColor = 821
        gStyle.SetLegendFont(42)

    # ============================================

    def load_main_config(self):
        parser = ConfigParser()
        parser.read(join(self.Dir, 'Configuration', 'main.ini'))
        return parser

    def load_run_config(self):
        run_parser = ConfigParser({'excluded_runs': '[]'})
        run_parser.read('Configuration/RunConfig_{tc}.cfg'.format(tc=self.TCString))
        return run_parser

    def load_run_configs(self, run_number):
        run_parser = ConfigParser({'excluded_runs': '[]'})
        # set run_number to zero if none is given to prevent crash
        run_number = 0 if run_number is None else run_number
        if self.MainConfigParser.has_section(self.TCString):
            split_runs = [0] + loads(self.MainConfigParser.get(self.TCString, 'split_runs')) + [int(1e10)]
            for i in xrange(1, len(split_runs)):
                if split_runs[i - 1] <= run_number < split_runs[i]:
                    config = '{dir}/Configuration/RunConfig_{tc}_{i}.cfg'.format(dir=self.get_program_dir(), tc=self.TCString, i=i)
                    run_parser.read(config)
                    break
        else:
            run_parser.read(join(self.Dir, 'Configuration', 'RunConfig_{tc}.cfg'.format(tc=self.TCString)))
        return run_parser

    def load_ana_config(self):
        ana_parser = ConfigParser()
        ana_parser.read('Configuration/AnalysisConfig_{tc}.cfg'.format(tc=self.TCString))
        return ana_parser

    @staticmethod
    def load_resolution(resolution):
        if resolution is not None:
            global res
            res = resolution
        if res is not None:
            return round_down_to(res, 500)
        else:
            try:
                m = get_monitors()
                return round_down_to(m[0].height, 500)
            except Exception as err:
                log_warning(err)
                return 1000

    def load_mask_file_dir(self):
        if self.run_config_parser.has_option('BASIC', 'maskfilepath'):
            file_path = self.run_config_parser.get('BASIC', 'maskfilepath')
        else:
            file_path = join(self.DataDir, self.TCDir, 'masks')
        if not dir_exists(file_path):
            log_warning('Did not file mask file directory!')
        return file_path

    def load_run_info_path(self):
        if self.run_config_parser.has_option('BASIC', 'runinfofile'):
            file_path = self.run_config_parser.get('BASIC', 'runinfofile')
        else:
            file_path = join(self.DataDir, self.TCDir, 'run_log.json')
        if not file_exists(file_path):
            log_critical('Run Log File: "{f}" does not exist!'.format(f=file_path))
        return file_path

    def generate_sub_set_str(self):
        return '-{0}'.format(self.SubSet) if self.SubSet is not None else ''

    def generate_tc_str(self):
        return '{tc}{s}'.format(tc=self.TESTCAMPAIGN, s=self.generate_sub_set_str())

    def generate_tc_directory(self):
        return 'psi_{y}_{m}{s}'.format(y=self.TESTCAMPAIGN[:4], m=self.TESTCAMPAIGN[-2:], s=self.generate_sub_set_str())

    def generate_results_directory(self):
        return join(self.Dir, 'Results{tc}{s}'.format(tc=self.TESTCAMPAIGN, s=self.generate_sub_set_str()))

    def set_global_testcampaign(self, testcampaign):
        if testcampaign is not None:
            global tc
            tc = testcampaign
        self.set_test_campaign(tc)

    def set_test_campaign(self, campaign):
        campaign = self.MainConfigParser.get('MAIN', 'default_test_campaign') if campaign is None else campaign
        if campaign not in self.find_test_campaigns():
            log_critical('The Testcampaign {tc} does not exist yet! Use create_new_testcampaign!'.format(tc=campaign))
        tc_data = str(campaign).split('-')
        self.TESTCAMPAIGN = tc_data[0]
        self.SubSet = tc_data[-1] if len(tc_data) > 1 else None

    def print_testcampaign(self, pr=True):
        out = datetime.strptime(self.TESTCAMPAIGN, '%Y%m').strftime('%b %Y')
        if pr:
            print '\nTESTCAMPAIGN: {0}{p}'.format(out, p=' Part {0}'.format(int_to_roman(int(self.SubSet))) if self.SubSet is not None else '')
        return out

    def get_test_campaigns(self):
        return loads(self.MainConfigParser.get('MAIN', 'test_campaigns'))

    # endregion

    def start_pbar(self, n):
        self.ProgressBar = ProgressBar(widgets=self.Widgets, maxval=n)
        self.ProgressBar.start()

    @staticmethod
    def create_colorlist():
        col_names = [kGreen, kOrange, kViolet, kYellow, kRed, kBlue, kMagenta, kAzure, kCyan, kTeal]
        colors = []
        for color in col_names:
            colors.append(color + (1 if color != 632 else -7))
        for color in col_names:
            colors.append(color + (3 if color != 800 else 9))
        return colors

    @staticmethod
    def ensure_dir(f):
        d = pth.dirname(f)
        if not pth.exists(d):
            makedirs(d)

    def get_color(self):
        self.count %= 20
        color = self.colors[self.count]
        self.count += 1
        return color

    def reset_colors(self):
        self.count = 0

    def verbose_print(self, *args):
        """
        Print command if verbose is activated.
        :param args:
        """
        if self.verbose:
            # Print each argument separately so caller doesn't need to put everything to be printed into a single string.
            for arg in args:
                print arg,
            print

    def log_info(self, msg, next_line=True):
        if self.verbose:
            t1 = time()
            t = datetime.now().strftime('%H:%M:%S')
            print 'INFO: {t} --> {msg}'.format(t=t, msg=msg),
            stdout.flush()
            if next_line:
                print
            return t1

    def add_info(self, t, msg='Done'):
        if self.verbose:
            print '{m} ({t:2.2f} s)'.format(m=msg, t=time() - t)

    @staticmethod
    def log_warning(msg):
        t = datetime.now().strftime('%H:%M:%S')
        print '{head} {t} --> {msg}'.format(t=t, msg=msg, head=colored('WARNING:', 'red'))

    @staticmethod
    def has_bit(num, bit):
        assert (num >= 0 and type(num) is int), 'num has to be non negative int'
        return bool(num & 1 << bit)

    def make_bias_string(self, bias=None):
        if bias is None:
            return self.make_bias_string(self.bias) if hasattr(self, 'bias') else ''
        pol = 'm' if bias < 0 else 'p'
        return '_{pol}{bias:04d}'.format(pol=pol, bias=int(abs(bias)))

    def make_info_string(self):
        info = ''
        if not self.MainConfigParser.getboolean('SAVE', 'short_name'):
            info = '_{dia}'.format(dia=self.diamond_name) if hasattr(self, 'diamond_name') else ''
            info += self.make_bias_string()
            info += '_{tc}'.format(tc=self.TESTCAMPAIGN)
            info = info.replace('-', '')
        return info

    def make_pickle_path(self, sub_dir, name=None, run=None, ch=None, suf=None, camp=None):
        ensure_dir(join(self.PickleDir, sub_dir))
        campaign = '{tc}{s}'.format(tc=self.TESTCAMPAIGN, s=self.generate_sub_set_str()) if camp is None else camp
        run = '_{r}'.format(r=run) if run is not None else ''
        ch = '_{c}'.format(c=ch) if ch is not None else ''
        suf = '_{s}'.format(s=suf) if suf is not None else ''
        name = '{n}_'.format(n=name) if name is not None else ''
        return '{dir}/{sdir}/{name}{tc}{run}{ch}{suf}.pickle'.format(dir=self.PickleDir, sdir=sub_dir, name=name, tc=campaign, run=run, ch=ch, suf=suf)

    def save_canvas(self, canvas, sub_dir=None, name=None, print_names=True, show=True):
        sub_dir = self.save_dir if hasattr(self, 'save_dir') and sub_dir is None else '{subdir}/'.format(subdir=sub_dir)
        canvas.Update()
        file_name = canvas.GetName() if name is None else name
        file_path = join(self.ResultsDir, sub_dir, '{typ}', file_name)
        ftypes = ['root', 'png', 'pdf', 'eps']
        out = 'Saving plots: {nam}'.format(nam=name)
        run_number = self.run_number if hasattr(self, 'run_number') else None
        run_number = 'rp{nr}'.format(nr=self.run_plan) if hasattr(self, 'run_plan') else run_number
        self.set_root_output(show)
        gROOT.ProcessLine("gErrorIgnoreLevel = kError;")
        info = self.make_info_string()
        for f in ftypes:
            ext = '.{typ}'.format(typ=f)
            if not f == 'png' and run_number is not None:
                ext = '{str}_{run}.{typ}'.format(str=info, run=run_number, typ=f)
            self.ensure_dir(file_path.format(typ=f))
            out_file = '{fname}{ext}'.format(fname=file_path, ext=ext)
            out_file = out_file.format(typ=f)
            canvas.SaveAs(out_file)
        self.save_on_kinder(canvas, file_name)
        if print_names:
            self.log_info(out)
        self.set_root_output(True)

    def save_on_kinder(self, canvas, file_name):
        if kinder_is_mounted():
            if hasattr(self, 'DiamondName'):
                if hasattr(self, 'RunPlan'):
                    rp = self.RunPlan
                    run_string = 'RunPlan{r}'.format(r=rp[1:] if rp[0] == '0' else rp)
                elif hasattr(self, 'RunNumber'):
                    run_string = str(self.RunNumber)
                else:
                    return
                path = join(get_base_dir(), 'mounts/psi/Diamonds', self.DiamondName, 'BeamTests', make_tc_str(self.generate_tc_str(), long_=False), run_string, file_name)
                canvas.SaveAs('{p}.pdf'.format(p=path))
                canvas.SaveAs('{p}.png'.format(p=path))

    def save_plots(self, savename, sub_dir=None, canvas=None, all_pads=True, both_dias=False, ind=None, prnt=True, save=True, show=True):
        """ Saves the canvas at the desired location. If no canvas is passed as argument, the active canvas will be saved. However for applications without graphical interface,
         such as in SSl terminals, it is recommended to pass the canvas to the method. """
        canvas = get_last_canvas() if canvas is None else canvas
        if canvas is None:
            return
        if ind is None:
            self.InfoLegend.draw(canvas, all_pads, both_dias, show) if hasattr(self, 'InfoLegend') else log_warning('Did not find InfoLegend class...') \
                if not any(hasattr(self, att) for att in ['RunSelections', 'CurrentGraph']) else do_nothing()
        else:
            self.collection.values()[ind].InfoLegend.draw(canvas, all_pads, both_dias, show) if hasattr(self, 'collection') else log_critical('sth went wrong...')
        canvas.Modified()
        canvas.Update()
        if save:
            try:
                self.save_canvas(canvas, sub_dir=sub_dir, name=savename, print_names=prnt, show=show)
                self.ROOTObjects.append(canvas)
            except Exception as inst:
                print log_warning('Error in save_canvas:\n{0}'.format(inst))

    def create_new_testcampaign(self):
        year = raw_input('Enter the year of the test campgaign (YYYY): ')
        month = raw_input('Enter the month of the testcampaign: ').zfill(2)
        if year + month in self.find_test_campaigns():
            print 'This test campaign already exists! --> returning'
            return
        new_tc = year + month
        new_tc_cfg = year + month + '.cfg'
        conf_dir = self.get_program_dir() + 'Configuration/'
        names = []
        old_tc_cfg = ''
        for f in glob(conf_dir + '*'):
            name = f.split('/')[-1].split('_')
            if len(name) > 1 and name[1].startswith('20') and name[0] not in names:
                if name[1] > old_tc_cfg:
                    old_tc_cfg = name[1]
                names.append(name[0])
        old_tc = old_tc_cfg.split('.')[0]
        for name in names:
            file_name = conf_dir + name + '_'
            copyfile(file_name + old_tc_cfg, file_name + new_tc_cfg)
            f = open(file_name + new_tc_cfg, 'r+')
            lines = []
            for line in f.readlines():
                print line
                print old_tc[2:], new_tc[2:], old_tc[:4] + '_' + old_tc[4:], year + '_' + month
                line = line.replace(old_tc[2:], new_tc[2:])
                old = old_tc[:4] + '_' + old_tc[4:]
                lines.append(line.replace(old, year + '_' + month))
            f.seek(0)
            f.writelines(lines)
            f.close()

    def print_elapsed_time(self, start, what='This', show=True):
        string = '{1} took {0:2.2f} seconds'.format(time() - start, what)
        self.print_banner(string) if show else self.do_nothing()
        return string

    @staticmethod
    def do_pickle(path, func, value=None, params=None, redo=False):
        if value is not None:
            f = open(path, 'w')
            pickle.dump(value, f)
            f.close()
            return value
        if file_exists(path) and not redo:
            f = open(path, 'r')
            return pickle.load(f)
        else:
            ret_val = func() if params is None else func(params)
            f = open(path, 'w')
            pickle.dump(ret_val, f)
            f.close()
            return ret_val

    @staticmethod
    def set_root_output(status=True):
        if status:
            gROOT.SetBatch(0)
            gROOT.ProcessLine("gErrorIgnoreLevel = 0;")
        else:
            gROOT.SetBatch(1)
            gROOT.ProcessLine("gErrorIgnoreLevel = kError;")

    @staticmethod
    def make_tgrapherrors(name, title, color=1, marker=20, marker_size=1, width=1, asym_err=False, style=1, x=None, y=None, ex=None, ey=None):
        x = list(x) if type(x) == ndarray else x
        if x is None:
            gr = TGraphErrors() if not asym_err else TGraphAsymmErrors()
        else:
            gr = TGraphErrors(*make_graph_args(x, y, ex, ey)) if not asym_err else TGraphAsymmErrors(*make_graph_args(x, y, ex, ey))
        gr.SetTitle(title)
        gr.SetName(name)
        gr.SetMarkerStyle(marker)
        gr.SetMarkerColor(color)
        gr.SetLineColor(color)
        gr.SetMarkerSize(marker_size)
        gr.SetLineWidth(width)
        gr.SetLineStyle(style)
        return gr

    def draw_axis(self, x1, x2, y1, y2, title, name='ax', col=1, width=1, off=.15, tit_size=.035, lab_size=0.035, line=False, opt='+SU', tick_size=0.03, l_off=.01):
        range_ = [y1, y2] if x1 == x2 else [x1, x2]
        a = TGaxis(x1, y1, x2, y2, range_[0], range_[1], 510, opt)
        a.SetName(name)
        a.SetLineColor(col)
        a.SetLineWidth(width)
        a.SetLabelSize(lab_size if not line else 0)
        a.SetTitleSize(tit_size)
        a.SetTitleOffset(off)
        a.SetTitle(title)
        a.SetTitleColor(col)
        a.SetLabelColor(col)
        a.SetLabelFont(42)
        a.SetTitleFont(42)
        a.SetTickSize(tick_size if not line else 0)
        a.SetTickLength(tick_size if not line else 0)
        a.SetNdivisions(0) if line else self.do_nothing()
        a.SetLabelOffset(l_off)
        a.Draw()
        self.ROOTObjects.append(a)
        return a

    def draw_y_axis(self, x, ymin, ymax, tit, name='ax', col=1, off=1, w=1, opt='+L', tit_size=.035, lab_size=0.035, tick_size=0.03, l_off=.01, line=False):
        return self.draw_axis(x, x, ymin, ymax, tit, name=name, col=col, off=off, opt=opt, width=w, tit_size=tit_size, lab_size=lab_size, tick_size=tick_size, l_off=l_off, line=line)

    def draw_x_axis(self, y, xmin, xmax, tit, col=1, off=1, w=1, opt='+L', tit_size=.035, lab_size=0.035, tick_size=0.03, l_off=.01, line=False):
        return self.draw_axis(xmin, xmax, y, y, tit, col=col, off=off, opt=opt, width=w, tit_size=tit_size, lab_size=lab_size, tick_size=tick_size, l_off=l_off, line=line)

    def draw_line(self, x1, x2, y1, y2, color=1, width=1, style=1, name='li'):
        l = TCutG(name, 2, array([x1, x2], 'd'), array([y1, y2], 'd'))
        l.SetLineColor(color)
        l.SetLineWidth(width)
        l.SetLineStyle(style)
        l.Draw('same')
        self.ROOTObjects.append(l)
        return l

    def draw_tline(self, x1, x2, y1, y2, color=1, width=1, style=1):
        l = TLine(x1, y1, x2, y2)
        l.SetLineColor(color)
        l.SetLineWidth(width)
        l.SetLineStyle(style)
        l.Draw()
        self.ROOTObjects.append(l)
        return l

    def draw_box(self, x1, y1, x2, y2, color=1, width=1, style=1, fillstyle=None, name='box', show=True):
        l = TCutG(name, 5, array([x1, x1, x2, x2, x1], 'd'), array([y1, y2, y2, y1, y1], 'd'))
        l.SetLineColor(color)
        l.SetFillColor(color)
        l.SetLineWidth(width)
        l.SetLineStyle(style)
        l.SetFillStyle(fillstyle) if fillstyle is not None else do_nothing()
        if show:
            l.Draw('same')
        self.ROOTObjects.append(l)
        return l

    def draw_vertical_line(self, x, ymin, ymax, color=1, w=1, style=1, name='li', tline=False):
        return self.draw_line(x, x, ymin, ymax, color, w, style, name) if not tline else self.draw_tline(x, x, ymin, ymax, color, w, style)

    def draw_horizontal_line(self, y, xmin, xmax, color=1, w=1, style=1, name='li', tline=False):
        return self.draw_line(xmin, xmax, y, y, color, w, style, name) if not tline else self.draw_tline(xmin, xmax, y, y, color, w, style)

    def make_legend(self, x1=.65, y2=.88, nentries=2, scale=1, name='l', y1=None, felix=False, margin=.25, x2=None):
        x2 = .95 if x2 is None else x2
        y1 = y2 - nentries * .05 * scale if y1 is None else y1
        l = TLegend(x1, y1, x2, y2)
        l.SetName(name)
        l.SetTextFont(42)
        l.SetTextSize(0.03 * scale)
        l.SetMargin(margin)
        if self.Felix or felix:
            l.SetLineWidth(2)
            l.SetBorderSize(0)
            l.SetFillColor(0)
            l.SetFillStyle(0)
            l.SetTextAlign(12)
        return l

    def format_histo(self, histo, name='', title='', x_tit='', y_tit='', z_tit='', marker=20, color=1, markersize=1, x_off=None, y_off=None, z_off=None, lw=1,
                     fill_color=None, fill_style=None, stats=True, tit_size=.04, lab_size=.04, l_off_y=None, draw_first=False, x_range=None, y_range=None, z_range=None,
                     do_marker=True, style=None, ndivx=None, ndivy=None, ncont=None, tick_size=None, t_ax_off=None):
        h = histo
        if draw_first:
            self.set_root_output(False)
            h.Draw('a')
            self.set_root_output(True)
        h.SetTitle(title) if title else h.SetTitle(h.GetTitle())
        h.SetName(name) if name else h.SetName(h.GetName())
        try:
            h.SetStats(stats)
        except AttributeError or ReferenceError:
            pass
        # markers
        try:
            if do_marker:
                h.SetMarkerStyle(marker) if marker is not None else do_nothing()
                h.SetMarkerColor(color) if color is not None else do_nothing()
                h.SetMarkerSize(markersize) if markersize is not None else do_nothing()
        except AttributeError or ReferenceError:
            pass
        # lines/fill
        try:
            h.SetLineColor(color) if color is not None else h.SetLineColor(h.GetLineColor())
            h.SetFillColor(fill_color) if fill_color is not None else do_nothing()
            h.SetFillStyle(fill_style) if fill_style is not None else do_nothing()
            h.SetLineWidth(lw)
            h.SetFillStyle(style) if style is not None else do_nothing()
            h.SetContour(ncont) if ncont is not None else do_nothing()
        except AttributeError or ReferenceError:
            pass
        # axis titles
        try:
            x_tit = untitle(x_tit) if self.Felix else x_tit
            y_tit = untitle(y_tit) if self.Felix else y_tit
            z_tit = untitle(z_tit) if self.Felix else z_tit
            x_axis = h.GetXaxis()
            if x_axis:
                x_axis.SetTitle(x_tit) if x_tit else h.GetXaxis().GetTitle()
                x_axis.SetTitleOffset(x_off) if x_off is not None else do_nothing()
                x_axis.SetTitleSize(tit_size)
                x_axis.SetLabelSize(lab_size)
                x_axis.SetRangeUser(x_range[0], x_range[1]) if x_range is not None else do_nothing()
                x_axis.SetNdivisions(ndivx) if ndivx is not None else do_nothing()
                do(x_axis.SetTickSize, tick_size)
            y_axis = h.GetYaxis()
            if y_axis:
                y_axis.SetTitle(y_tit) if y_tit else y_axis.GetTitle()
                y_axis.SetTitleOffset(y_off) if y_off is not None else do_nothing()
                y_axis.SetTitleSize(tit_size)
                y_axis.SetLabelSize(lab_size)
                do(y_axis.SetLabelOffset, l_off_y)
                y_axis.SetRangeUser(y_range[0], y_range[1]) if y_range is not None else do_nothing()
                do(y_axis.SetNdivisions, ndivy)
            z_axis = h.GetZaxis()
            if z_axis:
                z_axis.SetTitle(z_tit) if z_tit else h.GetZaxis().GetTitle()
                z_axis.SetTitleOffset(z_off) if z_off is not None else do_nothing()
                z_axis.SetTitleSize(tit_size)
                z_axis.SetLabelSize(lab_size)
                z_axis.SetRangeUser(z_range[0], z_range[1]) if z_range is not None else do_nothing()
        except AttributeError or ReferenceError:
            pass
        set_time_axis(h, off=t_ax_off) if t_ax_off is not None else do_nothing()

    def save_histo(self, histo, save_name='test', show=True, sub_dir=None, lm=.1, rm=.03, bm=.15, tm=None, draw_opt='', x_fac=None, y_fac=None, all_pads=True,
                   l=None, logy=False, logx=False, logz=False, canvas=None, gridx=False, gridy=False, save=True, both_dias=False, ind=None, prnt=True, phi=None, theta=None):
        if tm is None:
            tm = .1 if self.MainConfigParser.getboolean('SAVE', 'activate_title') else .03
        x = self.Res if x_fac is None else int(x_fac * self.Res)
        y = self.Res if y_fac is None else int(y_fac * self.Res)
        h = histo
        self.set_root_output(show)
        c = TCanvas('c_{0}'.format(h.GetName()), h.GetTitle().split(';')[0], x, y) if canvas is None else canvas
        c.SetMargin(lm, rm, bm, tm)
        c.SetLogx() if logx else self.do_nothing()
        c.SetLogy() if logy else self.do_nothing()
        c.SetLogz() if logz else self.do_nothing()
        c.SetGridx() if gridx else self.do_nothing()
        c.SetGridy() if gridy else self.do_nothing()
        c.SetPhi(phi) if phi is not None else do_nothing()
        c.SetTheta(theta) if theta is not None else do_nothing()
        h.Draw(draw_opt)
        if l is not None:
            l = [l] if type(l) is not list else l
            for i in l:
                i.Draw()
        self.save_plots(save_name, sub_dir=sub_dir, both_dias=both_dias, all_pads=all_pads, ind=ind, prnt=prnt, save=save, show=show)
        self.set_root_output(True)
        lst = [c, h, l] if l is not None else [c, h]
        self.ROOTObjects.append(lst)
        return c

    def draw_histo(self, histo, save_name='', show=True, sub_dir=None, lm=.1, rm=.03, bm=.15, tm=.1, draw_opt='', x=None, y=None, all_pads=True,
                   l=None, logy=False, logx=False, logz=False, canvas=None, gridy=False, gridx=False, both_dias=False, prnt=True, phi=None, theta=None, ind=None):
        return self.save_histo(histo, save_name, show, sub_dir, lm, rm, bm, tm, draw_opt, x, y, all_pads, l, logy, logx, logz, canvas, gridx, gridy, False, both_dias, ind, prnt, phi, theta)

    def draw_tlatex(self, x, y, text, align=20, color=1, size=.05, angle=None, ndc=False):
        l = TLatex(x, y, text)
        l.SetName(text)
        l.SetTextAlign(align)
        l.SetTextColor(color)
        l.SetTextSize(size)
        do(l.SetTextAngle, angle)
        l.SetNDC() if ndc else do_nothing()
        l.Draw()
        self.ROOTObjects.append(l)
        return l

    def draw_arrow(self, x1, x2, y1, y2, col=1, width=1, opt='<|', size=.005):
        ar = TArrow(x1, y1, x2, y2, size, opt)
        ar.SetLineWidth(width)
        ar.SetLineColor(col)
        ar.SetFillColor(col)
        ar.Draw()
        self.ROOTObjects.append(ar)

    def draw_preliminary(self, canvas=None):
        c = get_last_canvas() if canvas is None else canvas
        self.draw_tlatex((1 - c.GetRightMargin() + c.GetLeftMargin()) / 2, .5, 'Preliminary', align=22, color=19, size=.17, angle=30, ndc=True)
        make_transparent(c)
        for obj in c.GetListOfPrimitives():
            if obj.IsA().GetName() in ['TH1F', 'TH2F', 'TGraph', 'TGraphErrors']:
                obj.Draw('same')
        c.RedrawAxis()

    @staticmethod
    def calc_fwhm(histo):
        h = histo
        max_ = h.GetMaximum()
        bin1 = h.FindFirstBinAbove(max_ / 2)
        bin2 = h.FindLastBinAbove(max_ / 2)
        fwhm = h.GetBinCenter(bin2) - h.GetBinCenter(bin1)
        return fwhm

    @staticmethod
    def get_program_dir():
        return dirname(dirname(__file__))

    @staticmethod
    def adj_length(value):
        string = str(value)
        num = len(string) / 4 * 4 + 4
        return string.ljust(num)

    @staticmethod
    def fit_fwhm(histo, fitfunc='gaus', do_fwhm=True, draw=False):
        h = histo
        if do_fwhm:
            peak_pos = h.GetBinCenter(h.GetMaximumBin())
            bin1 = h.FindFirstBinAbove(h.GetMaximum() / 2)
            bin2 = h.FindLastBinAbove(h.GetMaximum() / 2)
            fwhm = h.GetBinLowEdge(bin2 + 2) - h.GetBinLowEdge(bin1 - 1)
            option = 'qs' if draw else 'qs0'
            fit = h.Fit(fitfunc, option, '', peak_pos - fwhm / 2, peak_pos + fwhm / 2)
        else:
            fit = h.Fit(fitfunc, 'qs')
        return fit

    @staticmethod
    def del_rootobj(obj):
        if obj is None:
            return
        try:
            if obj.IsA().GetName() != 'TCanvas':
                obj.Delete()
        except AttributeError:
            pass

    @staticmethod
    def normalise_histo(histo, to100=False):
        h = histo
        fac = 100 if to100 else 1
        h.Scale(fac / h.Integral(1, h.GetNbinsX()))
        return h

    @staticmethod
    def do_nothing():
        pass

    @staticmethod
    def triple_gauss_fit(histo, show=True):
        gROOT.ProcessLine("gErrorIgnoreLevel = kError;")
        h = histo
        fit = TF1('fit', 'gaus(0) + gaus(3) + gaus(6)', h.GetXaxis().GetXmin(), h.GetXaxis().GetXmax())
        s = TSpectrum(3)
        n = s.Search(h, 2)
        y = s.GetPositionY()[0], s.GetPositionY()[1] if n == 2 else s.GetPositionY()[2]
        x = s.GetPositionX()[0], s.GetPositionX()[1] if n == 2 else s.GetPositionX()[2]
        for i, par in enumerate([y[1], x[1], 10, y[0], x[0], 5, 10, x[0] + 10, 5]):
            fit.SetParameter(i, par)
        fit.SetParLimits(7, x[0] + 5, x[1] - 20)
        for i in xrange(1):
            h.Fit(fit, 'qs{0}'.format('' if show else '0'), '', -50, x[1])
        gROOT.ProcessLine("gErrorIgnoreLevel = 0;")
        return fit

    @staticmethod
    def make_class_from_instance(instance):
        copy = deepcopy(instance.__dict__)
        instance_factory = type('instance_factory', (instance.__class__, ), {})
        instance_factory.__init__ = lambda self, *args, **kwargs: self.__dict__.update(copy)
        return instance_factory

    @staticmethod
    def find_graph_margins(graphs):
        extrema = [max([TMath.MaxElement(gr.GetN(), gr.GetY()) for gr in graphs]), min([TMath.MinElement(gr.GetN(), gr.GetY()) for gr in graphs])]
        return [extrema[1] - (extrema[0] - extrema[1]) * .1, extrema[0] + (extrema[0] - extrema[1]) * .1]

    @staticmethod
    def print_banner(msg, symbol='='):
        print '\n{delim}\n{msg}\n{delim}\n'.format(delim=len(str(msg)) * symbol, msg=msg)

    def save_combined_pulse_heights(self, mg, mg1, l, mg_y, show=True, name=None, pulser_leg=None,
                                    x_range=None, y_range=None, rel_y_range=None, draw_objects=None):
        self.set_root_output(show)
        c = TCanvas('c', 'c', int(self.Res * 10 / 11.), self.Res)
        make_transparent(c)
        bm = .11
        scale = 1.5
        pm = bm + (1 - bm - .1) / 5.

        # set unified x-range:
        mg1.GetXaxis().SetLimits(5, 3e4) if x_range is None else do_nothing()
        mg.GetXaxis().SetLimits(5, 3e4) if x_range is None else do_nothing()

        # bottom pad with 20%
        p0 = self.draw_tpad('p0', 'p0', pos=[0, 0, 1, pm], margins=[.14, .03, bm / pm, 0], transparent=True, logx=True, gridy=True)
        scale_multigraph(mg1)
        rel_y_range = [.7, 1.3] if rel_y_range is None else rel_y_range
        self.format_histo(mg1, title='', y_range=rel_y_range, y_tit='Rel. ph [au]' if not scale > 1 else ' ', y_off=66, tit_size=.1 * scale, x_off=99, lab_size=.1 * scale)
        mg1.GetYaxis().SetNdivisions(3)
        hide_axis(mg1.GetXaxis())
        mg1.Draw('alp')
        x_range = [mg1.GetXaxis().GetXmin(), mg1.GetXaxis().GetXmax()] if x_range is None else x_range
        self.draw_x_axis(1.3, x_range[0], x_range[1], mg1.GetXaxis().GetTitle() + ' ', opt='SG+-=', tit_size=.1, lab_size=.1 * scale, off=99, tick_size=.1, l_off=0)
        c.cd()

        # top pad with zero suppression
        self.draw_tpad('p1', 'p1', pos=[0, pm, 1, 1], margins=[.14, .03, 0, .1], transparent=True, logx=True)
        mg.Draw('alp')
        hide_axis(mg.GetXaxis())
        if pulser_leg:
            pulser_leg()
        if y_range:
            mg.SetMinimum(y_range[0])
            mg.SetMaximum(y_range[1])
        self.format_histo(mg, tit_size=.04 * scale, y_off=1.75 / scale, lab_size=.04 * scale)
        self.draw_x_axis(mg_y, x_range[0], x_range[1], mg1.GetXaxis().GetTitle() + ' ', opt='SG=', tit_size=.035 * scale, lab_size=0, off=1, l_off=99)
        move_legend(l, .17, .03)
        l.Draw()
        if draw_objects is not None:
            for obj, opt in draw_objects:
                obj.Draw(opt)

        if hasattr(self, 'InfoLegend'):
            run_info = self.InfoLegend.draw(p0, all_pads=False, show=show)
            scale_legend(run_info[0], txt_size=.09, height=0.098 / pm)
            run_info[1].SetTextSize(.05)

        for obj in p0.GetListOfPrimitives():
            if obj.GetName() == 'title':
                obj.SetTextColor(0)
        self.save_canvas(c, name='CombinedPulseHeights' if name is None else name, show=show)

        self.ROOTObjects.append([c, draw_objects])
        self.set_root_output(True)

    def draw_tpad(self, name, tit='', pos=None, fill_col=0, gridx=None, gridy=None, margins=None, transparent=False, logy=None, logx=None, logz=None):
        margins = [.1, .1, .1, .1] if margins is None else margins
        pos = [0, 0, 1, 1] if pos is None else pos
        p = TPad(name, tit, *pos)
        p.SetFillColor(fill_col)
        p.SetMargin(*margins)
        do([p.SetLogx, p.SetLogy, p.SetLogz], [logx, logy, logz])
        do([p.SetGridx, p.SetGridy], [gridx, gridy])
        make_transparent(p) if transparent else do_nothing()
        p.Draw()
        p.cd()
        self.ROOTObjects.append(p)
        return p

    def make_canvas(self, name='c', title='c', x=1., y=1., show=True, logx=None, logy=None, logz=None, gridx=None, gridy=None, transp=None):
        self.set_root_output(show)
        c = TCanvas(name, title, int(x * self.Res), int(y * self.Res))
        do([c.SetLogx, c.SetLogy, c.SetLogz], [logx, logy, logz])
        do([c.SetGridx, c.SetGridy], [gridx, gridy])
        do(make_transparent, c, transp)
        self.ROOTObjects.append(c)
        return c


if __name__ == "__main__":
    z = Elementary()
