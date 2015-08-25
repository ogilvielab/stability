from __future__ import division, print_function
import sys
import os.path
import itertools as it

# from http://matplotlib.org/examples/user_interfaces/embedding_in_qt4.html 
from matplotlib.backends import qt_compat
use_pyside = qt_compat.QT_API == qt_compat.QT_API_PYSIDE
if use_pyside:
    from PySide import QtGui, QtCore
else:
    from PyQt4 import QtGui, QtCore

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from scipy.stats import variation
from scipy.io import loadmat
from numpy import squeeze, zeros_like, mean, diff, std, float64, array
from winspec import SpeFile

def load_wavelengths(path):
    '''load a pre-calibrated wavengths file generated with the
    ```manual_calibration``` script in MATLAB.
    '''
    calib_file = str(path)
    with open(calib_file, 'rb') as f:
        calib = loadmat(f)
        wl = squeeze(calib['saved_wavelengths'])
    return wl

class Analysis(object):
	frames_to_skip = 10
	ROI = 0
	
	def __init__(self, file, wavelengths=None):
                self.file_name = str(file)
		self.data_file = SpeFile(str(file))
                self.use_wavelength_axis = True if wavelengths else False

                if self.use_wavelength_axis:
                    self.setup_wavelength_axis(wavelengths)

        def setup_wavelength_axis(self, wavelengths):
            try:
                wl = load_wavelengths(wavelengths)
                self.wavelengths = wl
                self.use_wavelength_axis = True
            except Exception as e:
                self.wavelengths = None
                self.use_wavelength_axis = False

                raise e

	def run(self):
		self.data = array(self.data_file.data[self.frames_to_skip:,:,self.ROI], dtype=float64)
		self.variation = variation(self.data)
		self.mean = mean(self.data, axis=0)
		self.shot_to_shot = std(diff(self.data, axis=0), axis=0)/self.mean
		
class MainWindow(QtGui.QMainWindow):
	def __init__(self, parent=None):
		QtGui.QMainWindow.__init__(self, parent)
		self.setWindowTitle('Stability Analysis')
		self.create_main_frame()
		
		self.analysis = None
                self.data_filename = None
                self.wavelength_filename = None
		
	def create_main_frame(self):
		self.main_frame = QtGui.QWidget()
		self.fig = Figure((5.0, 4.0))
		self.canvas = FigureCanvas(self.fig)
		
		self.axes = (self.fig.add_subplot(311), 
                             self.fig.add_subplot(312),
                             self.fig.add_subplot(313))
		
                self.fig.subplots_adjust(
                        left=0.1, 
                        right=0.95, 
                        top=0.95,
                        bottom=0.05, 
                        hspace=0.25)

		self.file_btn = QtGui.QPushButton("Cho&ose file")
		self.file_btn.clicked.connect(self.on_choose_file)
		
		self.file_name_lb = QtGui.QLabel("Not selected")
		
                '''
		self.wlaxis_btn = QtGui.QPushButton("Choose &wavelength axis")
		self.wlaxis_btn.clicked.connect(self.on_choose_wavelength_axis)
                self.wlaxis_btn.setEnabled(False)
                '''

		self.wlaxis_lb = QtGui.QLabel("Wavelength calibration file")
                self.wlaxis_lb.setFixedSize(200, 20)

		self.wlaxis_name_lb = QtGui.QLabel("Not selected")
		
		grid = QtGui.QGridLayout()
		
		grid.addWidget(self.file_btn, 1, 1)
		grid.addWidget(self.file_name_lb, 1, 2)
		grid.addWidget(self.wlaxis_lb, 2, 1)
		grid.addWidget(self.wlaxis_name_lb, 2, 2)
		
		hbox = QtGui.QVBoxLayout()
		hbox.addWidget(self.canvas)
		hbox.addLayout(grid)
		
		self.main_frame.setLayout(hbox)
		self.setCentralWidget(self.main_frame)

	def on_choose_file(self):
            if self.data_filename == None:
                dir = ''
            else:
                dir, tail = os.path.split(str(self.data_filename))

            try:
                    file = QtGui.QFileDialog.getOpenFileName(self, 
                            "Open SPE file", dir, "WinSpec files (*.SPE)")
                    self.data_filename = file
                    self.file_name_lb.setText(file)
                    self.on_choose_wavelength_axis()
                    self.on_analyze()
            except Exception as e:
                    QtGui.QMessageBox.critical(self, "Exception occured", str(e))
		
	def on_analyze(self):
            self.analysis = Analysis(self.data_filename,
                    self.wavelength_filename)
            self.analysis.run()
            self.on_draw()
            self.on_save()
	
	def on_draw(self):
		ax1, ax2, ax3 = self.axes
		ax1.clear(), ax2.clear(), ax3.clear()
		
		if self.analysis:
                    if self.analysis.use_wavelength_axis:
                        wl = self.analysis.wavelengths
                    else:
                        wl = array(range(1340)) 

                    ax1.plot(wl, self.analysis.mean, color='blue', linewidth=3)
                    ax1.set_title('Mean spectrum')
                    ax1.set_ylabel('Counts')
                    
                    ax2.plot(wl, self.analysis.variation*100, color='red',
                            linewidth=3)
                    ax2.set_title('"Long-Term" Variation')
                    ax2.set_ylabel('Percent')
                    
                    ax3.plot(wl, self.analysis.shot_to_shot * 1e3,
                            color='green', linewidth=3)
                    ax3.set_ylabel('mAU')
                    ax3.set_title('Shot-to-Shot Variation')
                    
                    if self.analysis.use_wavelength_axis:
                        ax3.set_xlabel('wavelength / nm') 
                    else:
                        ax3.set_xlabel('pixels')
			
		ax1.grid(), ax2.grid(), ax3.grid()
		self.canvas.draw()

        def on_save(self):
            # get same folder that the stability trace is in
            base, ext = os.path.splitext(str(self.data_filename))
            pdf_name = base + '.pdf'

            self.fig.savefig(pdf_name, format='pdf', dpi=150)

        def on_choose_wavelength_axis(self):
            if self.wavelength_filename == None:
                if self.data_filename == None:
                    dir = ''
                else:
                    dir, tail = os.path.split(str(self.data_filename))

		try:
                    file = QtGui.QFileDialog.getOpenFileName(self, 
                        "Open calibration file", dir, "Calibration files (*.mat)")
                    self.wavelength_filename = file
                    self.wlaxis_name_lb.setText(file)
		except Exception as e:
                    QtGui.QMessageBox.critical(self, "Exception occured", str(e))
            else:
                pass
			
def main():
	app = QtGui.QApplication(sys.argv)
	window = MainWindow()
	window.resize(800, 800)
	window.show()
	app.exec_()
	
if __name__ == "__main__":
    main()
