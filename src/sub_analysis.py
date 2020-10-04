# --------------------------------------------------------
#       sub analysis class
# created on Oct 4th 2020 by M. Reichmann (remichae@phys.ethz.ch)
# --------------------------------------------------------

from analysis import Analysis


class SubAnanlysis(Analysis):
    """ small module to create all required fields for the subanalyses. """

    def __init__(self, analysis, results_dir='', pickle_dir=''):
        super().__init__(analysis.TCString, results_dir, pickle_dir)

        self.Ana = analysis
        self.Run = analysis.Run
        self.Tree = analysis.Tree
        self.Bins = analysis.Bins
        self.Cut = analysis.Cut

    def get_root_vec(self, n=0, ind=0, dtype=None, var=None, cut=''):
        return self.Run.get_root_vec(n, ind, dtype, var, cut)
